"""Frozen rival-firm models (spec 10; ADR PT-0008; TST ADR-0010). Never mutate.

Ported from backend/tst/sim/rivals/models.py @ 121d3180 (Tech Startup Tycoon), in part:
`RivalMove`, `PoachApproach` (as `Approach`), `FreeAgent` and `stream_key` keep TST's shape;
changed for law: a rival is a `RivalFirm` with pools of lawyers by practice and level instead
of product workforce pools, and its key people are `Member`s.

A rival keeps its top partners and rising associates as individuals (`Member`s, generated
on demand; in `GameState.people` once the player's firm has dealt with them as candidates
or employees) and the rest of its lawyers as pools. Its economics are annual
run-rates in cents held as floats (estimates that size headcount, never posted); what it
posts to its ledger each month is integer cents (ADR-0003).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

type RivalKind = Literal["real", "generated", "boutique"]
type RivalStatus = Literal["active", "merged", "collapsed", "failed"]
type MemberKind = Literal["partner", "associate"]
type ApproachStatus = Literal["pending", "accepted", "declined", "lapsed", "countered"]
type RfpKind = Literal["panel", "matter"]
type RfpStatus = Literal["open", "awarded"]

# Stable identities (TST ADR-0013 amendment, M12a): a rival's streams use its rival_key,
# never its database id. Real firms by firms.yaml index; generated firms by their ordinal;
# boutiques by their founding ordinal.
REAL_KEY, GENERATED_KEY, BOUTIQUE_KEY = 0, 1, 2  # tunable-exempt: rival_key tags
# Person ids of rival people start here, so the player's own ids never meet them
# (`GameState.next_id("person")` counts only ids below it).
RIVAL_PERSON_BASE: Final = 10_000_000  # tunable-exempt: an id range, not a game number


def stream_key(rival_key: tuple[int, ...]) -> tuple[int, ...]:
    return rival_key


@dataclass(frozen=True, slots=True)
class Pool:
    """A rival's lawyers in one practice (ADR PT-0008 3), key people included."""

    practice: str
    equity: float  # equity partners
    partners: float  # income partners and counsel
    associates: float

    @property
    def lawyers(self) -> float:
        return self.equity + self.partners + self.associates


@dataclass(frozen=True, slots=True)
class YearRecord:
    """A rival's fiscal year, recorded in December (for the Rival page and T11)."""

    year: int
    revenue_cents: int
    lawyers: int
    equity_partners: int
    pep_cents: int


@dataclass(frozen=True, slots=True)
class RivalFirm:
    id: int  # firm id (never the player's)
    rival_key: tuple[int, ...]
    key: str  # firms.yaml key, or gen_<n> / btq_<n>; the key client panels carry
    name: str
    short: str
    personality: str
    kind: RivalKind
    hq: str
    ny_office: bool
    offices: int
    founded_turn: int
    pools: tuple[Pool, ...]  # practices.yaml order
    rpl_cap_cents: float  # a year of revenue per lawyer at rate_index 1 and full utilisation
    cost_per_lawyer_cents: float  # a year
    demand_cents: float  # a year of work available (the run-rate)
    rate_index: float = 1.0
    shock: float = 0.0  # AR(1) log shock on demand (stream rival_firm)
    offset_cents: float = 0.0  # a year of work moved by the player's effects (+ won, - lost)
    status: RivalStatus = "active"
    ended_turn: int | None = None
    successor: str | None = None  # the firm it merged into or was absorbed by
    utilisation: float = 0.0
    revenue: tuple[int, ...] = ()  # the last 12 months' fees, oldest first
    profit: tuple[int, ...] = ()  # the last 12 months' profit, oldest first
    history: tuple[YearRecord, ...] = ()
    departures: tuple[tuple[int, int], ...] = ()  # (turn, key partners who left) last 12 months
    lost_to_player: int = 0  # key partners the player's firm hired, ever
    cooldowns: tuple[tuple[str, int], ...] = ()  # (action, first turn it may run again)
    anchor: tuple[int, float] | None = None  # a successor's (turn, demand) where its path starts
    lawyers_anchor: float = 0.0  # a successor's lawyers at its anchor
    base_offices: int = 0  # offices at founding (extra offices cost rivals.office_cost_cents)
    stance: float = 0.0  # its view of the player: + rivalry from the player's poaching
    growth_bias: float = 0.0  # a boutique's own demand growth a year beside its personality's
    people_made: int = 0  # key people generated for it so far (stream rival_people's n)
    key_target: int = 0  # key partners it keeps as individuals

    @property
    def active(self) -> bool:
        return self.status == "active"

    @property
    def lawyers(self) -> float:
        return sum(p.lawyers for p in self.pools)

    @property
    def equity_partners(self) -> float:
        return sum(p.equity for p in self.pools)

    @property
    def revenue_12m(self) -> int:
        return sum(self.revenue)

    @property
    def profit_12m(self) -> int:
        return sum(self.profit)

    def pool(self, practice: str) -> Pool:
        for p in self.pools:
            if p.practice == practice:
                return p
        raise KeyError(practice)

    def cooldown(self, action: str) -> int:
        return next((t for a, t in self.cooldowns if a == action), 0)


