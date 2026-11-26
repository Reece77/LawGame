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
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Final, Literal, Protocol

if TYPE_CHECKING:
    import numpy as np

    from ptk.sim.data_models import Balance, GameData, KindDef
    from ptk.sim.ledger import AccountCode, LedgerEntry
    from ptk.sim.log import LogItem
    from ptk.sim.matters.models import HoursRecord
    from ptk.sim.money import Cents
    from ptk.sim.rng import RngFactory
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
    from ptk.sim.org.seats import associate_morale

    # PT-M8: an associate's practice group leader and the CHRO (spec 9.1)
    return supervisor_morale(state, person_id, balance) + associate_morale(
        state, person_id, balance, data
    )


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


def reputation_change(state: GameState, firm_id: int, points: float, balance: Balance) -> GameState:
    """Move a firm's reputation by `points` in every practice (PT-M16, spec 12.1): an event's
    choice. The cause is remembered for the player's Practices screen."""
    from ptk.sim.reputation.formulas import apply_pulse

    return apply_pulse(state, firm_id, points, "an event", balance)


def confidence_change(state: GameState, firm_id: int, points: float) -> GameState:
    """Move the partners' confidence in the managing partner by `points` (PT-M4): a one-off
    nudge each equity partner but the MP takes at the next monthly update."""
    from dataclasses import replace

    from ptk.sim.partnership.models import with_firm_partnership, with_partner

    fp = state.partnership.of(firm_id)
    if fp is None or points == 0:
        return state
    for p in fp.equity_partners:
        if p.person_id != fp.mp_id:
            fp = with_partner(fp, replace(p, nudge=p.nudge + points))
    return replace(state, partnership=with_firm_partnership(state.partnership, fp))


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
    sector: str = ""  # PT-M7b: the crisis factor reads the client's sector


def billing_matters(
    state: GameState, firm_id: int, data: GameData
) -> tuple[MatterBillingView, ...]:
    """The firm's named matters that are open, or closed in the turn being played, by id."""
    from ptk.sim.matters.staffing import completed_share

    out: list[MatterBillingView] = []
    turn = state.turn
    for m in state.market.matters:
        if m.firm_id != firm_id or not (m.is_open or m.closed_turn == turn) or m.pro_bono:
            continue  # PT-M7a: pro bono matters are never billed
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


def blended_rate_cents(
    practice: str, kind_key: str, data: GameData, rate_index: float = 1.0
) -> int:
    """Cents an hour of a matter kind's task mix staffed at its natural levels (PT-M3a's
    rate card, times the firm's rate index from PT-M7a): the base of a blended-rate
    engagement."""
    from ptk.sim.matters import formulas as fx

    pdef = data.practice(practice)
    kind = data.market.kinds[pdef.kind(kind_key).kind]
    return round(fx.blended_rate(pdef, fx.kind_tasks(kind), data) * rate_index)


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
        sector=c.sector,
    )


def month_hours(state: GameState, firm_id: int) -> tuple[HoursRecord, ...]:
    """The hours of the month being played (PT-M3a's records, sorted by person, matter):
    each record's `value_cents` is tenths x rate / 10, rounded once (ADR PT-0005 3)."""
    from ptk.sim.matters.models import PRO_BONO_CLIENT_ID

    staff = set(state.staff_ids(firm_id))
    turn = state.turn
    return tuple(  # PT-M7a: pro bono hours have no value and are not billable
        r
        for r in state.market.hours
        if r.turn == turn and r.person_id in staff and r.client_id != PRO_BONO_CLIENT_ID
    )


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


# --- PT-M4 (partnership): partner flight, approaches, counter-offers, departures -----------
#
# Spec 8.7 and 5.7. PT-M4 builds the machinery with approaches from the static panel firms
# (clients.yaml panel_firms); PT-M5's rival firms reuse it unchanged, in both directions:
#
#     hook = partner_flight()
#     p = hook.leave_chance_bp(state, partner_id, balance, data)     # engine-only, never shown
#     v = hook.market_value_cents(state, partner_id, balance, data)  # engine-only, never shown
#     res = hook.approach(state, ApproachRequest(partner_id, Suitor("skadden", "Skadden"),
#                                                offer_comp_cents=v), balance=balance, data=data)
#     ... the target firm counters (the player's action, or a rival's AI) ...
#     res = hook.counter(state, CounterOffer(approach_id, comp_cents=...), balance=balance,
#                        data=data)
#     ... at the deadline the partner decides (stream `poach`, keyed (person_id,)) ...
#     res = hook.resolve(state, approach_id, draws=..., balance=balance, data=data,
#                        balances=ctx.balances)
#
# A departure (`depart`, or a resolved approach the partner accepts) ends the employment
# (reason "poached"), schedules the partner's capital return over 3 years, records the
# departure for contagion, and sends the portable share of their clients after them over
# 3-12 months. `arrive` is the reverse: a lateral partner joins a firm with a guarantee,
# their book's clients imported (conflicts, ADR PT-0009 4) and realised over 12-24 months
# (stream `lateral`). Views carry only what the firm may see: never portability, true
# market value or a true vote utility (CLAUDE.md section 10).

