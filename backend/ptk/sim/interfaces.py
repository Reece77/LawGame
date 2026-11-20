"""Small interfaces between lanes (PT-M1b and PT-M2 are built side by side).

The delegate hook (TST formulas.md 13.10, ADR-0015) is how PT-M2's delegated hiring drives
PT-M1b's hiring without reaching into `ptk.sim.hiring`. A delegate (a recruiting manager or a
practice group leader) acts in phase 2 by sending the same requests the player's actions
send, as its own actor, with its own energy and its own random stream (`delegate`, keyed
`(person_id, n)`, where n counts that delegate's actions this turn). Every rule the player
meets applies to the delegate: an offer needs an interview (ADR-0016), campus offers only in
the offer month, energy is spent at once.

Usage from PT-M2 (phase 2):

    hook = delegate_hiring()
    state = hook.set_energy(state, delegate_id, balance_energy)      # the month's budget
    for cand in hook.candidates(state, firm_id, role="corporate_ma"):
        ...rank by what the firm knows (revealed ranges) ...
    result = hook.apply(state, InterviewRequest(cand.candidate_id), actor_id=delegate_id,
                        draws=lambda: rng.stream(turn, "delegate", delegate_id, n),
                        balance=balance, data=data, balances=ctx.balances)
    ctx = ctx.post(*result.entries).log(*result.log); state = result.state

Offers carry a `plan_id` and a `unit_id`; `hook.hires(state, firm_id, turn)` lists the
offers accepted in phase 1 of `turn` with both, so PT-M2 can count plan hires and place each
hire in its unit. Nothing here exposes a hidden true value: candidate views carry only what
the firm can see (the ask is shown exactly, TST 7).

This module holds types only and imports no lane's package at import time; the hiring
implementation is loaded on first use.

PT-M2 (org) adds, at the end: the body of `manager_morale_term`, `org_morale_changes` (the
one-off morale of reorganising, raises and promotions, TST 13.7-13.8) and the pay seam a
raise uses (`salary_cents`, `set_salary`).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Protocol

if TYPE_CHECKING:
    import numpy as np

    from ptk.sim.data_models import Balance, GameData, KindDef
    from ptk.sim.ledger import AccountCode, LedgerEntry
    from ptk.sim.log import LogItem
    from ptk.sim.matters.models import HoursRecord
    from ptk.sim.money import Cents
    from ptk.sim.state import GameState

# Spec 5.7: campus (summer programme, offers in August, start the September after), and the
# lateral channels of TST 7 renamed: a recruiter search (20-25% fee on hire), a job post, a
# referral (TST's network search).
type HiringChannel = Literal["campus", "recruiter", "job_post", "referral"]


# --- Requests a delegate (or the player) sends ------------------------------------------------


@dataclass(frozen=True, slots=True)
class OpenSearchRequest:
    role: str  # roles.yaml key; a lawyer's role is their home practice
    channel: HiringChannel
    level: str | None = None  # lateral target level (balance people.levels); None: the mix
    school_tiers: tuple[str, ...] = ()  # law school tier filter; () = any tier
    plan_id: int | None = None  # the hiring plan the search serves (PT-M2)


@dataclass(frozen=True, slots=True)
class CloseSearchRequest:
    search_id: int


@dataclass(frozen=True, slots=True)
class InterviewRequest:
    candidate_id: int  # the candidate's person id


@dataclass(frozen=True, slots=True)
class ReferenceCheckRequest:
    candidate_id: int


@dataclass(frozen=True, slots=True)
class ScoutRequest:
    """Apply a month of scouting to every open candidate of one search (TST 11.12)."""

    search_id: int


@dataclass(frozen=True, slots=True)
class OfferRequest:
    candidate_id: int
    salary_cents: int  # annual
    plan_id: int | None = None  # the plan a delegate offers under (PT-M2)
    unit_id: int | None = None  # where the hire joins; None = the firm root (PT-M2)


type HiringRequest = (
    OpenSearchRequest
    | CloseSearchRequest
    | InterviewRequest
    | ReferenceCheckRequest
    | ScoutRequest
    | OfferRequest
)


# --- What a delegate can see ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SearchView:
    search_id: int
    firm_id: int
    role: str
    channel: HiringChannel
    opened_turn: int
    plan_id: int | None


@dataclass(frozen=True, slots=True)
class CandidateView:
    """An open candidate as the firm sees it. Rank candidates by the firm's revealed ranges
    (`ptk.sim.people.reveal.revealed_range` on `state.reveal(firm_id, candidate_id)`)."""

    candidate_id: int  # person id
    search_id: int
    role: str
    level: str
    channel: HiringChannel
    ask_cents: int  # the salary they expect (shown exactly, TST 7)
    interviewed: bool  # by anyone at the firm (ADR-0016)
    pending_offer_id: int | None
    offer_allowed: bool  # False for a campus candidate outside the offer month
    plan_id: int | None  # the plan of the search that found them


@dataclass(frozen=True, slots=True)
class HireView:
    """An offer accepted in phase 1: the person joins now, or at `start_turn` (campus)."""

    offer_id: int
    person_id: int
    firm_id: int
    plan_id: int | None
    unit_id: int | None
    accepted_turn: int
    start_turn: int


@dataclass(frozen=True, slots=True)
class HookResult:
    state: GameState
    entries: tuple[LedgerEntry, ...] = ()
    log: tuple[LogItem, ...] = ()


class DelegateHiringHook(Protocol):
    def energy_cost(self, request: HiringRequest, balance: Balance) -> int:
        """Energy the request costs its actor (balance `energy.cost`)."""
        ...

    def energy_left(self, state: GameState, person_id: int) -> int | None:
        """The person's energy this month; None if they do not track energy."""
        ...

    def set_energy(self, state: GameState, person_id: int, energy: int) -> GameState:
        """Give a delegate their month's energy (PT-M2 resets delegates in phase 2)."""
        ...

    def searches(self, state: GameState, firm_id: int) -> tuple[SearchView, ...]:
        """The firm's open searches, by id."""
        ...

    def candidates(
        self, state: GameState, firm_id: int, role: str | None = None
    ) -> tuple[CandidateView, ...]:
        """The firm's open candidates (optionally of one role), by candidate id."""
        ...

    def apply(
        self,
        state: GameState,
        request: HiringRequest,
        *,
        actor_id: int,
        draws: Callable[[], np.random.Generator],
        balance: Balance,
        data: GameData,
        balances: Mapping[tuple[int, AccountCode], Cents],
    ) -> HookResult:
        """Apply one request as `actor_id`, at once (ADR-0014). Raises a `SimError` and
        changes nothing if a rule forbids it. `draws` is called only if the request draws."""
        ...

    def hires(self, state: GameState, firm_id: int, turn: int) -> tuple[HireView, ...]:
        """Offers of the firm accepted in phase 1 of `turn`, by offer id."""
        ...


