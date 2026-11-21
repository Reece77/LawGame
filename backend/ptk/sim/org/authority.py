"""Seat holders with authority act in phase 2 (TST formulas.md 24.1-24.2; ADR-0015; PT-M8).

Ported from backend/tst/sim/org/authority.py @ 121d318a (Tech Startup Tycoon); changed:
Partner Track's seats and rules (below), reached through the same actions the player uses
(PT-M2's org actions, PT-M3a's matter actions, PT-M3b's billing actions, PT-M5's RFP pitch),
with the holder as actor; each holder has `authority.energy_per_month` for its seat's actions
this month (its own energy for anything else is left as it was); randomness is stream
`seat_act` (id 45) keyed (seat index, firm id, slot): the first uniform decides whether the
holder takes the right rule this month, with probability clamp(0.55 + 0.03 s, 0.6, 0.98)
from the TRUE seat score; the actions' own draws come after it on the same generator.

Choosing reads only what the firm can see (ADR-0015, ADR-0007): last month's hours, open
matters, its WIP, open RFPs, displayed skill ranges. A mistake is a plausible worse option:

- Practice group leader: when the group's last month ran at or above its `busy_bp`
  utilisation and it is under its headcount cap with no plan open, a hiring plan for
  `authority.hire_step` associates in the group; mistake: one fewer (none at step 1).
- General counsel: a waiver request on held (conflicted) instructions, oldest first, up to its
  monthly guardrail, never adverse to a key client (spec 9.4: that is a one-off); mistake: it
  waits a month.
- CFO: writes down the matter with the oldest unbilled time beyond its age guardrail, by its
  band; mistake: the second oldest.
- CMO: pitches open RFPs the firm is invited to, with the team it can see is strongest (the
  lead first), up to its monthly guardrail; mistake: the second-best lead.
- CHRO: in the campus register months, a campus plan of `class_size` for every practice group
  with a leader and none; mistake: one fewer.
- Pricing director: in December, next January's rate rise: the market's, plus its band when
  the firm ran at or above 85% utilisation, minus it below 70%; mistake: the market's.

Decisions are logged as `SeatDecision`s (the API shows the text, never the mistake flag) and
as `DelegateAction`-like decision-log rows, recomputed on replay (ADR-0015 section 5). The
spec 9.4 one-offs are never within authority: `act` refuses them (OneOffError).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, replace
from typing import Final

import numpy as np

from ptk.sim.billing.actions import WriteDownMatter, apply_billing_action
from ptk.sim.calendar import turn_to_ym
from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import OneOffError, SimError
from ptk.sim.ledger import AccountCode, LedgerEntry
from ptk.sim.log import LogItem
from ptk.sim.matters.actions import SeekWaiver, SetRatePolicy, apply_matter_action
from ptk.sim.matters.intake import key_clients
from ptk.sim.money import Cents
from ptk.sim.org.actions import CreatePlan, apply_org_action
from ptk.sim.org.seat_data import SeatDef
from ptk.sim.org.seat_models import PGL, SeatAuthority, SeatDecision
from ptk.sim.org.seats import (
    seat_index,
    seated_holder,
    slots,
    true_score,
    with_leadership,
)
from ptk.sim.people.models import fam_key
from ptk.sim.people.reveal import revealed_range
from ptk.sim.rivals.actions import PitchRfp, apply_rival_action
from ptk.sim.rivals.rfp import PITCH_SKILLS
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState, with_person_states

type Act = CreatePlan | SeekWaiver | WriteDownMatter | PitchRfp | SetRatePolicy

# Spec 9.4's one-offs, by the action kinds that carry them: never within authority.
ONE_OFF_KINDS: Final = frozenset(
    {
        "propose_partner",  # partnership admissions
        "deequitise",  # de-equitisations
        "lateral_offer",  # every hire with a guarantee
        "counter",  # a counter-offer's guarantee
        "counter_approach",
        "capital_call",
        "propose_terms",  # changes to the partnership agreement
        "exco_term",
        "set_pay_policy",  # a salary-scale change
        "approach_rival",  # combinations with a rival's people (mergers are PT-M13)
    }
)
AUTHORITY_KINDS: Final = frozenset(
    {"create_plan", "seek_waiver", "write_down_matter", "pitch_rfp", "set_rate_policy"}
)
BUSY_HIGH_BP: Final = 8500  # tunable-exempt: the pricing rule's busy line (85%), TST 24.1 analogue
BUSY_LOW_BP: Final = 7000  # tunable-exempt: and its quiet line (70%)
BP: Final = 10_000  # tunable-exempt: basis points
DECEMBER: Final = 12  # tunable-exempt: calendar
TEAM_SIZE: Final = 3  # tunable-exempt: an RFP team the CMO puts up (the lead and two)


@dataclass(frozen=True, slots=True)
class SeatRun:
    """A month of seat actions: the new state, ledger entries, log and decisions."""

    state: GameState
    entries: tuple[LedgerEntry, ...] = ()
    log: tuple[LogItem, ...] = ()
    decisions: tuple[SeatDecision, ...] = ()


def act_payload(d: SeatDecision) -> dict[str, object]:
    return {"source": "seat", **asdict(d)}


def quality(score: float, balance: Balance, bonus: float = 0.0) -> float:
    """P(the right rule) = clamp(base + per_score x s (+ bonus), min, max) (TST 24.2)."""
    q = balance.authority.quality
    return max(q.min, min(q.max, q.base + q.per_score * score + bonus))


def apply_authorised(
    state: GameState,
    action: Act,
    draws: Callable[[], np.random.Generator],
    balance: Balance,
    data: GameData,
) -> tuple[GameState, tuple[LedgerEntry, ...], tuple[LogItem, ...]]:
    """One action under authority, at once, or a SimError and no change."""
    if action.kind in ONE_OFF_KINDS or action.kind not in AUTHORITY_KINDS:
        raise OneOffError(f"{action.kind} is a one-off (spec 9.4): it needs the player")
    match action:
        case CreatePlan():
            out = apply_org_action(state, action, balance, data)
            return out.state, (), out.log_items
        case SeekWaiver() | SetRatePolicy():
            if isinstance(action, SeekWaiver):
                _check_waiver(state, action, balance)
            m = apply_matter_action(state, action, draws, balance, data)
            return m.state, m.entries, m.log
        case WriteDownMatter():
            b = apply_billing_action(state, action, draws, balance)
            return b.state, b.entries, b.log
        case PitchRfp():
            r = apply_rival_action(state, action, draws, balance, data)
            return r.state, r.entries, r.log


def _check_waiver(state: GameState, action: SeekWaiver, balance: Balance) -> None:
    """A waiver on a matter adverse to a key client is a one-off (spec 9.4)."""
    matter = state.market.matter(action.matter_id)
    if matter is None:
        return
    adverse = matter.adverse_client_id
    if adverse is not None and adverse in key_clients(state.market, matter.firm_id, balance):
        raise OneOffError("a waiver adverse to a key client is a one-off (spec 9.4)")


# --- What the firm can see ---------------------------------------------------------------------


def _members(state: GameState, unit_id: int) -> tuple[int, ...]:
    from ptk.sim.org.actions import unit_members

    out = set(unit_members(state, unit_id))
    for u in state.org.units:
        if u.parent_id == unit_id and u.status == "active":
            out |= set(unit_members(state, u.id))
    return tuple(sorted(out))


def utilisation_bp(
    state: GameState, people: tuple[int, ...], data: GameData, balance: Balance
) -> int | None:
    """Last month's hours over capacity of these fee earners, in bp (None without capacity)."""
    from ptk.sim.matters.staffing import fee_earners

    wanted = set(people)
    capacity = sum(
        f.capacity for f in fee_earners(state, state.player.id, data, balance) if f.id in wanted
    )
    if capacity <= 0:
        return None
    hours = sum(r.tenths for r in state.market.hours if r.person_id in wanted)
    return round(BP * hours / capacity)


