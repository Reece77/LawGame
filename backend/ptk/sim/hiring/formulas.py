"""Pure formulas for hiring, payroll, morale and resignations (TST formulas.md 6-10, spec 5.3).

Ported from backend/tst/sim/hiring/formulas.py @ 02fba2aa (Tech Startup Tycoon); changed:
no equity or stage terms in the offer score (a partnership grants no options), replaced by
the firm's prestige term (0 until PT-M5 and PT-M16); the fit term counts interests the
candidate's practice favours; the recruiter fee is 20% or 25% by seniority; morale's runway
term is gone (PT-M4's insolvency) and Partner Track's hours, interesting-work, prospects and
bonus-fairness terms are added (spec 5.3); resignation gains the lifer floor, burnout,
bonus timing and lateral market heat; no retirement (a follow-up).

No randomness: callers draw from their own stream (ADR-0013) and pass the result in.
"""

from __future__ import annotations

from typing import Literal

from simcore.kernel import dmath
from simcore.kernel.calendar import MONTHS_PER_YEAR
from simcore.kernel.money import BP_DENOMINATOR, Cents, pct_of, round_half_even
from simcore.kernel.scale import ATTR_MAX, ATTR_NEUTRAL, clamp_morale

from ptk.sim.data_models import (
    LEVELS,
    Balance,
    HiringBalance,
    MoraleBalance,
    OfferBalance,
    PayBalance,
    ResignBalance,
)

type HintBand = Literal["likely", "uncertain", "unlikely"]

# --- Section 6: energy ----------------------------------------------------------------------


def energy_cost(action: str, balance: Balance) -> int:
    return balance.energy.cost[action]


# --- Section 7: offers ----------------------------------------------------------------------


def offer_score(
    *,
    ratio: float,
    matching_interests: int,
    risk_appetite: float,
    offer: OfferBalance,
    prestige: float = 0.0,
    pitch: float = 0.0,
) -> float:
    """w_salary (R - 1) + w_fit F + prestige - w_risk (10 - risk_appetite) / 10 + pitch."""
    return (
        offer.w_salary * (ratio - 1)
        + offer.w_fit * matching_interests
        + prestige
        - offer.w_risk * (ATTR_NEUTRAL - risk_appetite) / ATTR_NEUTRAL
        + pitch
    )


def acceptance_probability(score: float, offer: OfferBalance) -> float:
    """p = 1 / (1 + exp(-k (score - threshold)))."""
    return 1 / (1 + dmath.exp(-offer.k * (score - offer.threshold)))


def pitch(recruiting: float, hiring: HiringBalance) -> float:
    """The offer maker's pitch: pitch_per_recruiting x (recruiting - 10) (TST 7, M2)."""
    return hiring.pitch_per_recruiting * (recruiting - ATTR_NEUTRAL)


def is_lowball(ratio: float, hiring: HiringBalance) -> bool:
    """Offers below lowball_ratio of the ask are always declined."""
    return ratio < hiring.lowball_ratio


def hint_band(score: float, hiring: HiringBalance) -> HintBand:
    if score >= hiring.hint_bands.hi:
        return "likely"
    if score < hiring.hint_bands.lo:
        return "unlikely"
    return "uncertain"


def recruiter_fee_cents(annual_salary_cents: Cents, level: str, hiring: HiringBalance) -> Cents:
    """20% of first-year salary, 25% from `recruiter_senior_from` up (spec 5.7)."""
    senior = LEVELS.index(level) >= LEVELS.index(hiring.recruiter_senior_from)
    fee = hiring.recruiter_fee_bp.senior if senior else hiring.recruiter_fee_bp.junior
    return pct_of(annual_salary_cents, fee)


# --- Section 8: payroll ---------------------------------------------------------------------


def monthly_salary_cents(annual_salary_cents: Cents) -> Cents:
    """round(salary / 12), half to even, exact integer arithmetic."""
    return round_half_even(annual_salary_cents, MONTHS_PER_YEAR)


def benefits_cents(monthly_salary: Cents, pay: PayBalance) -> Cents:
    return pct_of(monthly_salary, pay.benefits_bp)


