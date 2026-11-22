"""The macro and legal indices, 2005-2015 (PT-M7; spec 6, 14).

`macro_history.yaml` gives dated points of each index, 1.0 = the 2005 average; a month between
two points is interpolated linearly, a month after the last holds it (the seeded cycles to 2034
are v2's, PT-M10). Pure: everything is read from the data, the balance and the month.

How the indices act (balance.yaml `macro:`):

- **demand** (spec 6): D = D0 x G x (1 + beta_scale x beta_p (I_p - 1)) x eps, the driver term
  held at `demand_floor` or above; G is the `growth` index;
- **collections stress**: clients' days to pay x (1 + collections_weight (I - 1));
- **lateral heat**: resignations and a partner's market value (V_mkt) x
  (1 + lateral_heat_weight (I - 1));
- **rates**: the market's January rate rise is the year's `rate_rise` (after the last year,
  `rivals.rate_inflation`).
"""

from __future__ import annotations

import bisect

from ptk.sim.calendar import turn_to_ym
from ptk.sim.data_models import Balance, ClientFailureDef, GameData, PracticeDef
from ptk.sim.macro_data import MacroData
from ptk.sim.matters.models import Client

MONTHS = 12  # tunable-exempt: months in a year
RESTRUCTURING = "restructuring"  # the practice a bankrupt client's estate instructs


def _month(ym: tuple[int, int]) -> int:
    return ym[0] * MONTHS + ym[1] - 1


_POINTS: dict[tuple[int, str], tuple[MacroData, tuple[int, ...], tuple[float, ...]]] = {}
_KEEP = 256  # tunable-exempt: memoised series (a save's seeded world adds its own)


def _points(macro: MacroData, series: str) -> tuple[tuple[int, ...], tuple[float, ...]]:
    """The series' point months and values, memoised per loaded data (data is immutable; the
    entry holds the data, so a reused id never reads another world's points)."""
    key = (id(macro), series)
    hit = _POINTS.get(key)
    if hit is None or hit[0] is not macro:
        pts = [(_month(p.ym), p.values[series]) for p in macro.points if series in p.values]
        hit = (macro, tuple(m for m, _ in pts), tuple(v for _, v in pts))
        if len(_POINTS) >= _KEEP:
            _POINTS.clear()
        _POINTS[key] = hit
    return hit[1], hit[2]


def level(macro: MacroData, series: str, ym: tuple[int, int]) -> float:
    """The index `series` at month `ym`, interpolated between the points that give it."""
    months, values = _points(macro, series)
    m = _month(ym)
    if m <= months[0]:
        return values[0]
    i = bisect.bisect_left(months, m)
    if i >= len(months):
        return values[-1]
    m0, m1, v0, v1 = months[i - 1], months[i], values[i - 1], values[i]
    return v0 + (v1 - v0) * (m - m0) / (m1 - m0)


def at_turn(data: GameData, series: str, turn: int, start: tuple[int, int]) -> float:
    return level(data.macro, series, turn_to_ym(turn, start))


def shock_share(macro: MacroData, what: str, practice: str, ym: tuple[int, int]) -> float:
    """PT-M10: the share of a practice's `what` ("demand" or "hours") a dated shock takes this
    month (0 outside every shock)."""
    m = _month(ym)
    lost = 0.0
    for shock in macro.shocks:
        start = _month(shock.from_ym)
        if start <= m < start + shock.months:
            table = shock.demand if what == "demand" else shock.hours
            lost = max(lost, table.get(practice, 0.0))
    return lost


def docket_slowed(macro: MacroData, ym: tuple[int, int]) -> bool:
    """PT-M10: are the courts slowed this month (a shock with `docket`)?"""
    m = _month(ym)
    return any(
        s.docket and _month(s.from_ym) <= m < _month(s.from_ym) + s.months for s in macro.shocks
    )


def demand_factor(
    practice: PracticeDef, ym: tuple[int, int], data: GameData, balance: Balance
) -> float:
    """G x (1 + beta (I - 1)), the driver term floored (spec 6); PT-M10: less a dated shock's
    share."""
    cfg = balance.macro
    growth = level(data.macro, "growth", ym)
    index = level(data.macro, practice.index, ym)
    driver = max(cfg.demand_floor, 1.0 + cfg.beta_scale * practice.beta * (index - 1.0))
    return growth * driver * (1.0 - shock_share(data.macro, "demand", practice.key, ym))


def weighted(index: float, weight: float) -> float:
    return max(0.0, 1.0 + weight * (index - 1.0))


def collections_stress(turn: int, start: tuple[int, int], data: GameData, b: Balance) -> float:
    """Days-to-pay multiplier this month (times billing.macro_stress)."""
    return weighted(at_turn(data, "collections", turn, start), b.macro.collections_weight)


