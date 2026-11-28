"""Frozen client and matter models (spec 7; ADR PT-0004, PT-0005, PT-0009). Never mutate.

The client universe (real and generated clients with their general counsel), the player's
relationships, named matters, judges, hours by person and matter for the last month played,
origination credit and courtroom familiarity live in one `MarketState` on the game state, so
PT-M3a's tables are its own (lane A).

Hidden true values: a matter's `merits` and `opposing_quality`, a judge's traits and a general
counsel's personality are used by the engine and never reach the API or a prompt (CLAUDE.md
section 10). The API shows bands and labels built from them by explicit view functions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from simcore.kernel.hidden import HIDDEN_KEY, hidden_field

from ptk.sim.people.models import AttrSet, Personality

type SizeClass = Literal["large", "mid"]
type MatterStatus = Literal["open", "conflicted", "closed", "declined"]
# How a closed matter ended. Cases: won, lost, settled; deals: closed, collapsed; advisory and
# filings: done; conflicts: disqualified (a hidden conflict surfaced).
type Outcome = Literal["won", "lost", "settled", "closed", "collapsed", "done", "disqualified"]
type TeamRole = Literal["lead", "senior", "junior", "paralegal"]

TEAM_ROLES: tuple[TeamRole, ...] = ("lead", "senior", "junior", "paralegal")
# PT-M7a (spec 7.8): pro bono work's client. Hours and named matters for it carry this id; it
# has no wallet, panel or relationship, and its hours have no value (no WIP, bills or fees).
PRO_BONO_CLIENT_ID = 0


@dataclass(frozen=True, slots=True)
class JudgeTraits(AttrSet):
    """Procedural traits 1-20 (courts.yaml judge_traits): never a side (ADR PT-0013)."""


@dataclass(frozen=True, slots=True)
class GeneralCounsel:
    """A client's general counsel (spec 7.3): a generated person with a personality."""

    first_name: str
    last_name: str
    birth_turn: int
    personality: Personality = field(metadata={HIDDEN_KEY: True})  # hidden from the API


@dataclass(frozen=True, slots=True)
class Client:
    id: int
    name: str
    sector: str  # clients.yaml sectors key
    country: str
    real: bool  # a real 2005 company (clients.yaml)
    revenue_bn: float  # size, 2005 USD billions
    size_class: SizeClass
    price_sensitivity: float  # 1-20
    loyalty: float  # 1-20
    gc: GeneralCounsel
    panel: tuple[str, ...]  # static panel firms' keys (clients.yaml panel_firms), sorted
    city: str = ""  # PT-M11: cities.yaml key of its local market; "" = the home market


_NEUTRAL = 10.0  # tunable-exempt: a neutral 1-20 trait
PRO_BONO_CLIENT = Client(
    id=PRO_BONO_CLIENT_ID,
    name="Pro bono client",
    sector="pro_bono",  # not a clients.yaml sector: views label it themselves
    country="us",
    real=False,
    revenue_bn=0.0,
    size_class="mid",
    price_sensitivity=_NEUTRAL,
    loyalty=_NEUTRAL,
    gc=GeneralCounsel(
        first_name="Clinic",
        last_name="Director",
        birth_turn=0,
        personality=Personality(
            tuple(
                (k, _NEUTRAL)
                for k in (
                    "ambition",
                    "loyalty",
                    "professionalism",
                    "temperament",
                    "adaptability",
                    "risk_appetite",
                    "ego",
                    "integrity",
                    "sociability",
                )
            )
        ),
    ),
    panel=(),
)


@dataclass(frozen=True, slots=True)
class MeritsAssessment:
    """PT-M7a: early case assessment (spec 7.6): the merits as the firm now sees them, a
    revealed range (logit points) that always holds the hidden true merits."""

    turn: int
    lo: float
    hi: float


