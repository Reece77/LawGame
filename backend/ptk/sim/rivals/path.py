"""A real rival's published path (ADR PT-0008 2): revenue and lawyers as annual run-rates.

Each fiscal-year point (firms.yaml `fy2005` and `path`) sits at the middle of its year; the
run-rate between two points is geometric, so the trailing twelve months at December are
close to the fiscal year's figure. Before the first point the first value holds; after the
last, the run-rate grows with the market (balance `rivals.market_growth`). An outside merger
(firms.yaml events `outside_merger`) is a step: the left point's value holds until its month,
the right point's after. A successor firm (`start_ym`) starts from its anchor (the parties'
combined run-rate at the merger) and moves geometrically to its first point.

Lawyers: points without a lawyer count take it from revenue per lawyer, interpolated between
the points that have both.
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache

from ptk.sim import dmath
from ptk.sim.calendar import MONTHS_PER_YEAR, YearMonth, turn_to_ym
from ptk.sim.rivals.data import FirmDef, HistoryEventDef, RivalsBalance

HALF_YEAR = 0.5  # tunable-exempt: a fiscal year's point sits mid-year


def time_of(turn: int, start: YearMonth) -> float:
    """Continuous time: the middle of the month, in years."""
    y, m = turn_to_ym(turn, start)
    return y + (m - HALF_YEAR) / MONTHS_PER_YEAR


def market_factor(from_time: float, to_time: float, rb: RivalsBalance) -> float:
    """The market's nominal growth between two times (years, continuous). Fiscal year Y's
    growth (balance `rivals.market_growth`) runs from mid Y-1 to mid Y."""
    factor, t = 1.0, from_time
    while t < to_time - 1e-12:
        year = math.floor(t + HALF_YEAR)
        seg_end = min(to_time, year + HALF_YEAR)
        g = rb.market_growth.get(year, rb.market_growth_after)
        factor *= dmath.pow(1.0 + g, seg_end - t)
        t = seg_end
    return factor


@dataclass(frozen=True, slots=True)
class Path:
    """Revenue and lawyers points as (time, value); steps as times."""

    revenue: tuple[tuple[float, float], ...]
    lawyers: tuple[tuple[float, float], ...]
    steps: tuple[float, ...]
    start: float | None  # a successor's first time


def build_path(firm: FirmDef, events: Sequence[HistoryEventDef]) -> Path:
    return _build(firm, tuple(e for e in events if e.firm == firm.key))


@lru_cache(maxsize=256)
def _build(firm: FirmDef, events: tuple[HistoryEventDef, ...]) -> Path:
    points = ([firm.fy2005] if firm.fy2005 is not None else []) + list(firm.path)
    rev = tuple((p.year + HALF_YEAR, float(p.revenue_cents)) for p in points if p.revenue_cents)
    both = [
        (p.year + HALF_YEAR, p.revenue_cents / p.lawyers)
        for p in points
        if p.revenue_cents and p.lawyers
    ]
    lawyers: list[tuple[float, float]] = []
    for t, value in rev:
        known = next((p.lawyers for p in points if p.year + HALF_YEAR == t and p.lawyers), None)
        if known is not None:
            lawyers.append((t, float(known)))
        elif both:
            lawyers.append((t, value / _interp(tuple(both), t, ())))
    steps = tuple(
        e.ym[0] + (e.ym[1] - HALF_YEAR) / MONTHS_PER_YEAR
        for e in events
        if e.kind == "outside_merger"
    )
    start = None
    if firm.start_ym is not None:
        start = firm.start_ym[0] + (firm.start_ym[1] - HALF_YEAR) / MONTHS_PER_YEAR
    return Path(revenue=rev, lawyers=tuple(lawyers), steps=steps, start=start)


def _interp(points: tuple[tuple[float, float], ...], t: float, steps: tuple[float, ...]) -> float:
    if t <= points[0][0]:
        return points[0][1]
    for (t0, v0), (t1, v1) in itertools.pairwise(points):
        if t0 <= t <= t1:
            step = next((s for s in steps if t0 < s <= t1), None)
            if step is not None:
                return v0 if t < step else v1
            w = (t - t0) / (t1 - t0)
            return v0 * dmath.pow(v1 / v0, w)
    return points[-1][1]


def path_value(
    path: Path,
    which: str,
    t: float,
    rb: RivalsBalance,
    anchor: tuple[float, float] | None = None,
) -> float | None:
    """The path's annual run-rate of `which` ("revenue" or "lawyers") at time t; None if
    the firm has no points. `anchor`: a successor's (time, value) where its path starts."""
    points = path.revenue if which == "revenue" else path.lawyers
    if not points:
        return None
    if anchor is not None and t < points[0][0]:
        if t <= anchor[0]:
            return anchor[1]
        w = (t - anchor[0]) / (points[0][0] - anchor[0])
        return anchor[1] * dmath.pow(points[0][1] / anchor[1], w)
    last_t, last_v = points[-1]
    if t > last_t:
        return last_v * market_factor(last_t, t, rb)
    return _interp(points, t, path.steps)


def last_point_year(path: Path) -> int | None:
    return int(path.revenue[-1][0]) if path.revenue else None