type ApproachStatus = Literal["open", "countered", "stayed", "left", "withdrawn"]
type DepartureReason = Literal[
    "approach", "flight", "up_or_out", "de_equitised", "retired", "expelled", "dissolved"
]


@dataclass(frozen=True, slots=True)
class Suitor:
    """Who makes an approach or receives a departing partner."""

    key: str  # a static panel firm's key (PT-M4) or a rival_key (PT-M5)
    name: str
    firm_id: int | None = None  # a rival firm on the books (PT-M5); None: a static panel firm


@dataclass(frozen=True, slots=True)
class ApproachRequest:
    person_id: int  # a partner (equity or income) of the target firm
    suitor: Suitor
    offer_comp_cents: int  # comp a year the suitor offers
    guarantee_years: int = 0  # years of that comp guaranteed (0-3)
    respond_by_turn: int | None = None  # None: balance partnership.flight.answer_months


@dataclass(frozen=True, slots=True)
class CounterOffer:
    """The target firm's answer to an approach (spec 8.7: points, a seat, a guarantee)."""

    approach_id: int
    comp_cents: int = 0  # extra comp a year (a promise the December comp round honours)
    points: float = 0.0  # extra lockstep points from the next allocation
    guarantee_years: int = 0  # years the counter's comp is guaranteed (account 2700)
    seat: bool = False  # a seat (v2's seats; recorded and counted in the decision only)


@dataclass(frozen=True, slots=True)
class ApproachView:
    approach_id: int
    firm_id: int  # the target firm
    person_id: int
    suitor: Suitor
    offer_comp_cents: int  # what the suitor offers (the partner tells the firm)
    guarantee_years: int
    made_turn: int
    respond_by_turn: int
    status: ApproachStatus
    counter: CounterOffer | None
    stay_label: str  # "likely to stay", "undecided", "likely to go": a band, never a number


@dataclass(frozen=True, slots=True)
class DepartureView:
    person_id: int
    firm_id: int  # the firm they left
    suitor: Suitor | None  # where they went; None: out of the market (retired, in-house)
    turn: int
    practice: str  # their home practice
    reason: DepartureReason
    client_ids: tuple[int, ...]  # clients that follow (over the coming months), by id


@dataclass(frozen=True, slots=True)
class LateralArrival:
    """A partner joining a firm laterally (PT-M4's lateral market; PT-M5's rivals' people)."""

    person_id: int  # already in state.people; employed elsewhere or not at all
    firm_id: int  # the joining firm
    from_suitor: Suitor | None  # the firm they come from; None: the open lateral market
    comp_cents: int  # comp a year agreed
    guarantee_years: int = 0  # years guaranteed (account 2700)
    equity: bool = True  # equity or income partner
    client_ids: tuple[int, ...] = ()  # their book's clients (to import and realise), by id


class PartnerFlightHook(Protocol):
    def leave_chance_bp(
        self, state: GameState, person_id: int, balance: Balance, data: GameData
    ) -> int:
        """Spec 8.7's monthly p_leave for a partner, in bp. Engine-only: never shown."""
        ...

    def market_value_cents(
        self, state: GameState, person_id: int, balance: Balance, data: GameData
    ) -> int:
        """V_mkt: what a rival would pay a year for the partner's book and skills (book x
        the lateral market's multiple). Engine-only: the API shows a band."""
        ...

    def approach(
        self, state: GameState, request: ApproachRequest, *, balance: Balance, data: GameData
    ) -> HookResult:
        """Open an approach the target firm can counter. Raises a `SimError` if the person
        is not a partner, or already has an open approach."""
        ...

    def counter(
        self, state: GameState, offer: CounterOffer, *, balance: Balance, data: GameData
    ) -> HookResult:
        """Record the target firm's counter-offer (replaces an earlier one)."""
        ...

    def resolve(
        self,
        state: GameState,
        approach_id: int,
        *,
        draws: Callable[[], np.random.Generator],
        balance: Balance,
        data: GameData,
        balances: Mapping[tuple[int, AccountCode], Cents],
    ) -> HookResult:
        """The partner decides: stays (any counter is honoured) or leaves (`depart`)."""
        ...

    def depart(
        self,
        state: GameState,
        person_id: int,
        suitor: Suitor | None,
        reason: DepartureReason,
        *,
        draws: Callable[[], np.random.Generator],
        balance: Balance,
        data: GameData,
        balances: Mapping[tuple[int, AccountCode], Cents],
    ) -> HookResult:
        """A partner leaves now: employment ends, capital return scheduled, clients follow."""
        ...

    def arrive(
        self,
        state: GameState,
        arrival: LateralArrival,
        *,
        draws: Callable[[], np.random.Generator],
        balance: Balance,
        data: GameData,
        balances: Mapping[tuple[int, AccountCode], Cents],
    ) -> HookResult:
        """A lateral partner joins: employment, capital due, guarantee, book realised."""
        ...

    def approaches(self, state: GameState, firm_id: int) -> tuple[ApproachView, ...]:
        """The firm's partners' approaches that are open or countered, by id."""
        ...

    def departures(
        self, state: GameState, firm_id: int, since_turn: int
    ) -> tuple[DepartureView, ...]:
        """Partners who left the firm from `since_turn` on, by (turn, person id)."""
        ...


