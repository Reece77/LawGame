"""The seeded world after history (PT-M10; ADR PT-0002 2, ADR PT-0015): the macro and legal
indices, the market's rate rises and the associate salary scale from January 2026 to December
2034, drawn from the save's master seed with the statistics of 2005-2025's history.

History is pinned to December 2025 (`macro_history.yaml`, `salary_scale.yaml`); after it:

- **each index** follows an AR(1) process in logs, monthly, fitted to its July values over
  `macro.seeded.fit_years` (the persistence and the residual spread of years outside the
  recession episodes), reverting to its mean over `mean_years` (a `trend_series` index, the
  long-run growth G, reverts to its fitted trend instead); stream `macro_seed` (65), keyed by
  `(index_number,)` (the index's position in `macro_data.SERIES`);
- **recessions** are regime switches: each month a recession starts with history's frequency
  (episodes / months fitted), at most one every `recession_gap_months`; it replays one of
  history's episodes chosen at random (2008-2009 or 2020): over the episode's fall months each
  index takes that episode's fall (log of its trough over its start) as impulses, and the AR(1)
  brings it back. The regime draws are the same stream keyed `(len(SERIES),)`;
- **the rate rise** each January follows an AR(1) fitted to the history's rises outside
  recession years; a year after a recession began takes history's mean recession-year rise;
  stream `scale_seed` (66) keyed `(0,)`;
- **the salary scale** steps when the market runs hot: in `scale.month` of a year, if the
  lateral heat index averaged over the past 12 months is at least `heat_from`, the year's rate
  rise at least `rate_from` and `min_gap_years` have passed since the last step, the market
  leader raises with chance `chance_bp`, by one of history's step sizes (first-year salary
  steps since `step_years_from`) chosen at random; bonuses move with it. Stream `scale_seed`
  keyed `(1,)`.

`world_data(data, balance, seed)` returns the save's own `GameData` (memoised), its `macro`
and `salary_scale` extended to December 2034; everything else is shared. The turn, actions and
game creation call it, so every reader of the indices sees the save's world. Pure: the data,
the balance and the seed decide everything.
"""

from __future__ import annotations

import math
from collections import OrderedDict
from collections.abc import Sequence
from dataclasses import dataclass

from ptk.sim import dmath
from ptk.sim.data_models import Balance, BonusRow, GameData, SalaryScale, ScaleRow
from ptk.sim.macro_data import SERIES, MacroData, MacroPoint, SeededBalance
from ptk.sim.rng import RngFactory

MONTHS = 12  # tunable-exempt: months in a year
JULY = 7  # tunable-exempt: the annual figure's month (macro_history.yaml's mid-year points)
STREAM_TURN = 0  # tunable-exempt: the seeded world is drawn once per save, at turn 0
RATE_KEY = 0  # scale_seed key: the rate rises
SCALE_KEY = 1  # scale_seed key: the salary scale's steps
CACHE = 32  # tunable-exempt: saves' worlds kept in memory


def _m(ym: tuple[int, int]) -> int:
    return ym[0] * MONTHS + ym[1] - 1


