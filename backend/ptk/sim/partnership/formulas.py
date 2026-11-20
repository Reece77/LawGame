"""Pure partnership formulas (spec 5.5, 8.1-8.7; ADR PT-0003, PT-0007). Money in integer
cents; shares as floats only on the way to an exact split (`split_cents`).

Ported from backend/tst/sim/finance/formulas.py @ 02fba2aa (Tech Startup Tycoon), the
confidence rule only: `clamp_confidence` and `next_confidence` (B <- B + rate (T - B)) as is;
changed: the target's terms are ADR PT-0007 1's (a partner's PEP against expectation, the
firm's PEP trend, the MP's persona, money trouble, departures) instead of growth, runway and
patience; TST's confidence label becomes the whip count's label and ranges."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ptk.sim.data_models import (
    ConfidenceBalance,
    FlightBalance,
    LockstepBalance,
    PartnershipBalance,
    RevolverBalance,
)
from ptk.sim.money import BP_DENOMINATOR, pct_of, round_half_even

MONTHS_PER_YEAR = 12  # tunable-exempt: the calendar


# --- Exact splits ----------------------------------------------------------------------------


def split_cents(total: int, weights: Mapping[int, float]) -> dict[int, int]:
    """`total` split by weight, exactly (largest remainder; ties by key). Every key gets an
    amount; zero total weight splits evenly. Negative totals split the same way."""
    keys = sorted(weights)
    if not keys:
        return {}
    w = {k: max(0.0, weights[k]) for k in keys}
    s = sum(w.values())
    if s <= 0:
        w = dict.fromkeys(keys, 1.0)
        s = float(len(keys))
    sign = -1 if total < 0 else 1
    amount = abs(total)
    raw = {k: amount * w[k] / s for k in keys}
    out = {k: math.floor(raw[k]) for k in keys}
    left = amount - sum(out.values())
    order = sorted(keys, key=lambda k: (-(raw[k] - out[k]), k))
    for k in order[:left]:
        out[k] += 1
    return {k: sign * v for k, v in out.items()}


# --- Lockstep points (spec 8.5) --------------------------------------------------------------


def lockstep_points(years_as_partner: int, cfg: LockstepBalance) -> float:
    """10 at admission, +2.5 a year, a plateau of 25 at year 7."""
    return min(cfg.plateau_points, cfg.start_points + cfg.step_points * max(0, years_as_partner))


def next_points(points: float, steps: int, cfg: LockstepBalance) -> float:
    """A January step plus the comp round's gate steps, kept inside [start, plateau]."""
    return min(cfg.plateau_points, max(cfg.start_points, points + cfg.step_points * (1 + steps)))


# --- Comp: shares of the pool (spec 8.5) ----------------------------------------------------


@dataclass(frozen=True, slots=True)
class Credits:
    """A partner's year: origination, working and management credit (true values)."""

    origination_cents: int
    working_cents: int
    management: float


def _norm(values: Mapping[int, float]) -> dict[int, float]:
    total = sum(max(0.0, v) for v in values.values())
    if total <= 0:
        n = len(values)
        return {k: 1.0 / n for k in values} if n else {}
    return {k: max(0.0, v) / total for k, v in values.items()}


def contribution_shares(
    credits: Mapping[int, Credits], cfg: PartnershipBalance
) -> dict[int, float]:
    """Each partner's share by spec 8.5's credit formula, each credit normalised on its own:
    0.50 x origination share + 0.35 x working share + 0.15 x management share."""
    o = _norm({k: float(c.origination_cents) for k, c in credits.items()})
    w = _norm({k: float(c.working_cents) for k, c in credits.items()})
    m = _norm({k: c.management for k, c in credits.items()})
    e = cfg.ewyk
    total = e.origination + e.working + e.management
    return {
        k: (e.origination * o[k] + e.working * w[k] + e.management * m[k]) / total for k in credits
    }