def delegate_hiring() -> DelegateHiringHook:
    """PT-M1b's implementation of the hook."""
    from ptk.sim.hiring.hook import HIRING_HOOK

    return HIRING_HOOK


def manager_morale_term(
    state: GameState, person_id: int, balance: Balance, data: GameData
) -> float:
    """TST 13.4's manager term in a person's morale target (spec 5.3). PT-M1b's morale calls
    this for every person it updates. PT-M2: W_mgr from the person's supervising partner's
    true leadership, communication and mentoring and their span (0 for the founding partner
    and anyone not on a firm's books)."""
    from ptk.sim.org.rules import supervisor_morale

    return supervisor_morale(state, person_id, balance)


# --- PT-M2 (org): one-off morale changes and pay --------------------------------------------


def org_morale_changes(state: GameState, person_id: int) -> float:
    """One-off morale points from this turn's org actions (TST 13.7 reorganising, 13.8
    raises, pay cuts and promotions), not yet applied. The org adds them to each person's
    current morale (`PersonState.morale`) at the end of phase 8, after PT-M1b's morale step,
    and then clears them, so each counts exactly once. 0 for the founding partner."""
    return sum(n.points for n in state.org.nudges if n.person_id == person_id)


def salary_cents(state: GameState, person_id: int) -> int | None:
    """An employee's annual salary (PT-M1b's `Employment.salary_cents`); None if they are
    not on a firm's books. A raise (TST 13.8) reads it."""
    for e in state.employments:
        if e.person_id == person_id and e.counts_as_staff:
            return e.salary_cents
    return None


