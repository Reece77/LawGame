"""PT-M7 sub-task 1: the macro and legal indices 2005-2015 and history's client failures."""

from __future__ import annotations

from dataclasses import replace

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from ptk.sim.calendar import ym_to_turn
from ptk.sim.data_models import Balance, GameData
from ptk.sim.macro import (
    bankrupt_by,
    collections_stress,
    demand_factor,
    failure_turn,
    lateral_heat,
    level,
    market_rise,
    wallet_factors,
)
from ptk.sim.matters.failures import fail_clients
from ptk.sim.matters.intake import with_relationship
from ptk.sim.matters.market import monthly_demand, wallets
from ptk.sim.matters.models import Relationship
from ptk.sim.matters.rates import market_index
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState
from tests.matters_support import game, play

START = (2005, 1)


def _turn(year: int, month: int) -> int:
    return ym_to_turn(year, month, START)


def _client(state, name):  # type: ignore[no-untyped-def]
    return next(c for c in state.market.clients if c.real and c.name == name)


def test_indices_are_one_in_2005_interpolate_and_hold(data: GameData) -> None:
    m = data.macro
    assert level(m, "ma", (2005, 1)) == 1.0
    a, b = level(m, "ma", (2006, 7)), level(m, "ma", (2007, 7))
    assert min(a, b) <= level(m, "ma", (2007, 1)) <= max(a, b)
    assert level(m, "ma", (2030, 6)) == level(m, "ma", (2015, 7))  # after the last point


def test_the_crash_cuts_transactions_and_feeds_restructuring(
    data: GameData, balance: Balance
) -> None:
    def factor(key: str, year: int) -> float:
        return demand_factor(data.practice(key), (year, 7), data, balance)

    assert factor("corporate_ma", 2009) < 0.8 * factor("corporate_ma", 2007)
    assert factor("private_equity", 2009) < 0.5 * factor("private_equity", 2007)
    assert factor("restructuring", 2009) > 1.5 * factor("restructuring", 2007)
    assert factor("real_estate", 2009) < factor("real_estate", 2007)
    assert all(factor(p.key, 2009) >= balance.macro.demand_floor * 0.99 for p in data.practices)


def test_demand_follows_the_index(data: GameData, balance: Balance) -> None:
    state = game(data, balance)
    rng = RngFactory(3)
    flat = balance.model_copy(
        update={"macro": balance.macro.model_copy(update={"beta_scale": 0.0})}
    )
    t = _turn(2009, 4)
    corp = data.practice_keys.index("corporate_ma")
    driven, base = (
        monthly_demand(rng, t, state, data, balance),
        monthly_demand(rng, t, state, data, flat),
    )
    assert driven[corp] < base[corp]  # same seeded noise, the index applied


def test_collections_stress_and_lateral_heat(data: GameData, balance: Balance) -> None:
    assert collections_stress(0, START, data, balance) == 1.0
    assert collections_stress(_turn(2009, 4), START, data, balance) > 1.1
    assert lateral_heat(_turn(2009, 6), START, data, balance) < 0.8
    assert lateral_heat(_turn(2007, 7), START, data, balance) > 1.0


def test_market_rates_follow_history_then_free_play(data: GameData, balance: Balance) -> None:
    assert market_rise(2006, data, balance) == data.macro.rate_rise[2006]
    assert market_rise(2020, data, balance) == balance.rivals.rate_inflation
    index = market_index(_turn(2010, 2), START, data, balance)
    expected = 1.0
    for year in range(2006, 2011):
        expected *= 1 + round(data.macro.rate_rise[year] * 10_000) / 10_000
    assert index == pytest.approx(expected)


