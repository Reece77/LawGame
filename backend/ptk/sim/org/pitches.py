"""Seat holders' pitches: big moves they propose for the MP to approve (TST formulas.md 27.1;
spec 9.3; ADR-0015; PT-M8).

Ported from backend/tst/sim/org/pitches.py @ 121d318a (Tech Startup Tycoon); changed: Partner
Track's pitch kinds and seats (below); stream `pitch` (id 46) keyed (firm id, person id); no
Holiday auto-approval (pitches wait in the inbox and lapse at the holder's next quarterly
draw; Holiday's stops are PT-M7a's); the executive committee's e adds to every pitch's
decision quality (spec 9.1: "decision quality of firm-wide proposals").

In a quarter's first month (January, April, July, October), each holder with authority whose
seat pitches draws two uniforms: whether (clamp(base + per_ambition (ambition - 10)) from TRUE
ambition), then which (the best candidate with probability clamp(0.55 + 0.03 s +
exco_quality x e_exco, 0.6, 0.98) from the TRUE seat score, else the second best). At most
one pitch a quarter per holder. Candidates, costs and cases come only from what the firm can
see (ADR-0015, ADR-0007): its utilisation, its people's home practices, open matters, its
relationships' trailing fees, its rate card. The low and high cases widen for a holder the
firm rates lower (its DISPLAYED seat score). Neither true ambition, nor the score, nor the
quality draw ever reaches a number the player sees (TST 27.6).

Kinds (central case unit; what Approve does, as the holder unless noted):
- lateral_partner (PGL; cents a year of book): a lateral partner search in the group's
  practice (PT-M4's action, as the MP: the guarantee stays a one-off at the offer); scored
  by the books of partners who join in the practice.
- new_group (PGL; lawyers): a practice group for a practice with lawyers and no group; scored
  by the lawyers in it.
- campus_size (CHRO; people): a campus target for the busiest group with none; scored by its
  hires.
- rate_move (pricing; bp): next January's rise at the market's plus `rate_step_bp`; scored by
  the firm's rate index against its baseline.
- panel_push (CMO; cents of trailing-year fees): marketing spend and a relationship bump on
  named clients; scored by their trailing-year fees.
- fit_out (COO; morale points x 10): a fit-out (capex) and a firm morale-target modifier;
  scored by the staff's mean morale.
- cost_programme (CFO; cents saved): a rent and suppliers saving each month for
  `cost_months`, and a small morale cost; scored by the saving realised.

Follow-through (TST 27.1): `record_months` after approval each approved pitch is scored hit
(at or above its central case) or miss; a hit moves the holder's morale up and a partner
holder's confidence up, a miss down; a decline costs the holder morale once (more at high
ego).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from typing import Final, Literal

import numpy as np

from ptk.sim.calendar import format_turn, turn_to_ym
from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import InvalidActionError, SeatRuleError, SimError, UnknownPitchError
from ptk.sim.events.models import Modifier, with_modifier
from ptk.sim.ledger import CASH, RENT, AccountCode, LedgerBalances, LedgerEntry
from ptk.sim.log import LogItem, inbox_item
from ptk.sim.money import Cents, format_money
from ptk.sim.org import actions as org_actions
from ptk.sim.org.authority import _lawyer_role, _members, quality, utilisation_bp
from ptk.sim.org.seat_data import PitchKind, SeatDef
from ptk.sim.org.seat_models import EXCO, Pitch
from ptk.sim.org.seats import (
    displayed_score,
    effect,
    managing_partner,
    true_score,
    with_leadership,
)
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState

MARKETING: Final[AccountCode] = "6400_marketing"
PPE: Final[AccountCode] = "1500_ppe"
QUARTER: Final = 3  # tunable-exempt: calendar
DRAWS: Final = 2  # tunable-exempt: uniforms a draw month: whether, then which (27.1)
BP: Final = 10_000  # tunable-exempt: basis points
MORALE_SCALE: Final = 10  # tunable-exempt: fit_out's case unit (morale points x 10)
DEFAULT_BOOK_CENTS: Final = 100_000_000  # tunable-exempt: $1M, a book with no partners to judge by
CASE_UNIT: Final[dict[PitchKind, Literal["cents", "people", "bp", "morale"]]] = {
    "lateral_partner": "cents",
    "new_group": "people",
    "campus_size": "people",
    "rate_move": "bp",
    "panel_push": "cents",
    "fit_out": "morale",
    "cost_programme": "cents",
}
type Draws = Callable[[], np.random.Generator]


@dataclass(frozen=True, slots=True)
class Candidate:
    score: float  # higher is better (the kind's 24-month value, comparable within a seat)
    kind: PitchKind
    title: str
    why: str
    cost_cents: int
    central: int
    params: tuple[tuple[str, int], ...]
    baseline: int = 0


# --- What the firm can see ---------------------------------------------------------------------


def _staff_morale(state: GameState, firm_id: int) -> float:
    values = [
        ps.morale
        for e in state.staff(firm_id)
        if (ps := state.person_state(e.person_id)).morale is not None
    ]
    return sum(values) / len(values) if values else 0.0


def _practice_lawyers(state: GameState, firm_id: int, practice: str, data: GameData) -> int:
    role = _lawyer_role(data, practice)
    return sum(1 for e in state.staff(firm_id) if state.person(e.person_id).role == role)


def _partner_book(state: GameState, firm_id: int, practice: str, data: GameData) -> int:
    role = _lawyer_role(data, practice)
    books = [
        state.person(e.person_id).book_cents
        for e in state.staff(firm_id)
        if state.person(e.person_id).role == role
        and state.person(e.person_id).level in ("equity_partner", "income_partner")
        and state.person(e.person_id).book_cents > 0
    ]
    return sorted(books)[len(books) // 2] if books else DEFAULT_BOOK_CENTS


def _joined_partner_books(
    state: GameState, firm_id: int, practice: str, since: int, data: GameData
) -> int:
    role = _lawyer_role(data, practice)
    total = 0
    for e in state.staff(firm_id):
        p = state.person(e.person_id)
        if (
            p.role == role
            and e.start_turn >= since
            and p.level in ("equity_partner", "income_partner")
        ):
            total += p.book_cents
    return total


def _rent_month(state: GameState, firm_id: int, b: Balance) -> int:
    from ptk.sim.hiring.formulas import rent_cents

    heads = len(state.staff(firm_id))
    return int(rent_cents(heads, state.firm(firm_id).home_city, b.pay))


# --- Candidates by kind ------------------------------------------------------------------------


def _lateral(state: GameState, firm: int, slot: int, b: Balance, data: GameData) -> list[Candidate]:
    unit = state.org.unit(slot)
    if unit is None or unit.practice is None:
        return []
    util = utilisation_bp(state, _members(state, unit.id), data, b)
    if util is None or util < b.pitches.busy_bp:
        return []
    book = round(
        _partner_book(state, firm, unit.practice, data) * b.pitches.kinds["lateral_partner"].central
    )
    label = data.practice(unit.practice).label
    return [
        Candidate(
            score=float(book) * util / BP,
            kind="lateral_partner",
            title=f"a lateral {label} partner with a book",
            why=f"{unit.name} ran at {util / 100:.0f}% last month; partners there bill about "
            f"{format_money(book)} a year",
            cost_cents=b.pitches.kinds["lateral_partner"].cost_cents,
            central=book,
            params=(("unit", unit.id),),
        )
    ]


def _new_groups(state: GameState, firm: int, b: Balance, data: GameData) -> list[Candidate]:
    grouped = {u.practice for u in state.org.firm_units(firm) if u.kind == "practice_group"}
    out = []
    for i, p in enumerate(data.practice_keys):
        if p in grouped:
            continue
        n = _practice_lawyers(state, firm, p, data)
        if n < b.pitches.new_group_min_lawyers:
            continue
        central = round(n * b.pitches.kinds["new_group"].central)
        label = data.practice(p).label
        out.append(
            Candidate(
                score=float(n) * 10**6,
                kind="new_group",
                title=f"a {label} practice group",
                why=f"{n} {label} lawyers work without a group or a leader",
                cost_cents=b.pitches.kinds["new_group"].cost_cents,
                central=central,
                params=(("practice", i),),
                baseline=n,
            )
        )
    return out


def _campus(state: GameState, firm: int, b: Balance, data: GameData) -> list[Candidate]:
    out = []
    plans = state.org.firm_plans(firm)
    for unit in state.org.firm_units(firm):
        if unit.kind != "practice_group" or unit.leader_id is None:
            continue
        if any(p.unit_id == unit.id and p.campus for p in plans):
            continue
        util = utilisation_bp(state, _members(state, unit.id), data, b)
        if util is None or util < b.pitches.busy_bp:
            continue
        step = b.pitches.campus_step
        out.append(
            Candidate(
                score=float(util),
                kind="campus_size",
                title=f"{step} more first-years for {unit.name}",
                why=f"{unit.name} ran at {util / 100:.0f}% last month and has no campus target",
                cost_cents=b.pitches.kinds["campus_size"].cost_cents,
                central=round(step * b.pitches.kinds["campus_size"].central),
                params=(("size", step), ("unit", unit.id)),
            )
        )
    return out


def _rate(state: GameState, firm: int, b: Balance, data: GameData) -> list[Candidate]:
    from ptk.sim.matters.rates import market_rise_bp

    people = tuple(e.person_id for e in state.staff(firm))
    util = utilisation_bp(state, people, data, b)
    if util is None or util < b.pitches.busy_bp:
        return []
    year = turn_to_ym(state.turn, state.save_meta.start_ym)[0] + 1
    market = market_rise_bp(year, data, b)
    rise = min(b.rates.rise_max_bp, market + b.pitches.rate_step_bp)
    if state.firm(firm).rate_rise_bp == rise:
        return []
    central = round(rise * b.pitches.kinds["rate_move"].central)
    return [
        Candidate(
            score=float(util),
            kind="rate_move",
            title=f"a {rise / 100:+.1f}% rate rise next January",
            why=f"the firm ran at {util / 100:.0f}% last month; the market rises "
            f"{market / 100:+.1f}%",
            cost_cents=b.pitches.kinds["rate_move"].cost_cents,
            central=central,
            params=(("rise_bp", rise),),
            baseline=round(state.firm(firm).rate_index * BP),
        )
    ]


def _panel(state: GameState, firm: int, b: Balance, data: GameData) -> list[Candidate]:
    rels = sorted(
        (r for r in state.market.relationships if r.firm_id == firm and r.fees_12m > 0),
        key=lambda r: (-r.fees_12m, r.client_id),
    )[: b.pitches.panel_clients * 3]
    named = sorted(rels, key=lambda r: (r.score, r.client_id))[: b.pitches.panel_clients]
    if not named:
        return []
    fees = sum(int(r.fees_12m) for r in named)
    names = ", ".join(state.market.client(r.client_id).name for r in named)
    params = tuple((f"client_{i}", r.client_id) for i, r in enumerate(named))
    return [
        Candidate(
            score=float(fees),
            kind="panel_push",
            title=f"a panel push on {names}",
            why=f"they paid {format_money(fees)} in the last year, but our relationships there "
            "are the weakest of our big clients",
            cost_cents=b.pitches.kinds["panel_push"].cost_cents,
            central=round(fees * b.pitches.kinds["panel_push"].central),
            params=params,
            baseline=fees,
        )
    ]


def _fit_out(state: GameState, firm: int, b: Balance, data: GameData) -> list[Candidate]:
    heads = len(state.staff(firm))
    morale = _staff_morale(state, firm)
    if heads == 0:
        return []
    base = round(morale * MORALE_SCALE)
    return [
        Candidate(
            score=float(heads),
            kind="fit_out",
            title="a fit-out of the office",
            why=f"{heads} people work in space last fitted out years ago; morale averages "
            f"{morale:.0f}",
            cost_cents=b.pitches.kinds["fit_out"].cost_cents,
            central=round(base * b.pitches.kinds["fit_out"].central),
            params=(),
            baseline=base,
        )
    ]


def _cost(state: GameState, firm: int, b: Balance, data: GameData) -> list[Candidate]:
    rent = _rent_month(state, firm, b)
    saving = rent * b.pitches.cost_saving_bp // BP
    if saving <= 0:
        return []
    total = saving * b.pitches.cost_months
    return [
        Candidate(
            score=float(total),
            kind="cost_programme",
            title=f"a cost programme saving {format_money(saving)} a month",
            why=f"rent and suppliers run at {format_money(rent)} a month",
            cost_cents=b.pitches.kinds["cost_programme"].cost_cents,
            central=round(total * b.pitches.kinds["cost_programme"].central),
            params=(("saving_cents", saving),),
        )
    ]


def candidates(
    state: GameState, firm: int, seat: SeatDef, slot: int, b: Balance, data: GameData
) -> list[Candidate]:
    """A seat's candidates, best first (ties by title)."""
    out: list[Candidate] = []
    for kind in seat.pitches:
        match kind:
            case "lateral_partner":
                out += _lateral(state, firm, slot, b, data)
            case "new_group":
                out += _new_groups(state, firm, b, data)
            case "campus_size":
                out += _campus(state, firm, b, data)
            case "rate_move":
                out += _rate(state, firm, b, data)
            case "panel_push":
                out += _panel(state, firm, b, data)
            case "fit_out":
                out += _fit_out(state, firm, b, data)
            case "cost_programme":
                out += _cost(state, firm, b, data)
    return sorted(out, key=lambda c: (-c.score, c.title))


