"""Rival formulas (spec 10.2, 8.7; TST formulas.md 15): needs, utility, labels, poach odds.

Ported from backend/tst/sim/rivals/formulas.py @ 121d3180 (Tech Startup Tycoon); changed:
law firms' needs (rates against the history path or utilisation, headcount against the
path or demand, margin and PEP) replace TST's product needs; `utility`, `poach_score`,
`poach_probability` and `poach_band` keep TST's formulas; the money label reads a firm's
margin and PEP trend instead of months of cash. Pure functions of numbers.
"""

from __future__ import annotations

from ptk.sim import dmath
from ptk.sim.rivals.data import PoachBalance


def clamp01(value: float) -> float:
    return min(max(value, 0.0), 1.0)


def utility(need: float, weight: float, noise: float) -> float:
    """U(a) = need(a) x w_personality(a) + N(0, 0.1) (spec 10.2)."""
    return need * weight + noise


def need_gap(gap: float, span: float) -> float:
    """A relative shortfall turned into a 0-1 need: gap / span."""
    return clamp01(gap / span)


# --- Poaching (TST 15.6; spec 8.7) ------------------------------------------------------------


def poach_score(ratio: float, morale: float, loyalty: float, pb: PoachBalance) -> float:
    """s = 4 (R - 1) + (55 - morale) / 20 - (loyalty - 10) / 10 + leave_penalty: the
    person's side of leaving their firm for a rival's offer (TST's unvested-options term has
    no law-firm equivalent and is dropped)."""
    return (
        pb.salary_weight * (ratio - 1)
        + (pb.morale_mid - morale) / pb.morale_divisor
        - (loyalty - pb.loyalty_mid) / pb.loyalty_divisor
        + pb.leave_penalty
    )


def poach_probability(score: float, pb: PoachBalance) -> float:
    """p = 1 / (1 + e^(-2 s))."""
    return 1 / (1 + dmath.exp(-pb.steepness * score))


def poach_band(probability: float, pb: PoachBalance) -> str:
    """likely to stay (below 20%), might go (20-50%), likely to go (above 50%)."""
    if probability < pb.bands.lo:
        return "likely to stay"
    if probability <= pb.bands.hi:
        return "might go"
    return "likely to go"


# --- Labels (TST 15.5) --------------------------------------------------------------------


def money_label(margin: float, pep_change: float | None) -> str:
    """strong (margin 35%+ and PEP not falling), steady, strained (margin under 20% or PEP
    down a tenth): what the legal press would say of a firm's finances."""
    falling = pep_change is not None and pep_change < -0.1  # tunable-exempt: label band
    if margin < 0.2 or falling:  # tunable-exempt: label band
        return "strained"
    if margin >= 0.35 and (pep_change is None or pep_change >= 0):  # tunable-exempt
        return "strong"
    return "steady"


def stance_label(stance: float) -> str:
    """A rival's stance toward the player's firm (TST 15.5): from its recent losses to it."""
    if stance >= 2:  # tunable-exempt: label band (key partners lost to the player, decaying)
        return "hostile"
    if stance > 0.5:  # tunable-exempt: label band
        return "wary"
    return "neutral"


def rounded_headcount(n: float) -> int:
    """Shown headcount: to the nearest 10 above 100 (TST 15.5)."""
    value = round(n)
    if value > 100:  # tunable-exempt: TST's display rule
        return int(round(value / 10) * 10)
    return int(value)