@dataclass(frozen=True, slots=True)
class Relationship:
    """A firm on a client's panel (spec 7.2). Only the player's firm keeps relationships in
    PT-M3a; static panel firms have a fixed appeal."""

    client_id: int
    firm_id: int
    score: float  # 0-100
    partner_id: int | None  # the relationship partner, who earns origination credit
    practices: tuple[str, ...]  # practices the firm is instructed in (practices.yaml order)
    since_turn: int
    last_instructed_turn: int | None = None
    advance_waiver: bool = False  # the client waived conflicts in advance (ADR PT-0009 2)
    lost_share: float = 0.0  # last month's share of the client's flow the firm could not serve
    fees: tuple[int, ...] = ()  # standard-value cents of work, the last 12 months, oldest first
    intro_turns: tuple[tuple[str, int], ...] = ()  # (practice, turn) of the latest introduction

    @property
    def fees_12m(self) -> int:
        return sum(self.fees)


@dataclass(frozen=True, slots=True)
class TeamMember:
    person_id: int
    role: TeamRole
    planned_tenths: int  # hours a month the person is planned to work, in tenths


@dataclass(frozen=True, slots=True)
class SettlementOffer:
    """The other side's offer (spec 7.6): a pending item the player answers (ADR-0014)."""

    fraction_bp: int  # share of the stakes the client would recover
    made_turn: int
    expires_turn: int  # the last turn it can be accepted


@dataclass(frozen=True, slots=True)
class Matter:
    id: int
    firm_id: int
    client_id: int
    practice: str
    kind_key: str  # practices.yaml matter_kinds key
    kind: str  # deal, case, investigation, restructuring, advisory, filing
    name: str
    opened_turn: int
    planned_months: int  # duration at intake (after the court's pace)
    expected_fees_cents: int  # at standard rates (ADR PT-0004)
    hours_needed_tenths: int  # standard hours of work (grows with rework and discovery)
    status: MatterStatus = "open"
    adverse_client_id: int | None = None  # the adverse party when it is a client
    adverse_name: str = ""
    critical: bool = False
    flagged: bool = False
    checked: bool = True  # conflicts were checked at intake (ADR PT-0009 5)
    waiver: bool = False  # a specific waiver let it open
    hidden_conflict: bool = hidden_field(
        default=False
    )  # adverse to a current client, unseen: checks were skipped
    originator_id: int | None = None
    lead_id: int | None = None
    team: tuple[TeamMember, ...] = ()  # sorted by person id
    auto_staff: bool = True  # re-planned monthly by the default rule until the player staffs it
    phase_index: int = 0
    phase_progress: float = 0.0  # 0-1 of the current phase
    worked_tenths: int = 0
    wip_cents: int = 0  # standard value of hours worked (PT-M3b bills it)
    craft_hours: float = 0.0  # Σ hours x effective craft (for p_win and deal quality)
    craft_weight: float = 0.0  # Σ hours behind craft_hours
    under_months: int = 0  # months under the planned pace
    errors_caught: int = 0
    errors_escaped: int = 0
    missed_deadlines: int = 0
    court: str | None = None  # courts.yaml key (case kinds)
    judge_id: int | None = None
    stakes_cents: int = 0  # cases: the amount in dispute
    merits: float = hidden_field(default=0.0)  # hidden: logit points for our side (spec 7.6)
    opposing_quality: float = hidden_field(default=0.0)  # hidden: opposing counsel's craft 1-20
    settlement: SettlementOffer | None = None
    outcome: Outcome | None = None
    closed_turn: int | None = None
    quality: float | None = None  # 1-20: the team's craft on the result
    assessment: MeritsAssessment | None = None  # PT-M7a: early case assessment (revealed)

    @property
    def pro_bono(self) -> bool:
        """PT-M7a (spec 7.8): work for the pro bono client, with no fees."""
        return self.client_id == PRO_BONO_CLIENT_ID

    @property
    def is_open(self) -> bool:
        return self.status == "open"

    def member(self, person_id: int) -> TeamMember | None:
        return next((m for m in self.team if m.person_id == person_id), None)


@dataclass(frozen=True, slots=True)
class Judge:
    id: int
    court: str
    first_name: str
    last_name: str
    traits: JudgeTraits = field(metadata={HIDDEN_KEY: True})  # hidden: procedural only
    real: bool = False  # real judges arrive with PT-M5 (ADR PT-0013)
    from_turn: int = 0  # PT-M5: first turn on the bench
    until_turn: int | None = None  # PT-M5: first turn off it (None: never leaves)

    def sits(self, turn: int) -> bool:
        return self.from_turn <= turn and (self.until_turn is None or turn < self.until_turn)


