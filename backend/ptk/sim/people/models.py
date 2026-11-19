"""Frozen people models (ADR-0002, ADR-0007, ADR PT-0006). Return new objects; never mutate.

Ported from backend/tst/sim/people/models.py @ 02fba2aa (Tech Startup Tycoon); changed:
levels are class years and titles (ADR PT-0006 section 1); a person carries practice
familiarity and its peak, law school tier, bar admissions, strain and burnout, and a
partner's book and hidden portability; every person has a role (a founding partner's is
their home practice, not TST's best fit); employment is with a firm; reveal records also
cover familiarity. PT-M1b adds an employment's salary (asks live on hiring candidates).

True values live here and are used by the sim. What an observer firm knows is a separate
`RevealState` per (observer, person); the API only ever sees ranges built from it.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Final, Literal, Self

from ptk.sim.calendar import age_at
from ptk.sim.data_models import GameData, Role
from ptk.sim.people.formulas import current_ability as _ca
from ptk.sim.scale import ATTR_MAX, ATTR_MIN

PA_KEY: Final = "potential_ability"  # reveal record key for potential ability
FAM_PREFIX: Final = "fam:"  # reveal record keys for familiarity: "fam:<practice>"

type EmploymentStatus = Literal["active", "notice", "ended"]
type Rest = Literal["none", "holiday", "sabbatical"]
type EndReason = Literal["resigned", "fired", "retired", "firm_dissolved", "poached"]


def fam_key(practice: str) -> str:
    return f"{FAM_PREFIX}{practice}"


@dataclass(frozen=True, slots=True)
class AttrSet:
    """An ordered, immutable set of named 1-20 attributes.

    Order follows the data file (skills.yaml, personality.yaml, practices.yaml), which fixes
    the order of random draws (ADR-0013). Every value is clamped on construction.
    """

    items: tuple[tuple[str, float], ...]

    def __post_init__(self) -> None:
        lo, hi = ATTR_MIN, ATTR_MAX
        object.__setattr__(
            self,
            "items",
            tuple((k, hi if v > hi else lo if v < lo else v) for k, v in self.items),
        )

    @classmethod
    def build(cls, keys: Iterable[str], values: Mapping[str, float]) -> Self:
        return cls(tuple((k, values[k]) for k in keys))

    def __getitem__(self, key: str) -> float:
        for k, v in self.items:
            if k == key:
                return v
        raise KeyError(key)

    def __contains__(self, key: object) -> bool:
        return any(k == key for k, _ in self.items)

    def keys(self) -> tuple[str, ...]:
        return tuple(k for k, _ in self.items)

    def as_dict(self) -> dict[str, float]:
        return dict(self.items)

    def updated(self, changes: Mapping[str, float]) -> Self:
        """A copy with some values replaced (clamped)."""
        return type(self)(tuple((k, changes.get(k, v)) for k, v in self.items))


@dataclass(frozen=True, slots=True)
class Skills(AttrSet):
    pass


@dataclass(frozen=True, slots=True)
class Personality(AttrSet):
    pass


@dataclass(frozen=True, slots=True)
class HiddenTraits(AttrSet):
    pass


@dataclass(frozen=True, slots=True)
class Familiarity(AttrSet):
    """Practice familiarity 1-20 per practice (ADR PT-0006 section 2)."""


@dataclass(frozen=True, slots=True)
class Person:
    id: int
    first_name: str
    last_name: str
    birth_turn: int
    role: str  # roles.yaml key; a lawyer's role is their home practice
    level: str  # balance people.levels key
    skills: Skills
    personality: Personality
    hidden: HiddenTraits  # never in the API or a prompt (ADR PT-0006 section 5)
    potential_ability: float  # hidden, 10-200, never changes
    familiarity: Familiarity
    familiarity_peak: Familiarity  # highest reached: decay stops 3 below it (spec 5.3)
    interests: tuple[str, ...]
    work_style: str
    tags: tuple[str, ...]  # true behavior tags (hidden until revealed per observer)
    school_tier: str | None  # lawyers only
    bar_admissions: tuple[str, ...]  # jurisdiction keys, sorted
    city: str
    strain: float = 0.0  # 0-100 (spec 5.6)
    burnout_since: int | None = None  # turn the current burnout began; None = not burnt out
    last_burnout_turn: int | None = None  # start of the latest burnout (its 6-month effects)
    book_cents: int = 0  # a partner's book of business a year, 2005 USD (used from PT-M3a)
    portability_bp: int | None = None  # hidden: share of the book that follows them (PT-M4)
    is_founder: bool = False  # the player's own founding partner
    founding_partner: bool = False  # any partner who founded the firm (spec 2.1)
    background: str | None = None  # backgrounds.yaml key, founding partners only
    real: bool = False  # a real lawyer (ADR PT-0013; from PT-M5): no negative tags or events

    def age(self, turn: int) -> int:
        return age_at(turn, self.birth_turn)

    @property
    def burnt_out(self) -> bool:
        return self.burnout_since is not None


@dataclass(frozen=True, slots=True)
class RevealRecord:
    """What one observer knows about one attribute: half-width and centre offset."""

    hw: float
    offset: float
    last_updated_turn: int


@dataclass(frozen=True, slots=True)
class RevealState:
    """Everything one observer firm knows about one person (ADR-0007)."""

    observer_firm_id: int
    person_id: int
    # skills, personality, PA_KEY, then familiarity ("fam:<practice>")
    attributes: tuple[tuple[str, RevealRecord], ...]
    profile_revealed_turn: int | None  # interests and work style shown from this turn
    revealed_tags: tuple[tuple[str, int], ...]  # (tag, revealed_turn)

    def record(self, attribute: str) -> RevealRecord:
        for key, rec in self.attributes:
            if key == attribute:
                return rec
        raise KeyError(attribute)


@dataclass(frozen=True, slots=True)
class Employment:
    id: int
    person_id: int
    firm_id: int
    start_turn: int
    end_turn: int | None = None
    status: EmploymentStatus = "active"
    end_reason: EndReason | None = None
    salary_cents: int = 0  # a year (PT-M1b); 0 for equity partners, who take profit

    @property
    def counts_as_staff(self) -> bool:
        """Active and notice employments are on the books (headcount, growth)."""
        return self.status != "ended"


@dataclass(frozen=True, slots=True)
class WorkMonth:
    """One person's month of work (ADR PT-0005: hours in integer tenths).

    Until PT-M3a staffs matters, this is a test input (the brief): hours worked in each
    practice, how many of all hours were substantive work at or slightly above the person's
    level (learn(h), ADR PT-0006 section 4), hours outside any practice (business
    development, management) and whether the month was a holiday or a sabbatical.
    """

    person_id: int
    practice_tenths: tuple[tuple[str, int], ...] = ()  # (practice, tenths), practices order
    substantive_tenths: int = 0
    other_tenths: int = 0
    rest: Rest = "none"

    @property
    def total_tenths(self) -> int:
        return sum(t for _, t in self.practice_tenths) + self.other_tenths

    def tenths_in(self, practice: str) -> int:
        return sum(t for p, t in self.practice_tenths if p == practice)


# --- Current ability ------------------------------------------------------------------------


def role_ability(skills: Skills, role: Role) -> float:
    return _ca(skills.as_dict(), role.primary, role.secondary)


def current_ability(person: Person, data: GameData) -> float:
    """CA for a person against their role (formulas.md 1)."""
    return role_ability(person.skills, data.role(person.role))
