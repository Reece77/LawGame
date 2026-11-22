"""PT-M16's place in the turn (spec 12): phase 10, after the partnership's stage checks and the
founder's month. Reputation moves; then the rankings publish (their places and bands move
reputation, and a ranking day is a press moment); then the press's month."""

from __future__ import annotations

from ptk.sim.data_models import Balance, GameData
from ptk.sim.log import LogItem
from ptk.sim.press import phase as press
from ptk.sim.rankings import phase as rankings
from ptk.sim.reputation import phase as reputation
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState


def month(
    state: GameState, start: GameState, rng: RngFactory, balance: Balance, data: GameData
) -> tuple[GameState, tuple[LogItem, ...]]:
    if state.ended:
        return state, ()
    state = reputation.month(state, data, balance)
    state, ranked, ranking_days = rankings.month(state, data, balance)
    state, pressed = press.month(state, start, rng, balance, data, ranking_days)
    return state, (*ranked, *pressed)
