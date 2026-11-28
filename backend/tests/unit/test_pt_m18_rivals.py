"""PT-M18 (the product manager's decision, 2026-11-27): free play reads a rival's rate index
against the market's price level in its own terms, and the growth bias has a floor; T16: after
the pin, history's firms carry history's own collapse hazard.

A rival that followed history's path kept its 2005 capacity per lawyer while pinned, so its
index at the pin's end carries the market's rate rises and its own premium. Its level is the
index its path needed in December 2025 (its capacity rises with the market afterwards); every
other firm's is 1 (unchanged before 2026). Before this, every seed's big rivals lost about
half their demand a year from 2026 (against 1), then the premium US firms shrank (against
their region's mean); seed 36's run stopped when a boutique's bias passed -1.
"""

from __future__ import annotations

from dataclasses import replace

from simcore.kernel.calendar import ym_to_turn

from ptk.sim.data_models import Balance, GameData
from ptk.sim.rivals.economy import Month, price_level, reference_index, update_demand
from ptk.sim.rivals.history import dated_collapse_turn, hazard
from ptk.sim.rivals.mergers import free_targets
from ptk.sim.rivals.path import time_of
from tests.rivals_support import start, turn_of


def _month(state, data: GameData, balance: Balance, year: int) -> Month:  # type: ignore[no-untyped-def]
    return Month(
        turn=turn_of(state, year, 6), start=state.save_meta.start_ym, data=data, balance=balance
    )


def test_history_followers_are_read_against_their_own_index_at_the_pins_end(
    data: GameData, balance: Balance
) -> None:
    state = start(data, balance, 1)
    m2025, m2028 = (_month(state, data, balance, y) for y in (2025, 2028))
    rb = balance.rivals
    followers = [f for f in state.rivals.active if m2028.follows_history(f)]
    others = [f for f in state.rivals.active if not m2028.follows_history(f)]
    assert followers and others
    for f in others:
        assert price_level(f, m2028) == 1.0
    end = ym_to_turn(rb.pin.end_year, 12, state.save_meta.start_ym)
    t_end = time_of(end, state.save_meta.start_ym)
    for f in followers:
        ref = reference_index(f, m2025)
        assert ref is not None and ref > 0
        rpl = m2025.path_revenue(f, t_end) / m2025.path_lawyers(f, t_end)  # type: ignore[operator]
        assert abs(ref - rpl / (f.rpl_cap_cents * m2025.personality(f).utilisation)) < 1e-9
        # three free-play Januaries later its capacity is 3% a year higher: the same level
        raised = replace(f, rpl_cap_cents=f.rpl_cap_cents * (1 + rb.rate_inflation) ** 3)
        assert abs(price_level(raised, m2028) - ref) < 1e-9
    # a premium firm (its path's revenue per lawyer above its peers') is not read as overpriced
    top = max(followers, key=lambda f: reference_index(f, m2025) or 0.0)
    at_ref = replace(top, rate_index=reference_index(top, m2025) or 1.0)
    grown = update_demand(at_ref, 0.0, m2028, price_level(at_ref, m2028))
    assert grown.demand_cents >= at_ref.demand_cents * 0.999


def test_history_firms_carry_a_hazard_only_after_the_pin(data: GameData, balance: Balance) -> None:
    state = start(data, balance, 1)
    m2020, m2028 = (_month(state, data, balance, y) for y in (2020, 2028))
    cb = balance.rivals.collapse
    for f in state.rivals.active:
        if not m2028.follows_history(f) or f.departures:
            continue
        if dated_collapse_turn(f, m2020) is None:
            assert hazard(f, state.rivals, m2020) == (0.0, False)
        p, losing = hazard(f, state.rivals, m2028)
        assert not losing
        assert abs(p - cb.free_play_bp * m2028.personality(f).fragility / 10_000) < 1e-12


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


def test_a_free_play_merger_takes_only_a_smaller_firm_by_fees_too(
    data: GameData, balance: Balance
) -> None:
    """T15: a buyer takes at most half its lawyers and (PT-M18) half its last year's fees, so
    no deal makes a firm more than 1.5 times its size (seed 6's DLA Piper went from $4.1bn
    to $10.3bn in 2032 by taking a firm with half its lawyers and 1.5 times its fees)."""
    state = start(data, balance, 1)
    firms = sorted(state.rivals.active, key=lambda f: -f.lawyers)
    buyer = replace(firms[0], revenue=(1_000_000,) * 12)
    small = replace(firms[-1], revenue=(400_000,) * 12)
    rich = replace(firms[-2], revenue=(600_000,) * 12)
    ratio = balance.mergers.rival.free_max_ratio
    assert rich.lawyers <= ratio * buyer.lawyers
    picked = free_targets(buyer, [buyer, small, rich], frozenset(), ratio)
    assert picked == [small]
    assert free_targets(buyer, [buyer, small], frozenset({small.key}), ratio) == []