def comp_weights(
    system: str,
    points: Mapping[int, float],
    credits: Mapping[int, Credits],
    adjust_bp: Mapping[int, int],
    cfg: PartnershipBalance,
) -> dict[int, float]:
    """Shares (summing to 1) of the pool left after guarantees, by comp system.

    - lockstep: by points
    - modified_lockstep: (1 - bonus pool) by points; the bonus pool by contribution, moved by
      the comp round's adjustments
    - eat_what_you_kill: by contribution shares
    - committee: 0.4 x origination share + 0.6 x contribution share, then the comp round's
      adjustments (each at most adjust_max_bp of the share)"""
    if not points:
        return {}
    contrib = contribution_shares(credits, cfg)
    if system == "lockstep":
        return _norm(dict(points))
    if system == "modified_lockstep":
        pool = cfg.modified.bonus_pool_bp / BP_DENOMINATOR
        base = _norm(dict(points))
        bonus = _norm({k: contrib[k] * (1 + adjust_bp.get(k, 0) / BP_DENOMINATOR) for k in points})
        return {k: (1 - pool) * base[k] + pool * bonus[k] for k in points}
    if system == "eat_what_you_kill":
        return contrib
    o = _norm({k: float(c.origination_cents) for k, c in credits.items()})
    wo = cfg.committee.origination
    cap = cfg.committee.adjust_max_bp
    raw = {
        k: (wo * o[k] + (1 - wo) * contrib[k])
        * (1 + max(-cap, min(cap, adjust_bp.get(k, 0))) / BP_DENOMINATOR)
        for k in points
    }
    return _norm(raw)


def satisfaction(
    comp_cents: int, contribution_cents: int, ego: float, market_cents: int, cfg: PartnershipBalance
) -> float:
    """Spec 8.5: comp against max(contribution x (1 + ego term), market value)."""
    s = cfg.satisfaction
    felt = contribution_cents * (1 + s.ego_weight * (ego - 10))
    expected = max(felt, float(market_cents), 1.0)
    return max(s.floor, min(s.ceiling, comp_cents / expected - 1))


# --- PEP and KPIs (spec 8.1-8.2) --------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PepIdentity:
    """PEP = RPL x margin x leverage (spec 8.1); RPL = hours x rate x realisation x collection."""

    revenue_cents: int
    profit_cents: int
    lawyers: float
    equity_partners: float

    @property
    def rpl_cents(self) -> int | None:
        return None if self.lawyers <= 0 else round(self.revenue_cents / self.lawyers)

    @property
    def margin_bp(self) -> int | None:
        if self.revenue_cents <= 0:
            return None
        return round_half_even(self.profit_cents * BP_DENOMINATOR, self.revenue_cents)

    @property
    def leverage(self) -> float | None:
        return None if self.equity_partners <= 0 else self.lawyers / self.equity_partners

    @property
    def pep_cents(self) -> int | None:
        if self.equity_partners <= 0:
            return None
        return round(self.profit_cents / self.equity_partners)


def revenue_from_hours(
    lawyers: int, hours: int, rate_cents: int, realisation_bp: int, collection_bp: int
) -> int:
    """Spec 8.1: lawyers x hours x standard rate x realisation x collection, exactly once."""
    return round_half_even(
        lawyers * hours * rate_cents * realisation_bp * collection_bp,
        BP_DENOMINATOR * BP_DENOMINATOR,
    )


# --- Confidence (ADR PT-0007 1; TST 14.6's rule, ported) ---------------------------------------


def clamp_confidence(value: float) -> float:
    return min(max(value, 0.0), 100.0)


def next_confidence(confidence: float, target: float, cfg: ConfidenceBalance) -> float:
    """B <- B + rate (T - B), kept in 0..100 (TST formulas.md 14.6)."""
    return clamp_confidence(confidence + cfg.rate * (target - confidence))


def confidence_target(
    satisfaction_value: float,
    pep_trend: float,
    mp_skill: float,
    draws_suspended: bool,
    bank_trouble: bool,
    departures_12m: int,
    cfg: ConfidenceBalance,
) -> float:
    """T = base + PEP against expectation + the firm's PEP trend + the MP's persona + money
    trouble + recent departures."""
    t = cfg.target_base
    t += cfg.pep_weight * max(-1.0, min(1.0, satisfaction_value))
    t += cfg.trend_weight * max(-1.0, min(1.0, pep_trend))
    t += cfg.mp_weight * (mp_skill - 10) / 10
    t += cfg.draws_suspended if draws_suspended else 0.0
    t += cfg.bank_trouble if bank_trouble else 0.0
    t += cfg.departure_hit * departures_12m
    return t


def whip_label(confidence: float, cfg: ConfidenceBalance) -> str:
    if confidence >= cfg.supportive:
        return "supportive"
    if confidence < cfg.restless:
        return "restless"
    return "neutral"


def whip_range(confidences: Sequence[float], cfg: ConfidenceBalance) -> dict[str, tuple[int, int]]:
    """The whip count with ranges: each partner seen within +-range_half_width; a partner
    whose band straddles a boundary counts in both labels' upper bounds."""
    out = {"supportive": [0, 0], "neutral": [0, 0], "restless": [0, 0]}
    hw = cfg.range_half_width
    for c in confidences:
        lo_label, hi_label = whip_label(c - hw, cfg), whip_label(c + hw, cfg)
        mid = whip_label(c, cfg)
        labels = {lo_label, hi_label, mid}
        if lo_label == hi_label:
            out[mid][0] += 1
        for label in labels:
            out[label][1] += 1
    return {k: (v[0], v[1]) for k, v in out.items()}