def test_history_fails_lehman_and_rescues_bear(data: GameData, balance: Balance) -> None:
    state = game(data, balance)
    lehman, bear = _client(state, "Lehman Brothers"), _client(state, "Bear Stearns")
    filed = failure_turn(lehman, data, START)
    assert filed == _turn(2008, 9)
    assert not bankrupt_by(lehman, filed - 1, data, START) and bankrupt_by(
        lehman, filed, data, START
    )
    assert not bankrupt_by(bear, _turn(2010, 1), data, START)  # a rescue pays its bills
    estate = wallet_factors(lehman, filed, data, balance, START)
    assert estate is not None
    for p, f in zip(data.practices, estate, strict=True):
        assert f == (balance.macro.estate_mult if p.key == "restructuring" else 0.0)
    gone = wallet_factors(lehman, filed + balance.macro.estate_months, data, balance, START)
    assert gone is not None and not any(gone)
    rescued = _turn(2008, 3)
    assert wallet_factors(bear, rescued, data, balance, START) is None
    late = wallet_factors(bear, rescued + balance.macro.rescue_months, data, balance, START)
    assert late is not None and not any(late)
    generated = next(c for c in state.market.clients if not c.real)
    assert failure_turn(generated, data, START) is None


@settings(max_examples=25, deadline=None)
@given(turn=st.integers(min_value=0, max_value=200))
def test_wallets_always_sum_to_the_market(turn: int, data: GameData, balance: Balance) -> None:
    """Property: failures move shares between clients, never out of the market."""
    state = _STATE.get("s") or _STATE.setdefault("s", game(data, balance))
    shares = wallets(state.market.clients, data, balance, turn, START)
    for i in range(len(data.practices)):
        assert sum(s[i] for s in shares.shares.values()) == pytest.approx(1.0)


_STATE: dict[str, GameState] = {}


def test_a_failure_stops_the_clients_work_and_loses_its_bills(
    data: GameData, balance: Balance
) -> None:
    state = game(data, balance, seed=2)
    lehman = _client(state, "Lehman Brothers")
    partner = next(p.id for p in state.people if p.is_founder)
    rel = Relationship(
        client_id=lehman.id,
        firm_id=state.player.id,
        score=90.0,
        partner_id=partner,
        practices=("corporate_ma", "banking_finance", "commercial_litigation"),
        since_turn=0,
    )
    state = replace(state, market=with_relationship(state.market, rel))
    state, results = play(state, data, balance, _turn(2008, 11), seed=2)
    failed = [i for r in results for i in r.log_items if i.kind == "client_failed"]
    assert len(failed) == 1 and failed[0].turn == _turn(2008, 9)
    assert not [
        m
        for m in state.market.matters
        if m.client_id == lehman.id and m.is_open and m.practice != "restructuring"
    ]
    bills = [b for b in state.billing.bills if b.client_id == lehman.id]
    assert bills and not [b for b in bills if b.is_open]
    assert any(b.status == "written_off" for b in bills)
    assert not any(
        b.issued_turn > _turn(2008, 10) for b in bills
    )  # the estate instructs no more corporate work


def test_the_estate_instructs_a_firm_with_restructuring_lawyers(
    data: GameData, balance: Balance
) -> None:
    state = game(data, balance)
    lehman = _client(state, "Lehman Brothers")
    founder = next(p for p in state.people if p.is_founder)
    rel = Relationship(lehman.id, state.player.id, 60.0, founder.id, ("corporate_ma",), 0)
    state = replace(state, market=with_relationship(state.market, rel), turn=_turn(2008, 9))
    plain, _ = fail_clients(state, data, balance)
    assert plain.market.relationship(lehman.id, state.player.id).practices == ("corporate_ma",)  # type: ignore[union-attr]
    restructurer = replace(founder, role=data.practice_role("restructuring").key)
    state = replace(
        state, people=tuple(restructurer if p.id == founder.id else p for p in state.people)
    )
    hired, logs = fail_clients(state, data, balance)
    got = hired.market.relationship(lehman.id, state.player.id)
    assert got is not None and got.practices == ("corporate_ma", "restructuring")
    assert [i.kind for i in logs] == ["client_failed"]
