"""Family members as people (TST formulas.md 45.1, 45.3): a partner and children generated
from stream `family` (id 51), a child's development each month, and the player's view.

Ported from backend/tst/sim/family/people.py @ 121d318a (Tech Startup Tycoon); changed:
members are generated with Partner Track's person generator (a child as a future lawyer of a
drawn practice, a partner as a business-services adult), never real (ADR PT-0013); a child's
development is a monthly pull of every skill toward their potential (Partner Track's growth
formula needs a month of work), times school or law school's `e` and closeness; no MBA.

Every draw is stream `family` (ADR-0013): `(head_id, member_index)` a member's making,
`(person_id, 1)` a child's month of development noise.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Final

import numpy as np

from ptk.sim.calendar import MONTHS_PER_YEAR
from ptk.sim.data_models import Balance, GameData
from ptk.sim.family.models import FamilyMember
from ptk.sim.people.generator import generate_person
from ptk.sim.people.models import PA_KEY, Person, RevealRecord, Skills
from ptk.sim.people.reveal import new_reveal_state
from ptk.sim.rng import RngFactory
from ptk.sim.scale import ABILITY_PER_ATTR, ATTR_MAX, ATTR_MIN
from ptk.sim.state import GameState, with_person, with_reveals

DEV_KEY: Final = 1  # stream family's (person_id, 1): a child's development noise
MIN_ADULT: Final = 21  # tunable-exempt: a partner's youngest age
CLOSENESS_BASE: Final = 0.8  # tunable-exempt: TST 45.3's x (0.8 + 0.4 x closeness / 100)
CLOSENESS_SPAN: Final = 0.4  # tunable-exempt: TST 45.3's formula constant
SCORE_MAX: Final = 100.0  # tunable-exempt: closeness is 0-100
PARTNER_ROLE: Final = "finance"  # a partner is generated as a business-services adult
CHILD_LEVEL: Final = "trainee"  # a child is generated as a future lawyer (the level's draws)


def family_stream(rng: RngFactory, turn: int, *key: int) -> np.random.Generator:
    """Stream `family` (51), this package's one call site: `(head_id, index)` a member's
    making (index >= 1), `(head_id, 0, k)` life events, `(person_id, 1)` development,
    `(head_id, 2, 0)` health."""
    return rng.stream(turn, "family", *key)


def _level_for(kind: str, balance: Balance) -> str:
    return next(k for k, v in balance.people.levels.items() if v.kind == kind)


def generate_partner(
    gen: np.random.Generator,
    head: Person,
    turn: int,
    person_id: int,
    balance: Balance,
    data: GameData,
    jurisdiction: str,
) -> Person:
    """A partner (TST 45.1): an adult near the head's age, with their own personality and
    interests; never on a firm's books."""
    role = data.role(PARTNER_ROLE)
    person = generate_person(
        gen,
        data,
        balance,
        turn,
        role,
        _level_for(role.kind, balance),
        person_id=person_id,
        city=head.city,
        jurisdiction=jurisdiction,
    )
    age = max(
        MIN_ADULT, head.age(turn) + round(float(gen.normal(0, balance.family.partner_age_sd)))
    )
    month = int(gen.integers(0, MONTHS_PER_YEAR))
    return replace(person, birth_turn=turn - MONTHS_PER_YEAR * age - month, real=False)


