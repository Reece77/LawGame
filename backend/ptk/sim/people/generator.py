"""Person generation (formulas.md section 2, adapted; spec 5.1-5.2).

Ported from backend/tst/sim/people/generator.py @ 02fba2aa (Tech Startup Tycoon); changed:
levels are class years (ADR PT-0006); a lawyer draws a law school tier first, which shifts
the target CA and the potential gap; practice familiarity is drawn after the name (home
practice in the level's 10-16 range, others 1-6); partners draw a hidden portability;
lawyers are admitted in the firm's home jurisdiction; one US name pool; no regions, cities'
talent bonuses or salary expectation (PT-M1b).

The caller passes a `numpy.random.Generator` from the right stream (ADR-0013): starting
staff and searches use `people_gen`; founding partners use `founder`. Draws happen in this
fixed order, one call each, so a person is reproducible from the generator state:

1. school tier                    lawyers only; weighted by people.school_tier_weights
2. target CA                      Normal(level mean + tier shift, sd), clipped to ca_clip
3. skills, in skills.yaml order    primary Normal(0, sd_p) / secondary Normal(0, sd_s) /
                                   other Uniform(min, max) -- exactly one draw per skill
4. age                            integer in the level's [min, max]
5. birth month                    integer in [0, 11]
6. potential gap                  Normal(gap_mean(age) + tier shift, pa_gap_sd)
7. personality, then hidden traits Normal(mean, sd) each, in personality.yaml order
8. interest count, then interests count in interest_count; weighted, without replacement
9. work style                     weighted by the role
10. tags, in tags.yaml order      one roll in [0, 10000) per tag, always drawn
11. first name, then last name    uniform from the pool
12. familiarity                   lawyers and paralegals: one Uniform per practice, in
                                  practices.yaml order (the home practice in the level's
                                  home_familiarity range, others in other_familiarity)
13. portability                   partners only: integer bp in people.portability_bp

Rescaling the primaries to hit the target CA draws nothing.
"""

from __future__ import annotations

import itertools
from collections.abc import Mapping, Sequence

import numpy as np

from ptk.sim.calendar import MONTHS_PER_YEAR
from ptk.sim.data_models import PARTNER_LEVELS, Balance, GameData, Role, Tag
from ptk.sim.errors import InvalidPersonError
from ptk.sim.money import BP_DENOMINATOR
from ptk.sim.people.formulas import current_ability, pa_gap_mean
from ptk.sim.people.models import Familiarity, HiddenTraits, Person, Personality, Skills
from ptk.sim.rng import RngFactory
from ptk.sim.scale import (
    ABILITY_MAX,
    ABILITY_PER_ATTR,
    ATTR_MAX,
    ATTR_MIN,
    PRIMARY_WEIGHT,
    SECONDARY_WEIGHT,
    clamp_ability,
    clamp_attr,
)

NAME_POOL = "us"  # v1's one country (names.yaml)


def _weighted_pick(
    gen: np.random.Generator, weights: Mapping[str, float], keys: Sequence[str]
) -> str:
    w = np.array([weights[k] for k in keys], dtype=float)
    return keys[int(gen.choice(len(keys), p=w / w.sum()))]


def draw_school_tier(gen: np.random.Generator, balance: Balance) -> str:
    weights = balance.people.school_tier_weights
    return _weighted_pick(gen, weights, list(weights))  # in balance.yaml order


def draw_traits(
    gen: np.random.Generator, keys: Sequence[str], balance: Balance
) -> dict[str, float]:
    """Normal(mean, sd) per trait, in the given order (step 7)."""
    people = balance.people
    return {k: float(gen.normal(people.personality_mean, people.personality_sd)) for k in keys}


def draw_interests(
    gen: np.random.Generator, role: Role, data: GameData, balance: Balance
) -> tuple[str, ...]:
    """Count uniform in interest_count, then weighted draws without replacement (step 8)."""
    span = balance.people.interest_count
    count = int(gen.integers(int(span.lo), int(span.hi), endpoint=True))
    keys = data.interest_keys
    w = np.array([role.interest_weights.get(k, 1.0) for k in keys], dtype=float)
    count = min(count, int(np.count_nonzero(w)))
    picks = gen.choice(len(keys), size=count, replace=False, p=w / w.sum())
    return tuple(keys[int(i)] for i in picks)


