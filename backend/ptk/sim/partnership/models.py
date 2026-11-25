"""Frozen partnership models (spec 5.5, 5.7, 8; ADR PT-0003, PT-0007). Never mutate.

One `FirmPartnership` per firm that keeps a partnership (the player's in PT-M4; PT-M5's
rivals may add theirs). Hidden values: each partner's `confidence` and `satisfaction`, a
lateral candidate's true book and every vote's utilities are engine-only (CLAUDE.md section
10): the API shows labels and ranges built by explicit view functions.

Capital and current accounts are sub-ledgers: `Partner.capital_cents` and `current_cents`
(plus `CapitalReturn.remaining_cents` for partners who have left) always sum to the ledger's
3000 and 2700 balances (a property test holds this).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, fields, replace
from typing import Literal

from ptk.sim.data_models import AgreementTerms, CompSystem, VotingRule

type PartnerClass = Literal["equity", "income"]
type VoteKind = Literal[
    "admission",  # December: a candidate for equity or income partnership
    "terms",  # a change to the partnership agreement (or the comp system)
    "capital_call",
    "deequity",  # December: an equity partner to income partner, or out
    "election",  # the MP election
    "merger",  # PT-M13: a merger or a verein (spec 8.8: two thirds; ptk.sim.mergers.terms)
]
type VoteStatus = Literal["open", "passed", "failed", "withdrawn"]
type Track = Literal["equity", "income", "counsel", "not_this_year"]
type ApproachState = Literal["open", "countered", "stayed", "left", "withdrawn"]
type LateralStatus = Literal["open", "offered", "hired", "declined", "expired"]
type Param = str | int | float | bool


@dataclass(frozen=True, slots=True)
class Agreement:
    """The partnership agreement as data (spec 8.6), voted on (ADR PT-0007 2)."""

    comp_system: CompSystem
    two_tier: bool
    voting: VotingRule
    admission_bp: int
    equity_lockstep_bp: int
    terms_bp: int
    capital_call_bp: int
    deequity_bp: int
    track_years: int
    mp_term_years: int
    retirement_age: int
    notice_months: int
    capital_share_bp: int
    draw_share_bp: int
    retain_bp: int

    @classmethod
    def of(cls, terms: AgreementTerms) -> Agreement:
        return cls(**{f.name: getattr(terms, f.name) for f in fields(cls)})

    def with_term(self, term: str, value: Param) -> Agreement:
        return replace(self, **{term: value})  # type: ignore[arg-type]


AGREEMENT_TERMS: tuple[str, ...] = tuple(f.name for f in fields(Agreement))


@dataclass(frozen=True, slots=True)
class Partner:
    """A partner's place in the partnership (equity: capital, points, draws; income: salary
    on the books, votes nothing)."""

    person_id: int
    firm_id: int
    klass: PartnerClass
    admitted_turn: int
    points: float = 0.0  # lockstep points (equity)
    capital_required_cents: int = 0
    capital_cents: int = 0  # paid in: the 3000 sub-ledger
    capital_instalment_cents: int = 0  # a month, until capital_required is reached
    budget_cents: int = 0  # this year's budgeted share; draws follow it
    budget_base_cents: int = 0  # the budget set in December (re-forecasts only cut from it)
    drawn_ytd_cents: int = 0
    current_cents: int = 0  # the 2700 sub-ledger: allocated, not yet paid (negative: overdrawn)
    guarantee_cents: int = 0  # comp a year guaranteed (laterals, counter-offers)
    guarantee_until_turn: int | None = None  # last turn the guarantee covers
    promised_cents: int = 0  # extra comp promised (a counter-offer), at the next allocation
    promised_points: float = 0.0  # extra points promised (lobbying), at the next allocation
    comp_last_cents: int = 0  # the last December allocation
    satisfaction: float = 0.0  # hidden: -1..0.5 (spec 8.5)
    confidence: float = 65.0  # hidden: 0-100 in the MP (ADR PT-0007 1)
    gate_steps: int = 0  # the comp round's gate (modified lockstep), this December
    adjust_bp: int = 0  # the comp round's adjustment (committee, bonus pool), this December
    working_ytd_cents: int = 0  # standard value of the partner's own hours this year
    lobbied_turn: int | None = None  # the turn the MP last lobbied them (one conversation a month)
    seat: bool = False  # promised a seat (v2's seats)
    nudge: float = 0.0  # one-off confidence points not yet applied (comp round, fear)

    @property
    def equity(self) -> bool:
        return self.klass == "equity"

    def guaranteed(self, turn: int) -> bool:
        return self.guarantee_until_turn is not None and turn <= self.guarantee_until_turn


@dataclass(frozen=True, slots=True)
class CapitalReturn:
    """A departed partner's capital and current account, repaid over 3 years (spec 8.4)."""

    person_id: int
    monthly_cents: int
    remaining_capital_cents: int
    remaining_current_cents: int  # their 2700 balance at departure (owed to them, >= 0)
    start_turn: int


