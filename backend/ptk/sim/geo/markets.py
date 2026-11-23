"""Cities' local markets: their demand and their clients (PT-M11; spec 8.8 local demand reach).

A city other than the home city has its own legal market: each month its demand by practice is
the home market's base (practices.yaml D0, seasonality and the macro's `demand_factor`) x the
city's size (cities.yaml `demand`) x its practice mix, times the region's own series for a city
outside the US (macro_history.yaml `regions`, London's 2008, 2016 and 2023), with noise from
stream `city_demand` (103, keyed (city index, practice index)). Its clients split it by wallet,
as New York's clients split New York's (`ptk.sim.matters.market.wallets` per city).

A city's clients are made when the player's firm first opens an office there (a pure function of
the seed: stream `city_clients`, 100, keyed (city index, n)): London's real clients
(clients.yaml `uk_clients`, FTSE 100 names) then `cities.yaml clients` generated ones, each
with a panel of the rivals present in the city's region. Until then nobody serves that market,
so a firm that never opens an office plays exactly as v1. Demand is drawn only for cities where
the player has an office.
"""

from __future__ import annotations

import bisect
from dataclasses import replace
from typing import Final

import numpy as np

from ptk.sim import dmath
from ptk.sim.calendar import MONTHS_PER_YEAR, turn_to_ym
from ptk.sim.data_models import Balance, GameData, PracticeDef
from ptk.sim.geo.cities import city_def, region_of_city, rival_region
from ptk.sim.geo.data import CityDef
from ptk.sim.macro import demand_factor
from ptk.sim.macro_data import MacroData
from ptk.sim.matters.models import Client, GeneralCounsel, SizeClass
from ptk.sim.people.models import Personality
from ptk.sim.rng import RngFactory
from ptk.sim.scale import ATTR_MAX, ATTR_MIN
from ptk.sim.state import GameState

TRAIT_MEAN: Final = 10.0  # tunable-exempt: the 1-20 scale's centre (as matters.setup)
TRAIT_SD: Final = 3.5  # tunable-exempt: generated traits' spread (as matters.setup)
UK_NAMES: Final = "uk"  # names.yaml pool for London's generated clients, if present


def city_index(data: GameData, city: str) -> int:
    return [c.key for c in data.geo.cities].index(city)


def _month(ym: tuple[int, int]) -> int:
    return ym[0] * MONTHS_PER_YEAR + ym[1] - 1


def region_multiplier(macro: MacroData, region: str, series: str, ym: tuple[int, int]) -> float:
    """A region's multiplier on an index at a month (1.0 where none is given)."""
    points = [
        (_month(p.ym), p.values[series])
        for p in macro.regions.get(region, ())
        if series in p.values
    ]
    if not points:
        return 1.0
    months = [m for m, _ in points]
    m = _month(ym)
    if m <= months[0]:
        return points[0][1]
    i = bisect.bisect_left(months, m)
    if i >= len(months):
        return points[-1][1]
    (m0, v0), (m1, v1) = points[i - 1], points[i]
    return v0 if m1 == m0 else v0 + (v1 - v0) * (m - m0) / (m1 - m0)


def local_factor(
    practice: PracticeDef, city: CityDef, ym: tuple[int, int], data: GameData
) -> float:
    """The city's size, mix and (outside the US) its region's multiplier on the practice's index."""
    size = city.demand * city.mix.get(practice.key, 1.0)
    if city.region == "us":
        return size
    return size * region_multiplier(data.macro, city.region, practice.index, ym)


def city_demand(
    rng: RngFactory, turn: int, state: GameState, city: str, data: GameData, balance: Balance
) -> tuple[int, ...]:
    """A city's demand this month in standard-value cents, by practice (practices.yaml order)."""
    cdef = data.geo.city(city)
    ym = turn_to_ym(turn, state.save_meta.start_ym)
    out = []
    ci = city_index(data, cdef.key)
    for index, practice in enumerate(data.practices):
        z = float(rng.stream(turn, "city_demand", ci, index).standard_normal())
        eps = dmath.exp(practice.sigma * z)
        base = practice.demand_cents / MONTHS_PER_YEAR * practice.seasonality[ym[1] - 1]
        factor = demand_factor(practice, ym, data, balance) * local_factor(practice, cdef, ym, data)
        out.append(round(base * factor * eps))
    return tuple(out)


def demand_month(state: GameState, rng: RngFactory, data: GameData, balance: Balance) -> GameState:
    """Phase 4: the demand of every city where the player has an office (none: unchanged)."""
    cities = sorted({o.city for o in state.geo.firm_offices(state.player.id)})
    if not cities and not state.geo.demand:
        return state
    demand = tuple((c, city_demand(rng, state.turn, state, c, data, balance)) for c in cities)
    return replace(state, geo=replace(state.geo, demand=demand))


