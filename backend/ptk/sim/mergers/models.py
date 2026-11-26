"""Frozen merger and verein models (spec 8.8; ADR PT-0016). Never mutate.

A `Deal` follows one combination from the approach to closing (or its end): talks, diligence,
terms and the other side's answer, both partnerships' votes, conflicts clearance, closing. The
other firm's client book (`BookClient`s) is drawn when talks open and fixed for the deal.
After closing an `Integration` record follows the combination for `integration.months`. A
`Verein` joins member firms under one brand; each keeps its own books. An `ExitScore` records
the campaign's end when the player's firm was absorbed.

Hidden values (engine-only, never in an API schema or a prompt): `BookClient.adverse_client_id`
before clearance, the other firm's annuity share and lease years (drawn from stream
`merger_target`, never stored), its partners' answer noise.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

type DealForm = Literal["merger", "verein"]
type Initiator = Literal["player", "rival"]
type DealStage = Literal[
    "approached",  # a rival's approach to the player, waiting for the player's answer
    "talks",  # talks open (diligence may run; terms not yet put)
    "terms",  # terms put; the other side answers in phase 1
    "countered",  # the other side asked for a better share; the player answers
    "voting",  # both partnerships vote (phase 1)
    "clearance",  # both passed; conflicts cleared; closing at the next phase 1
    "closed",  # combined (merger), joined (verein) or absorbed (exit)
    "ended",  # walked away, refused, failed, lapsed
]
type NameTerm = Literal["ours", "theirs", "combined"]
type MpTerm = Literal["ours", "theirs"]
type RateTerm = Literal["ours", "theirs", "higher", "blend"]
type ConflictOutcome = Literal["waived", "kept_ours", "kept_theirs"]


@dataclass(frozen=True, slots=True)
class BookClient:
    """One client of the other firm's book (ADR PT-0016 2)."""

    client_id: int
    score: float  # the other firm's relationship, 0-100
    practices: tuple[str, ...]  # practices.yaml order
    share: float  # its share of the book's work (the book's shares sum to 1)
    adverse_client_id: int | None = None  # hidden until clearance: an engagement against them
    kept: bool = True  # False: dropped at clearance


@dataclass(frozen=True, slots=True)
class Sheet:
    """A closing balance sheet in cents (assets positive, liabilities and capital positive)."""

    cash: int
    wip: int
    receivables: int
    right_of_use: int
    leases: int
    annuities: int
    revolver: int
    capital: int

    @property
    def assets(self) -> int:
        return self.cash + self.wip + self.receivables + self.right_of_use

    @property
    def claims(self) -> int:
        return self.leases + self.annuities + self.revolver + self.capital


@dataclass(frozen=True, slots=True)
class Terms:
    our_share_bp: int  # the player's partners' share of the merged profit pool
    name: NameTerm = "ours"
    mp: MpTerm = "ours"
    comp_system: str = "modified_lockstep"
    rates: RateTerm = "ours"


@dataclass(frozen=True, slots=True)
class Conflict:
    """A conflict clearance found, and how it ended (ADR PT-0016 3)."""

    our_client_id: int  # a client of the player's firm (or a book client, kind "engagement")
    their_client_id: int  # a book client
    matter_id: int | None  # the player's matter adverse to the book client (kind "matter")
    outcome: ConflictOutcome


@dataclass(frozen=True, slots=True)
class Deal:
    id: int
    rival_id: int
    rival_key: str
    form: DealForm
    initiator: Initiator
    opened_turn: int
    stage: DealStage = "talks"
    stage_turn: int = 0  # the turn the stage began
    diligence_level: int = 0
    diligence_due_turn: int | None = None  # a level in progress ends here
    diligence_fees_cents: int = 0
    book: tuple[BookClient, ...] = ()  # by client id
    terms: Terms | None = None
    counter_share_bp: int | None = None  # the other side's counter
    rounds: int = 0  # terms answered so far
    their_yes_bp: int | None = None  # the other partnership's last count (yes share)
    our_vote_id: int | None = None
    conflicts: tuple[Conflict, ...] = ()
    leaked: bool = False
    absorbed: bool = False  # the terms make the player's firm the absorbed one
    ended_turn: int | None = None
    ended_reason: str = ""

    @property
    def is_open(self) -> bool:
        return self.stage not in ("closed", "ended")


