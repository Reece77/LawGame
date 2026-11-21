"""Immutable game state. Cash is never a field: it is derived from ledger balances (ADR-0003).

Pattern from tst/sim/state.py @ 02fba2aa: frozen dataclasses, tuples sorted by id, new
objects returned rather than mutated. Partner Track's own fields; later milestones add
theirs (people, matters, clients, rivals) as sorted tuples with empty defaults.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from typing import Literal

from ptk.sim.billing.models import EMPTY_BILLING, BillingState
from ptk.sim.calendar import YearMonth
from ptk.sim.events.models import EMPTY_EVENTS, EventsState
from ptk.sim.hiring.models import Candidate, Offer, PayPolicy, PersonState, Search
from ptk.sim.matters.models import EMPTY_MARKET, MarketState
from ptk.sim.org.models import EMPTY_ORG, OrgState
from ptk.sim.partnership.models import EMPTY_PARTNERSHIP, PartnershipState
from ptk.sim.people.models import Employment, Person, RevealState
from ptk.sim.rivals.models import EMPTY_RIVALS, RIVAL_PERSON_BASE, RivalsState

# ADR PT-0007 section 4: a game ends when the campaign completes or the firm dissolves.
# Ironman (ADR PT-0007 3): losing the MP election is final.
type GameOutcome = Literal["active", "campaign_complete", "dissolved", "election_lost"]


@dataclass(frozen=True, slots=True)
class SaveMeta:
    name: str
    master_seed: int
    scenario_id: str
    difficulty: str
    start_ym: YearMonth  # turn 0 (ADR PT-0002)
    game_state: GameOutcome = "active"
    ended_turn: int | None = None


@dataclass(frozen=True, slots=True)
class FirmState:
    id: int
    name: str
    is_player: bool
    stage: int  # spec section 3: 0 founding .. 5 global
    founded_turn: int
    home_city: str
    pay_policy: PayPolicy = field(default_factory=PayPolicy)  # PT-M1b (spec 5.4)
    conflict_checks: bool = True  # PT-M3a (ADR PT-0009 5): run checks at intake
    # PT-M7a: pro bono (spec 7.8) and the yearly rate rise
    pro_bono_credit_hours: int | None = None  # hours a year credited; None: balance default
    pro_bono_avg_tenths: float = 0.0  # pro bono tenths a lawyer a month, a moving average
    rate_rise_bp: int | None = None  # each January's rise; None: the market's
    rate_index: float = 1.0  # the firm's rate card over the practices' 2005 cards
    # PT-M7b: the firm's share of each practice's top card, bp by practice key, sorted; a
    # practice not listed bills at the full card (10000)
    rate_card: tuple[tuple[str, int], ...] = ()
    # PT-M7b: the firm-wide billable target, hours a year; None: the levels' targets
    billable_target_hours: int | None = None


@dataclass(frozen=True, slots=True)
class GameState:
    save_meta: SaveMeta
    turn: int  # the next turn to be played; 0 = the scenario's start month
    firms: tuple[FirmState, ...]  # sorted by id
    people: tuple[Person, ...] = ()  # sorted by id (PT-M1a)
    employments: tuple[Employment, ...] = ()  # sorted by id
    reveals: tuple[RevealState, ...] = ()  # sorted by (observer_firm_id, person_id)
    # PT-M1b: hiring and per-person state; every record stays (no ids are reused).
    searches: tuple[Search, ...] = ()  # sorted by id
    candidates: tuple[Candidate, ...] = ()  # sorted by person_id
    offers: tuple[Offer, ...] = ()  # sorted by id
    person_states: tuple[PersonState, ...] = ()  # sorted by person_id
    org: OrgState = EMPTY_ORG  # units, membership, plans, delegates (PT-M2)
    market: MarketState = EMPTY_MARKET  # clients, relationships, matters, judges (PT-M3a)
    events: EventsState = EMPTY_EVENTS  # events, storylines, modifiers, colleagues (PT-M6)
    billing: BillingState = EMPTY_BILLING  # WIP, bills, client money, totals (PT-M3b)
    rivals: RivalsState = EMPTY_RIVALS  # rival firms, their key people, RFPs (PT-M5)
    partnership: PartnershipState = EMPTY_PARTNERSHIP  # capital, comp, votes, flight (PT-M4)

    @property
    def ended(self) -> bool:
        return self.save_meta.game_state != "active"

    def person(self, person_id: int) -> Person:
        for person in self.people:
            if person.id == person_id:
                return person
        raise KeyError(f"no person {person_id}")

    def staff_ids(self, firm_id: int) -> tuple[int, ...]:
        """Ids of the people on a firm's books (active or notice), ascending."""
        return tuple(
            sorted(
                e.person_id for e in self.employments if e.firm_id == firm_id and e.counts_as_staff
            )
        )

    def founder_of(self, firm_id: int) -> int | None:
        """The firm's own founding partner played by the player (the org root's leader)."""
        staff = set(self.staff_ids(firm_id))
        for person in self.people:
            if person.is_founder and person.id in staff:
                return person.id
        return None

    def employer_of(self, person_id: int) -> int | None:
        """The firm whose books the person is on (active or notice), if any."""
        for e in self.employments:
            if e.person_id == person_id and e.counts_as_staff:
                return e.firm_id
        return None

    def reveal(self, observer_firm_id: int, person_id: int) -> RevealState | None:
        for state in self.reveals:
            if state.observer_firm_id == observer_firm_id and state.person_id == person_id:
                return state
        return None

    @property
    def player(self) -> FirmState:
        for firm in self.firms:
            if firm.is_player:
                return firm
        raise LookupError("no player firm")

    # --- PT-M1b lookups ----------------------------------------------------------------------

    def firm(self, firm_id: int) -> FirmState:
        for firm in self.firms:
            if firm.id == firm_id:
                return firm
        raise KeyError(f"no firm {firm_id}")

    def employment_of(self, person_id: int) -> Employment | None:
        """The person's current (active or notice) employment."""
        for e in self.employments:
            if e.person_id == person_id and e.counts_as_staff:
                return e
        return None

    def staff(self, firm_id: int) -> tuple[Employment, ...]:
        """A firm's active and notice employments, by person id."""
        return tuple(
            sorted(
                (e for e in self.employments if e.firm_id == firm_id and e.counts_as_staff),
                key=lambda e: e.person_id,
            )
        )

    def search(self, search_id: int) -> Search | None:
        return next((s for s in self.searches if s.id == search_id), None)

    def candidate(self, person_id: int) -> Candidate | None:
        return next((c for c in self.candidates if c.person_id == person_id), None)

    def offer(self, offer_id: int) -> Offer | None:
        return next((o for o in self.offers if o.id == offer_id), None)

    def pending_offer_for(self, person_id: int) -> Offer | None:
        return next(
            (o for o in self.offers if o.candidate_id == person_id and o.status == "pending"),
            None,
        )

    def person_state(self, person_id: int) -> PersonState:
        for ps in self.person_states:
            if ps.person_id == person_id:
                return ps
        return PersonState(person_id=person_id)

    def next_id(self, kind: Literal["person", "employment", "search", "offer"]) -> int:
        """max + 1 of a table's ids (records are never dropped, so ids are never reused)."""
        ids: Iterable[int]
        if kind == "person":
            # PT-M5: rival people have ids from RIVAL_PERSON_BASE; the player's stay below
            ids = (p.id for p in self.people if p.id < RIVAL_PERSON_BASE)
        elif kind == "employment":
            ids = (e.id for e in self.employments)
        elif kind == "search":
            ids = (s.id for s in self.searches)
        else:
            ids = (o.id for o in self.offers)
        return max(ids, default=0) + 1