# --- Making pitches ----------------------------------------------------------------------------


def chance(ambition: float, b: Balance) -> float:
    p = b.pitches
    lo, hi = p.chance_clamp
    return max(lo, min(hi, p.base + p.per_ambition * (ambition - 10)))


def spread(shown: float, b: Balance) -> float:
    p = b.pitches
    lo, hi = p.spread_clamp
    return max(lo, min(hi, p.spread_base + p.spread_per_point * (15 - shown)))


def is_draw_month(state: GameState) -> bool:
    return (turn_to_ym(state.turn, state.save_meta.start_ym)[1] - 1) % QUARTER == 0


def _name(state: GameState, pid: int) -> str:
    p = state.person(pid)
    return f"{p.first_name} {p.last_name}"


def pitch_text(state: GameState, p: Pitch) -> str:
    unit = CASE_UNIT[p.kind]

    def show(v: int) -> str:
        if unit == "cents":
            return format_money(v)
        if unit == "bp":
            return f"{v / 100:+.1f}%"
        if unit == "morale":
            return f"{v / MORALE_SCALE:.0f} morale"
        return f"{v} people"

    cost = f" It costs {format_money(p.cost_cents)} now." if p.cost_cents else ""
    return (
        f"{p.why[:1].upper()}{p.why[1:]}.{cost} Low case {show(p.low)}, central {show(p.central)}, "
        f"high {show(p.high)} after {24} months. Approve, modify or decline."
    )