@dataclass(frozen=True, slots=True)
class Vote:
    id: int
    firm_id: int
    kind: VoteKind
    subject_id: int | None  # the candidate, the partner, or the rival candidate
    params: tuple[tuple[str, Param], ...]  # sorted (term, value), (track, ...), (amount, ...)
    opened_turn: int
    threshold_bp: int
    status: VoteStatus = "open"
    resolved_turn: int | None = None
    yes_weight: float = 0.0
    no_weight: float = 0.0
    ballots: tuple[tuple[int, bool], ...] = ()  # (person id, voted yes), by person id

    def param(self, key: str) -> Param | None:
        return next((v for k, v in self.params if k == key), None)


@dataclass(frozen=True, slots=True)
class Candidacy:
    """A December proposal (spec 5.5): equity or income partnership, counsel, or not yet."""

    person_id: int
    firm_id: int
    track: Track
    sponsor_id: int | None
    year: int
    vote_id: int | None = None


@dataclass(frozen=True, slots=True)
class MovingOn:
    """An associate told to move on (up or out): leaves at `leave_turn` unless made counsel."""

    person_id: int
    firm_id: int
    told_turn: int
    leave_turn: int
    in_house: bool  # goes to a client's in-house team (an alumnus, v2)


@dataclass(frozen=True, slots=True)
class Approach:
    id: int
    firm_id: int
    person_id: int
    suitor_key: str
    suitor_name: str
    suitor_firm_id: int | None
    offer_comp_cents: int
    guarantee_years: int
    made_turn: int
    respond_by_turn: int
    status: ApproachState = "open"
    counter_comp_cents: int = 0
    counter_points: float = 0.0
    counter_guarantee_years: int = 0
    counter_seat: bool = False
    countered: bool = False
    resolved_turn: int | None = None
    stay_hint: str = "undecided"  # the band the firm sees: likely to stay, undecided, likely to go


@dataclass(frozen=True, slots=True)
class Departure:
    person_id: int
    firm_id: int
    turn: int  # when they resigned or were told
    leave_turn: int  # their last turn on the books
    practice: str
    reason: str  # interfaces.DepartureReason
    equity: bool
    suitor_key: str | None
    suitor_name: str | None
    suitor_firm_id: int | None
    book_cents: int  # their book a year at departure (origination, or their book)
    follows: tuple[tuple[int, int], ...] = ()  # (client id, turn it follows), by client id


@dataclass(frozen=True, slots=True)
class LateralCandidate:
    """A lateral partner available to the firm (spec 5.7). `book_lo`/`book_hi` are what the
    firm sees; the true book is the person's `book_cents`, and portability stays hidden."""

    person_id: int
    firm_id: int
    search_id: int
    practice: str
    ask_cents: int  # comp a year they ask (shown exactly)
    guarantee_ask_years: int
    book_lo_cents: int
    book_hi_cents: int
    client_ids: tuple[int, ...]  # the clients their book comes from, by id (diligence names them)
    conflict_ids: tuple[int, ...]  # book clients adverse to the firm's open matters
    created_turn: int
    expires_turn: int
    diligence: bool = False
    status: LateralStatus = "open"
    offer_comp_cents: int = 0
    offer_guarantee_years: int = 0
    offer_equity: bool = True
    offer_turn: int | None = None
    resolved_turn: int | None = None