def partner_flight() -> PartnerFlightHook:
    """PT-M4's implementation of the hook (ptk.sim.partnership.flight)."""
    from ptk.sim.partnership.flight import FLIGHT_HOOK

    return FLIGHT_HOOK


def has_sponsor(state: GameState, person_id: int) -> bool:
    """Whether an associate has a partnership sponsor (spec 5.3's prospects term, 5.5)."""
    firm = state.employer_of(person_id)
    fp = state.partnership.of(firm) if firm is not None else None
    return fp is not None and fp.sponsor_of(person_id) is not None


# --- PT-M8 (seats): the one seam other lanes' systems read seats through -------------------


def seat_effect(
    state: GameState,
    firm_id: int,
    seat_key: str,
    balance: Balance,
    data: GameData,
    *,
    unit_id: int | None = None,
) -> float:
    """The spec's seat effect `e` (spec 9.1, TST 18.3): clamp((s - 10) / 8, -0.5, 1) from the
    holder's true seat score, -0.5 for a seat vacant from its stage, 0 before its stage (and
    for rival firms). A practice group leader's needs the group's `unit_id`; the executive
    committee's is its members' mean. Engine-only: never sent to the API or a prompt."""
    from ptk.sim.org.seats import effect

    return effect(state, firm_id, seat_key, balance, data, slot=unit_id)


def practice_leader_effect(
    state: GameState, firm_id: int, practice: str, balance: Balance, data: GameData
) -> float:
    """The practice group leader's `e` for the group of a practice (0 without a group)."""
    from ptk.sim.org.seats import group_effect

    return group_effect(state, firm_id, practice, balance, data)


# --- PT-M17 (founder's life and succession, lane C): what lane C reads and asks of the
# partnership (PT-M4), without editing `ptk.sim.partnership` ---------------------------------
#
# The founder's personal book mirrors their draws, true-up, capital and capital return from
# the partnership's sub-ledgers (`partner_account`); succession and the retirement-age vote run
# through PT-M4's vote functions (`open_partnership_vote`, `election_utility`,
# `election_noise`, `record_vote`); the hand-over is PT-M4's `hand_over`; a retiring partner
# leaves through the flight hook's `depart` (reason "retired"). Views carry nothing hidden
# except where marked engine-only.


@dataclass(frozen=True, slots=True)
class PartnerAccountView:
    """A partner's (or a departed partner's) accounts in the partnership's sub-ledgers."""

    person_id: int
    firm_id: int
    equity: bool
    partner: bool  # still a partner (False: left, with a capital return running)
    drawn_ytd_cents: int
    current_cents: int  # 2700: allocated, not yet paid
    capital_cents: int  # 3000: paid in
    comp_last_cents: int  # the last December allocation
    return_current_cents: int  # a departed partner's current account still to be repaid
    return_capital_cents: int  # and their capital


def partner_account(state: GameState, firm_id: int, person_id: int) -> PartnerAccountView | None:
    fp = state.partnership.of(firm_id)
    if fp is None:
        return None
    p = fp.partner(person_id)
    ret = next((r for r in fp.capital_returns if r.person_id == person_id), None)
    if p is None and ret is None:
        return None
    return PartnerAccountView(
        person_id=person_id,
        firm_id=firm_id,
        equity=p is not None and p.equity,
        partner=p is not None,
        drawn_ytd_cents=p.drawn_ytd_cents if p else 0,
        current_cents=p.current_cents if p else 0,
        capital_cents=p.capital_cents if p else 0,
        comp_last_cents=p.comp_last_cents if p else 0,
        return_current_cents=ret.remaining_current_cents if ret else 0,
        return_capital_cents=ret.remaining_capital_cents if ret else 0,
    )


def equity_partner_ids(state: GameState, firm_id: int) -> tuple[int, ...]:
    fp = state.partnership.of(firm_id)
    return () if fp is None else tuple(p.person_id for p in fp.equity_partners)


def managing_partner(state: GameState, firm_id: int) -> int | None:
    fp = state.partnership.of(firm_id)
    return None if fp is None else fp.mp_id


def set_managing_partner(state: GameState, firm_id: int, person_id: int) -> GameState:
    """The MP seat passes to `person_id` (a succession the partnership elected): a clean
    slate, no ousted founder and no open election result."""
    from dataclasses import replace

    from ptk.sim.partnership.models import with_firm_partnership

    fp = state.partnership.of(firm_id)
    if fp is None:
        return state
    fp = replace(fp, mp_id=person_id, ousted_mp_id=None, election_lost_turn=None)
    return replace(state, partnership=with_firm_partnership(state.partnership, fp))


def ousted_founder(state: GameState, firm_id: int) -> bool:
    """The player lost an MP election and has not answered it (ADR PT-0007 3)."""
    fp = state.partnership.of(firm_id)
    return fp is not None and fp.election_lost_turn is not None


def retirement_age(state: GameState, firm_id: int, balance: Balance) -> int:
    """The agreement's mandatory retirement age (spec 8.6)."""
    fp = state.partnership.of(firm_id)
    return (
        balance.partnership.agreement.retirement_age if fp is None else fp.agreement.retirement_age
    )


