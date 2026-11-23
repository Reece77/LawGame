"""Seats (spec 9.1-9.2; PT-M8): who may sit, seat scores, effects, and the player's seat
actions (appoint, replace, vacate; authority and guardrails; the exco term).

Ported from backend/tst/sim/org/executives.py and formulas.py (seat score, effect) @ 121d318a
(Tech Startup Tycoon); changed: Partner Track's seats come from seats.yaml with a stage each
(spec 3) instead of one stage for all; partner seats need an equity partner (an income partner
too where the seat says so), business-services seats a business-services person at
`seats.bs_min_level` or above, or a partner; the managing partner's seat is the player's (or
the partnership's MP); a practice group leader's seat is PT-M2's unit leader; the executive
committee has member slots and its e is the members' mean with missing members counted vacant;
appointment moves a partner holder's confidence by their ambition (not a salary change).

The seat score `s` = sum of weight x the holder's TRUE skills (and integrity, a personality
trait), and `e = clamp((s - 10) / 8, -0.5, 1)`; a seat vacant from its stage has
`e = -0.5`; before its stage a seat has no effect (e = 0). Only the engine reads `s` and `e`:
the API shows the holder's revealed ranges and a fit band from the DISPLAYED score (the
revealed midpoints), never `s` (TST 18.8, 24.4).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Final, Literal

from ptk.sim.data_models import BUSINESS_SERVICES_LEVELS, PARTNER_LEVELS, Balance, GameData
from ptk.sim.errors import (
    InvalidActionError,
    NotManagingPartnerError,
    SeatRuleError,
    UnknownSeatError,
)
from ptk.sim.hiring.actions import spend_energy
from ptk.sim.log import LogItem, inbox_item
from ptk.sim.org import actions as org_actions
from ptk.sim.org.seat_data import SeatDef
from ptk.sim.org.seat_models import (
    EXCO,
    MP,
    PGL,
    FirmLeadership,
    LeadershipState,
    SeatAuthority,
    SeatHolder,
)
from ptk.sim.people.models import Person
from ptk.sim.people.reveal import revealed_range
from ptk.sim.state import GameState

type FitBand = Literal["weak", "fair", "good", "strong", "unknown"]
FIT_BANDS: Final[tuple[FitBand, ...]] = ("weak", "fair", "good", "strong")
SINGLE_SLOT: Final = 0


# --- State helpers ----------------------------------------------------------------------------


def with_leadership(state: GameState, leadership: LeadershipState) -> GameState:
    return replace(state, leadership=leadership)


def _sorted_holders(holders: list[SeatHolder]) -> tuple[SeatHolder, ...]:
    return tuple(sorted(holders, key=lambda h: (h.firm_id, h.seat, h.slot)))


def set_holder(
    state: GameState, firm_id: int, seat: str, slot: int, person_id: int | None
) -> GameState:
    ls = state.leadership
    rest = [
        h for h in ls.holders if not (h.firm_id == firm_id and h.seat == seat and h.slot == slot)
    ]
    if person_id is not None:
        rest.append(SeatHolder(firm_id, seat, slot, person_id, state.turn))
    return with_leadership(state, replace(ls, holders=_sorted_holders(rest)))


def with_authority(state: GameState, authority: SeatAuthority) -> GameState:
    ls = state.leadership
    key = (authority.firm_id, authority.seat, authority.slot)
    rest = [a for a in ls.authorities if (a.firm_id, a.seat, a.slot) != key]
    merged = sorted([*rest, authority], key=lambda a: (a.firm_id, a.seat, a.slot))
    return with_leadership(state, replace(ls, authorities=tuple(merged)))


def with_firm_leadership(state: GameState, record: FirmLeadership) -> GameState:
    ls = state.leadership
    rest = [f for f in ls.firms if f.firm_id != record.firm_id]
    merged = sorted([*rest, record], key=lambda f: f.firm_id)
    return with_leadership(state, replace(ls, firms=tuple(merged)))


# --- Who sits ---------------------------------------------------------------------------------


def seat_index(data: GameData, seat: str) -> int:
    """The seat's position in seats.yaml (the `seat_act` stream's key)."""
    for i, s in enumerate(data.seats.seats):
        if s.key == seat:
            return i
    raise UnknownSeatError(f"no seat {seat!r}")


def seat_def(data: GameData, seat: str) -> SeatDef:
    try:
        return data.seat(seat)
    except KeyError as exc:
        raise UnknownSeatError(f"no seat {seat!r}") from exc


def lawyer_count(state: GameState, firm_id: int, data: GameData) -> int:
    from ptk.sim.org.rules import lawyer_count as count

    return count(state, firm_id, data)


def in_play(state: GameState, firm_id: int, seat: SeatDef) -> bool:
    """Seats are the player's firm's (rivals have none, PT-M5), from the seat's stage."""
    firm = state.firm(firm_id)
    return firm.is_player and firm.stage >= seat.stage