def draw_work_style(gen: np.random.Generator, role: Role, data: GameData) -> str:
    return _weighted_pick(gen, role.work_style_weights, data.work_style_keys)


def tag_chance_bp(tag: Tag, personality: Personality) -> float:
    """base_bp, times the boost multiplier when every boost condition holds (step 10)."""
    boosted = all(c.holds(personality[c.attr]) for c in tag.boost.when)
    return tag.base_bp * (tag.boost.multiplier if boosted else 1)


def draw_tags(
    gen: np.random.Generator,
    personality: Personality,
    data: GameData,
    balance: Balance,
    *,
    real: bool = False,
) -> tuple[str, ...]:
    """One roll per tag in file order; skip excluded tags; at most max_tags (step 10).

    A real person (ADR PT-0013) never receives a negative tag; the roll is still drawn."""
    assigned: list[str] = []
    for tag in data.tags:
        roll = int(gen.integers(0, BP_DENOMINATOR))
        if len(assigned) >= balance.people.max_tags or (real and tag.negative):
            continue
        if any(tag.key in data_tag.excludes for data_tag in data.tags if data_tag.key in assigned):
            continue
        if roll < tag_chance_bp(tag, personality):
            assigned.append(tag.key)
    return tuple(assigned)


def draw_name(gen: np.random.Generator, data: GameData) -> tuple[str, str]:
    pool = data.names[NAME_POOL]
    first = pool.first[int(gen.integers(0, len(pool.first)))]
    last = pool.last[int(gen.integers(0, len(pool.last)))]
    return first, last


def draw_familiarity(
    gen: np.random.Generator,
    data: GameData,
    home: str | None,
    home_range: tuple[float, float],
    other_range: tuple[float, float],
    *,
    familiar: frozenset[str] = frozenset(),
) -> Familiarity:
    """One Uniform per practice in file order (step 12): `home` and `familiar` practices in
    `home_range`, every other practice in `other_range`."""
    values: dict[str, float] = {}
    for key in data.practice_keys:
        lo, hi = home_range if key == home or key in familiar else other_range
        values[key] = float(gen.uniform(lo, hi))
    return Familiarity.build(data.practice_keys, values)


def flat_familiarity(data: GameData) -> Familiarity:
    """Business services staff: familiarity 1 everywhere, no draws."""
    return Familiarity.build(data.practice_keys, dict.fromkeys(data.practice_keys, ATTR_MIN))


def potential_ability(
    gen: np.random.Generator, ca: float, age: int, balance: Balance, shift: float = 0.0
) -> float:
    """PA = min(200, CA + max(0, Normal(gap_mean(age) + shift, sd))) (step 6)."""
    mean = pa_gap_mean(age, balance.people) + shift
    gap = float(gen.normal(mean, balance.people.pa_gap_sd))
    return clamp_ability(min(ABILITY_MAX, ca + max(0.0, gap)))


def draw_portability_bp(gen: np.random.Generator, balance: Balance) -> int:
    span = balance.people.portability_bp
    return int(gen.integers(int(span.lo), int(span.hi), endpoint=True))


def _rescale_primaries(skills: dict[str, float], role: Role, target_ca: float) -> dict[str, float]:
    """Scale the primaries by one common factor f so CA hits the target (step 3).

    With clamping, the primary sum S(f) = sum(clamp(p_i x f)) is continuous, non-decreasing
    and linear between the breakpoints where a primary reaches 1 or 20, so f is found exactly
    by locating the segment that contains the needed sum. Targets outside what clamped
    primaries can reach get the nearest reachable CA.
    """
    primary = [skills[k] for k in role.primary]
    secondary_sum = sum(skills[k] for k in role.secondary)
    weight = PRIMARY_WEIGHT * len(role.primary) + SECONDARY_WEIGHT * len(role.secondary)
    needed = (target_ca / ABILITY_PER_ATTR * weight - SECONDARY_WEIGHT * secondary_sum) / (
        PRIMARY_WEIGHT
    )

    def total(f: float) -> float:
        return sum(clamp_attr(p * f) for p in primary)

    points = sorted({b / p for p in primary for b in (ATTR_MIN, ATTR_MAX)})
    if needed <= total(points[0]):
        factor = points[0]
    elif needed >= total(points[-1]):
        factor = points[-1]
    else:
        factor = points[-1]
        for lo, hi in itertools.pairwise(points):
            s_lo, s_hi = total(lo), total(hi)
            if s_lo <= needed <= s_hi:
                factor = lo if s_hi == s_lo else lo + (needed - s_lo) * (hi - lo) / (s_hi - s_lo)
                break
    return {**skills, **{k: clamp_attr(skills[k] * factor) for k in role.primary}}