def _ym(m: int) -> tuple[int, int]:
    return (m // MONTHS, m % MONTHS + 1)


@dataclass(frozen=True, slots=True)
class Fit:
    """One index's fitted process (logs): mean (or trend), monthly persistence and spread."""

    mean: float  # the log level it reverts to (a trend series: at the last history month)
    trend: float  # log growth a month (0 for a mean-reverting index)
    phi: float  # monthly AR(1) coefficient
    sigma: float  # monthly residual sd
    falls: tuple[float, ...]  # log fall in each recession episode


def _level(macro: MacroData, series: str, ym: tuple[int, int]) -> float:
    from ptk.sim.macro import level

    return level(macro, series, ym)


def _in_episode(year: int, cfg: SeededBalance) -> bool:
    return any(e.from_ym[0] <= year <= e.trough[0] + 1 for e in cfg.episodes)


def _ar1(values: Sequence[float], skip: Sequence[bool]) -> tuple[float, float]:
    """Annual AR(1) through the origin on deviations; (phi, residual sd) from the years whose
    pair is outside the recession episodes."""
    pairs = [
        (values[i - 1], values[i]) for i in range(1, len(values)) if not (skip[i] or skip[i - 1])
    ]
    den = sum(a * a for a, _ in pairs)
    phi = sum(a * b for a, b in pairs) / den if den > 0 else 0.0
    resid = [b - phi * a for a, b in pairs]
    sd = math.sqrt(sum(r * r for r in resid) / len(resid)) if resid else 0.0
    return phi, sd


def fit_series(macro: MacroData, series: str, cfg: SeededBalance) -> Fit:
    """The index's AR(1) and recession falls, from the history's July values."""
    first, last = cfg.fit_years
    years = list(range(first, last + 1))
    logs = [dmath.log(_level(macro, series, (y, JULY))) for y in years]
    skip = [_in_episode(y, cfg) for y in years]
    trend = 0.0
    if series in cfg.trend_series:
        trend = (logs[-1] - logs[0]) / (len(years) - 1)
        devs = [v - (logs[0] + trend * i) for i, v in enumerate(logs)]
    else:
        lo, hi = cfg.mean_years
        window = [v for y, v in zip(years, logs, strict=True) if lo <= y <= hi]
        mean = sum(window) / len(window)
        devs = [v - mean for v in logs]
    phi_a, sd_a = _ar1(devs, skip)
    phi_a = min(max(phi_a, cfg.phi_range[0]), cfg.phi_range[1])
    phi = dmath.pow(phi_a, 1 / MONTHS) if phi_a > 0 else 0.0
    # the monthly spread that gives the annual residual spread at this persistence
    ratio = (1 - phi * phi) / (1 - phi_a * phi_a) if phi_a < 1 else 1.0
    sigma = sd_a * math.sqrt(ratio) * cfg.noise_scale
    falls = tuple(
        dmath.log(_level(macro, series, e.trough) / _level(macro, series, e.from_ym))
        for e in cfg.episodes
    )
    end = _ym(_m(cfg.start) - 1)
    if series in cfg.trend_series:
        base = dmath.log(_level(macro, series, end))
        return Fit(base, trend / MONTHS, phi, sigma, falls)
    return Fit(mean, 0.0, phi, sigma, falls)


@dataclass(frozen=True, slots=True)
class Recession:
    start: int  # absolute month
    episode: int


def recessions(rng: RngFactory, cfg: SeededBalance) -> tuple[Recession, ...]:
    """The seeded recessions: history's frequency, one at a time, `recession_gap_months`
    apart (stream macro_seed, key (len(SERIES),))."""
    fitted = _m((cfg.fit_years[1], MONTHS)) - _m((cfg.fit_years[0], 1)) + 1
    hazard = len(cfg.episodes) / fitted * cfg.recession_hazard_scale
    gen = rng.stream(STREAM_TURN, "macro_seed", len(SERIES))
    out: list[Recession] = []
    last = -(10**6)
    for m in range(_m(cfg.start), _m(cfg.until) + 1):
        u, pick = float(gen.random()), int(gen.integers(0, len(cfg.episodes)))
        if m - last >= cfg.recession_gap_months and u < hazard:
            out.append(Recession(m, pick))
            last = m
    return tuple(out)


def _impulses(cfg: SeededBalance, found: Sequence[Recession]) -> dict[int, tuple[int, int]]:
    """month -> (episode, fall months) for each month a recession is falling."""
    out: dict[int, tuple[int, int]] = {}
    for r in found:
        e = cfg.episodes[r.episode]
        months = max(1, _m(e.trough) - _m(e.from_ym))
        for k in range(months):
            out[r.start + k] = (r.episode, months)
    return out


def seeded_points(macro: MacroData, cfg: SeededBalance, rng: RngFactory) -> tuple[MacroPoint, ...]:
    """Monthly points from `cfg.start` to `cfg.until`, every index."""
    found = recessions(rng, cfg)
    falling = _impulses(cfg, found)
    end = _ym(_m(cfg.start) - 1)
    paths: dict[str, list[float]] = {}
    for i, series in enumerate(SERIES):
        fit = fit_series(macro, series, cfg)
        gen = rng.stream(STREAM_TURN, "macro_seed", i)
        level0 = dmath.log(_level(macro, series, end))
        dev = level0 - fit.mean
        out = []
        for k, m in enumerate(range(_m(cfg.start), _m(cfg.until) + 1)):
            dev = fit.phi * dev + fit.sigma * float(gen.standard_normal())
            if m in falling:
                episode, months = falling[m]
                dev += fit.falls[episode] / months
            out.append(dmath.exp(fit.mean + fit.trend * (k + 1) + dev))
        paths[series] = out
    return tuple(
        MacroPoint(
            ym=_ym(m),
            values={s: round(paths[s][k], 6) for s in SERIES},
            note="seeded" if k else "seeded from here",
        )
        for k, m in enumerate(range(_m(cfg.start), _m(cfg.until) + 1))
    )


def seeded_rate_rises(
    macro: MacroData, cfg: SeededBalance, found: Sequence[Recession], rng: RngFactory
) -> dict[int, float]:
    """The market's January rise for each seeded year (stream scale_seed, key (0,))."""
    hist = dict(sorted(macro.rate_rise.items()))
    years = list(hist)
    in_rec = [
        any(e.from_ym[0] + 1 == y or e.trough[0] + 1 == y for e in cfg.episodes) for y in years
    ]
    calm = [v for v, r in zip(hist.values(), in_rec, strict=True) if not r]
    mean = sum(calm) / len(calm)
    phi, sd = _ar1([v - mean for v in hist.values()], in_rec)
    phi = min(max(phi, cfg.phi_range[0]), cfg.phi_range[1])
    rec = [v for v, r in zip(hist.values(), in_rec, strict=True) if r]
    rec_mean = sum(rec) / len(rec) if rec else mean
    gen = rng.stream(STREAM_TURN, "scale_seed", RATE_KEY)
    dev = hist[years[-1]] - mean
    out: dict[int, float] = {}
    for year in range(cfg.start[0], cfg.until[0] + 1):
        dev = phi * dev + sd * cfg.noise_scale * float(gen.standard_normal())
        hit = any(r.start // MONTHS in (year - 1, year) and r.start < _m((year, 1)) for r in found)
        value = rec_mean if hit else mean + dev
        if hit:
            dev = value - mean
        out[year] = round(min(max(value, cfg.rate_range[0]), cfg.rate_range[1]), 4)
    return out


def _steps(scale: SalaryScale, cfg: SeededBalance) -> tuple[float, ...]:
    """History's first-year steps (ratios less one) since `step_years_from`."""
    out = []
    for a, b in zip(scale.scale, scale.scale[1:], strict=False):
        if b.from_ym[0] >= cfg.scale.step_years_from and b.salaries[0] > a.salaries[0]:
            out.append(b.salaries[0] / a.salaries[0] - 1)
    return tuple(out)


def seeded_scale(
    scale: SalaryScale,
    macro: MacroData,
    rises: dict[int, float],
    cfg: SeededBalance,
    rng: RngFactory,
) -> SalaryScale:
    """The salary scale's seeded steps and bonuses (stream scale_seed, key (1,))."""
    sc = cfg.scale
    steps = _steps(scale, cfg) or (sc.fallback_step,)
    gen = rng.stream(STREAM_TURN, "scale_seed", SCALE_KEY)
    rows = list(scale.scale)
    bonuses = list(scale.bonuses)
    last_year = rows[-1].from_ym[0]
    for year in range(cfg.start[0], cfg.until[0] + 1):
        u, pick = float(gen.random()), int(gen.integers(0, len(steps)))
        at = (year, sc.month)
        heat = sum(_level(macro, "lateral_heat", _ym(_m(at) - k)) for k in range(MONTHS)) / MONTHS
        hot = heat >= sc.heat_from and rises.get(year, 0.0) >= sc.rate_from
        if not (hot and year - last_year >= sc.min_gap_years and u * 10_000 < sc.chance_bp):
            continue
        step = steps[pick]
        rows.append(
            ScaleRow.model_validate({"from": at, "salaries": _raise(rows[-1].salaries, step)})
        )
        latest = next((b for b in reversed(bonuses) if b.year <= year), bonuses[-1])
        bonuses = [b for b in bonuses if b.year < year]
        bonuses.append(BonusRow(year=year, amounts=_raise(latest.amounts, step)))
        last_year = year
    return SalaryScale(scale=tuple(rows), bonuses=tuple(bonuses), bands=scale.bands)


def _raise(amounts: Sequence[int], step: float) -> tuple[int, ...]:
    """Each amount up by `step`, rounded to $2,500 (the scale's own steps; integer cents)."""
    unit = 250_000  # tunable-exempt: $2,500 in cents, the market's rounding
    return tuple(round(a * (1 + step) / unit) * unit for a in amounts)


_WORLDS: OrderedDict[tuple[int, int, int], tuple[GameData, Balance, GameData]] = OrderedDict()


def world_data(data: GameData, balance: Balance, seed: int) -> GameData:
    """The save's world: `data` with the seeded indices, rate rises and salary scale to
    December 2034 (memoised; the same seed always gives the same world)."""
    if data.macro.seed is not None:
        return data
    cfg = balance.macro.seeded
    if cfg is None:
        return data
    key = (id(data), id(balance), seed)
    hit = _WORLDS.get(key)
    if hit is not None and hit[0] is data and hit[1] is balance:
        _WORLDS.move_to_end(key)
        return hit[2]
    rng = RngFactory(seed)
    history = data.macro
    points = tuple(p for p in history.points if p.ym < cfg.start)
    end = _ym(_m(cfg.start) - 1)
    if points[-1].ym != end:  # history pinned: its last values hold to December 2025
        values = {s: _level(history, s, end) for s in SERIES}
        points = (*points, MacroPoint(ym=end, values=values, note="history held"))
    found = recessions(rng, cfg)
    seeded = seeded_points(history, cfg, rng)
    rises = {
        **{y: r for y, r in history.rate_rise.items() if y < cfg.start[0]},
        **seeded_rate_rises(history, cfg, found, rng),
    }
    macro = MacroData(
        sources=history.sources,
        points=(*points, *seeded),
        rate_rise=rises,
        shocks=history.shocks,
        seed=seed,
    )
    scale = seeded_scale(data.salary_scale, macro, rises, cfg, rng)
    world = data.model_copy(update={"macro": macro, "salary_scale": scale})
    _WORLDS[key] = (data, balance, world)
    while len(_WORLDS) > CACHE:
        _WORLDS.popitem(last=False)
    return world