def set_salary(state: GameState, person_id: int, salary: int) -> GameState:
    """The state with an employee's annual salary changed, from the next payroll (TST 13.8)."""
    from dataclasses import replace

    from ptk.sim.errors import OrgRuleError
    from ptk.sim.state import with_employment

    for e in state.employments:
        if e.person_id == person_id and e.counts_as_staff:
            return with_employment(state, replace(e, salary_cents=salary))
    raise OrgRuleError(f"person {person_id} is not on a firm's books")


# --- PT-M6 (events): effects whose systems belong to other lanes ------------------------------
#
# An event choice may write down a matter's WIP (PT-M3b's billing), move the firm's reputation
# (PT-M5's rankings) or the partners' confidence in the managing partner (PT-M4). A hook whose
# system has not merged is a no-op: the event's words and choices are unchanged and the effect
# is recorded on the event, but nothing moves. The owning lane replaces the body.


def write_down_wip(
    state: GameState, matter_id: int, pct: float, balance: Balance
) -> tuple[GameState, tuple[LedgerEntry, ...]]:
    """Write down `pct` percent of a matter's time on its next bill, through PT-M3b's
    write-down (spec 7.7): the engagement's `writedown_bp` rises to at least pct x 100, held to
    billing.writedown_max_bp; fixed, retainer and contingency matters are not billed by the
    hour and are unchanged. No energy is spent (the event's choice is the decision); the
    ledger moves when the bill goes out."""
    from dataclasses import replace

    e = state.billing.engagement(matter_id)
    if e is None or e.closed or e.model in ("fixed", "retainer", "contingency"):
        return state, ()
    bp = min(
        balance.billing.writedown_max_bp, max(e.writedown_bp, round(pct * 100))
    )  # tunable-exempt: % to bp
    engagements = tuple(
        replace(x, writedown_bp=bp) if x.matter_id == matter_id else x
        for x in state.billing.engagements
    )
    return replace(state, billing=replace(state.billing, engagements=engagements)), ()


def reputation_change(state: GameState, firm_id: int, points: float) -> GameState:
    """Move a firm's reputation by `points` (PT-M5). No-op until rankings arrive."""
    return state


def confidence_change(state: GameState, firm_id: int, points: float) -> GameState:
    """Move the partners' confidence in the managing partner by `points` (PT-M4). No-op until
    the partnership arrives."""
    return state


# --- PT-M3b (billing): what billing reads of matters, and the relationship it moves --------


@dataclass(frozen=True, slots=True)
class MatterBillingView:
    """A named matter as billing sees it (lane B reads matters only through this). Carries
    no hidden value: never merits, opposing quality or the outcome chance."""

    matter_id: int
    firm_id: int
    client_id: int
    practice: str
    kind: str  # deal, case, investigation, restructuring, advisory, filing
    kind_key: str
    name: str
    status: str  # open, conflicted, closed, declined
    outcome: str | None
    opened_turn: int
    closed_turn: int | None
    planned_months: int
    expected_fees_cents: int  # at standard rates
    stakes_cents: int  # cases: the amount in dispute
    lead_id: int | None
    progress: float  # 0-1: the share of the matter's phases completed
    phases_done: int  # phases completed
    done_share: float  # 0-1: the hours shares of the phases completed (fixed fees bill by it)
    settlement_bp: int | None  # the other side's open offer, as a share of the stakes


@dataclass(frozen=True, slots=True)
class ClientBillingView:
    """A client as billing sees it: size, price sensitivity and its general counsel's
    temperament and integrity (engine-only; never shown)."""

    client_id: int
    name: str
    real: bool
    size_class: str  # large, mid
    price_sensitivity: float  # 1-20
    gc_temperament: float  # 1-20
    gc_integrity: float  # 1-20