@dataclass(frozen=True, slots=True)
class Arrival:
    """A lateral partner's client that follows them to the firm at `turn` (spec 5.7)."""

    person_id: int
    firm_id: int
    client_id: int
    turn: int
    practice: str


@dataclass(frozen=True, slots=True)
class PnlPoint:
    """Cumulative accrual revenue and costs at a month end, with the headcount (spec 8.2)."""

    turn: int
    revenue_cents: int
    costs_cents: int
    equity_partners: int
    lawyers: int
    # PT-M7b: the month end's balances, for the CFO's forecast
    drawn_cents: int = 0
    capital_cents: int = 0
    cash_cents: int = 0


@dataclass(frozen=True, slots=True)
class Forecast:
    """PT-M7b: the CFO's projected covenant breach (spec 8.7)."""

    covenant: str
    months: int  # months from now the breach is projected
    drawn_cents: int  # the projected drawn balance then


@dataclass(frozen=True, slots=True)
class FirmPartnership:
    firm_id: int
    agreement: Agreement
    mp_id: (
        int | None
    )  # the managing partner (the player's founding partner by the founding agreement)
    partners: tuple[Partner, ...] = ()  # current partners, by person id
    capital_returns: tuple[CapitalReturn, ...] = ()  # by person id
    votes: tuple[Vote, ...] = ()  # by id; open, and the last three years'
    candidacies: tuple[Candidacy, ...] = ()  # this year's, by person id
    sponsors: tuple[tuple[int, int], ...] = ()  # (associate, sponsoring partner), by associate
    moving_on: tuple[MovingOn, ...] = ()  # by person id
    approaches: tuple[Approach, ...] = ()  # by id; open, and the last year's
    departures: tuple[Departure, ...] = ()  # by (turn, person id); the last three years'
    laterals: tuple[LateralCandidate, ...] = ()  # by person id; open, and recent
    arrivals: tuple[Arrival, ...] = ()  # pending book clients, by (turn, client id)
    pnl: tuple[PnlPoint, ...] = ()  # month ends, the last 13
    pnl_closed_revenue_cents: int = 0  # cumulative revenue at the last December allocation
    pnl_closed_costs_cents: int = 0
    wc_closed_cents: int = (
        0  # working capital (WIP, receivables, net of provisions and deferred fees) then
    )
    last_profit_cents: int | None = None  # the last allocated year's profit
    last_pep_cents: int | None = None
    last_revenue_cents: int | None = None
    allocated_ytd_cents: int = 0  # allocated this year at departures (their draws, ADR PT-0003 6)
    equity_months: int = 0  # Σ equity partners at each month end this year (PEP's average)
    months: int = 0  # month ends this year
    facility_cents: int = 0  # the revolver's facility (its limit before the borrowing base)
    breach_months: int = 0  # consecutive months with a covenant breached
    called_turn: int | None = None  # the bank called the revolver
    insolvent_months: int = 0
    draws_suspended: bool = False  # the MP has stopped draws
    last_warning_turn: int | None = None  # the CFO's last warning
    last_forecast_turn: int | None = None  # PT-M7b: the CFO's last forecast warning
    term_ends_turn: int | None = None  # the MP's term (from stage 2)
    low_confidence_months: int = 0
    election_lost_turn: int | None = None  # the player lost an election and must choose
    ousted_mp_id: int | None = None  # the player's founder after losing (stays as partner)

    def partner(self, person_id: int) -> Partner | None:
        return next((p for p in self.partners if p.person_id == person_id), None)

    @property
    def equity_partners(self) -> tuple[Partner, ...]:
        return tuple(p for p in self.partners if p.equity)

    def vote(self, vote_id: int) -> Vote | None:
        return next((v for v in self.votes if v.id == vote_id), None)

    def approach(self, approach_id: int) -> Approach | None:
        return next((a for a in self.approaches if a.id == approach_id), None)

    def lateral(self, person_id: int) -> LateralCandidate | None:
        return next((c for c in self.laterals if c.person_id == person_id), None)

    def candidacy(self, person_id: int) -> Candidacy | None:
        return next((c for c in self.candidacies if c.person_id == person_id), None)

    def sponsor_of(self, person_id: int) -> int | None:
        return next((s for a, s in self.sponsors if a == person_id), None)