def _with_pitch(state: GameState, pitch: Pitch) -> GameState:
    ls = state.leadership
    rest = [p for p in ls.pitches if p.id != pitch.id]
    merged = tuple(sorted([*rest, pitch], key=lambda p: p.id))
    nxt = max(ls.next_pitch_id, pitch.id + 1)
    return with_leadership(state, replace(ls, pitches=merged, next_pitch_id=nxt))


def draw_pitches(
    state: GameState, rng: RngFactory, b: Balance, data: GameData, *, force: bool = False
) -> tuple[GameState, list[LogItem]]:
    """Phase 2, a quarter's first month: each holder with authority may pitch once.
    `force` (the e2e suite's debug route only): every holder pitches now."""
    from ptk.sim.org.authority import acting_holders

    logs: list[LogItem] = []
    if not state.firms or not (force or is_draw_month(state)):
        return state, logs
    firm = state.player.id
    exco_bonus = b.seats.effects.exco_quality * effect(state, firm, EXCO, b, data)
    for seat, slot, pid, _auth in acting_holders(state, firm, b, data):
        if not seat.pitches:
            continue
        for p in state.leadership.pitches:
            if p.firm_id == firm and p.person_id == pid and p.status == "pending":
                state = _with_pitch(state, replace(p, status="lapsed", resolved_turn=state.turn))
                logs.append(_item(state, p, "pitch_lapsed"))
        gen = rng.stream(state.turn, "pitch", firm, pid)
        u_pitch, u_pick = (float(gen.random()) for _ in range(DRAWS))
        person = state.person(pid)
        if not force and u_pitch >= chance(person.personality["ambition"], b):  # true, unshown
            continue
        ranked = candidates(state, firm, seat, slot, b, data)
        if not ranked:
            continue
        q = quality(true_score(person, seat), b, exco_bonus)
        pick = ranked[0] if u_pick < q or len(ranked) == 1 else ranked[1]
        s = spread(displayed_score(state, firm, pid, seat, b), b)
        pitch = Pitch(
            id=state.leadership.next_pitch_id,
            firm_id=firm,
            seat=seat.key,
            slot=slot,
            person_id=pid,
            kind=pick.kind,
            title=pick.title,
            why=pick.why,
            made_turn=state.turn,
            cost_cents=pick.cost_cents,
            low=round(pick.central * (1 - s)),
            central=pick.central,
            high=round(pick.central * (1 + s)),
            params=pick.params,
            baseline=pick.baseline,
        )
        state = _with_pitch(state, pitch)
        logs.append(_item(state, pitch, "pitch", detail=pitch_text(state, pitch)))
    return state, logs