# --- Flight (spec 8.7) -----------------------------------------------------------------------


def leave_chance_bp(
    market_cents: int,
    comp_cents: int,
    loyalty: float,
    departed_12m: int,
    group_size: int,
    confidence: float,
    star_mult: float,
    cfg: FlightBalance,
) -> int:
    """p_leave = b (1 + 2 max(0, (V_mkt - comp) / comp)) ((21 - loyalty) / 10)
    (1 + c departed_12m / group) (1 + max(0, 50 - conf) / 25), in bp, capped."""
    comp = max(comp_cents, 1)
    gap = max(0.0, (market_cents - comp) / comp)
    p = cfg.base_bp * (1 + cfg.gap_weight * gap)
    p *= max(0.0, (cfg.loyalty_ref - loyalty) / cfg.loyalty_divisor)
    p *= 1 + cfg.contagion * departed_12m / max(1, group_size)
    p *= 1 + max(0.0, cfg.confidence_ref - confidence) / cfg.confidence_divisor
    p *= star_mult
    return min(cfg.cap_bp, round(p))


def market_value_cents(book_cents: int, cfg: FlightBalance) -> int:
    """V_mkt = book x the lateral market's multiple."""
    return pct_of(max(book_cents, cfg.min_book_cents), cfg.market_multiple_bp)


def stay_probability(
    firm_comp_cents: int,
    offer_cents: int,
    loyalty: float,
    confidence: float,
    counter_guarantee_years: int,
    offer_guarantee_years: int,
    seat: bool,
    cfg: FlightBalance,
) -> float:
    """The partner's choice when an approach comes due: a logistic in the comp gap."""
    gap = (firm_comp_cents - offer_cents) / max(offer_cents, 1)
    x = (
        cfg.stay_base
        + cfg.stay_gap_weight * gap
        + cfg.stay_loyalty * (loyalty - 10)
        + cfg.stay_confidence * (confidence - 50)
        + cfg.guarantee_value * (counter_guarantee_years - offer_guarantee_years)
        + (cfg.seat_bonus if seat else 0.0)
    )
    return 1 / (1 + math.exp(-x))


def stay_label(p: float, cfg: FlightBalance) -> str:
    if p >= cfg.stay_hint_bands.hi:
        return "likely to stay"
    if p < cfg.stay_hint_bands.lo:
        return "likely to go"
    return "undecided"


# --- Revolver (spec 8.4) ----------------------------------------------------------------------


def borrowing_base_cents(receivables: int, wip: int, cfg: RevolverBalance) -> int:
    return pct_of(max(receivables, 0), cfg.receivables_bp) + pct_of(max(wip, 0), cfg.wip_bp)


def monthly_interest_cents(drawn: int, cfg: RevolverBalance) -> int:
    return round_half_even(max(drawn, 0) * cfg.rate_bp, BP_DENOMINATOR * MONTHS_PER_YEAR)


@dataclass(frozen=True, slots=True)
class Covenant:
    name: str
    value: int  # what is measured, cents
    limit: int  # its limit, cents
    floor: bool  # True: value must be at least limit; False: at most

    @property
    def holds(self) -> bool:
        return self.value >= self.limit if self.floor else self.value <= self.limit

    def near(self, headroom_bp: int) -> bool:
        """Within headroom_bp of its limit (the CFO's warning)."""
        if self.floor:
            return self.value < self.limit + pct_of(self.limit, headroom_bp)
        return self.value > self.limit - pct_of(self.limit, headroom_bp)


def covenants(
    drawn: int, revenue_12m: int, capital: int, departed_books: int, cfg: RevolverBalance
) -> tuple[Covenant, ...]:
    """Leverage, minimum partner capital, partner departures as a share of revenue. With
    nothing drawn every covenant holds."""
    if drawn <= 0:
        return ()
    return (
        Covenant("leverage", drawn, pct_of(max(revenue_12m, 0), cfg.leverage_max_bp), False),
        Covenant("partner capital", capital, pct_of(drawn, cfg.min_capital_bp), True),
        Covenant(
            "partner departures",
            departed_books,
            pct_of(max(revenue_12m, 0), cfg.departures_max_bp),
            False,
        ),
    )


def stage_for(lawyers: int, thresholds: Sequence[int]) -> int:
    stage = 0
    for i, t in enumerate(thresholds):
        if lawyers >= t:
            stage = i
    return stage