def lateral_heat(turn: int, start: tuple[int, int], data: GameData, b: Balance) -> float:
    """The lateral market's multiplier on resignations and partners' market value."""
    return weighted(at_turn(data, "lateral_heat", turn, start), b.macro.lateral_heat_weight)


def market_rise(year: int, data: GameData, balance: Balance) -> float:
    """The market's rate rise in January of `year` (a fraction)."""
    return data.macro.rate_rise.get(year, balance.rivals.rate_inflation)


# --- PT-M7b: the crisis (spec 14) ----------------------------------------------------------


def _ramp(value: float, start: float, full: float) -> float:
    """0 at `start`, 1 at `full` (either direction), clipped."""
    if full == start:
        return 0.0
    return min(1.0, max(0.0, (value - start) / (full - start)))


def crisis_stress(turn: int, start: tuple[int, int], data: GameData, b: Balance) -> float:
    """The month's crisis stress, 0-1: the larger of the collections and credit stresses."""
    cfg = b.macro.crisis
    collections = _ramp(
        at_turn(data, "collections", turn, start), cfg.collections_from, cfg.collections_full
    )
    credit = _ramp(at_turn(data, "credit", turn, start), cfg.credit_from, cfg.credit_full)
    return max(collections, credit)


def driver_shortfall(practice: PracticeDef, ym: tuple[int, int], data: GameData) -> float:
    """A pro-cyclical practice's driver index below 1 (0 for a counter-cyclical one)."""
    if practice.beta <= 0:
        return 0.0
    return max(0.0, 1.0 - level(data.macro, practice.index, ym))


def sector_shortfall(sector: str, ym: tuple[int, int], data: GameData) -> float:
    """A client sector's mix-weighted driver shortfall (how stressed its own business is)."""
    table = next((x for x in data.clients.sectors if x.key == sector), None)
    if table is None:
        return 0.0
    total = sum(table.mix.values())
    if total <= 0:
        return 0.0
    return (
        sum(w * driver_shortfall(data.practice(p), ym, data) for p, w in table.mix.items()) / total
    )


def crisis_factor(
    price_sensitivity: float, sector: str, ym: tuple[int, int], data: GameData, b: Balance
) -> float:
    """A client's crisis factor: price-sensitive clients and stressed sectors ask for more."""
    cfg = b.macro.crisis
    return (price_sensitivity / cfg.sensitivity_neutral) * (
        1.0 + cfg.sector_weight * sector_shortfall(sector, ym, data)
    )


# --- Real clients' dated failures (clients.yaml `fails`; dossier s1) -------------------------

_FAILURES: dict[int, dict[str, ClientFailureDef]] = {}


def _failures(data: GameData) -> dict[str, ClientFailureDef]:
    key = id(data.clients)
    table = _FAILURES.get(key)
    if table is None:
        table = {c.name: c.fails for c in data.clients.real_clients if c.fails is not None}
        _FAILURES[key] = table
    return table


def failure_of(client: Client, data: GameData) -> ClientFailureDef | None:
    """A real client's scripted failure, if history has one (never a generated client)."""
    return _failures(data).get(client.name) if client.real else None


def failure_turn(client: Client, data: GameData, start: tuple[int, int]) -> int | None:
    fails = failure_of(client, data)
    return None if fails is None else _month(fails.ym) - _month(start)


def bankrupt_by(client: Client, turn: int, data: GameData, start: tuple[int, int]) -> bool:
    """Has this client filed for bankruptcy by `turn` (its bills are then the firm's loss)?"""
    fails = failure_of(client, data)
    return (
        fails is not None
        and fails.kind == "bankruptcy"
        and _month(start) + turn >= _month(fails.ym)
    )


def wallet_factors(
    client: Client, turn: int, data: GameData, balance: Balance, start: tuple[int, int]
) -> tuple[float, ...] | None:
    """The client's wallet weight multipliers by practice this month, or None while it lives.

    A bankrupt client's estate instructs only restructuring work, its weight x estate_mult, for
    estate_months; a rescued client's wallet runs rescue_months past the rescue. Then both end.
    """
    t = failure_turn(client, data, start)
    if t is None or turn < t:
        return None
    fails = failure_of(client, data)
    assert fails is not None
    cfg = balance.macro
    zero = tuple(0.0 for _ in data.practices)
    if fails.kind == "rescue":
        return None if turn < t + cfg.rescue_months else zero
    if turn >= t + cfg.estate_months:
        return zero
    return tuple(cfg.estate_mult if p.key == RESTRUCTURING else 0.0 for p in data.practices)