def hand_over(
    state: GameState, firm_id: int, founder_id: int, successor_id: int, balance: Balance
) -> GameState:
    """PT-M4's hand-over (TST 45.5's play the heir): the player flag and the month's energy
    pass to the successor; the old player keeps their partnership."""
    from ptk.sim.partnership.actions import hand_over as _hand_over

    return _hand_over(state, firm_id, founder_id, successor_id, balance)


def open_partnership_vote(
    state: GameState,
    firm_id: int,
    kind: Literal["terms", "election"],
    subject_id: int | None,
    params: Mapping[str, str | int | float | bool],
) -> tuple[GameState, int]:
    """Open a vote with PT-M4's `open_vote` (its threshold from the agreement). A "terms"
    vote counts in phase 1 like any (PT-M4); an "election" vote is never counted by PT-M4's
    phases (elections run in phase 10 from the MP's term), so the caller counts it."""
    from ptk.sim.partnership.governance import open_vote

    state, vote = open_vote(state, firm_id, kind, subject_id, dict(params))
    return state, vote.id


def open_vote_kinds(state: GameState, firm_id: int) -> tuple[tuple[int, str, str | None], ...]:
    """Open votes as (vote id, kind, term) for a lane that must not open the same twice."""
    fp = state.partnership.of(firm_id)
    if fp is None:
        return ()
    out = []
    for v in fp.votes:
        if v.status == "open":
            term = v.param("term")
            out.append((v.id, v.kind, term if isinstance(term, str) else None))
    return tuple(out)


def election_utility(
    state: GameState, firm_id: int, vote_id: int, person_id: int, balance: Balance, data: GameData
) -> float:
    """PT-M4's utility of one partner for an open election vote (their confidence in the
    MP, lobbying): engine-only, never shown."""
    from ptk.sim.partnership.governance import base_utility

    fp = state.partnership.of(firm_id)
    assert fp is not None
    vote = fp.vote(vote_id)
    p = fp.partner(person_id)
    assert vote is not None and p is not None
    return base_utility(state, fp, vote, p, balance, data)


def election_noise(
    rng: RngFactory, turn: int, vote_id: int, person_id: int, balance: Balance
) -> float:
    """PT-M4's vote noise (stream `vote`, keyed (vote_id, person_id); its one call site)."""
    from ptk.sim.partnership.governance import vote_noise

    return vote_noise(rng, turn, vote_id, person_id, balance.partnership.votes.noise_sd)


def vote_weight(state: GameState, firm_id: int, person_id: int) -> float:
    """A partner's weight under the agreement's voting rule (per capita, or points)."""
    fp = state.partnership.of(firm_id)
    p = fp.partner(person_id) if fp is not None else None
    if fp is None or p is None or not p.equity:
        return 0.0
    return p.points if fp.agreement.voting == "points" else 1.0


def vote_threshold_bp(state: GameState, firm_id: int, vote_id: int) -> int:
    fp = state.partnership.of(firm_id)
    vote = fp.vote(vote_id) if fp is not None else None
    assert vote is not None
    return vote.threshold_bp


def record_vote(
    state: GameState,
    firm_id: int,
    vote_id: int,
    ballots: tuple[tuple[int, bool], ...],
    yes: float,
    no: float,
    passed: bool,
) -> GameState:
    """Write a counted vote back (the partnership's record: status, weights, ballots)."""
    from dataclasses import replace

    from ptk.sim.partnership.models import with_firm_partnership, with_vote

    fp = state.partnership.of(firm_id)
    vote = fp.vote(vote_id) if fp is not None else None
    assert fp is not None and vote is not None
    vote = replace(
        vote,
        status="passed" if passed else "failed",
        resolved_turn=state.turn,
        yes_weight=yes,
        no_weight=no,
        ballots=tuple(sorted(ballots)),
    )
    return replace(state, partnership=with_firm_partnership(state.partnership, with_vote(fp, vote)))


def withdraw_vote(state: GameState, firm_id: int, vote_id: int) -> GameState:
    from dataclasses import replace

    from ptk.sim.partnership.models import with_firm_partnership, with_vote

    fp = state.partnership.of(firm_id)
    vote = fp.vote(vote_id) if fp is not None else None
    if fp is None or vote is None or vote.status != "open":
        return state
    vote = replace(vote, status="withdrawn", resolved_turn=state.turn)
    return replace(state, partnership=with_firm_partnership(state.partnership, with_vote(fp, vote)))


def rival_nominee(
    state: GameState, firm_id: int, balance: Balance, exclude: frozenset[int]
) -> int | None:
    """PT-M4's rival candidate: the most ambitious equity partner not excluded."""
    from ptk.sim.partnership.election import rival_candidate

    fp = state.partnership.of(firm_id)
    return None if fp is None else rival_candidate(state, fp, balance, set(exclude))


def candidate_rating(state: GameState, firm_id: int, person_id: int, data: GameData) -> float:
    """A candidate's ability as the firm sees it, 1-20 (PT-M4's `candidate_quality`)."""
    from ptk.sim.partnership.governance import candidate_quality

    return candidate_quality(state, firm_id, person_id, data)


def predict_k(balance: Balance) -> float:
    """PT-M4's band of indifference for a predicted vote range."""
    return balance.partnership.votes.predict_k


