"""PT-M18 (the product manager's decision, 2026-11-27): free play reads a rival's rate index
against the market's price level in its own terms, and the growth bias has a floor.

A rival that followed history's path carries the market's rate rises in its index after the
pin ends (its capacity per lawyer stayed at 2005's), so it is read against its region's
history-following rivals' mean; every other firm against 1 (unchanged before 2026). Before
this, every seed's big rivals lost about half their demand a year from 2026, and seed 36's
run stopped when a boutique's bias passed -1.
"""

from __future__ import annotations

from dataclasses import replace

from ptk.sim.data_models import Balance, GameData
from ptk.sim.geo.cities import rival_region
from ptk.sim.rivals.economy import Month, price_levels, update_demand
from tests.rivals_support import start, turn_of


def _month(state, data: GameData, balance: Balance, year: int) -> Month:  # type: ignore[no-untyped-def]
    return Month(
        turn=turn_of(state, year, 6), start=state.save_meta.start_ym, data=data, balance=balance
    )


def test_history_followers_are_read_against_their_regions_mean(
    data: GameData, balance: Balance
) -> None:
    state = start(data, balance, 1)
    month = _month(state, data, balance, 2027)
    firms = tuple(
        replace(f, rate_index=2.0) if month.follows_history(f) else f for f in state.rivals.active
    )
    levels = price_levels(firms, month, lambda f: rival_region(data, f.hq))
    for f in firms:
        assert levels[f.id] == (2.0 if month.follows_history(f) else 1.0)
    assert any(month.follows_history(f) for f in firms)
    assert any(not month.follows_history(f) for f in firms)


def test_a_firm_priced_at_the_market_loses_no_growth_and_the_floor_holds(
    data: GameData, balance: Balance
) -> None:
    state = start(data, balance, 1)
    month = _month(state, data, balance, 2027)
    firm = next(f for f in state.rivals.active if f.kind != "real")
    firm = replace(firm, rate_index=2.0, growth_bias=0.0, shock=0.0, demand_cents=1e10)
    at_market = update_demand(firm, 0.0, month, price_level=2.0)
    over = update_demand(firm, 0.0, month, price_level=1.0)
    assert over.demand_cents < at_market.demand_cents
    extreme = update_demand(replace(firm, rate_index=50.0), 0.0, month, price_level=1.0)
    floor = balance.rivals.growth_bias_floor
    ratio = extreme.demand_cents / at_market.demand_cents
    assert ratio > 0  # no math domain error, and demand stays positive
    pdef = month.personality(firm)
    assert abs(ratio - ((1 + floor) / (1 + pdef.growth_bias)) ** (1 / 12)) < 1e-9