def _item(state: GameState, p: Pitch, template: str, **extra: str | int) -> LogItem:
    params: dict[str, str | int] = {
        "name": _name(state, p.person_id),
        "what": p.title,
        **extra,
    }
    return inbox_item(state.turn, p.firm_id, template, link_kind="pitch", link_id=p.id, **params)


# --- Answering (a player action) ----------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AnswerPitch:
    """Approve, modify (approve with a changed size or rise) or decline a pending pitch."""

    actor_id: int
    pitch_id: int
    answer: Literal["approve", "modify", "decline"]
    value: int | None = None  # modify: the new size (people) or rise (bp)
    kind: Literal["answer_pitch"] = "answer_pitch"


@dataclass(frozen=True, slots=True)
class PitchOutcome:
    state: GameState
    entries: tuple[LedgerEntry, ...] = ()
    log: tuple[LogItem, ...] = ()


MODIFIABLE: Final[dict[PitchKind, str]] = {"campus_size": "size", "rate_move": "rise_bp"}


def answer_pitch(
    state: GameState,
    a: AnswerPitch,
    rng: RngFactory,
    draws: Draws,
    b: Balance,
    data: GameData,
    balances: LedgerBalances,
) -> PitchOutcome:
    from ptk.sim.hiring.actions import spend_energy

    firm = org_actions.acting_firm(state, a.actor_id)
    if a.actor_id != managing_partner(state, firm):
        raise SeatRuleError("only the managing partner answers pitches")
    pitch = state.leadership.pitch(a.pitch_id)
    if pitch is None or pitch.firm_id != firm:
        raise UnknownPitchError(f"no pitch {a.pitch_id}")
    if pitch.status != "pending":
        raise SeatRuleError(f"that pitch is {pitch.status}")
    state = spend_energy(state, a.actor_id, "answer_pitch", b)
    if a.answer == "decline":
        state = _with_pitch(state, replace(pitch, status="declined", resolved_turn=state.turn))
        ego = state.person(pitch.person_id).personality["ego"]
        drop = (
            b.pitches.decline_morale_high_ego
            if ego >= b.pitches.high_ego
            else b.pitches.decline_morale
        )
        state = org_actions.nudge(state, pitch.person_id, -drop, "pitch declined")
        item = _item(state, pitch, "pitch_answered", outcome="declined", detail="Declined.")
        return PitchOutcome(state, (), (item,))
    if a.answer == "modify":
        key = MODIFIABLE.get(pitch.kind)
        if key is None or a.value is None:
            raise InvalidActionError("only a class size or a rate rise can be modified")
        if (
            key == "size" and not 1 <= a.value <= 30
        ):  # tunable-exempt: the class-size guardrail's range
            raise InvalidActionError("a class size is 1 to 30")
        if key == "rise_bp" and not b.rates.rise_min_bp <= a.value <= b.rates.rise_max_bp:
            raise InvalidActionError("that rate rise is outside the policy's range")
        params = tuple(sorted({**dict(pitch.params), key: a.value}.items()))
        pitch = replace(pitch, params=params)
    try:
        state, entries, logs = execute(state, pitch, a.actor_id, rng, draws, b, data, balances)
    except SimError as exc:
        failed = replace(pitch, status="failed", resolved_turn=state.turn)
        state = _with_pitch(state, failed)
        item = _item(state, pitch, "pitch_answered", outcome="could not go ahead", detail=str(exc))
        return PitchOutcome(state, (), (item,))
    current = state.leadership.pitch(pitch.id) or pitch  # execute may record what it made
    done = replace(current, status="approved", resolved_turn=state.turn)
    state = _with_pitch(state, done)
    item = _item(state, done, "pitch_answered", outcome="approved", detail=pitch_text(state, done))
    return PitchOutcome(state, entries, (*logs, item))