def retire_partner(
    state: GameState,
    person_id: int,
    *,
    draws: Callable[[], np.random.Generator],
    balance: Balance,
    data: GameData,
    balances: Mapping[tuple[int, AccountCode], Cents],
) -> HookResult:
    """A partner retires (spec 2.5, 8.6): PT-M4's departure with reason "retired" and no
    suitor (their clients pass to a colleague; capital and current account repaid over
    three years)."""
    return partner_flight().depart(
        state,
        person_id,
        None,
        "retired",
        draws=draws,
        balance=balance,
        data=data,
        balances=balances,
    )


@dataclass(frozen=True, slots=True)
class PartnershipMonthView:
    """What the partnership did this turn that moves the founder's persona (spec 2.3).
    `unhappy` counts equity partners unhappy with their December share (engine-only)."""

    deequitisations: int  # de-equitisation votes passed this turn
    laterals_hired: tuple[tuple[int, int], ...]  # (person id, guarantee years), hired this turn
    counter_guarantees: int  # counter-offers with a guarantee that kept a partner this turn
    breach_started: bool  # a covenant breach's first month
    revolver_drawn_cents: int
    facility_cents: int
    unhappy: int
    equity_partners: int
    last_revenue_cents: int | None


def partnership_month(
    state: GameState, firm_id: int, balances: Mapping[tuple[int, AccountCode], Cents]
) -> PartnershipMonthView | None:
    from ptk.sim.ledger import REVOLVER

    fp = state.partnership.of(firm_id)
    if fp is None:
        return None
    turn = state.turn
    return PartnershipMonthView(
        deequitisations=sum(
            1
            for v in fp.votes
            if v.kind == "deequity" and v.status == "passed" and v.resolved_turn == turn
        ),
        laterals_hired=tuple(
            (c.person_id, c.offer_guarantee_years)
            for c in fp.laterals
            if c.status == "hired" and c.resolved_turn == turn
        ),
        counter_guarantees=sum(
            1
            for a in fp.approaches
            if a.countered
            and a.counter_guarantee_years > 0
            and a.status == "stayed"
            and a.resolved_turn == turn
        ),
        breach_started=fp.breach_months == 1 and fp.called_turn is None,
        revolver_drawn_cents=-balances.get((firm_id, REVOLVER), 0),
        facility_cents=fp.facility_cents,
        unhappy=sum(1 for p in fp.equity_partners if p.satisfaction < 0),
        equity_partners=len(fp.equity_partners),
        last_revenue_cents=fp.last_revenue_cents,
    )


def partner_ids(state: GameState, firm_id: int) -> tuple[int, ...]:
    """Every current partner (equity and income), by person id."""
    fp = state.partnership.of(firm_id)
    return () if fp is None else tuple(p.person_id for p in fp.partners)


def partner_confidence(state: GameState, firm_id: int, person_id: int) -> float | None:
    """An equity partner's confidence in the MP, 0-100. Engine-only: never shown."""
    fp = state.partnership.of(firm_id)
    p = fp.partner(person_id) if fp is not None else None
    return None if p is None or not p.equity else p.confidence


def terms_bias(balance: Balance) -> tuple[float, float]:
    """PT-M4's (confidence weight, status-quo bias) for a vote on the agreement's terms."""
    v = balance.partnership.votes
    return v.confidence_weight, v.terms_bias


def clear_election_result(state: GameState, firm_id: int) -> GameState:
    """The player has answered a lost MP election (PT-M4's ElectionChoice does the same)."""
    from dataclasses import replace

    from ptk.sim.partnership.models import with_firm_partnership

    fp = state.partnership.of(firm_id)
    if fp is None:
        return state
    fp = replace(fp, election_lost_turn=None)
    return replace(state, partnership=with_firm_partnership(state.partnership, fp))


# --- PT-M17's effects on hiring (spec 2.3: the persona, the foundation and bar politics) ----


def founder_recruiting_term(state: GameState, firm_id: int, balance: Balance) -> float:
    """Offer-score points the player's founding partner adds to every offer of their firm:
    Visionary at the effect line, an education or local foundation's grants, influence.
    0 for any other firm, and for a founder with none of these."""
    from ptk.sim.founder import foundation, influence, persona

    if firm_id != state.player.id:
        return 0.0
    pid = state.founder_of(firm_id)
    if pid is None:
        return 0.0
    fl = state.founder_life
    life = fl.life(pid)
    return (
        persona.recruiting_points(life, balance)
        + foundation.recruiting_points(fl.foundation(pid), state.turn, balance)
        + influence.recruiting_points(life, balance)
    )


def founder_resign_mult(state: GameState, firm_id: int, balance: Balance) -> float:
    """The player's resignation factor: Beloved at the effect line, an access-to-justice or
    health foundation's grants. 1.0 for any other firm."""
    from ptk.sim.founder import foundation, persona

    if firm_id != state.player.id:
        return 1.0
    pid = state.founder_of(firm_id)
    if pid is None:
        return 1.0
    fl = state.founder_life
    return persona.resign_mult(fl.life(pid), balance) * foundation.resign_mult(
        fl.foundation(pid), state.turn, balance
    )


