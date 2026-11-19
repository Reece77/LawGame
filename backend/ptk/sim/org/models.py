"""Frozen org models: units, membership, hiring plans and delegates (TST formulas.md 13).

Ported from backend/tst/sim/org/models.py @ 02fba2aa (Tech Startup Tycoon); changed: unit
kinds are the practice group (one per practice) and the team, not TST's division and
department; no seats, authority, proposals or pitches (v2); work-location policy, product and
office links dropped; plans have PT's channels (campus, referral) and no equity; who belongs
to which unit, delegate energy, raise history and one-off morale changes live in one
`OrgState` on the game state, so the org's tables are its own (lane B beside PT-M1b).

The firm root is implicit: it has no row, `parent_id` and a member's unit are None for it,
and its leader is the firm's own founding partner (the player). Dissolved units and closed
plans stay in the state (they are few) so the save keeps their history; the helpers below
return live ones.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

type UnitKind = Literal["practice_group", "team"]
type UnitStatus = Literal["active", "dissolved"]
# PT's hiring channels (spec 5.7); "any" searches with a job post (13.10 step 1)
type PlanChannel = Literal["job_post", "recruiter", "referral", "campus", "any"]
type PlanFocus = Literal["current", "potential"]  # 13.10: best now, or spot potential
# active: the delegate works it; paused: its owner left or lost the right; filled; closed
type PlanStatus = Literal["active", "paused", "filled", "closed"]

UNIT_KINDS: tuple[UnitKind, ...] = ("practice_group", "team")
PLAN_CHANNELS: tuple[PlanChannel, ...] = ("job_post", "recruiter", "referral", "campus", "any")
PLAN_FOCUSES: tuple[PlanFocus, ...] = ("current", "potential")
# focus potential considers only these levels (13.10; TST's junior and mid)
POTENTIAL_LEVELS: frozenset[str] = frozenset(
    {"paralegal", "trainee", "associate_1", "associate_2", "associate_3", "staff"}
)
CAMPUS_LEVEL = "associate_1"  # a campus plan hires next September's first-year class (spec 5.7)


@dataclass(frozen=True, slots=True)
class OrgUnit:
    id: int
    firm_id: int
    kind: UnitKind
    name: str
    parent_id: int | None  # None = the firm root
    leader_id: int | None  # a member of this unit, or None
    created_turn: int
    practice: str | None = None  # a practice group's practice (practices.yaml key)
    status: UnitStatus = "active"
    dissolved_turn: int | None = None


@dataclass(frozen=True, slots=True)
class Membership:
    """A person's unit; people without one belong to the firm root."""

    person_id: int
    unit_id: int


@dataclass(frozen=True, slots=True)
class PlanActivity:
    """What a plan's delegate did in one turn (for the plan list and the inbox summary)."""

    turn: int
    searches: int = 0
    interviews: int = 0
    scouted: int = 0
    offers: int = 0

    @property
    def acted(self) -> bool:
        return bool(self.searches or self.interviews or self.scouted or self.offers)


@dataclass(frozen=True, slots=True)
class HiringPlan:
    id: int
    firm_id: int
    owner_id: int  # the delegate: a unit leader or a recruiting manager, never the founder
    unit_id: int | None  # where hires join; None = the firm root
    role: str
    target: int  # hires wanted in total
    channel: PlanChannel
    ratio_bp: int  # offered salary as bp of the candidate's ask
    created_turn: int
    status: PlanStatus = "active"
    hired: int = 0  # accepted offers made under this plan
    closed_turn: int | None = None
    last_activity: PlanActivity | None = None
    focus: PlanFocus = "current"
    level: str | None = None  # search filter: only candidates at this level
    hires: tuple[int, ...] = ()  # person ids hired under the plan, ascending

    @property
    def campus(self) -> bool:
        return self.channel == "campus"


@dataclass(frozen=True, slots=True)
class OrgPerson:
    """Org facts about one person: a delegate's own energy (13.10, ADR-0015), the turn of the
    last raise that earned the morale bonus (13.8), and accelerated promotions (class years
    skipped ahead of September)."""

    person_id: int
    energy: int | None = None  # None: not a delegate (no energy tracked)
    last_raise_turn: int | None = None
    accelerated_years: int = 0
    last_promoted_turn: int | None = None


@dataclass(frozen=True, slots=True)
class MoraleNudge:
    """A one-off morale change (13.7, 13.8) recorded by an org action in `turn`. Morale
    (PT-M1b) applies it in phase 8 of that turn; the org clears it then (interfaces.py)."""

    person_id: int
    turn: int
    points: float
    reason: str


@dataclass(frozen=True, slots=True)
class OrgState:
    units: tuple[OrgUnit, ...] = ()  # every unit, dissolved included, sorted by id
    members: tuple[Membership, ...] = ()  # sorted by person id
    plans: tuple[HiringPlan, ...] = ()  # every plan, closed included, sorted by id
    people: tuple[OrgPerson, ...] = ()  # sorted by person id
    nudges: tuple[MoraleNudge, ...] = ()  # in the order recorded
    next_unit_id: int = 1
    next_plan_id: int = 1

    def unit(self, unit_id: int) -> OrgUnit | None:
        for unit in self.units:
            if unit.id == unit_id:
                return unit
        return None

    def plan(self, plan_id: int) -> HiringPlan | None:
        for plan in self.plans:
            if plan.id == plan_id:
                return plan
        return None

    def unit_of(self, person_id: int) -> int | None:
        for m in self.members:
            if m.person_id == person_id:
                return m.unit_id
        return None

    def person(self, person_id: int) -> OrgPerson:
        for p in self.people:
            if p.person_id == person_id:
                return p
        return OrgPerson(person_id=person_id)

    def firm_units(self, firm_id: int) -> tuple[OrgUnit, ...]:
        """The firm's active units, by id."""
        return tuple(u for u in self.units if u.firm_id == firm_id and u.status == "active")

    def firm_plans(self, firm_id: int) -> tuple[HiringPlan, ...]:
        """The firm's plans that are not closed, by id."""
        return tuple(p for p in self.plans if p.firm_id == firm_id and p.status != "closed")

    def led_unit(self, person_id: int) -> OrgUnit | None:
        for unit in self.units:
            if unit.status == "active" and unit.leader_id == person_id:
                return unit
        return None


EMPTY_ORG = OrgState()
