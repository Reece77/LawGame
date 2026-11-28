"""Pure people formulas (formulas.md sections 1-4; spec 5.1, 5.3, 5.6).

Ported from backend/tst/sim/people/formulas.py @ 02fba2aa (Tech Startup Tycoon); changed:
growth gains the learning factor `learn(h)` (ADR PT-0006 section 4); new formulas for
practice familiarity (fam_factor, gain and decay) and strain (spec 5.6); the salary
expectation (TST 2.8) waits for PT-M1b's salary scale.

No randomness here: callers draw noise from their own stream (ADR-0013) and add it.
Every number comes from `Balance` or from the scale definitions in `simcore.kernel.scale`.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Final

from simcore.kernel.scale import (
    ABILITY_PER_ATTR,
    ATTR_MAX,
    ATTR_MIN,
    PRIMARY_WEIGHT,
    PROFESSIONALISM_DIVISOR,
    SECONDARY_WEIGHT,
)

from ptk.sim.data_models import (
    FamiliarityBalance,
    GrowthBalance,
    PeopleBalance,
    RevealBalance,
    StrainBalance,
    band_value,
)

# Below half an attribute point the range collapses to the rounded true value (section 4).
EXACT_HALF_WIDTH: Final = 0.5  # tunable-exempt: rounding threshold in the reveal rule
HOURS_PER_HUNDRED: Final = 100  # tunable-exempt: familiarity gain is quoted per 100 hours
STRAIN_MIN: Final = 0.0  # strain scale floor (spec 5.6)
STRAIN_MAX: Final = 100.0  # tunable-exempt: strain scale ceiling (spec 5.6)


# --- Section 1: current ability -------------------------------------------------------------


def current_ability(
    skills: Mapping[str, float], primary: Sequence[str], secondary: Sequence[str]
) -> float:
    """CA = 10 x (3 x sum(primary) + sum(secondary)) / (3 x n_primary + n_secondary)."""
    numerator = PRIMARY_WEIGHT * sum(skills[k] for k in primary) + SECONDARY_WEIGHT * sum(
        skills[k] for k in secondary
    )
    denominator = PRIMARY_WEIGHT * len(primary) + SECONDARY_WEIGHT * len(secondary)
    return ABILITY_PER_ATTR * numerator / denominator


# --- Section 2: generation helpers ----------------------------------------------------------


def pa_gap_mean(age: int, people: PeopleBalance) -> float:
    return band_value(people.pa_gap_mean, age)


# --- Section 3: monthly growth, with learning (ADR PT-0006 section 4) -------------------------


def learn_factor(total_tenths: int, substantive_tenths: int, growth: GrowthBalance) -> float:
    """learn(h) = (substantive share of hours) / reference share, clamped (spec 5.3).

    A month with no hours learns at the lower bound."""
    lo, hi = growth.learn.clamp.lo, growth.learn.clamp.hi
    if total_tenths <= 0:
        return lo
    share = min(max(substantive_tenths, 0), total_tenths) / total_tenths
    return min(max(share / growth.learn.reference_share, lo), hi)


def growth_delta(
    *,
    in_role: bool,
    age: int,
    ca: float,
    pa: float,
    professionalism: float,
    growth: GrowthBalance,
    noise: float = 0.0,
    mentoring: float = 1.0,
    learn: float = 1.0,
) -> float:
    """Monthly change for one skill.

    Role skills: r x a(age) x max(0, PA - CA) / PA x professionalism / 10
                 x max(0, 1 + noise) x mentoring x learn(h) - d(age),
    where the caller draws noise ~ Normal(0, growth.noise_rel_sd); noise 0 is the
    noise-free value used by the worked examples. `mentoring` is TST 13.5's M_growth (1
    until PT-M2's supervising partners). Other skills: -d(age), with no noise.
    """
    decline = band_value(growth.decline, age)
    if not in_role:
        return -decline
    multiplier = max(0.0, 1 + noise)
    return growth_base(age, ca, pa, professionalism, growth) * multiplier * mentoring * learn - (
        decline
    )


def growth_base(
    age: int, ca: float, pa: float, professionalism: float, growth: GrowthBalance
) -> float:
    """growth_delta's role-skill factors before the noise: r x a(age) x headroom x
    professionalism / 10 (evaluated left to right, as growth_delta always has)."""
    headroom = max(0.0, pa - ca) / pa
    factor = band_value(growth.age_factor, age)
    return growth.rate * factor * headroom * professionalism / PROFESSIONALISM_DIVISOR


# --- Practice familiarity (spec 5.1, 5.3; ADR PT-0006 section 2) ------------------------------


def fam_factor(familiarity: float, fam: FamiliarityBalance) -> float:
    """Effective-skill multiplier: 0.70 + 0.30 x min(1, (f - 1) / 14) by default."""
    span = fam.full_at - ATTR_MIN
    progress = min(1.0, max(0.0, (familiarity - ATTR_MIN) / span))
    return fam.factor_at_one + (1 - fam.factor_at_one) * progress


def familiarity_after(
    current: float, peak: float, hours_tenths: int, fam: FamiliarityBalance
) -> float:
    """One month's familiarity in one practice (spec 5.3).

    With hours: + per_100h per 100 hours, the gain shrinking linearly from taper_from to
    nothing at 20. Without: - decay_per_month, never below max(1, peak - floor_below_peak)
    (nor below the current value if it is already under that floor)."""
    if hours_tenths > 0:
        gain = fam.per_100h * hours_tenths / (HOURS_PER_HUNDRED * 10)
        value = current
        if value < fam.taper_from:  # full rate up to the taper, then the tapered rate
            room = fam.taper_from - value
            full_rate = min(gain, room)
            value += full_rate
            gain -= full_rate
        if gain > 0:
            remaining = max(0.0, (ATTR_MAX - value) / (ATTR_MAX - fam.taper_from))
            value += gain * remaining
        return min(value, ATTR_MAX)
    floor = min(current, max(ATTR_MIN, peak - fam.floor_below_peak))
    return max(current - fam.decay_per_month, floor)


# --- Strain (spec 5.6; ADR PT-0006 section 3) -------------------------------------------------


def strain_comfort(stamina: float, strain: StrainBalance) -> float:
    """comfort = 1.0 + 0.01 x (stamina - 10)."""
    return strain.comfort_base + strain.comfort_per_stamina * (stamina - strain.stamina_neutral)


def strain_load_multiplier(burnout_risk: float, strain: StrainBalance, *, grinder: bool) -> float:
    """0.5 + burnout_risk / 20, times the grinder tag's 0.7."""
    base = strain.risk_base + burnout_risk / strain.risk_divisor
    return base * (strain.grinder_load if grinder else 1.0)