def rent_cents(heads: int, city: str, pay: PayBalance) -> Cents:
    """Rent a month for `heads` people on the books in a city (spec 8.3)."""
    return heads * pct_of(pay.rent_per_head_cents, pay.city(city))


# --- Section 9: morale ----------------------------------------------------------------------


def pay_term(salary_cents: Cents, market_cents: Cents, morale: MoraleBalance) -> float:
    """clamp(60 x (salary / market - 1), -20, +15); the market is the class-year scale for
    associates, the band for others (spec 5.3). No market (equity partners): 0."""
    if market_cents <= 0:
        return 0.0
    # money-exact: ratio
    raw = morale.pay_slope * (salary_cents / market_cents - 1)
    return min(max(raw, morale.pay_min), morale.pay_max)


def interest_term(matches: int, morale: MoraleBalance) -> float:
    """Interesting work: points per interest the person's practice favours (named-matter
    exposure joins with PT-M3a)."""
    return morale.interest_per_match * matches


def hours_term(hours_ratio: float | None, morale: MoraleBalance) -> float:
    """W_hours = -10 x max(0, h/target - 1.1), and -5 below 0.6 (spec 5.3). None (no hours
    recorded for the month, as before PT-M3a staffs matters): 0."""
    if hours_ratio is None:
        return 0.0
    if hours_ratio < morale.hours_idle_below:
        return morale.hours_idle
    return morale.hours_over_slope * max(0.0, hours_ratio - morale.hours_over_from)


def prospects_term(level: str, has_sponsor: bool, morale: MoraleBalance) -> float:
    """Partnership prospects for years 6-8 (spec 5.3): a sponsor raises them (PT-M4)."""
    if level not in morale.prospects_levels:
        return 0.0
    return morale.prospects_sponsor if has_sponsor else morale.prospects_no_sponsor


def bonus_fairness_shock(bonus_cents: Cents, market_cents: Cents, morale: MoraleBalance) -> float:
    """December: clamp(bonus_slope x (bonus / market bonus - 1), min, max); none without a
    market bonus."""
    if market_cents <= 0:
        return 0.0
    # money-exact: ratio
    raw = morale.bonus_slope * (bonus_cents / market_cents - 1)
    return min(max(raw, morale.bonus_min), morale.bonus_max)


def morale_target(terms: float, morale: MoraleBalance) -> float:
    return morale.target_base + terms


def morale_noise_sd(temperament: float, morale: MoraleBalance) -> float:
    """noise_scale x (21 - temperament) / 20."""
    return morale.noise_scale * (ATTR_MAX + 1 - temperament) / ATTR_MAX


def morale_step(current: float, target: float, noise: float, morale: MoraleBalance) -> float:
    """morale + rate (target - morale) + noise, clamped to [0, 100]."""
    return clamp_morale(current + morale.rate * (target - current) + noise)


# --- Section 10: resignation ----------------------------------------------------------------


def resignation_bp(
    morale: float,
    loyalty: float,
    resign: ResignBalance,
    *,
    job_hopper: bool = False,
    lifer: bool = False,
    burnout: bool = False,
    month_mult: float = 1.0,
    heat: float = 1.0,
) -> float:
    """base x (1 + max(0, floor - morale) / 20) x (21 - loyalty) / 10 x (2 if job hopper)
    x (2 within a burnout's effect) x bonus timing x lateral market heat x the
    macro's lateral heat (`heat`, PT-M7), capped. A lifer's loyalty counts as at least
    lifer_loyalty_floor."""
    if lifer:
        loyalty = max(loyalty, resign.lifer_loyalty_floor)
    chance = (
        resign.base_bp
        * (1 + max(0.0, resign.morale_floor - morale) / resign.morale_divisor)
        * (ATTR_MAX + 1 - loyalty)
        / resign.loyalty_divisor
        * (resign.job_hopper_mult if job_hopper else 1)
        * (resign.burnout_mult if burnout else 1)
        * month_mult
        * resign.lateral_market_heat
        * heat
    )
    return min(chance, resign.cap_bp)


def roll_succeeds(roll: int, chance_bp: float) -> bool:
    """A roll in [0, 10000) succeeds when it is below the chance (formulas.md section 0)."""
    return roll < chance_bp


ROLL_RANGE = BP_DENOMINATOR  # rolls are integers in [0, ROLL_RANGE)