@dataclass(frozen=True, slots=True)
class Member:
    """A rival's key person (ADR PT-0008 3): scoutable and poachable.

    The person is generated on demand (people.person_of) from `(gen_key, n, made_turn)` with
    `practice` and `gen_level`, so a game does not store thousands of people it may never
    look at; `level` and `book_cents` are their current values. Once the player's firm has
    met them (a candidate, an employee, or someone who left it for a rival) their record
    lives in GameState.people instead (`outside`)."""

    person_id: int
    firm_id: int
    kind: MemberKind
    practice: str
    book_cents: int  # a partner's book a year (associates 0)
    since_turn: int
    level: str
    gen_key: tuple[int, ...]  # the rival_key of the firm that made them
    gen_hq: str
    n: int  # stream rival_people's n
    made_turn: int
    gen_level: str
    notable: str | None = None  # notables.yaml key of a real lawyer
    outside: bool = False


@dataclass(frozen=True, slots=True)
class RivalMove:
    """One rival action or history event, for news, cooldowns and replay (spec 10.2-10.4)."""

    id: int
    firm_id: int
    turn: int
    action: str  # a RIVAL_ACTIONS key, or founded, merged, collapsed, renamed, failed, ...
    detail: str = ""  # the news line
    person_id: int | None = None
    other_firm_id: int | None = None


@dataclass(frozen=True, slots=True)
class Approach:
    """A rival's offer to one of the player's people (TST 15.6; spec 8.7): answered in
    phase 1 of the next turn unless the player counters."""

    id: int
    firm_id: int  # the rival
    person_id: int
    offer_cents: int  # a year
    made_turn: int
    status: ApproachStatus = "pending"
    resolved_turn: int | None = None


@dataclass(frozen=True, slots=True)
class FreeAgent:
    """A collapsed or failed rival's person looking for work (TST M6): they can join the
    player's next lateral search until `until_turn`."""

    member: Member  # who they are (no longer a key person of any firm)
    released_turn: int
    until_turn: int

    @property
    def person_id(self) -> int:
        return self.member.person_id


@dataclass(frozen=True, slots=True)
class Pitch:
    """The player's pitch for an RFP (spec 7.2): a team and claims."""

    team: tuple[int, ...]  # person ids, the lead first
    claims: tuple[str, ...]  # balance-free claim keys (rfp.CLAIMS)
    turn: int


@dataclass(frozen=True, slots=True)
class Rfp:
    """A panel review or a big-matter RFP (spec 7.2), awarded in phase 4 of `award_turn`."""

    id: int
    client_id: int
    kind: RfpKind
    practices: tuple[str, ...]  # the practices the panel or matter covers
    opened_turn: int
    award_turn: int
    seats: int  # panel seats on offer (a matter RFP: 1)
    incumbents: tuple[str, ...]  # panel keys at the start (the player as "player")
    bidders: tuple[str, ...]  # rival keys bidding beside the incumbents, sorted
    player_invited: bool
    matter_cents: int = 0  # a matter RFP's expected fees
    pitch: Pitch | None = None
    status: RfpStatus = "open"
    winners: tuple[str, ...] = ()  # rival keys and/or "player", by score


@dataclass(frozen=True, slots=True)
class HistoryDone:
    """A dated event (firms.yaml events) that has happened, been called off or brought
    forward (ADR PT-0008 2)."""

    key: str
    turn: int
    outcome: Literal["happened", "called_off", "forward"]


PLAYER_PANEL_KEY: Final = "player"  # tunable-exempt: the player's firm in an RFP's lists


@dataclass(frozen=True, slots=True)
class RivalsState:
    real_people: bool = True  # world.real_people at game creation (ADR PT-0013)
    firms: tuple[RivalFirm, ...] = ()  # sorted by id
    members: tuple[Member, ...] = ()  # sorted by person_id
    moves: tuple[RivalMove, ...] = ()  # the last 24 months, sorted by id
    approaches: tuple[Approach, ...] = ()  # sorted by id
    rfps: tuple[Rfp, ...] = ()  # open RFPs and those awarded in the last 24 months, by id
    free_agents: tuple[FreeAgent, ...] = ()  # sorted by person_id
    history_done: tuple[HistoryDone, ...] = ()  # sorted by key
    next_person_id: int = RIVAL_PERSON_BASE
    next_move_id: int = 1
    next_approach_id: int = 1
    next_rfp_id: int = 1
    boutiques_founded: int = 0
    # each active rival's NY panel appeal by practice (practices order), for the next intake
    appeals: tuple[tuple[str, tuple[float, ...]], ...] = ()
    opposing: tuple[tuple[int, str], ...] = ()  # (matter id, rival key or "" for a pool), by id

    def firm(self, firm_id: int) -> RivalFirm | None:
        for f in self.firms:
            if f.id == firm_id:
                return f
        return None

    def by_key(self, key: str) -> RivalFirm | None:
        for f in self.firms:
            if f.key == key:
                return f
        return None

    def member(self, person_id: int) -> Member | None:
        for m in self.members:
            if m.person_id == person_id:
                return m
        return None

    def members_of(self, firm_id: int) -> tuple[Member, ...]:
        return tuple(m for m in self.members if m.firm_id == firm_id)

    def rfp(self, rfp_id: int) -> Rfp | None:
        return next((r for r in self.rfps if r.id == rfp_id), None)

    def done(self, key: str) -> HistoryDone | None:
        return next((h for h in self.history_done if h.key == key), None)

    @property
    def active(self) -> tuple[RivalFirm, ...]:
        return tuple(f for f in self.firms if f.active)


EMPTY_RIVALS = RivalsState()