def has_market(state: GameState, city: str) -> bool:
    return any(c.city == city for c in state.market.clients)


def region_panel(state: GameState, city: str, data: GameData) -> list[tuple[str, float]]:
    """(rival key, weight) for the rivals present in a city's region: real and generated
    firms whose headquarters are in the region (a London client's panel is UK firms)."""
    region = region_of_city(data, city)
    out = []
    for f in state.rivals.active:
        if f.kind == "boutique" or rival_region(data, f.hq) != region:
            continue
        weight = max(1.0, f.revenue_12m / 1e9) ** 0.5  # tunable-exempt: by size's square root
        out.append((f.key, weight))
    return sorted(out)


def _pick(gen: np.random.Generator, items: list[str] | tuple[str, ...]) -> str:
    return items[int(gen.integers(len(items)))]


def _panel(gen: np.random.Generator, pool: list[tuple[str, float]], n: int) -> tuple[str, ...]:
    if not pool:
        return ()
    n = min(n, len(pool))
    keys = [k for k, _ in pool]
    w = np.array([x for _, x in pool], dtype=float)
    idx = gen.choice(len(keys), size=n, replace=False, p=w / w.sum())
    return tuple(sorted(keys[int(i)] for i in idx))


def make_city_clients(
    state: GameState, city: str, rng: RngFactory, data: GameData, balance: Balance
) -> GameState:
    """The city's clients join the client universe (once): real ones, then generated."""
    if has_market(state, city):
        return state
    cdef = data.geo.city(city)
    cfg = balance.clients
    ci = city_index(data, cdef.key)
    pool = region_panel(state, city, data)
    names = data.names.get(UK_NAMES) if cdef.region == "uk" else None
    names = names or data.names["us"]
    taken = {c.name for c in state.market.clients}
    reals = data.clients.uk_clients if cdef.region == "uk" else ()
    lo_rev, hi_rev = balance.geo.local_client_revenue_bn
    next_id = max((c.id for c in state.market.clients), default=0) + 1
    out: list[Client] = []
    for n in range(len(reals) + cdef.clients):
        gen = rng.stream(0, "city_clients", ci, n)
        if n < len(reals):
            real = reals[n]
            name, sector, revenue, is_real = real.name, real.sector, real.revenue_bn, True
            if name in taken:
                name = f"{name} ({cdef.label})"
        else:
            sector = _weighted(gen, data.clients.generated_sector_weights)
            revenue = round(dmath.exp(gen.uniform(dmath.log(lo_rev), dmath.log(hi_rev))), 3)
            suffixes = data.clients.sector(sector).suffixes
            name = f"{_pick(gen, names.last)} {_pick(gen, suffixes)}"
            if name in taken:
                name = f"{name} ({cdef.label})"
            if name in taken:
                name = f"{name} {n}"
            is_real = False
        taken.add(name)
        size_class: SizeClass = "large" if revenue >= cfg.large_revenue_bn else "mid"
        lo, hi = cfg.panel_large if size_class == "large" else cfg.panel_mid
        panel = _panel(gen, pool, int(gen.integers(lo, hi + 1)))
        price = float(gen.uniform(cfg.price_sensitivity.lo, cfg.price_sensitivity.hi))
        loyalty = float(gen.uniform(cfg.loyalty.lo, cfg.loyalty.hi))
        age = int(gen.integers(cfg.gc_age[0], cfg.gc_age[1] + 1))
        gc = GeneralCounsel(
            first_name=_pick(gen, names.first),
            last_name=_pick(gen, names.last),
            birth_turn=state.turn - age * MONTHS_PER_YEAR - int(gen.integers(MONTHS_PER_YEAR)),
            personality=Personality.build(
                data.personality_keys,
                {
                    k: min(
                        ATTR_MAX,
                        max(ATTR_MIN, TRAIT_MEAN + TRAIT_SD * float(gen.standard_normal())),
                    )
                    for k in data.personality_keys
                },
            ),
        )
        out.append(
            Client(
                id=next_id + n,
                name=name,
                sector=sector,
                country="uk" if cdef.region == "uk" else "us",
                real=is_real,
                revenue_bn=revenue,
                size_class=size_class,
                price_sensitivity=price,
                loyalty=loyalty,
                gc=gc,
                panel=panel,
                city=cdef.key,
            )
        )
    market = replace(state.market, clients=(*state.market.clients, *out))
    return replace(state, market=market)


def _weighted(gen: np.random.Generator, weights: dict[str, float]) -> str:
    keys = list(weights)
    total = sum(weights.values())
    u = float(gen.random()) * total
    acc = 0.0
    for k in keys:
        acc += weights[k]
        if u < acc:
            return k
    return keys[-1]


def city_of_client_ok(data: GameData, city: str) -> bool:
    return city_def(data, city) is not None