@dataclass(frozen=True, slots=True)
class VoteSummary:
    """A partnership vote as lane C reads it (the adviser): no utilities, no ballots."""

    vote_id: int
    kind: str
    status: str
    opened_turn: int
    resolved_turn: int | None
    title: str
    succession: bool  # a succession election (PT-M17's own)


def partnership_votes(state: GameState, firm_id: int) -> tuple[VoteSummary, ...]:
    from ptk.sim.partnership.governance import vote_title

    fp = state.partnership.of(firm_id)
    if fp is None:
        return ()
    return tuple(
        VoteSummary(
            v.id,
            v.kind,
            v.status,
            v.opened_turn,
            v.resolved_turn,
            vote_title(state, v),
            bool(v.param("succession")),
        )
        for v in fp.votes
    )


def terms_threshold_bp(state: GameState, firm_id: int, balance: Balance) -> int:
    """The agreement's threshold for a change to its terms."""
    fp = state.partnership.of(firm_id)
    return balance.partnership.agreement.terms_bp if fp is None else fp.agreement.terms_bp


# --- PT-M16 (reputation, press and rankings, lane C): what lane C reads of rivals -----------
#
# Thin, read-only views of the rival firms (PT-M5), so reputation, the press and the rankings
# never reach into `ptk.sim.rivals`. Only public figures and labels: a rival's lawyers by
# practice (its pools, the legal press's headcounts), its trailing revenue and profit (Am Law's
# figures), its strong practices (firms.yaml, the dossier) and the key people the press may
# name. Never demand, shocks, books or hidden traits.


@dataclass(frozen=True, slots=True)
class RivalStandingView:
    firm_id: int
    rival_key: tuple[int, ...]  # its stable stream key (ADR-0013 amendment)
    key: str
    name: str
    short: str
    kind: str  # real, generated, boutique
    lawyers: tuple[tuple[str, float], ...]  # by practice, practices.yaml order
    revenue_12m_cents: int
    profit_12m_cents: int
    equity_partners: float
    strong: frozenset[str]
    departures: int  # key partners who left it this month
    lost_to_player: int  # key partners the player's firm has hired from it, ever
    founded_turn: int
    personality: str
    associates: float
    utilisation: float  # its lawyers' hours over capacity (the associates' survey reads it)
    years: tuple[tuple[int, int, int, int], ...]  # fiscal years: (year, revenue, lawyers, pep)

    @property
    def total_lawyers(self) -> float:
        return sum(n for _, n in self.lawyers)

    def in_practice(self, practice: str) -> float:
        return next((n for p, n in self.lawyers if p == practice), 0.0)


_STANDING_MEMO: dict[str, tuple[object, int, tuple[RivalStandingView, ...]]] = {}


def rival_standing(state: GameState, data: GameData) -> tuple[RivalStandingView, ...]:
    """Every active rival, by firm id (PT-M16); memoised on the rivals' state and the turn (a
    month reads it several times)."""
    hit = _STANDING_MEMO.get("last")
    if hit is not None and hit[0] is state.rivals and hit[1] == state.turn:
        return hit[2]
    views = _rival_standing(state, data)
    _STANDING_MEMO["last"] = (state.rivals, state.turn, views)
    return views


def _rival_standing(state: GameState, data: GameData) -> tuple[RivalStandingView, ...]:
    from ptk.sim.geo.cities import rival_region
    from ptk.sim.rivals.market import strong_practices

    turn = state.turn
    out = []
    defs = {d.key: d for d in data.rivals.firms.firms}  # T12: once, not per firm
    for f in state.rivals.active:
        if rival_region(data, f.hq) != "us":  # PT-M11: the US tables, reputation and press
            continue
        out.append(
            RivalStandingView(
                firm_id=f.id,
                rival_key=f.rival_key,
                key=f.key,
                name=f.name,
                short=f.short,
                kind=f.kind,
                lawyers=tuple((p.practice, p.lawyers) for p in f.pools),
                revenue_12m_cents=f.revenue_12m,
                profit_12m_cents=f.profit_12m,
                equity_partners=f.equity_partners,
                strong=strong_practices(f, data, defs),
                departures=sum(n for t, n in f.departures if t == turn),
                lost_to_player=f.lost_to_player,
                founded_turn=f.founded_turn,
                personality=f.personality,
                associates=sum(p.associates for p in f.pools),
                utilisation=f.utilisation,
                years=tuple((y.year, y.revenue_cents, y.lawyers, y.pep_cents) for y in f.history),
            )
        )
    return tuple(out)


@dataclass(frozen=True, slots=True)
class RivalMoveView:
    """A rival's move this month as the legal press reports it."""

    firm_id: int
    action: str
    detail: str
    person_id: int | None
    other_firm_id: int | None


def rival_moves_in(state: GameState, turn: int) -> tuple[RivalMoveView, ...]:
    return tuple(
        RivalMoveView(m.firm_id, m.action, m.detail, m.person_id, m.other_firm_id)
        for m in state.rivals.moves
        if m.turn == turn
    )


def rival_name(state: GameState, firm_id: int) -> str | None:
    """A rival's current name (or a gone rival's last), None for an unknown id."""
    f = state.rivals.firm(firm_id)
    return f.name if f is not None else None