def generate_child(
    gen: np.random.Generator,
    parents: tuple[Person, ...],
    age: int,
    turn: int,
    person_id: int,
    balance: Balance,
    data: GameData,
    jurisdiction: str,
) -> Person:
    """A child (TST 45.1): a future lawyer of a drawn practice; personality blends the
    parents' (`inherit`) with their own and noise; potential is hidden; skills start at
    `child_skill_birth` plus a year's worth for each year before `develop_from`."""
    fb = balance.family
    head = parents[0]
    lawyers = [r for r in data.roles if r.kind == "lawyer"]
    role = lawyers[int(gen.integers(0, len(lawyers)))]
    base = generate_person(
        gen,
        data,
        balance,
        turn,
        role,
        CHILD_LEVEL,
        person_id=person_id,
        city=head.city,
        jurisdiction=jurisdiction,
    )
    month = int(gen.integers(0, MONTHS_PER_YEAR)) if age > 0 else 0
    birth = turn - MONTHS_PER_YEAR * age - month
    traits = {}
    for key in data.personality_keys:
        mean = sum(p.personality[key] for p in parents) / len(parents)
        noise = float(gen.normal(0.0, fb.trait_noise_sd))
        traits[key] = fb.inherit * mean + (1 - fb.inherit) * base.personality[key] + noise
    start = fb.child_skill_birth + fb.child_skill_year * min(age, fb.develop_from)
    skills = Skills.build(
        data.skill_keys,
        {k: start + float(gen.normal(0.0, fb.child_skill_sd)) for k in data.skill_keys},
    )
    pa = float(gen.uniform(fb.child_pa.lo, fb.child_pa.hi))
    child = replace(
        base,
        first_name=base.first_name,
        last_name=head.last_name,
        birth_turn=birth,
        skills=skills,
        personality=base.personality.updated(traits),
        potential_ability=pa,
        school_tier=None,
        bar_admissions=(),
        real=False,
    )
    lived = max(0, age - fb.develop_from) * MONTHS_PER_YEAR
    for _ in range(lived):  # a childhood already lived (setup ages), no noise
        child = develop(child, None, 1.0, CLOSENESS_BASE, balance)
    return child


def education_mult(member: FamilyMember | None, age: int, balance: Balance) -> float:
    """TST 45.3's `e`: the school's from school age, law school's until qualifying."""
    ed = balance.family.education
    if member is None:
        return 1.0
    if ed.school_age <= age < ed.law_school_age and member.school is not None:
        return ed.mult[f"school_{member.school}"]
    if ed.law_school_age <= age < ed.qualify_age and member.law_school is not None:
        return ed.mult[f"law_{member.law_school}"]
    return 1.0


def develop(
    person: Person,
    gen: np.random.Generator | None,
    e: float,
    bond: float,
    balance: Balance,
) -> Person:
    """One month of a child's development: each skill moves `child_growth / 12 x e x bond x
    noise` of the way toward potential / 10 (the 1-20 scale)."""
    fb = balance.family
    ceiling = min(ATTR_MAX, max(ATTR_MIN, person.potential_ability / ABILITY_PER_ATTR))
    noise = 1.0 + (float(gen.normal(0.0, 0.1)) if gen is not None else 0.0)  # tunable-exempt: sd
    rate = fb.child_growth / MONTHS_PER_YEAR * e * bond * max(0.0, noise)
    changes = {}
    for key, value in person.skills.items:
        gap = ceiling - value
        if gap > 0:
            changes[key] = value + rate * gap / ceiling
    return replace(person, skills=person.skills.updated(changes)) if changes else person


def bond_mult(closeness: float) -> float:
    return CLOSENESS_BASE + CLOSENESS_SPAN * closeness / SCORE_MAX


def add_member_person(
    state: GameState, person: Person, rng: RngFactory, balance: Balance, data: GameData
) -> GameState:
    """The person and the player's first view of them (ranges as for a stranger, narrowing
    with family time, TST 45.3)."""
    state = with_person(state, person)
    reveal = new_reveal_state(
        observer_firm_id=state.player.id,
        person=person,
        turn=state.turn,
        rng=rng,
        data=data,
        balance=balance,
    )
    return with_reveals(state, (reveal,))


def narrow_view(state: GameState, person_id: int, share: float, balance: Balance) -> GameState:
    """The player's view of a family member narrows: every half-width x (1 - share); the
    potential's never below `pa_hw_floor` (CLAUDE.md 10: never shown exactly)."""
    if share <= 0:
        return state
    reveal = state.reveal(state.player.id, person_id)
    if reveal is None:
        return state
    floor = balance.family.pa_hw_floor
    attrs = []
    for key, rec in reveal.attributes:
        hw = rec.hw * (1 - share)
        if key == PA_KEY:
            hw = max(min(rec.hw, floor), hw)
        attrs.append((key, RevealRecord(hw, rec.offset, state.turn)))
    return with_reveals(state, (replace(reveal, attributes=tuple(attrs)),))