def people_gen_stream(rng: RngFactory, turn: int, *key: int) -> np.random.Generator:
    """Stream `people_gen` (ADR-0013): key `(search_id, n)`, the n-th person of a search;
    search 0 is a scenario's starting staff. This is the stream's one call site."""
    return rng.stream(turn, "people_gen", *key)


def generate_person(
    gen: np.random.Generator,
    data: GameData,
    balance: Balance,
    turn: int,
    role: Role,
    level: str,
    *,
    person_id: int,
    city: str,
    jurisdiction: str,
    practice: str | None = None,
) -> Person:
    """One generated person of `role` at `level`. A lawyer's home practice is their role's;
    a paralegal's is `practice` (or none). Lawyers past trainee are admitted in
    `jurisdiction`."""
    people = balance.people
    level_def = people.levels.get(level)
    if level_def is None or level_def.kind != role.kind:
        raise InvalidPersonError(f"a {role.kind} role ({role.key}) cannot hold level {level!r}")
    is_lawyer = role.kind == "lawyer"
    home = role.practice if is_lawyer else practice

    tier = draw_school_tier(gen, balance) if is_lawyer else None
    ca_shift = data.school_tier(tier).ca_shift if tier else 0.0
    pa_shift = data.school_tier(tier).pa_shift if tier else 0.0
    target = float(gen.normal(level_def.ca.mean + ca_shift, level_def.ca.sd))
    target = min(max(target, people.ca_clip.lo), people.ca_clip.hi)

    primaries, secondaries = set(role.primary), set(role.secondary)
    raw: dict[str, float] = {}
    for key in data.skill_keys:
        if key in primaries:
            noise = float(gen.normal(0.0, people.skill_noise_sd.primary))
            raw[key] = clamp_attr(target / ABILITY_PER_ATTR + noise)
        elif key in secondaries:
            noise = float(gen.normal(0.0, people.skill_noise_sd.secondary))
            raw[key] = clamp_attr(target / ABILITY_PER_ATTR - people.secondary_offset + noise)
        else:
            lo, hi = people.other_skill_range.lo, people.other_skill_range.hi
            raw[key] = clamp_attr(float(gen.uniform(lo, hi)))
    if abs(current_ability(raw, role.primary, role.secondary) - target) > people.ca_tolerance:
        raw = _rescale_primaries(raw, role, target)
    skills = Skills.build(data.skill_keys, raw)
    ca = current_ability(skills.as_dict(), role.primary, role.secondary)

    ages = level_def.age
    age = int(gen.integers(int(ages.lo), int(ages.hi), endpoint=True))
    birth_month = int(gen.integers(0, MONTHS_PER_YEAR))
    birth_turn = turn - MONTHS_PER_YEAR * age - birth_month
    pa = potential_ability(gen, ca, age, balance, pa_shift)

    personality = Personality.build(
        data.personality_keys, draw_traits(gen, data.personality_keys, balance)
    )
    hidden = HiddenTraits.build(data.hidden_keys, draw_traits(gen, data.hidden_keys, balance))
    interests = draw_interests(gen, role, data, balance)
    work_style = draw_work_style(gen, role, data)
    tags = draw_tags(gen, personality, data, balance)
    first, last = draw_name(gen, data)

    if level_def.home_familiarity is None:
        familiarity = flat_familiarity(data)
    else:
        home_span = level_def.home_familiarity
        other = people.other_familiarity
        familiarity = draw_familiarity(
            gen, data, home, (home_span.lo, home_span.hi), (other.lo, other.hi)
        )
    portability = draw_portability_bp(gen, balance) if level in PARTNER_LEVELS else None
    admitted = is_lawyer and level != "trainee"
    return Person(
        id=person_id,
        first_name=first,
        last_name=last,
        birth_turn=birth_turn,
        role=role.key,
        level=level,
        skills=skills,
        personality=personality,
        hidden=hidden,
        potential_ability=pa,
        familiarity=familiarity,
        familiarity_peak=familiarity,
        interests=interests,
        work_style=work_style,
        tags=tags,
        school_tier=tier,
        bar_admissions=(jurisdiction,) if admitted else (),
        city=city,
        portability_bp=portability,
    )