def shown_mid(state: GameState, firm_id: int, person_id: int, key: str) -> float:
    reveal = state.reveal(firm_id, person_id)
    if reveal is None:
        return 10.0  # tunable-exempt: the attribute scale's neutral point
    lo, hi = revealed_range(state.person(person_id), reveal, key)
    return (lo + hi) / 2


# --- One holder's month ------------------------------------------------------------------------


@dataclass
class _Holder:
    state: GameState
    firm_id: int
    seat: SeatDef
    slot: int
    person_id: int
    auth: SeatAuthority
    right: bool
    gen: np.random.Generator
    balance: Balance
    data: GameData
    entries: list[LedgerEntry]
    logs: list[LogItem]
    decisions: list[SeatDecision]

    def rail(self, key: str) -> int:
        return self.auth.value(key, self.seat.guardrail(key).default)

    def act(self, action: Act, text: str, mistake: bool = False) -> bool:
        try:
            state, entries, logs = apply_authorised(
                self.state, action, lambda: self.gen, self.balance, self.data
            )
        except SimError:
            return False
        self.state = state
        self.entries += entries
        self.logs += logs
        self.decisions.append(
            SeatDecision(
                turn=state.turn,
                firm_id=self.firm_id,
                seat=self.seat.key,
                slot=self.slot,
                person_id=self.person_id,
                action=action.kind,
                text=text,
                mistake=mistake,
            )
        )
        return True