def exco_max(state: GameState, firm_id: int, balance: Balance) -> int:
    stage = state.firm(firm_id).stage
    sizes = balance.seats.exco.max_by_stage
    return max((n for s, n in sizes.items() if s <= stage), default=0)


def slots(state: GameState, firm_id: int, seat: SeatDef, balance: Balance) -> tuple[int, ...]:
    """The seat's slots: 0; each active practice group's unit id; the committee's 1..max."""
    match seat.slots:
        case "one":
            return (SINGLE_SLOT,)
        case "per_group":
            return tuple(u.id for u in state.org.firm_units(firm_id) if u.kind == "practice_group")
        case "committee":
            return tuple(range(1, exco_max(state, firm_id, balance) + 1))
        case _:
            # per_office (PT-M11): from a second office, each office's (the home office is 0)
            offices = state.geo.firm_offices(firm_id)
            return (0, *(o.id for o in offices)) if offices else ()


def managing_partner(state: GameState, firm_id: int) -> int | None:
    fp = state.partnership.of(firm_id)
    if fp is not None and fp.mp_id is not None:
        return fp.mp_id
    return state.founder_of(firm_id)


def holder_of(state: GameState, firm_id: int, seat: str, slot: int = SINGLE_SLOT) -> int | None:
    """Who sits: the MP for the MP's seat, the unit leader for a group, else the record."""
    if seat == MP:
        return managing_partner(state, firm_id)
    if seat == PGL:
        unit = state.org.unit(slot)
        if unit is None or unit.firm_id != firm_id or unit.status != "active":
            return None
        return unit.leader_id
    h = state.leadership.holder(firm_id, seat, slot)
    return h.person_id if h is not None else None


def ineligible_reason(
    state: GameState, firm_id: int, person_id: int, seat: SeatDef, balance: Balance
) -> str | None:
    """Why the person may not hold the seat, or None (spec 9.1's Who column)."""
    e = state.employment_of(person_id)
    if e is None or e.firm_id != firm_id or e.status != "active":
        return "not on the firm's active staff"
    person = state.person(person_id)
    level = person.level
    if seat.who == "player":
        return None if person_id == managing_partner(state, firm_id) else "the MP's own seat"
    if person_id == managing_partner(state, firm_id):
        return "the managing partner holds the firm's own seat"
    partner_levels = PARTNER_LEVELS if seat.income else frozenset({"equity_partner"})
    if seat.who == "partner":
        if level not in partner_levels:
            return "needs an equity partner" if not seat.income else "needs a partner"
        return None
    if level in PARTNER_LEVELS:
        return None
    minimum = balance.seats.bs_min_level
    allowed = BUSINESS_SERVICES_LEVELS[BUSINESS_SERVICES_LEVELS.index(minimum) :]
    if level not in allowed:
        return f"needs a business-services {minimum} or above, or a partner"
    return None


def seated_holder(
    state: GameState, firm_id: int, seat: SeatDef, slot: int, balance: Balance
) -> int | None:
    """The holder if they are still eligible (left, demoted or poached: vacant)."""
    pid = holder_of(state, firm_id, seat.key, slot)
    if pid is None or ineligible_reason(state, firm_id, pid, seat, balance) is not None:
        return None
    return pid


# --- Scores and effects -------------------------------------------------------------------------


def _attr(person: Person, key: str) -> float:
    return person.skills[key] if key in person.skills else person.personality[key]


def true_score(person: Person, seat: SeatDef) -> float:
    """s from TRUE skills (and integrity): engine-only, never shown (TST 18.8)."""
    return sum(w * _attr(person, k) for k, w in seat.weights.items())