# --- Upserts (return new states; tuples stay sorted) -----------------------------------------


def with_firm(state: GameState, firm: FirmState) -> GameState:
    return replace(state, firms=tuple(firm if f.id == firm.id else f for f in state.firms))


def with_employment(state: GameState, employment: Employment) -> GameState:
    rest = [e for e in state.employments if e.id != employment.id]
    return replace(state, employments=tuple(sorted([*rest, employment], key=lambda e: e.id)))


def with_person(state: GameState, person: Person) -> GameState:
    rest = [p for p in state.people if p.id != person.id]
    return replace(state, people=tuple(sorted([*rest, person], key=lambda p: p.id)))


def with_search(state: GameState, search: Search) -> GameState:
    rest = [s for s in state.searches if s.id != search.id]
    return replace(state, searches=tuple(sorted([*rest, search], key=lambda s: s.id)))


def with_candidates(state: GameState, candidates: Iterable[Candidate]) -> GameState:
    new = {c.person_id: c for c in candidates}
    if not new:
        return state
    rest = [c for c in state.candidates if c.person_id not in new]
    merged = sorted([*rest, *new.values()], key=lambda c: c.person_id)
    return replace(state, candidates=tuple(merged))


def with_offer(state: GameState, offer: Offer) -> GameState:
    rest = [o for o in state.offers if o.id != offer.id]
    return replace(state, offers=tuple(sorted([*rest, offer], key=lambda o: o.id)))


def with_person_states(state: GameState, states: Iterable[PersonState]) -> GameState:
    new = {ps.person_id: ps for ps in states}
    if not new:
        return state
    rest = [ps for ps in state.person_states if ps.person_id not in new]
    merged = sorted([*rest, *new.values()], key=lambda ps: ps.person_id)
    return replace(state, person_states=tuple(merged))


def with_reveals(state: GameState, reveals: Iterable[RevealState]) -> GameState:
    new = {(r.observer_firm_id, r.person_id): r for r in reveals}
    if not new:
        return state
    rest = [r for r in state.reveals if (r.observer_firm_id, r.person_id) not in new]
    merged = sorted([*rest, *new.values()], key=lambda r: (r.observer_firm_id, r.person_id))
    return replace(state, reveals=tuple(merged))


def with_people(state: GameState, people: Iterable[Person]) -> GameState:
    new = {p.id: p for p in people}
    if not new:
        return state
    rest = [p for p in state.people if p.id not in new]
    return replace(state, people=tuple(sorted([*rest, *new.values()], key=lambda p: p.id)))
