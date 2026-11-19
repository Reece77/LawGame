"""The associate salary scale, pay bands and bonuses (spec 5.4; PT-M1b, no TST counterpart).

Associates (class years 1-8, senior associates as class 8) are paid on the market scale of
`salary_scale.yaml` for the month, times the firm's pay policy. Counsel, income partners,
paralegals and business services are paid from a band, times the city's multiplier. Equity
partners take a share of profit (PT-M4) and have no salary. Pure; money in integer cents.
"""

from __future__ import annotations

from typing import Final

from ptk.sim.calendar import YearMonth
from ptk.sim.data_models import SCALE_LEVELS, Balance, GameData
from ptk.sim.hiring.models import PayPolicy
from ptk.sim.money import Cents, pct_of, round_half_even

EQUITY_PARTNER: Final = "equity_partner"
SENIOR_CLASS_INDEX: Final = 7  # tunable-exempt: senior associates are paid as class 8


def class_index(level: str) -> int | None:
    """0-7 for associates (class years 1-8; a senior associate is class 8), else None."""
    if level not in SCALE_LEVELS:
        return None
    return min(SCALE_LEVELS.index(level), SENIOR_CLASS_INDEX)


def on_scale(level: str) -> bool:
    return class_index(level) is not None


def market_scale_cents(data: GameData, ym: YearMonth, level: str) -> Cents:
    """The market's salary a year for an associate class year in month `ym`."""
    index = class_index(level)
    if index is None:
        raise ValueError(f"level {level!r} is not on the associate scale")
    return data.salary_scale.market_salaries(ym)[index]


def band_cents(data: GameData, balance: Balance, level: str, city: str) -> Cents:
    """An off-scale level's salary a year in a city (TST's role bands by city)."""
    return pct_of(data.salary_scale.bands[level], balance.pay.city(city))


def market_pay_cents(
    data: GameData, balance: Balance, level: str, ym: YearMonth, city: str
) -> Cents:
    """What the market pays this level a year: the scale for associates, a band for others,
    nothing for equity partners."""
    if level == EQUITY_PARTNER:
        return 0
    if on_scale(level):
        return market_scale_cents(data, ym, level)
    return band_cents(data, balance, level, city)


def policy_pay_cents(market_cents: Cents, policy: PayPolicy) -> Cents:
    """The market amount times the firm's policy (match, lag or lead)."""
    return pct_of(market_cents, policy.pct_bp)


def firm_scale_cents(data: GameData, ym: YearMonth, level: str, policy: PayPolicy) -> Cents:
    return policy_pay_cents(market_scale_cents(data, ym, level), policy)


def firm_pay_cents(
    data: GameData, balance: Balance, level: str, ym: YearMonth, city: str, policy: PayPolicy
) -> Cents:
    """The salary a new hire or a scale step gets at this firm: associates on the firm's scale
    (policy applies); off-scale levels at the market band (policy applies only to the scale)."""
    market = market_pay_cents(data, balance, level, ym, city)
    return policy_pay_cents(market, policy) if on_scale(level) else market


def market_bonus_cents(
    data: GameData, balance: Balance, level: str, year: int, salary_cents: Cents
) -> Cents:
    """The market's year-end bonus for a full year: by class year for associates; the
    level's discretionary share of salary for others; none for equity partners."""
    if level == EQUITY_PARTNER:
        return 0
    index = class_index(level)
    if index is not None:
        return data.salary_scale.market_bonuses(year)[index]
    return pct_of(salary_cents, balance.pay.discretionary_bonus_bp.get(level, 0))


def prorated(amount: Cents, months: int, months_in_year: int) -> Cents:
    """amount x months / months_in_year, rounded half to even (a part-year's bonus)."""
    if months >= months_in_year:
        return amount
    return round_half_even(amount * max(months, 0), months_in_year)