@dataclass(frozen=True, slots=True)
class RivalPersonView:
    person_id: int
    name: str
    real: bool  # a real lawyer (ADR PT-0013): professional matters only
    practice: str
    notable_standing: str | None  # notables.yaml standing (elite, leading, strong) if real


def rival_managing_partner(
    state: GameState, firm_id: int, data: GameData, balance: Balance
) -> RivalPersonView | None:
    """A rival's managing partner (TST 29.4's CEO): its chair (notables.yaml `chair`) while on
    its staff, else its key partner with the lowest id; re-chosen whenever asked."""
    members = [m for m in state.rivals.members_of(firm_id) if m.kind == "partner"]
    if not members:
        return None
    chairs = {n.key for n in data.rivals.people.notables if n.chair}
    chosen = next((m for m in members if m.notable in chairs), None) or min(
        members, key=lambda m: m.person_id
    )
    return _person_view(state, chosen.person_id, data, balance)


def rival_key_people(
    state: GameState, firm_id: int, data: GameData, balance: Balance
) -> tuple[RivalPersonView, ...]:
    """A rival's key partners, by id (the directory's individuals)."""
    out = []
    for m in state.rivals.members_of(firm_id):
        if m.kind == "partner":
            view = _person_view(state, m.person_id, data, balance)
            if view is not None:
                out.append(view)
    return tuple(out)


def _person_view(
    state: GameState, person_id: int, data: GameData, balance: Balance
) -> RivalPersonView | None:
    from ptk.sim.rivals.people import find_person

    m = state.rivals.member(person_id)
    person = find_person(state, person_id, data, balance)
    if person is None:
        return None
    standing = None
    if m is not None and m.notable is not None:
        standing = next(
            (n.standing for n in data.rivals.people.notables if n.key == m.notable), None
        )
    return RivalPersonView(
        person_id=person_id,
        name=f"{person.first_name} {person.last_name}",
        real=person.real,
        practice=m.practice if m is not None else person.role,
        notable_standing=standing,
    )


def rival_stance_nudge(state: GameState, firm_id: int, points: float) -> GameState:
    """A feud's rivalry (TST 29.4) moves the rival's stance toward the player (PT-M5's label)."""
    from dataclasses import replace

    firms = tuple(
        replace(f, stance=f.stance + points) if f.id == firm_id else f for f in state.rivals.firms
    )
    return replace(state, rivals=replace(state.rivals, firms=firms))


def founder_persona_source(
    state: GameState, firm_id: int, source: str, balance: Balance
) -> GameState:
    """PT-M16: a persona source PT-M17 left without one (`broken_claim`, spec 2.3), on the
    player's founding partner's life, if they have one yet."""
    from dataclasses import replace

    from ptk.sim.founder.models import with_life
    from ptk.sim.founder.persona import apply_source

    you = state.founder_of(firm_id)
    life = state.founder_life.life(you) if you is not None else None
    if life is None:
        return state
    life = apply_source(life, source, state.turn, balance)
    return replace(state, founder_life=with_life(state.founder_life, life))


# --- PT-M9 (automation, lane B): an area runs a seat's default rule ---------------------------
#
# An automated area whose seat has an authority rule (PT-M8: the practice group leader's
# plans, the general counsel's waivers, the CFO's write-downs, the CMO's RFP pitches, the
# CHRO's campus targets, the pricing director's January rise) runs that rule as it is, with
# every action passed to the area's own `act` (which checks one-offs and money limits, then
# applies the action or files a proposal). Nothing in `ptk.sim.org.authority` changes.

type SeatAct = Callable[[GameState, object, str, bool], tuple[bool, GameState]]


def run_seat_rule(
    state: GameState,
    firm_id: int,
    seat_key: str,
    slot: int,
    person_id: int,
    guardrails: tuple[tuple[str, int], ...],
    right: bool,
    gen: np.random.Generator,
    balance: Balance,
    data: GameData,
    act: SeatAct,
) -> GameState:
    """Run PT-M8's rule for `seat_key` once with `right` (the area's quality draw) and the
    area's guardrails; `act(state, action, text, mistake) -> (taken, new_state)` is called for
    each action the rule would take. Returns the state after the rule."""
    from dataclasses import dataclass as _dc

    from ptk.sim.org.authority import RULES, _Holder
    from ptk.sim.org.seat_models import SeatAuthority

    rule = RULES.get(seat_key)
    if rule is None:
        return state

    @_dc
    class _AreaHolder(_Holder):
        def act(self, action: object, text: str, mistake: bool = False) -> bool:
            taken, self.state = act(self.state, action, text, mistake)
            return taken

    auth = SeatAuthority(firm_id, seat_key, slot, True, guardrails)
    h = _AreaHolder(
        state, firm_id, data.seat(seat_key), slot, person_id, auth, right, gen, balance, data,
        [], [], [],
    )  # fmt: skip
    rule(h)
    return h.state


