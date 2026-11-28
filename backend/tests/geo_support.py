"""PT-M11 test helpers: a game with an office opened in it."""

from __future__ import annotations

from ptk.sim.actions import apply_action
from ptk.sim.data_models import Balance, GameData
from ptk.sim.geo.actions import OpenOffice
from ptk.sim.hiring.actions import Outcome
from ptk.sim.state import GameState
from ptk.sim.streams import RngFactory
from tests.matters_support import game


def open_london(
    state: GameState,
    data: GameData,
    balance: Balance,
    *,
    seed: int = 1,
    how: str = "team_lift",
    partners: int = 2,
    associates: int = 4,
    seats: int = 10,
    rival: str = "clifford_chance",
    city: str = "london",
) -> Outcome:
    founder = state.founder_of(state.player.id)
    assert founder is not None
    partner = None
    if how == "organic":
        partner = next(
            p.id
            for p in state.people
            if p.id in state.staff_ids(state.player.id)
            and p.level == "equity_partner"
            and p.id != founder
        )
    return apply_action(
        state,
        OpenOffice(
            actor_id=founder,
            city=city,
            seats=seats,
            how=how,  # type: ignore[arg-type]
            practice="corporate_ma",
            rival_key=rival if how == "team_lift" else None,
            partners=partners,
            associates=associates,
            partner_id=partner,
        ),
        seq=1,
        rng=RngFactory(seed),
        balance=balance,
        data=data,
        ledger_balances={},
    )


def london_game(data: GameData, balance: Balance, seed: int = 1, **kw: object) -> Outcome:
    return open_london(game(data, balance, seed), data, balance, seed=seed, **kw)  # type: ignore[arg-type]