@dataclass(frozen=True, slots=True)
class PartnershipState:
    firms: tuple[FirmPartnership, ...] = ()  # by firm id
    next_vote_id: int = 1
    next_approach_id: int = 1

    def of(self, firm_id: int) -> FirmPartnership | None:
        return next((f for f in self.firms if f.firm_id == firm_id), None)


EMPTY_PARTNERSHIP = PartnershipState()


# --- Upserts ---------------------------------------------------------------------------------


def _sorted[T](items: Iterable[T], key: str) -> tuple[T, ...]:
    return tuple(sorted(items, key=lambda x: getattr(x, key)))


def with_firm_partnership(ps: PartnershipState, fp: FirmPartnership) -> PartnershipState:
    rest = [f for f in ps.firms if f.firm_id != fp.firm_id]
    return replace(ps, firms=_sorted([*rest, fp], "firm_id"))


def with_partner(fp: FirmPartnership, partner: Partner) -> FirmPartnership:
    rest = [p for p in fp.partners if p.person_id != partner.person_id]
    return replace(fp, partners=_sorted([*rest, partner], "person_id"))


def without_partner(fp: FirmPartnership, person_id: int) -> FirmPartnership:
    return replace(fp, partners=tuple(p for p in fp.partners if p.person_id != person_id))


def with_vote(fp: FirmPartnership, vote: Vote) -> FirmPartnership:
    rest = [v for v in fp.votes if v.id != vote.id]
    return replace(fp, votes=_sorted([*rest, vote], "id"))


def with_approach(fp: FirmPartnership, approach: Approach) -> FirmPartnership:
    rest = [a for a in fp.approaches if a.id != approach.id]
    return replace(fp, approaches=_sorted([*rest, approach], "id"))


def with_lateral(fp: FirmPartnership, cand: LateralCandidate) -> FirmPartnership:
    rest = [c for c in fp.laterals if c.person_id != cand.person_id]
    return replace(fp, laterals=_sorted([*rest, cand], "person_id"))


def with_candidacy(fp: FirmPartnership, cand: Candidacy) -> FirmPartnership:
    rest = [c for c in fp.candidacies if c.person_id != cand.person_id]
    return replace(fp, candidacies=_sorted([*rest, cand], "person_id"))


def with_sponsor(fp: FirmPartnership, person_id: int, sponsor_id: int | None) -> FirmPartnership:
    rest = [(a, s) for a, s in fp.sponsors if a != person_id]
    if sponsor_id is not None:
        rest.append((person_id, sponsor_id))
    return replace(fp, sponsors=tuple(sorted(rest)))


def with_departure(fp: FirmPartnership, dep: Departure) -> FirmPartnership:
    rest = [d for d in fp.departures if not (d.person_id == dep.person_id and d.turn == dep.turn)]
    return replace(fp, departures=tuple(sorted([*rest, dep], key=lambda d: (d.turn, d.person_id))))


def with_capital_return(fp: FirmPartnership, ret: CapitalReturn) -> FirmPartnership:
    rest = [r for r in fp.capital_returns if r.person_id != ret.person_id]
    if ret.remaining_capital_cents > 0 or ret.remaining_current_cents > 0:
        rest.append(ret)
    return replace(fp, capital_returns=_sorted(rest, "person_id"))


def with_moving_on(fp: FirmPartnership, m: MovingOn) -> FirmPartnership:
    rest = [x for x in fp.moving_on if x.person_id != m.person_id]
    return replace(fp, moving_on=_sorted([*rest, m], "person_id"))