def billing_matters(
    state: GameState, firm_id: int, data: GameData
) -> tuple[MatterBillingView, ...]:
    """The firm's named matters that are open, or closed in the turn being played, by id."""
    from ptk.sim.matters.staffing import completed_share

    out: list[MatterBillingView] = []
    turn = state.turn
    for m in state.market.matters:
        if m.firm_id != firm_id or not (m.is_open or m.closed_turn == turn):
            continue
        out.append(
            MatterBillingView(
                matter_id=m.id,
                firm_id=m.firm_id,
                client_id=m.client_id,
                practice=m.practice,
                kind=m.kind,
                kind_key=m.kind_key,
                name=m.name,
                status=m.status,
                outcome=m.outcome,
                opened_turn=m.opened_turn,
                closed_turn=m.closed_turn,
                planned_months=m.planned_months,
                expected_fees_cents=m.expected_fees_cents,
                stakes_cents=m.stakes_cents,
                lead_id=m.lead_id,
                progress=completed_share(m, data.market.kinds[m.kind]),
                phases_done=m.phase_index,
                done_share=_done_share(m.phase_index, data.market.kinds[m.kind]),
                settlement_bp=None if m.settlement is None else m.settlement.fraction_bp,
            )
        )
    return tuple(out)


def billing_matter(state: GameState, matter_id: int, data: GameData) -> MatterBillingView | None:
    """One matter of any firm and status (for actions and views), or None."""
    from ptk.sim.matters.staffing import completed_share

    m = state.market.matter(matter_id)
    if m is None:
        return None
    return MatterBillingView(
        matter_id=m.id,
        firm_id=m.firm_id,
        client_id=m.client_id,
        practice=m.practice,
        kind=m.kind,
        kind_key=m.kind_key,
        name=m.name,
        status=m.status,
        outcome=m.outcome,
        opened_turn=m.opened_turn,
        closed_turn=m.closed_turn,
        planned_months=m.planned_months,
        expected_fees_cents=m.expected_fees_cents,
        stakes_cents=m.stakes_cents,
        lead_id=m.lead_id,
        progress=completed_share(m, data.market.kinds[m.kind]),
        phases_done=m.phase_index,
        done_share=_done_share(m.phase_index, data.market.kinds[m.kind]),
        settlement_bp=None if m.settlement is None else m.settlement.fraction_bp,
    )


def _done_share(phase_index: int, kind: KindDef) -> float:
    return min(1.0, sum(p.share for p in kind.phases[:phase_index]))


def blended_rate_cents(practice: str, kind_key: str, data: GameData) -> int:
    """Cents an hour of a matter kind's task mix staffed at its natural levels (PT-M3a's
    rate card): the base of a blended-rate engagement."""
    from ptk.sim.matters import formulas as fx

    pdef = data.practice(practice)
    kind = data.market.kinds[pdef.kind(kind_key).kind]
    return round(fx.blended_rate(pdef, fx.kind_tasks(kind), data))


def billing_client(state: GameState, client_id: int) -> ClientBillingView:
    c = state.market.client(client_id)
    return ClientBillingView(
        client_id=c.id,
        name=c.name,
        real=c.real,
        size_class=c.size_class,
        price_sensitivity=c.price_sensitivity,
        gc_temperament=c.gc.personality["temperament"],
        gc_integrity=c.gc.personality["integrity"],
    )


def month_hours(state: GameState, firm_id: int) -> tuple[HoursRecord, ...]:
    """The hours of the month being played (PT-M3a's records, sorted by person, matter):
    each record's `value_cents` is tenths x rate / 10, rounded once (ADR PT-0005 3)."""
    staff = set(state.staff_ids(firm_id))
    turn = state.turn
    return tuple(r for r in state.market.hours if r.turn == turn and r.person_id in staff)


def relationship_partner(state: GameState, client_id: int, firm_id: int) -> int | None:
    rel = state.market.relationship(client_id, firm_id)
    return None if rel is None else rel.partner_id


def bump_relationship(state: GameState, client_id: int, firm_id: int, points: float) -> GameState:
    """Move a client's relationship with the firm (billing write-downs and disputes)."""
    from dataclasses import replace

    from ptk.sim.matters.intake import bump

    return replace(state, market=bump(state.market, client_id, firm_id, points))


def relationship_score(state: GameState, client_id: int, firm_id: int) -> float:
    """The client's relationship with the firm, 0-100 (0 without one)."""
    rel = state.market.relationship(client_id, firm_id)
    return 0.0 if rel is None else rel.score


def fee_earner_capacity_tenths(
    state: GameState, firm_id: int, data: GameData, balance: Balance
) -> int:
    """The month's capacity of the firm's lawyers and paralegals, in tenths (utilisation's
    denominator, ADR PT-0005 4)."""
    from ptk.sim.matters.staffing import fee_earners

    return sum(f.capacity for f in fee_earners(state, firm_id, data, balance))