@dataclass(frozen=True, slots=True)
class Integration:
    """A combination's first `integration.months` after closing (TST 28.5, re-cast)."""

    deal_id: int
    rival_key: str
    name: str  # the other firm's name at closing
    closed_turn: int
    until_turn: int
    clash: float  # culture distance 0-1
    their_people: tuple[int, ...]  # the other side's lawyers who joined, by id
    their_partners: tuple[int, ...]  # ... its equity partners
    our_partners: tuple[int, ...]  # the player's equity partners at closing
    pep_before: tuple[tuple[int, int], ...]  # (person id, PEP a year expected before), by id
    card_rise: float  # the merged card over the other firm's, for its clients (0: no rise)
    balk_clients: tuple[int, ...]  # book clients exposed to the card rise, by id
    lost_partners: tuple[tuple[int, int], ...] = ()  # (person id, turn) equity partners gone
    lost_clients: tuple[tuple[int, int], ...] = ()  # (client id, turn) balked
    surrender_cents: int = 0
    lawyers_at_closing: int = 0
    partners_at_closing: int = 0
    # PT-M12: practices where each firm had at least `integration.contested_min_share` of its
    # own lawyers before closing (subordination's flight counts only there), sorted
    contested: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Verein:
    """A brand shared by member firms (ADR PT-0016 5): the player's firm and rival members."""

    id: int
    name: str
    formed_turn: int
    members: tuple[tuple[str, int], ...]  # (rival key, joined turn), by key
    costs_cents: int = 0  # the player's share paid to date


@dataclass(frozen=True, slots=True)
class ExitScore:
    """The campaign's end by absorption (ADR PT-0016 6)."""

    turn: int
    firm_name: str  # the absorbing firm
    capital_cents: int  # the founder's capital account at closing
    earnings_cents: int  # the founder's December allocations to date
    rank: int  # the merged firm's rank by revenue among active firms
    revenue_cents: int  # the merged firm's revenue a year


@dataclass(frozen=True, slots=True)
class MergersState:
    deals: tuple[Deal, ...] = ()  # by id
    integrations: tuple[Integration, ...] = ()  # by deal id
    vereins: tuple[Verein, ...] = ()  # by id (the player belongs to at most one)
    exit: ExitScore | None = None
    cooldowns: tuple[tuple[str, int], ...] = ()  # (rival key, first turn talks may reopen)
    next_deal_id: int = 1
    last_rival_approach_turn: int | None = None

    def deal(self, deal_id: int) -> Deal | None:
        return next((d for d in self.deals if d.id == deal_id), None)

    def open_deals(self) -> tuple[Deal, ...]:
        return tuple(d for d in self.deals if d.is_open)

    def open_with(self, rival_key: str) -> Deal | None:
        return next((d for d in self.deals if d.is_open and d.rival_key == rival_key), None)

    def cooldown(self, rival_key: str) -> int:
        return next((t for k, t in self.cooldowns if k == rival_key), 0)

    @property
    def verein(self) -> Verein | None:
        return self.vereins[-1] if self.vereins else None

    def member_keys(self) -> frozenset[str]:
        v = self.verein
        return frozenset(k for k, _ in v.members) if v is not None else frozenset()

    def integration(self, deal_id: int) -> Integration | None:
        return next((i for i in self.integrations if i.deal_id == deal_id), None)


EMPTY_MERGERS = MergersState()


def with_deal(ms: MergersState, deal: Deal) -> MergersState:
    rest = [d for d in ms.deals if d.id != deal.id]
    return replace(ms, deals=tuple(sorted([*rest, deal], key=lambda d: d.id)))


def with_integration(ms: MergersState, item: Integration) -> MergersState:
    rest = [i for i in ms.integrations if i.deal_id != item.deal_id]
    return replace(ms, integrations=tuple(sorted([*rest, item], key=lambda i: i.deal_id)))


def with_verein(ms: MergersState, v: Verein) -> MergersState:
    rest = [x for x in ms.vereins if x.id != v.id]
    return replace(ms, vereins=tuple(sorted([*rest, v], key=lambda x: x.id)))


def with_cooldown(ms: MergersState, rival_key: str, turn: int) -> MergersState:
    rest = [(k, t) for k, t in ms.cooldowns if k != rival_key]
    return replace(ms, cooldowns=tuple(sorted([*rest, (rival_key, turn)])))
