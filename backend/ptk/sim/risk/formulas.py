"""Pure risk formulas (PT-M15; docs/formulas.md's PT-M15 section is ADR PT-0017 2-6)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Final

from ptk.sim.risk.config import FloatSpan, Span

BP: Final = 10_000  # tunable-exempt: basis points
NEUTRAL: Final = 10.0  # tunable-exempt: a neutral 1-20 attribute


@dataclass(frozen=True, slots=True)
class Split:
    """One payment on a claim, split by the policy (spec 11.3): the firm pays within the
    deductible, the insurer up to the limit, the firm again above it (the excess). Defence
    costs erode both (defence within limits)."""

    deductible: int
    insurer: int
    excess: int

    @property
    def firm(self) -> int:
        return self.deductible + self.excess

    @property
    def total(self) -> int:
        return self.deductible + self.insurer + self.excess


def split_payment(amount: int, deductible_left: int, limit_left: int) -> Split:
    """`amount` >= 0 against what is left of the deductible and the limit."""
    amount = max(0, amount)
    ded = min(amount, max(0, deductible_left))
    ins = min(amount - ded, max(0, limit_left))
    return Split(ded, ins, amount - ded - ins)


def span(gen_u: float, s: Span) -> int:
    """An integer uniform on [lo, hi] from one uniform."""
    return s.lo + min(s.hi - s.lo, int(gen_u * (s.hi - s.lo + 1)))


def uniform(u: float, s: FloatSpan) -> float:
    return s.lo + (s.hi - s.lo) * u


def log_uniform(u: float, s: FloatSpan) -> float:
    lo, hi = max(s.lo, 1e-9), max(s.hi, 1e-9)
    return math.exp(math.log(lo) + (math.log(hi) - math.log(lo)) * u)


def integrity_mult(integrity: float, slope: float) -> float:
    """exp(slope x (10 - integrity) / 10): 1 at integrity 10, higher below it."""
    return math.exp(slope * (NEUTRAL - integrity) / NEUTRAL)


def gc_mult(effect: float, weight_bp: int) -> float:
    """A chance x (1 - weight x e) for the GC's seat effect e in [-0.5, 1]: a vacant seat
    (e = -0.5) raises it, a strong GC lowers it."""
    return max(0.0, 1.0 - weight_bp / BP * effect)


def experience_mod(
    claims: int,
    lawyer_years: float,
    expected_per_100: float,
    losses_cents: int,
    premiums_cents: int,
    count_weight: float,
    loss_weight: float,
    loss_target: float,
    lo: float,
    hi: float,
) -> float:
    """A renewal's experience modifier (spec 11.3): the claims notified per 100 lawyer-years
    against what the market expects, and the losses incurred against the premiums paid, over
    the history the renewal reads. A firm with no history is rated at 1."""
    mod = 1.0
    if lawyer_years > 0:
        freq = 100.0 * claims / lawyer_years
        mod += count_weight * (freq / expected_per_100 - 1.0)
    if premiums_cents > 0:
        mod += loss_weight * (losses_cents / premiums_cents - loss_target)
    return min(hi, max(lo, mod))


def premium_cents(
    exposure_cents: int,
    rate_bp: int,
    mix: float,
    mod: float,
    insurer_factor: float,
    limit_factor: float,
    deductible_factor: float,
    min_premium_cents: int,
) -> int:
    """A year's premium: the fees it covers x the market's rate x the practice mix x the
    firm's experience x the insurer's and the terms' factors, at least the insurer's minimum."""
    raw = exposure_cents * rate_bp / BP * mix * mod * insurer_factor * limit_factor
    return max(min_premium_cents, round(raw * deductible_factor))


def merit_range(merit: float, width: float, u: float) -> tuple[float, float]:
    """The merit as the firm reads it: a band 2 x width wide holding the true value at a drawn
    place `u` (so the band's middle is not the truth), clipped to 0-1."""
    lo = merit - 2.0 * width * u
    hi = lo + 2.0 * width
    return round(max(0.0, lo), 2), round(min(1.0, hi), 2)
