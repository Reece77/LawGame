"""Pure formulas for clients and matters (spec 6-7; docs/formulas.md PT-M3a section).

Every transcendental goes through `simcore.kernel.dmath`, so results are the same on every platform.
"""

from __future__ import annotations

from collections.abc import Mapping
from functools import lru_cache
from typing import Final

from simcore.kernel import dmath

from ptk.sim.data_models import (
    BAND_TASK_LEVEL,
    Balance,
    GameData,
    KindDef,
    OutcomesBalance,
    PracticeDef,
)
from ptk.sim.people.formulas import fam_factor
from ptk.sim.people.models import Person

TENTHS: Final = 10  # tunable-exempt: hours are integer tenths (ADR PT-0005)
POISSON_CAP: Final = 60  # tunable-exempt: a month never brings more matters of one kind
_BISECT_STEPS: Final = 80  # tunable-exempt: bisection to a double's precision
LEVEL_BANDS: Final = ("paralegal", "junior", "mid", "senior", "partner")  # task level -> band


def sigmoid(x: float) -> float:
    if x >= 0:
        return 1.0 / (1.0 + dmath.exp(-x))
    e = dmath.exp(x)
    return e / (1.0 + e)


@lru_cache(maxsize=4096)
def normal_cdf(z: float) -> float:
    """P(Z <= z) for a standard normal, by bisection on dmath's inverse (platform-exact)."""
    if z <= -8.0:  # tunable-exempt: the tail is below a double's resolution of interest
        return 0.0
    if z >= 8.0:  # tunable-exempt
        return 1.0
    lo, hi = 1e-300, 1.0 - 1e-16
    for _ in range(_BISECT_STEPS):
        mid = (lo + hi) / 2
        if dmath.normal_inv_cdf(mid) < z:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def poisson_from_uniform(lam: float, u: float) -> int:
    """The Poisson(lam) count at quantile u, by inversion (one uniform per draw)."""
    if lam <= 0:
        return 0
    p = dmath.exp(-lam)
    cdf, k = p, 0
    while u > cdf and k < POISSON_CAP:
        k += 1
        p *= lam / k
        cdf += p
    return k


def lognormal_mu(median: float) -> float:
    return dmath.log(median)


def lognormal_mean(median: float, sigma: float) -> float:
    return median * dmath.exp(sigma * sigma / 2)


def tail_split(median: float, sigma: float, threshold: float) -> tuple[float, float, float]:
    """For LogNormal(ln median, sigma): (P(X >= t), share of the mean from X >= t, Φ(z_t))."""
    z = (dmath.log(threshold) - dmath.log(median)) / sigma
    cdf = normal_cdf(z)
    return 1.0 - cdf, 1.0 - normal_cdf(z - sigma), cdf


# --- Rates and levels ------------------------------------------------------------------------


def rate_band(level: str, data: GameData) -> str | None:
    return data.market.rate_bands.get(level)


def task_level(level: str, data: GameData) -> int | None:
    band = rate_band(level, data)
    return None if band is None else BAND_TASK_LEVEL[band]


def rate_cents(practice: PracticeDef, level: str, data: GameData) -> int:
    band = rate_band(level, data)
    return 0 if band is None else practice.rates[band]


def level_shares(tasks: Mapping[str, float], data: GameData) -> tuple[float, ...]:
    """Share of a task mix's hours at each task level 0-4."""
    out = [0.0] * len(LEVEL_BANDS)
    total = sum(tasks.values())
    for key, w in tasks.items():
        out[data.market.task(key).level] += w / total
    return tuple(out)


def kind_tasks(kind: KindDef) -> dict[str, float]:
    """A kind's whole task mix: phase shares times phase task weights."""
    mix: dict[str, float] = {}
    for phase in kind.phases:
        total = sum(phase.tasks.values())
        for key, w in phase.tasks.items():
            mix[key] = mix.get(key, 0.0) + phase.share * w / total
    return mix


def blended_rate(practice: PracticeDef, tasks: Mapping[str, float], data: GameData) -> float:
    """Cents an hour of a task mix staffed at its natural levels."""
    shares = level_shares(tasks, data)
    return sum(s * practice.rates[LEVEL_BANDS[lv]] for lv, s in enumerate(shares))