def strain_delta(
    *,
    hours_tenths: int,
    capacity_tenths: float,
    stamina: float,
    burnout_risk: float,
    grinder: bool,
    rest: str,
    strain: StrainBalance,
) -> float:
    """One month's change in strain (spec 5.6), before clamping to 0-100.

    Over comfort: + load x (hours / capacity - comfort) x load multiplier. At or under:
    - recover. A holiday or sabbatical month replaces the recovery with its own (larger)
    amount; work above comfort in that month still adds its load."""
    ratio = hours_tenths / capacity_tenths if capacity_tenths > 0 else 0.0
    over = ratio - strain_comfort(stamina, strain)
    gained = (
        strain.load * over * strain_load_multiplier(burnout_risk, strain, grinder=grinder)
        if over > 0
        else 0.0
    )
    if rest == "holiday":
        return gained - strain.holiday
    if rest == "sabbatical":
        return gained - strain.sabbatical
    return gained if over > 0 else -strain.recover


def clamp_strain(value: float) -> float:
    return min(max(value, STRAIN_MIN), STRAIN_MAX)


# --- Section 4: revealed ranges -------------------------------------------------------------


def scout_factor(judgment_of_talent: float, reveal: RevealBalance) -> float:
    return reveal.scout_base + judgment_of_talent / reveal.scout_divisor


def pa_scout_factor(judgment_of_talent: float, reveal: RevealBalance) -> float:
    """clamp(judgment_of_talent / 16, 0.1, 1.0): potential narrows more steeply with
    judgment than skills do (formulas.md section 4, M2b)."""
    raw = judgment_of_talent / reveal.pa_scout_divisor
    return min(max(raw, reveal.pa_scout_clamp.lo), reveal.pa_scout_clamp.hi)


def narrow_pa(
    hw: float, strength: float, judgment_of_talent: float, reveal: RevealBalance
) -> float:
    """PA's hw x (1 - pa_strength x pa_scout_factor), never below 0 or above the old hw."""
    shrink = strength * pa_scout_factor(judgment_of_talent, reveal)
    return hw * min(max(1 - shrink, 0.0), 1.0)


def narrow(hw: float, strength: float, judgment_of_talent: float, reveal: RevealBalance) -> float:
    """hw x (1 - strength x scout_factor), never below 0 and never above the old hw."""
    shrink = strength * scout_factor(judgment_of_talent, reveal)
    return hw * min(max(1 - shrink, 0.0), 1.0)


def displayed_range(
    true_value: float, hw: float, offset: float, lo: float, hi: float
) -> tuple[int, int]:
    """(min, max) shown to an observer; `lo`/`hi` are the attribute's scale bounds."""
    if hw < EXACT_HALF_WIDTH:
        exact = round(true_value)
        return exact, exact
    low = math.floor(min(max(true_value - hw * (1 + offset), lo), hi))
    high = math.ceil(min(max(true_value + hw * (1 - offset), lo), hi))
    return low, high


PA_PHRASES: Final = ("limited", "decent", "good", "excellent", "outstanding")


def potential_phrase(lo: float, hi: float, bounds: tuple[float, ...]) -> str:
    """Phrase for each PA bucket the displayed range touches, joined with "to" (section 4).

    `bounds` are the lower edges of every bucket after the first (balance pa_phrase_bounds).
    """
    if len(bounds) != len(PA_PHRASES) - 1:
        raise ValueError("pa_phrase_bounds must have one fewer entry than the phrases")

    def bucket(value: float) -> int:
        return sum(1 for b in bounds if value >= b)

    first, last = bucket(lo), bucket(hi)
    if first == last:
        return PA_PHRASES[first]
    return f"{PA_PHRASES[first]} to {PA_PHRASES[last]}"