@dataclass(frozen=True, slots=True)
class Appearance:
    """Hours a lawyer has appeared before a judge (spec 7.6a), in tenths."""

    person_id: int
    judge_id: int
    tenths: int


@dataclass(frozen=True, slots=True)
class Origination:
    """Origination credit (spec 7.2): standard-value cents of work from a partner's clients."""

    person_id: int
    year: int
    cents: int


@dataclass(frozen=True, slots=True)
class HoursRecord:
    """One person's hours on one matter (or one client's flow) in a month (ADR PT-0005)."""

    turn: int
    person_id: int
    client_id: int
    practice: str
    matter_id: int | None  # None: flow work
    tenths: int
    substantive_tenths: int
    value_cents: int  # tenths x rate / 10, rounded half to even once


@dataclass(frozen=True, slots=True)
class MarketState:
    clients: tuple[Client, ...] = ()  # sorted by id
    relationships: tuple[Relationship, ...] = ()  # sorted by (client_id, firm_id)
    matters: tuple[Matter, ...] = ()  # sorted by id
    judges: tuple[Judge, ...] = ()  # sorted by id
    appearances: tuple[Appearance, ...] = ()  # sorted by (person_id, judge_id)
    originations: tuple[Origination, ...] = ()  # sorted by (person_id, year)
    hours: tuple[HoursRecord, ...] = ()  # the last month played, sorted by (person, matter)
    demand_cents: tuple[int, ...] = ()  # the last month's demand by practice (practices order)

    def client(self, client_id: int) -> Client:
        if client_id == PRO_BONO_CLIENT_ID:  # PT-M7a: never stored with the clients
            return PRO_BONO_CLIENT
        # ids are 1..n in order (clients are never removed in PT-M3a)
        if 0 < client_id <= len(self.clients) and self.clients[client_id - 1].id == client_id:
            return self.clients[client_id - 1]
        for c in self.clients:
            if c.id == client_id:
                return c
        raise KeyError(f"no client {client_id}")

    def relationship(self, client_id: int, firm_id: int) -> Relationship | None:
        # PT-M13 (T12): an index memoised on the (immutable) tuple's identity; the first match
        # by position, as the scan returned
        rels = self.relationships
        hit = _REL_INDEX.get(id(rels))
        if hit is None or hit[0] is not rels:
            index: dict[tuple[int, int], Relationship] = {}
            for r in rels:
                index.setdefault((r.client_id, r.firm_id), r)
            hit = (rels, index)
            if len(_REL_INDEX) >= _INDEX_KEEP:
                _REL_INDEX.clear()
            _REL_INDEX[id(rels)] = hit
        return hit[1].get((client_id, firm_id))

    def matter(self, matter_id: int) -> Matter | None:
        matters = self.matters  # PT-M13 (T12): memoised as `relationship`
        hit = _MATTER_INDEX.get(id(matters))
        if hit is None or hit[0] is not matters:
            index: dict[int, Matter] = {}
            for m in matters:
                index.setdefault(m.id, m)
            hit = (matters, index)
            if len(_MATTER_INDEX) >= _INDEX_KEEP:
                _MATTER_INDEX.clear()
            _MATTER_INDEX[id(matters)] = hit
        return hit[1].get(matter_id)

    def judge(self, judge_id: int) -> Judge:
        for j in self.judges:
            if j.id == judge_id:
                return j
        raise KeyError(f"no judge {judge_id}")

    def open_matters(self, firm_id: int) -> tuple[Matter, ...]:
        return tuple(m for m in self.matters if m.firm_id == firm_id and m.is_open)

    @property
    def next_matter_id(self) -> int:
        return max((m.id for m in self.matters), default=0) + 1


_REL_INDEX: dict[int, tuple[tuple[Relationship, ...], dict[tuple[int, int], Relationship]]] = {}
_MATTER_INDEX: dict[int, tuple[tuple[Matter, ...], dict[int, Matter]]] = {}
_INDEX_KEEP = 64  # tunable-exempt: memoised tuples (a cache, not a rule)

EMPTY_MARKET = MarketState()
