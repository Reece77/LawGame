"""PT-M7a sub-task 5: yearly rate rises. Each January the firm's card rises by its policy
(default the market's), the appeal's price term is 0 for the default firm and negative above
the market, and hours are valued on the firm's card."""

from __future__ import annotations

from dataclasses import replace

import pytest

from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import MatterActionError
from ptk.sim.matters.actions import SetRatePolicy
from ptk.sim.matters.market import player_appeal
from ptk.sim.matters.rates import market_index, market_rise_bp, price_term, yearly_rise
from ptk.sim.state import with_firm
from tests.hiring_helpers import start
from tests.matters_support import game, play


def test_january_raises_the_card_by_the_market_by_default(data: GameData, balance: Balance) -> None:
    state = game(data, balance)
    assert state.player.rate_index == 1.0
    state, logs = yearly_rise(state, data, balance)  # turn 0: never
    assert state.player.rate_index == 1.0 and not logs
    state, _ = play(state, data, balance, 13)  # through January 2006 (turn 12)
    rise = market_rise_bp(2006, data, balance) / 10000
    assert state.player.rate_index == pytest.approx(1.0 + rise)
    assert market_index(state.turn, state.save_meta.start_ym, data, balance) == pytest.approx(
        1 + rise
    )
    assert price_term(state, state.player.id, data, balance) == pytest.approx(0.0)


def test_a_player_policy_and_the_price_term(data: GameData, balance: Balance) -> None:
    g = start(data, balance)
    g.act(SetRatePolicy(g.founder_id, 800))
    assert g.state.player.rate_rise_bp == 800
    with pytest.raises(MatterActionError):
        g.act(SetRatePolicy(g.founder_id, balance.rates.rise_max_bp + 1))
    g.advance(13)
    assert g.state.player.rate_index == pytest.approx(1.08)
    term = price_term(g.state, g.state.player.id, data, balance)
    assert term < 0
    client = g.state.market.client(g.state.market.relationships[0].client_id)
    rel = g.state.market.relationships[0]
    assert player_appeal(client, rel, 0.5, False, balance, term) < player_appeal(
        client, rel, 0.5, False, balance, 0.0
    )
    g.act(SetRatePolicy(g.founder_id, None))  # back to the market's
    assert g.state.player.rate_rise_bp is None


def test_hours_are_valued_on_the_firms_card(data: GameData, balance: Balance) -> None:
    state = game(data, balance)
    state = with_firm(state, replace(state.player, rate_index=1.5))
    state, _ = play(state, data, balance, 1)
    base, _ = play(game(data, balance), data, balance, 1)
    v1 = sum(r.value_cents for r in state.market.hours)
    v0 = sum(r.value_cents for r in base.market.hours)
    t1 = sum(r.tenths for r in state.market.hours if r.value_cents)
    t0 = sum(r.tenths for r in base.market.hours if r.value_cents)
    assert v1 / t1 == pytest.approx(1.5 * v0 / t0, rel=0.05)
