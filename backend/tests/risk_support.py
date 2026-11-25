"""Helpers for PT-M15 tests: a firm with open matters, and claims built directly."""

from __future__ import annotations

from dataclasses import replace
from functools import cache

from ptk.loader import load_balance, load_game_data
from ptk.sim.data_models import Balance, GameData
from ptk.sim.matters.models import Matter
from ptk.sim.risk.models import EMPTY_RISK, Claim, Policy, with_claim, with_policy
from ptk.sim.state import GameState
from tests.conftest import DATA_DIR
from tests.matters_support import game, play


@cache
def loaded() -> tuple[GameData, Balance]:
    return load_game_data(DATA_DIR), load_balance(DATA_DIR)


@cache
def busy_firm(seed: int = 1, turns: int = 18) -> GameState:
    """The spin-out played `turns` months: a firm with open named matters."""
    data, balance = loaded()
    state, _ = play(game(data, balance, seed), data, balance, turns, seed)
    return state


def player_matters(state: GameState) -> list[Matter]:
    return [m for m in state.market.matters if m.firm_id == state.player.id]


def escaped(state: GameState, matter_ids: dict[int, int]) -> GameState:
    """`state` with `n` more escaped errors on each matter id (the month's work, faked)."""
    market = state.market
    matters = tuple(
        replace(m, errors_escaped=m.errors_escaped + matter_ids.get(m.id, 0))
        for m in market.matters
    )
    return replace(state, market=replace(market, matters=matters))


def a_claim(
    state: GameState,
    *,
    merit: float = 0.5,
    size: int = 100_000_000,
    turn: int | None = None,
    cid: int = 1,
) -> Claim:
    m = player_matters(state)[0]
    t = state.turn if turn is None else turn
    return Claim(
        id=cid,
        firm_id=state.player.id,
        matter_id=m.id,
        client_id=m.client_id,
        practice=m.practice,
        source="error",
        created_turn=t,
        surfaces_turn=t,
        merit=merit,
        size_cents=size,
        demand_cents=size * 2,
    )


def with_a_policy(state: GameState, limit: int, deductible: int) -> GameState:
    """`state` with no risk history but one policy in force."""
    p = Policy(
        id=900,
        firm_id=state.player.id,
        insurer="national_carrier",
        start_turn=state.turn - 1,
        end_turn=state.turn + 240,
        limit_cents=limit,
        deductible_cents=deductible,
        premium_cents=1_200_000,
        mod=1.0,
        rate_bp=120,
        exposure_cents=100_000_000,
        lawyers=10,
    )
    return replace(
        state, risk=with_policy(replace(EMPTY_RISK, next_id=1000), p)
    )  # only this policy


def with_a_claim(state: GameState, claim: Claim) -> GameState:
    return replace(state, risk=with_claim(state.risk, claim))