def _pgl(h: _Holder) -> None:
    state, b, data = h.state, h.balance, h.data
    unit = state.org.unit(h.slot)
    if unit is None or unit.practice is None:
        return
    members = _members(state, unit.id)
    util = utilisation_bp(state, members, data, b)
    if util is None or util < h.rail("busy_bp"):
        return
    if any(p.unit_id == unit.id and p.status == "active" for p in state.org.firm_plans(h.firm_id)):
        return
    room = h.rail("headcount_cap") - len(members)
    want = min(b.authority.hire_step if h.right else b.authority.hire_step - 1, room)
    if want <= 0:
        return
    role = _lawyer_role(data, unit.practice)
    h.act(
        CreatePlan(
            actor_id=h.person_id,
            owner_id=h.person_id,
            role=role,
            target=want,
            channel="any",
            ratio_bp=b.authority.plan_ratio_bp,
            unit_id=unit.id,
        ),
        f"opened a plan for {want} hire(s) in {unit.name} at {util / 100:.0f}% utilisation",
        mistake=not h.right,
    )


def _gc(h: _Holder) -> None:
    if not h.right:
        return  # waits a month
    held = sorted(
        (m for m in h.state.market.matters if m.firm_id == h.firm_id and m.status == "conflicted"),
        key=lambda m: (m.opened_turn, m.id),
    )
    done = 0
    for m in held:
        if done >= h.rail("waivers_per_month"):
            break
        if h.act(SeekWaiver(h.person_id, m.id), f"asked for a waiver on {m.name}"):
            done += 1


def _cfo(h: _Holder) -> None:
    state = h.state
    age = h.rail("aged_months")
    aged = sorted(
        (
            e
            for e in state.billing.engagements
            if e.firm_id == h.firm_id
            and not e.closed
            and e.wip_cents > 0
            and e.writedown_bp == 0
            and e.model not in ("fixed", "retainer", "contingency")
            and state.turn - (e.last_bill_turn if e.last_bill_turn is not None else e.opened_turn)
            >= age
        ),
        key=lambda e: (
            e.last_bill_turn if e.last_bill_turn is not None else e.opened_turn,
            e.matter_id,
        ),
    )
    if not aged:
        return
    pick = aged[0] if h.right or len(aged) == 1 else aged[1]
    bp = min(h.rail("writedown_bp"), h.balance.billing.writedown_max_bp)
    if bp <= 0:
        return
    m = state.market.matter(pick.matter_id)
    name = m.name if m is not None else f"matter {pick.matter_id}"
    h.act(
        WriteDownMatter(h.person_id, pick.matter_id, bp),
        f"wrote down {name}'s next bill by {bp / 100:.0f}%",
        mistake=pick is not aged[0],
    )


def _cmo(h: _Holder) -> None:
    state = h.state
    rfps = [
        r
        for r in state.rivals.rfps
        if r.status == "open" and r.player_invited and r.pitch is None and r.award_turn > state.turn
    ]
    done = 0
    for rfp in sorted(rfps, key=lambda r: r.id):
        if done >= h.rail("rfps_per_month"):
            break
        team = _team(state, h.firm_id, rfp.practices, h.right, h.data)
        if not team:
            continue
        client = state.market.client(rfp.client_id).name
        if h.act(
            PitchRfp(h.person_id, rfp.id, team),
            f"pitched for {client}'s {rfp.kind} RFP",
            mistake=not h.right,
        ):
            done += 1


def _team(
    state: GameState, firm_id: int, practices: tuple[str, ...], right: bool, data: GameData
) -> tuple[int, ...]:
    """The strongest team the firm can see for an RFP: lawyers by displayed pitch skills and
    familiarity in the RFP's practices; a mistake swaps the lead for the second best."""
    scored = []
    for e in state.staff(firm_id):
        p = state.person(e.person_id)
        if e.status != "active" or data.role(p.role).kind != "lawyer" or p.is_founder:
            continue
        skills = sum(shown_mid(state, firm_id, p.id, k) for k in PITCH_SKILLS) / len(PITCH_SKILLS)
        fam = sum(shown_mid(state, firm_id, p.id, fam_key(x)) for x in practices) / len(practices)
        scored.append(((skills + fam) / 2, p.id))
    ranked = [pid for _, pid in sorted(scored, key=lambda x: (-x[0], x[1]))][:TEAM_SIZE]
    if not right and len(ranked) >= 2:
        ranked[0], ranked[1] = ranked[1], ranked[0]
    return tuple(ranked)