def displayed_score(
    state: GameState, firm_id: int, person_id: int, seat: SeatDef, balance: Balance
) -> float:
    """s from the firm's displayed ranges' midpoints: what the player can judge."""
    reveal = state.reveal(firm_id, person_id)
    if reveal is None:
        return balance.seats.score_mid
    person = state.person(person_id)
    total = 0.0
    for key, w in seat.weights.items():
        lo, hi = revealed_range(person, reveal, key)
        total += w * (lo + hi) / 2
    return total


def fit_band(score: float, balance: Balance) -> FitBand:
    band: FitBand = "weak"
    for edge, name in zip(balance.seats.fit_bands, FIT_BANDS[1:], strict=True):
        if score >= edge:
            band = name
    return band


def effect_of_score(score: float, balance: Balance) -> float:
    """e = clamp((s - 10) / 8, -0.5, 1) (TST 18.3)."""
    sb = balance.seats
    lo, hi = sb.effect_range
    return min(hi, max(lo, (score - sb.score_mid) / sb.score_span))


def holder_effect(
    state: GameState, firm_id: int, seat: SeatDef, slot: int, balance: Balance
) -> float:
    pid = seated_holder(state, firm_id, seat, slot, balance)
    if pid is None:
        return balance.seats.vacant_effect
    return effect_of_score(true_score(state.person(pid), seat), balance)


def effect(
    state: GameState,
    firm_id: int,
    seat_key: str,
    balance: Balance,
    data: GameData,
    slot: int | None = None,
) -> float:
    """The spec's e for one seat of a firm (-0.5..1): 0 before the seat's stage. The
    executive committee's is its members' mean, each missing member up to
    seats.exco.min_members counting vacant. A group's (slot = its unit id): 0 if the unit is
    not an active practice group."""
    seat = seat_def(data, seat_key)
    if not in_play(state, firm_id, seat):
        return 0.0
    if seat.slots == "committee":
        values = [
            effect_of_score(true_score(state.person(pid), seat), balance)
            for s in slots(state, firm_id, seat, balance)
            if (pid := seated_holder(state, firm_id, seat, s, balance)) is not None
        ]
        missing = max(0, balance.seats.exco.min_members - len(values))
        values += [balance.seats.vacant_effect] * missing
        return sum(values) / len(values) if values else 0.0
    if seat.slots == "per_group":
        if slot is None or slot not in slots(state, firm_id, seat, balance):
            return 0.0
        return holder_effect(state, firm_id, seat, slot, balance)
    if seat.slots == "per_office":  # PT-M11: the office's managing partner
        if slot is None or slot not in slots(state, firm_id, seat, balance):
            return 0.0
        return holder_effect(state, firm_id, seat, slot, balance)
    return holder_effect(state, firm_id, seat, SINGLE_SLOT, balance)


def group_of_practice(state: GameState, firm_id: int, practice: str) -> int | None:
    for u in state.org.firm_units(firm_id):
        if u.kind == "practice_group" and u.practice == practice:
            return u.id
    return None


def group_effect(
    state: GameState, firm_id: int, practice: str, balance: Balance, data: GameData
) -> float:
    """The practice group leader's e for a practice (0 without a group)."""
    unit = group_of_practice(state, firm_id, practice)
    return 0.0 if unit is None else effect(state, firm_id, PGL, balance, data, slot=unit)


def candidates(
    state: GameState, firm_id: int, seat: SeatDef, balance: Balance
) -> tuple[tuple[int, float], ...]:
    """Eligible people by displayed fit, best first (ties by id): (person id, displayed s)."""
    scored = [
        (e.person_id, displayed_score(state, firm_id, e.person_id, seat, balance))
        for e in state.staff(firm_id)
        if ineligible_reason(state, firm_id, e.person_id, seat, balance) is None
    ]
    return tuple(sorted(scored, key=lambda x: (-x[1], x[0])))


# --- Player actions (TST ADR-0014: at once, energy spent) --------------------------------------


@dataclass(frozen=True, slots=True)
class AppointSeat:
    """Appoint, replace (a holder already sits) or vacate (person_id None) a seat."""

    actor_id: int
    seat: str
    slot: int = SINGLE_SLOT
    person_id: int | None = None
    kind: Literal["appoint_seat"] = "appoint_seat"


@dataclass(frozen=True, slots=True)
class SetAuthority:
    actor_id: int
    seat: str
    slot: int = SINGLE_SLOT
    enabled: bool = True
    guardrails: tuple[tuple[str, int], ...] = ()
    kind: Literal["seat_authority"] = "seat_authority"


