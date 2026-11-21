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

import itertools

from ptk.sim.calendar import turn_to_ym
from ptk.sim.data_models import Balance, ClientFailureDef, GameData, PracticeDef
from ptk.sim.macro_data import MacroData
from ptk.sim.matters.models import Client

MONTHS = 12  # tunable-exempt: months in a year
RESTRUCTURING = "restructuring"  # the practice a bankrupt client's estate instructs


def _month(ym: tuple[int, int]) -> int:
    return ym[0] * MONTHS + ym[1] - 1


_POINTS: dict[tuple[int, str], tuple[tuple[int, float], ...]] = {}


def _points(macro: MacroData, series: str) -> tuple[tuple[int, float], ...]:
    """The series' (month, value) points, memoised per loaded data (data is immutable)."""
    key = (id(macro), series)
    pts = _POINTS.get(key)
    if pts is None:
        pts = tuple((_month(p.ym), p.values[series]) for p in macro.points if series in p.values)
        _POINTS[key] = pts
    return pts


def level(macro: MacroData, series: str, ym: tuple[int, int]) -> float:
    """The index `series` at month `ym`, interpolated between the points that give it."""
    pts = _points(macro, series)
    m = _month(ym)
    if m <= pts[0][0]:
        return pts[0][1]
    for (m0, v0), (m1, v1) in itertools.pairwise(pts):
        if m <= m1:
            return v0 + (v1 - v0) * (m - m0) / (m1 - m0)
    return pts[-1][1]


def at_turn(data: GameData, series: str, turn: int, start: tuple[int, int]) -> float:
    return level(data.macro, series, turn_to_ym(turn, start))


def demand_factor(
    practice: PracticeDef, ym: tuple[int, int], data: GameData, balance: Balance
) -> float:
    """G x (1 + beta (I - 1)), the driver term floored (spec 6)."""
    cfg = balance.macro
    growth = level(data.macro, "growth", ym)
    index = level(data.macro, practice.index, ym)
    driver = max(cfg.demand_floor, 1.0 + cfg.beta_scale * practice.beta * (index - 1.0))
    return growth * driver


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