def _chro(h: _Holder) -> None:
    state, b, data = h.state, h.balance, h.data
    from ptk.sim.hiring.rules import campus_registration_open

    if not campus_registration_open(state, b):
        return
    size = h.rail("class_size") if h.right else h.rail("class_size") - 1
    if size <= 0:
        return
    for unit in state.org.firm_units(h.firm_id):
        if unit.kind != "practice_group" or unit.leader_id is None or unit.practice is None:
            continue
        if any(p.unit_id == unit.id and p.campus for p in h.state.org.firm_plans(h.firm_id)):
            continue
        h.act(
            CreatePlan(
                actor_id=h.person_id,
                owner_id=unit.leader_id,
                role=_lawyer_role(data, unit.practice),
                target=size,
                channel="campus",
                ratio_bp=b.authority.plan_ratio_bp,
                unit_id=unit.id,
            ),
            f"set {unit.name}'s campus class at {size}",
            mistake=not h.right,
        )


def _lawyer_role(data: GameData, practice: str) -> str:
    for role in data.roles:
        if role.kind == "lawyer" and role.practice == practice:
            return role.key
    return practice


def _pricing(h: _Holder) -> None:
    from ptk.sim.matters.rates import market_rise_bp

    state, b, data = h.state, h.balance, h.data
    if turn_to_ym(state.turn, state.save_meta.start_ym)[1] != DECEMBER:
        return
    year = turn_to_ym(state.turn, state.save_meta.start_ym)[0] + 1  # next January's
    market = market_rise_bp(year, data, b)
    band = h.rail("band_bp")
    people = tuple(e.person_id for e in state.staff(h.firm_id))
    util = utilisation_bp(state, people, data, b) or 0
    rise = market
    if h.right:
        if util >= BUSY_HIGH_BP:
            rise = market + band
        elif util < BUSY_LOW_BP:
            rise = market - band
    rise = max(b.rates.rise_min_bp, min(b.rates.rise_max_bp, rise))
    if state.firm(h.firm_id).rate_rise_bp == rise:
        return
    h.act(
        SetRatePolicy(h.person_id, rise),
        f"set January's rate rise at {rise / 100:+.1f}% (market {market / 100:+.1f}%)",
        mistake=not h.right and rise != market,
    )


RULES: Final[dict[str, Callable[[_Holder], None]]] = {
    PGL: _pgl,
    "general_counsel": _gc,
    "cfo": _cfo,
    "cmo": _cmo,
    "chro": _chro,
    "pricing_director": _pricing,
}


def acting_holders(
    state: GameState, firm_id: int, balance: Balance, data: GameData
) -> list[tuple[SeatDef, int, int, SeatAuthority]]:
    """(seat, slot, holder, authority) of every seat holder with authority, in seats.yaml
    then slot order."""
    from ptk.sim.org.seats import in_play

    out = []
    for seat in data.seats.seats:
        if not seat.has_authority or not in_play(state, firm_id, seat):
            continue
        for slot in slots(state, firm_id, seat, balance):
            a = state.leadership.authority(firm_id, seat.key, slot)
            pid = seated_holder(state, firm_id, seat, slot, balance)
            if a is not None and a.enabled and pid is not None:
                out.append((seat, slot, pid, a))
    return out


def seats_act(
    state: GameState,
    rng: RngFactory,
    balance: Balance,
    data: GameData,
    balances: Mapping[tuple[int, AccountCode], Cents],
) -> SeatRun:
    """Phase 2: each holder with authority runs its seat's rule (the player's firm only)."""
    if state.ended or not state.firms:
        return SeatRun(state)
    firm_id = state.player.id
    entries: list[LedgerEntry] = []
    logs: list[LogItem] = []
    decisions: list[SeatDecision] = []
    for seat, slot, pid, auth in acting_holders(state, firm_id, balance, data):
        rule = RULES.get(seat.key)
        if rule is None:
            continue
        gen = rng.stream(state.turn, "seat_act", seat_index(data, seat.key), firm_id, slot)
        u = float(gen.random())
        right = u < quality(true_score(state.person(pid), seat), balance)
        saved = state.person_state(pid)
        state = with_person_states(
            state, [replace(saved, energy=balance.authority.energy_per_month)]
        )
        h = _Holder(state, firm_id, seat, slot, pid, auth, right, gen, balance, data, [], [], [])
        rule(h)
        state = with_person_states(
            h.state, [replace(h.state.person_state(pid), energy=saved.energy)]
        )
        entries += h.entries
        logs += h.logs
        decisions += h.decisions
    state = remember(state, decisions, balance)
    return SeatRun(state, tuple(entries), tuple(logs), tuple(decisions))


def remember(state: GameState, new: list[SeatDecision], balance: Balance) -> GameState:
    keep_from = state.turn - balance.authority.keep_decision_turns + 1
    kept = tuple(d for d in state.leadership.decisions if d.turn >= keep_from)
    if not new and kept == state.leadership.decisions:
        return state
    return with_leadership(state, replace(state.leadership, decisions=kept + tuple(new)))