# --- PT-M14 (legal tech and AI, lane C): the two hooks matters and billing read tech through --
#
# Matters (PT-M3a) read `tech_hours` where they compute hours: a phase's hours on each task are
# its base hours x the firm's efficiency on the task (ADR PT-0011 3), so output an hour is
# divided by the task mix's factor (progress, the staffing rule's expected output) and flow
# work's hours are multiplied by it; training hours are non-billable and count as learning;
# AI's removed hours lower a person's substantive share (ADR PT-0006 4). Billing (PT-M3b) reads
# `tech_billing`: the realisation cut clients make on hourly bills' exposed tasks and the
# firm's fixed-fee products (spec 13, 7.7). A firm with no technology gets exact no-ops.


@dataclass(frozen=True, slots=True)
class TechHoursView:
    efficiency: Mapping[str, float]  # task -> hours multiplier (1.0: no saving)
    learning_loss: float = 0.0  # learn_loss x (1 - restore x training cover)
    training_tenths: Mapping[int, int] = field(default_factory=dict)  # person -> a month's

    @property
    def idle(self) -> bool:
        return not self.efficiency and not self.training_tenths

    def factor(self, tasks: Mapping[str, float]) -> float:
        """Hours a task mix takes at the firm's efficiency, per base hour (1.0 when idle)."""
        if not self.efficiency:
            return 1.0
        total = sum(tasks.values())
        return sum(w * self.efficiency.get(t, 1.0) for t, w in tasks.items()) / total

    def learning(self, mine: Mapping[str, float]) -> float:
        """Multiplier on a person's substantive share for the tasks they do (`mine`: weights
        summing to 1): 1 - loss x the share of those hours AI removes."""
        if not self.efficiency or self.learning_loss <= 0:
            return 1.0
        removed = sum(w * (1.0 - self.efficiency.get(t, 1.0)) for t, w in mine.items())
        return max(0.0, 1.0 - self.learning_loss * removed)


NO_TECH_HOURS: Final = TechHoursView(efficiency={})


@dataclass(frozen=True, slots=True)
class TechBillingView:
    cuts: Mapping[str, float]  # task -> realisation cut on hourly bills (0-1)
    efficiency: Mapping[str, float]  # task -> the firm's efficiency (weights a bill's hours)
    products: Mapping[str, float]  # matter kind key -> fixed price / standard expected fees
    accept: Mapping[str, float] = field(default_factory=dict)  # kind key -> clients' take-up 0-1

    def cut_bp(self, tasks: Mapping[str, float]) -> int:
        """The cut on an hourly bill for a task mix, in bp: each task's cut weighted by the
        hours the firm spends on it (base weight x efficiency)."""
        if not self.cuts:
            return 0
        hours = {t: w * self.efficiency.get(t, 1.0) for t, w in tasks.items()}
        total = sum(hours.values())
        if total <= 0:
            return 0
        cut = sum(h * self.cuts.get(t, 0.0) for t, h in hours.items()) / total
        return round(cut * 10000)  # tunable-exempt: basis points


NO_TECH_BILLING: Final = TechBillingView(cuts={}, efficiency={}, products={})


def kind_task_mix(kind: str, data: GameData) -> Mapping[str, float]:
    """A matter kind's whole task mix (phase shares x task weights), for billing's cut
    (memoised on the data's identity: the mix never changes)."""
    hit = _KIND_MIX.get(kind)
    if hit is not None and hit[0] is data:
        return hit[1]
    from ptk.sim.matters.formulas import kind_tasks

    mix = kind_tasks(data.market.kinds[kind])
    _KIND_MIX[kind] = (data, mix)
    return mix


_KIND_MIX: dict[str, tuple[GameData, Mapping[str, float]]] = {}


def tech_hours(state: GameState, firm_id: int, data: GameData, balance: Balance) -> TechHoursView:
    """The firm's month of technology for matters' hours (memoised on what it reads)."""
    from ptk.sim.tech.hooks import hours_view

    return hours_view(state, firm_id, data, balance)


def tech_billing(
    state: GameState, firm_id: int, data: GameData, balance: Balance
) -> TechBillingView:
    """Client expectations and products for billing this month."""
    from ptk.sim.tech.hooks import billing_view

    return billing_view(state, firm_id, data, balance)


def tech_rfp_gap(state: GameState, firm_id: int, data: GameData, balance: Balance) -> float | None:
    """PT-M14 (spec 13, ADR PT-0011 4): from `tech.clients.rfp_from_year`, how far the firm's
    AI adoption runs ahead of (+) or behind (-) the market's, -1..1, for RFPs and the
    `ai_efficiency` pitch claim; None before then."""
    from ptk.sim.tech.hooks import rfp_gap

    return rfp_gap(state, firm_id, data, balance)


# --- PT-M15 (risk): what other systems read of a lawyer's discipline and the firm's policy --


def suspended_ids(state: GameState) -> frozenset[int]:
    """Lawyers suspended by the bar this month (spec 11.4): on the books, no billable work."""
    return state.risk.suspended_ids(state.turn)


def suspended(state: GameState, person_id: int) -> bool:
    return person_id in suspended_ids(state)


def lax_supervision_hours(state: GameState, firm_id: int, balance: Balance) -> int:
    """Hours a month a partner's non-billable time falls under the firm's lax supervision
    policy (PT-M15; 0 under standard supervision or with risk off)."""
    if not balance.risk.enabled or state.risk.firm(firm_id).supervision != "lax":
        return 0
    return balance.risk.policy.lax_hours