def execute(
    state: GameState,
    p: Pitch,
    mp: int,
    rng: RngFactory,
    draws: Draws,
    b: Balance,
    data: GameData,
    balances: LedgerBalances,
) -> tuple[GameState, tuple[LedgerEntry, ...], tuple[LogItem, ...]]:
    """Carry out an approved pitch through the normal actions (TST 27.1)."""
    entries: list[LedgerEntry] = []
    logs: list[LogItem] = []
    if p.cost_cents:
        cash = balances.get((p.firm_id, CASH), 0)
        if cash < p.cost_cents:
            raise SeatRuleError(f"the firm lacks the {format_money(p.cost_cents)} it needs")
        debit = PPE if p.kind == "fit_out" else MARKETING
        entries.append(
            LedgerEntry.transfer(
                turn=state.turn,
                firm_id=p.firm_id,
                memo=f"Pitch: {p.title}",
                debit=debit,
                credit=CASH,
                amount=p.cost_cents,
            )
        )
    match p.kind:
        case "lateral_partner":
            from ptk.sim.partnership.actions import LateralSearch, apply_partnership_action

            unit = state.org.unit(p.param("unit"))
            if unit is None or unit.practice is None:
                raise SeatRuleError("the group has gone")
            energy = state.person_state(mp)
            out = apply_partnership_action(
                state, LateralSearch(mp, unit.practice), rng, draws, b, data, balances
            )
            state = _keep_energy(out.state, energy)  # the holder's work, not the MP's
            entries += out.entries
            logs += out.log
        case "new_group":
            practice = data.practice_keys[p.param("practice")]
            o = org_actions.create_unit(
                state,
                org_actions.CreateUnit(p.person_id, "practice_group", None, None, practice),
                b,
                data,
            )
            state = o.state
            p = replace(p, params=tuple(sorted({**dict(p.params), "unit": o.unit_id or 0}.items())))
            state = _with_pitch(state, p)
        case "campus_size":
            unit = state.org.unit(p.param("unit"))
            if unit is None or unit.leader_id is None or unit.practice is None:
                raise SeatRuleError("the group has no leader to own a campus target")
            o = org_actions.create_plan(
                state,
                org_actions.CreatePlan(
                    actor_id=p.person_id,
                    owner_id=unit.leader_id,
                    role=_lawyer_role(data, unit.practice),
                    target=p.param("size"),
                    channel="campus",
                    ratio_bp=b.authority.plan_ratio_bp,
                    unit_id=unit.id,
                ),
                b,
                data,
            )
            state = o.state
            p = replace(p, params=tuple(sorted({**dict(p.params), "plan": o.plan_id or 0}.items())))
            state = _with_pitch(state, p)
        case "rate_move":
            from ptk.sim.matters.actions import SetRatePolicy, apply_matter_action

            m = apply_matter_action(
                state, SetRatePolicy(p.person_id, p.param("rise_bp")), draws, b, data
            )
            state = m.state
        case "panel_push":
            from ptk.sim.interfaces import bump_relationship

            for key, client in p.params:
                if key.startswith("client_"):
                    state = bump_relationship(state, client, p.firm_id, b.pitches.panel_bump)
        case "fit_out":
            state = _firm_modifier(
                state, p.firm_id, b.pitches.fit_out_morale_pct, b.pitches.fit_out_months
            )
        case "cost_programme":
            state = _firm_modifier(
                state, p.firm_id, b.pitches.cost_morale_pct, b.pitches.cost_months
            )
    return state, tuple(entries), tuple(logs)