@dataclass(frozen=True, slots=True)
class ProposeExcoTerm:
    actor_id: int
    elected: bool
    kind: Literal["exco_term"] = "exco_term"


@dataclass(frozen=True, slots=True)
class SeatOutcome:
    state: GameState
    log: tuple[LogItem, ...] = ()


def _mp_firm(state: GameState, actor_id: int) -> int:
    firm = org_actions.acting_firm(state, actor_id)
    if actor_id != managing_partner(state, firm):
        raise NotManagingPartnerError("only the managing partner appoints and directs seats")
    return firm


def _confidence(
    state: GameState, firm_id: int, person_id: int, sign: int, balance: Balance
) -> GameState:
    """A partner holder's confidence moves by their (true) ambition, once (PT-M8 brief)."""
    from ptk.sim.partnership.models import with_firm_partnership, with_partner

    fp = state.partnership.of(firm_id)
    partner = fp.partner(person_id) if fp is not None else None
    if fp is None or partner is None:
        return state
    ambition = state.person(person_id).personality["ambition"]
    points = sign * balance.seats.appoint_confidence_per_ambition * (ambition - 10)
    fp = with_partner(fp, replace(partner, nudge=partner.nudge + points))
    return replace(state, partnership=with_firm_partnership(state.partnership, fp))


def exco_elected(state: GameState, firm_id: int, balance: Balance, data: GameData) -> bool:
    """The committee is elected at the December vote (spec 9.2): the voted term, else from
    seats.exco.appointed_below_lawyers lawyers."""
    voted = state.leadership.firm(firm_id).exco_elected
    if voted is not None:
        return voted
    return lawyer_count(state, firm_id, data) >= balance.seats.exco.appointed_below_lawyers


def _check_slot(state: GameState, firm_id: int, seat: SeatDef, slot: int, b: Balance) -> None:
    if not in_play(state, firm_id, seat):
        raise SeatRuleError(f"the {seat.label} seat opens at stage {seat.stage}")
    if slot not in slots(state, firm_id, seat, b):
        raise SeatRuleError(f"the {seat.label} seat has no slot {slot}")


def appoint(state: GameState, action: AppointSeat, balance: Balance, data: GameData) -> SeatOutcome:
    firm = _mp_firm(state, action.actor_id)
    seat = seat_def(data, action.seat)
    if seat.who == "player":
        raise SeatRuleError("the managing partner's seat is the MP's (ADR PT-0007)")
    _check_slot(state, firm, seat, action.slot, balance)
    if seat.slots == "committee" and exco_elected(state, firm, balance, data):
        raise SeatRuleError("the executive committee is elected at the December vote")
    old = holder_of(state, firm, seat.key, action.slot)
    new = action.person_id
    if new is None and old is None:
        raise SeatRuleError(f"the {seat.label} seat is already vacant")
    if new is not None:
        if new == old:
            raise SeatRuleError("they already hold this seat")
        if reason := ineligible_reason(state, firm, new, seat, balance):
            raise SeatRuleError(f"cannot hold the {seat.label} seat: {reason}")
        if seat.slots != "committee":
            held = [h for h in state.leadership.seats_of(new) if h.seat != EXCO]
            if held or (state.org.led_unit(new) is not None and seat.key != PGL):
                raise SeatRuleError("a person holds at most one seat besides the committee")
        elif any(h.seat == EXCO for h in state.leadership.seats_of(new)):
            raise SeatRuleError("they already sit on the executive committee")
    state = spend_energy(state, action.actor_id, "appoint_seat", balance)
    if seat.key == PGL:
        state = _set_group_leader(state, action.actor_id, action.slot, new, balance, data)
    else:
        state = set_holder(state, firm, seat.key, action.slot, new)
    if old is not None:
        state = _confidence(state, firm, old, -1, balance)
    if new is not None:
        state = _confidence(state, firm, new, 1, balance)
    name = _name(state, new) if new is not None else "nobody"
    item = inbox_item(
        state.turn,
        firm,
        "seat_appointed" if new is not None else "seat_vacated",
        link_kind="org",
        link_id=None,
        seat=seat.label,
        name=name,
    )
    return SeatOutcome(state, (item,))