def person_tasks(tasks: Mapping[str, float], level: int, data: GameData) -> dict[str, float]:
    """The part of a task mix a person at task level `level` does: tasks within one level of
    their own, else the nearest tasks (normalised weights)."""
    by_gap: dict[int, dict[str, float]] = {}
    for key, w in tasks.items():
        gap = abs(data.market.task(key).level - level)
        by_gap.setdefault(gap, {})[key] = w
    near = {k: w for gap, part in by_gap.items() if gap <= 1 for k, w in part.items()}
    if not near:
        near = by_gap[min(by_gap)]
    total = sum(near.values())
    return {k: w / total for k, w in near.items()}


def substantive_share(tasks: Mapping[str, float], level: int, data: GameData, window: int) -> float:
    """Share of the person's hours on tasks at or up to `window` levels above their own
    (learn(h), ADR PT-0006 section 4)."""
    mine = person_tasks(tasks, level, data)
    return sum(w for k, w in mine.items() if level <= data.market.task(k).level <= level + window)


def skill_mix(person: Person, weights: Mapping[str, float]) -> float:
    total = sum(weights.values())
    return sum(person.skills[k] * w for k, w in weights.items()) / total


def task_skill(person: Person, tasks: Mapping[str, float], data: GameData) -> float:
    """Raw skill 1-20 on a (normalised) task mix."""
    return sum(w * skill_mix(person, data.market.task(k).skills) for k, w in tasks.items())


def effective_skill(
    person: Person, tasks: Mapping[str, float], practice: str, data: GameData, balance: Balance
) -> float:
    """Skill on the tasks the person does, times familiarity's factor (spec 5.1)."""
    level = task_level(person.level, data)
    mine = person_tasks(tasks, 0 if level is None else level, data)
    return task_skill(person, mine, data) * fam_factor(
        person.familiarity[practice], balance.familiarity
    )


def craft(person: Person, weights: Mapping[str, float], practice: str, balance: Balance) -> float:
    """Case or deal craft 1-20 (spec 7.6), with familiarity."""
    return skill_mix(person, weights) * fam_factor(
        person.familiarity[practice], balance.familiarity
    )


def strain_output(strain: float, balance: Balance) -> float:
    cfg = balance.progress
    over = max(0.0, strain - cfg.strain_from) / (100.0 - cfg.strain_from)
    return 1.0 - cfg.strain_output * over


# --- Outcomes (spec 7.6) -----------------------------------------------------------------------


def case_quality(
    craft_mean: float, prep: float, big_moments: float, outcomes: OutcomesBalance
) -> float:
    """Q_us: the team's hours-weighted craft, the lead's big moments at trial and preparation
    (progress delivered by the trial; below 1 when the team fell behind)."""
    bm = outcomes.big_moments * (big_moments - 10.0) / 10.0
    return craft_mean + bm - outcomes.prep * max(0.0, 1.0 - prep)


def p_win(q_us: float, q_them: float, merits: float, outcomes: OutcomesBalance) -> float:
    """p_win = sigmoid(k (Q_us - Q_them) + m) (spec 7.6). No judge term: a judge never favours a
    side (spec 7.6a, ADR PT-0013)."""
    return sigmoid(outcomes.case_k * (q_us - q_them) + merits)


def p_close(q_deal: float, critical: bool, outcomes: OutcomesBalance, crisis: float = 0.0) -> float:
    """`crisis` (PT-M7b): logit points off for the deal's driver index below 1."""
    crit = outcomes.critical_deal if critical else 0.0
    return sigmoid(outcomes.deal_base + outcomes.deal_k * (q_deal - 10.0) + crit - crisis)


def error_chance(
    team_skill: float,
    strain_mult: float,
    cowboy: bool,
    shortfall: float,
    balance: Balance,
) -> float:
    """p_error = base x (2 - skill/10) x strain x cowboy x supervision shortfall (spec 7.6)."""
    cfg = balance.errors
    p = (
        cfg.base_bp
        / 10000
        * max(0.1, 2.0 - team_skill / 10.0)
        * strain_mult
        * (cfg.cowboy_mult if cowboy else 1.0)
        * (1.0 + shortfall)
    )
    return min(p, cfg.max_bp / 10000)


def person_error_strain(strain: float, burnout_effects: bool, balance: Balance) -> float:
    cfg = balance.errors
    return (1.0 + cfg.strain_slope * strain / 100.0) * (
        cfg.burnout_mult if burnout_effects else 1.0
    )