def _keep_energy(state: GameState, before: object) -> GameState:
    from ptk.sim.hiring.models import PersonState
    from ptk.sim.state import with_person_states

    assert isinstance(before, PersonState)
    return with_person_states(state, [before])


def _firm_modifier(state: GameState, firm: int, pct: float, months: int) -> GameState:
    es = state.events
    mod = Modifier(
        id=es.next_modifier_id,
        firm_id=firm,
        event_id=None,
        target=f"firm:{firm}",
        stat="morale_target",
        value_pct=pct,
        start_turn=state.turn,
        end_turn=state.turn + months,
    )
    return replace(state, events=with_modifier(es, mod))


# --- Follow-through and running programmes (phase 2) ---------------------------------------------


def measure(state: GameState, p: Pitch, data: GameData) -> int:
    """What the pitch's central case is scored against (its unit), from the firm's own books."""
    since = p.resolved_turn if p.resolved_turn is not None else p.made_turn
    match p.kind:
        case "lateral_partner":
            unit = state.org.unit(p.param("unit"))
            practice = unit.practice if unit is not None and unit.practice else ""
            return _joined_partner_books(state, p.firm_id, practice, since, data) if practice else 0
        case "new_group":
            unit = state.org.unit(p.param("unit"))
            if unit is None or unit.status != "active":
                return 0
            return len(_members(state, unit.id))
        case "campus_size":
            plan = state.org.plan(p.param("plan"))
            return plan.hired if plan is not None else 0
        case "rate_move":
            return round(state.firm(p.firm_id).rate_index * BP - p.baseline)
        case "panel_push":
            total = 0
            for key, client in p.params:
                if key.startswith("client_"):
                    rel = state.market.relationship(client, p.firm_id)
                    total += int(rel.fees_12m) if rel is not None else 0
            return total
        case "fit_out":
            return round(_staff_morale(state, p.firm_id) * MORALE_SCALE)
        case "cost_programme":
            return p.param("saved_cents")