def _set_group_leader(
    state: GameState,
    actor: int,
    unit_id: int,
    new: int | None,
    balance: Balance,
    data: GameData,
) -> GameState:
    """A practice group leader's seat is PT-M2's unit leader (moved into the group first)."""
    if new is not None and state.org.unit_of(new) != unit_id:
        led = state.org.led_unit(new)
        if led is not None:
            state = org_actions.set_leader(
                state, org_actions.SetLeader(actor, led.id, None), balance
            ).state
        state = org_actions.move_person(
            state, org_actions.MovePerson(actor, new, unit_id), balance
        ).state
    return org_actions.set_leader(state, org_actions.SetLeader(actor, unit_id, new), balance).state


def set_authority(
    state: GameState, action: SetAuthority, balance: Balance, data: GameData
) -> SeatOutcome:
    firm = _mp_firm(state, action.actor_id)
    seat = seat_def(data, action.seat)
    if not seat.has_authority:
        raise SeatRuleError(f"the {seat.label} seat has no authority to give")
    _check_slot(state, firm, seat, action.slot, balance)
    rails: dict[str, int] = {}
    for key, value in action.guardrails:
        try:
            g = seat.guardrail(key)
        except KeyError as exc:
            raise InvalidActionError(str(exc)) from exc
        if not g.min <= value <= g.max:
            raise InvalidActionError(f"{g.label} must be {g.min} to {g.max}")
        rails[key] = value
    current = state.leadership.authority(firm, seat.key, action.slot)
    if current is not None:
        rails = {**dict(current.guardrails), **rails}
    state = spend_energy(state, action.actor_id, "seat_authority", balance)
    record = SeatAuthority(
        firm, seat.key, action.slot, action.enabled, tuple(sorted(rails.items()))
    )
    return SeatOutcome(with_authority(state, record))


def propose_exco_term(
    state: GameState, action: ProposeExcoTerm, balance: Balance, data: GameData
) -> SeatOutcome:
    firm = _mp_firm(state, action.actor_id)
    current = state.leadership.firm(firm)
    if exco_elected(state, firm, balance, data) == action.elected and current.exco_proposed is None:
        raise SeatRuleError("the agreement already says so")
    state = spend_energy(state, action.actor_id, "exco_term", balance)
    return SeatOutcome(with_firm_leadership(state, replace(current, exco_proposed=action.elected)))


type SeatAction = AppointSeat | SetAuthority | ProposeExcoTerm
SEAT_ACTION_TYPES: Final[dict[str, type[SeatAction]]] = {
    "appoint_seat": AppointSeat,
    "seat_authority": SetAuthority,
    "exco_term": ProposeExcoTerm,
}


def apply_seat_action(
    state: GameState, action: SeatAction, balance: Balance, data: GameData
) -> SeatOutcome:
    match action:
        case AppointSeat():
            return appoint(state, action, balance, data)
        case SetAuthority():
            return set_authority(state, action, balance, data)
        case ProposeExcoTerm():
            return propose_exco_term(state, action, balance, data)


def _name(state: GameState, person_id: int) -> str:
    p = state.person(person_id)
    return f"{p.first_name} {p.last_name}"


# --- Effects read by other systems (spec 9.1; through ptk.sim.interfaces) -----------------------


def associate_morale(state: GameState, person_id: int, balance: Balance, data: GameData) -> float:
    """Morale target points from the seats for an associate (spec 9.1): their practice group
    leader's pgl_morale x e, plus the CHRO's chro_morale x e. 0 for anyone else."""
    from ptk.sim.data_models import SCALE_LEVELS

    firm = state.employer_of(person_id)
    if firm is None or state.person(person_id).level not in SCALE_LEVELS:
        return 0.0
    if not state.firm(firm).is_player or state.firm(firm).stage < min(
        s.stage for s in data.seats.seats
    ):
        return 0.0
    fx = balance.seats.effects
    points = fx.chro_morale * effect(state, firm, "chro", balance, data)
    unit = state.org.unit_of(person_id)
    group = state.org.unit(unit) if unit is not None else None
    while group is not None and group.kind != "practice_group" and group.parent_id is not None:
        group = state.org.unit(group.parent_id)
    if group is not None and group.kind == "practice_group":
        points += fx.pgl_morale * effect(state, firm, PGL, balance, data, slot=group.id)
    return points
