"""Billing formulas (spec 7.7; ADR PT-0005): discounts, fees by model, days to pay, chances.

Money is integer cents throughout: a share of an amount is computed exactly and rounded half
to even once (`ptk.sim.money`).
"""

from __future__ import annotations

import math
from statistics import NormalDist
from typing import Final

import numpy as np

from ptk.sim.billing.models import Engagement
from ptk.sim.data_models import BillingBalance
from ptk.sim.interfaces import ClientBillingView
from ptk.sim.money import BP_DENOMINATOR, pct_of, round_half_even, times
from ptk.sim.rng import RngFactory

NEUTRAL: Final = 10.0  # tunable-exempt: the 1-20 scale's neutral point
TENTHS: Final = 10  # tunable-exempt: tenths in an hour (ADR PT-0005)
_NORMAL: Final = NormalDist()

# Purposes of the `billing` stream's first key (ADR PT-0012): one call site, keyed by
# (purpose, entity id) so each draw belongs to one entity (ADR-0013).
TERMS: Final = 0  # (TERMS, matter_id): a matter's billing terms, in its first month
BILL: Final = 1  # (BILL, bill_id): guideline rejection, padding dispute, days to pay, short pay
CLIENT: Final = 2  # (CLIENT, client_id): a client's month (bankruptcy)
DISPUTE: Final = 3  # (DISPUTE, bill_id): the default rule's answer to a dispute
DRAWS: Final = 8  # tunable-exempt: uniforms per billing draw, drawn whether used or not


def billing_draws(rng: RngFactory, turn: int, purpose: int, key: int) -> list[float]:
    """The stream's only call site: DRAWS uniforms for one (purpose, entity)."""
    gen: np.random.Generator = rng.stream(turn, "billing", purpose, key)
    return [float(x) for x in gen.random(DRAWS)]


def bp_chance(base_bp: float, per_point_bp: float, price_sensitivity: float) -> float:
    """A chance (0-1) that rises per price-sensitivity point above 10."""
    bp = base_bp + per_point_bp * (price_sensitivity - NEUTRAL)
    return min(1.0, max(0.0, bp / BP_DENOMINATOR))


def client_discount_bp(client: ClientBillingView, cfg: BillingBalance) -> int:
    bp = cfg.discount_base_bp + cfg.discount_per_point_bp * (client.price_sensitivity - NEUTRAL)
    return int(min(cfg.discount_max_bp, max(0, round(bp))))


def uniform(lo: float, hi: float, u: float) -> float:
    return lo + (hi - lo) * u


def after_discount(cents: int, discount_bp: int) -> int:
    return pct_of(cents, BP_DENOMINATOR - discount_bp)


def hourly_fee(e: Engagement, wip: int, tenths: int) -> int:
    """The fee for unbilled work before write-downs, by the engagement's model."""
    if e.model == "blended":
        return round_half_even(
            tenths * e.rate_cents * (BP_DENOMINATOR - e.discount_bp), 10 * BP_DENOMINATOR
        )
    fee = after_discount(wip, e.discount_bp)
    if e.model == "success":
        return pct_of(fee, e.share_bp)
    if e.model == "capped":
        return min(fee, max(0, e.price_cents - e.billed_cents))
    return fee


def fixed_due(e: Engagement, share: float) -> int:
    """A fixed fee's amount earned at a completed share, less what is billed."""
    return max(0, times(e.price_cents, min(1.0, max(0.0, share))) - e.billed_cents)


def overrun_writedown(
    e: Engagement, expected_cents: int, wip: int, fee: int, cfg: BillingBalance
) -> int:
    """The default rule (spec 7.7): the share of this bill's work above the budget's
    tolerance is written down at `overrun_writedown`, at the bill's own rate."""
    if wip <= 0 or fee <= 0:
        return 0
    threshold = times(expected_cents, 1.0 + cfg.overrun_tolerance)
    over = min(wip, max(0, e.standard_cents - threshold))
    if over <= 0:
        return 0
    return min(fee, round_half_even(times(over, cfg.overrun_writedown) * fee, wip))


def days_to_pay(client: ClientBillingView, u: float, cfg: BillingBalance) -> float:
    base = cfg.days_to_pay[client.size_class] + cfg.days_per_point * (
        client.price_sensitivity - NEUTRAL
    )
    z = _NORMAL.inv_cdf(min(1.0 - 1e-9, max(1e-9, u)))  # tunable-exempt: open interval
    return max(1.0, base) * cfg.macro_stress * math.exp(cfg.days_sigma * z)


def due_turn(turn: int, days: float, cfg: BillingBalance) -> int:
    return turn + max(1, round(days / cfg.days_per_month))


def dispute_chance(client: ClientBillingView, padded: bool, cfg: BillingBalance) -> float:
    rel = 1.0 + cfg.dispute_temperament * (NEUTRAL - client.gc_temperament)
    p = cfg.dispute_bp / BP_DENOMINATOR * max(0.0, rel)
    return min(1.0, p * (cfg.dispute_padding_mult if padded else 1.0))


def hold_chance(relationship: float, cfg: BillingBalance) -> float:
    x = cfg.hold_base + cfg.hold_relationship * (relationship - 50.0) / 50.0
    return 1.0 / (1.0 + math.exp(-x))


def provision_bp(age_months: int, cfg: BillingBalance) -> int:
    bp = cfg.provision_bp[0].value
    for step in cfg.provision_bp:
        if age_months >= step.from_months:
            bp = step.value
    return bp


def expected_value(e: Engagement, share: float, cfg: BillingBalance) -> int:
    """What the engagement's unbilled WIP is expected to bill (the WIP provision's base),
    clipped to 0..WIP: prudence never books a write-up before it is billed."""
    wip = e.wip_cents
    if wip <= 0:
        return 0
    if e.model == "fixed":
        ev = fixed_due(e, share)
    elif e.model == "contingency":
        ev = pct_of(wip, cfg.contingency_ev_bp)
    elif e.model == "retainer":
        ev = wip
    else:
        ev = hourly_fee(e, wip, e.wip_tenths)
    return min(wip, max(0, ev))