def follow_through(
    state: GameState, b: Balance, data: GameData, balances: Mapping[tuple[int, AccountCode], Cents]
) -> tuple[GameState, list[LedgerEntry], list[LogItem]]:
    """Running cost programmes save; approved pitches record_months old are scored."""
    entries: list[LedgerEntry] = []
    logs: list[LogItem] = []
    for p in state.leadership.pitches:
        start = p.resolved_turn
        if p.status != "approved" or p.outcome is not None or start is None:
            continue
        if p.kind == "cost_programme" and state.turn - start < b.pitches.cost_months:
            saving = p.param("saving_cents")
            if saving > 0:
                entries.append(
                    LedgerEntry.transfer(
                        turn=state.turn,
                        firm_id=p.firm_id,
                        memo=f"Cost programme: {p.title}",
                        debit=CASH,
                        credit=RENT,
                        amount=saving,
                    )
                )
                saved = p.param("saved_cents") + saving
                p = replace(
                    p, params=tuple(sorted({**dict(p.params), "saved_cents": saved}.items()))
                )
                state = _with_pitch(state, p)
        if state.turn < start + b.pitches.record_months:
            continue
        value = measure(state, p, data)
        hit = value >= p.central
        done = replace(p, outcome="hit" if hit else "miss", outcome_turn=state.turn, measured=value)
        state = _with_pitch(state, done)
        if state.employer_of(p.person_id) == p.firm_id:
            state = org_actions.nudge(
                state,
                p.person_id,
                b.pitches.hit_morale if hit else b.pitches.miss_morale,
                "pitch record",
            )
            points = b.pitches.hit_confidence if hit else b.pitches.miss_confidence
            state = _confidence_points(state, p.firm_id, p.person_id, points)
        made = format_turn(p.made_turn, state.save_meta.start_ym)
        logs.append(
            _item(
                state,
                done,
                "pitch_scored",
                outcome="hit" if hit else "miss",
                made_label=made,
                central=_show(done, done.central),
                measured=_show(done, value),
            )
        )
    return state, entries, logs


def _show(p: Pitch, v: int) -> str:
    unit = CASE_UNIT[p.kind]
    if unit == "cents":
        return format_money(v)
    if unit == "bp":
        return f"{v / 100:+.1f}%"
    if unit == "morale":
        return f"{v / MORALE_SCALE:.0f} morale"
    return f"{v} people"


def _confidence_points(state: GameState, firm: int, pid: int, points: float) -> GameState:
    from ptk.sim.partnership.models import with_firm_partnership, with_partner

    fp = state.partnership.of(firm)
    partner = fp.partner(pid) if fp is not None else None
    if fp is None or partner is None or points == 0:
        return state
    fp = with_partner(fp, replace(partner, nudge=partner.nudge + points))
    return replace(state, partnership=with_firm_partnership(state.partnership, fp))


def record(state: GameState, person_id: int) -> tuple[int, int]:
    """(hits, misses) of a holder's scored pitches (shown on the panel)."""
    scored = [p for p in state.leadership.pitches if p.person_id == person_id and p.outcome]
    return sum(1 for p in scored if p.outcome == "hit"), sum(
        1 for p in scored if p.outcome == "miss"
    )


def pitches_month(
    state: GameState,
    rng: RngFactory,
    b: Balance,
    data: GameData,
    balances: Mapping[tuple[int, AccountCode], Cents],
) -> tuple[GameState, tuple[LedgerEntry, ...], tuple[LogItem, ...]]:
    if state.ended or not state.firms:
        return state, (), ()
    state, entries, logs = follow_through(state, b, data, balances)
    state, drawn = draw_pitches(state, rng, b, data)
    return state, tuple(entries), (*logs, *drawn)
