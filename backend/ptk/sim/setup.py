"""Game creation: the initial state and the turn-0 capital entry (ADR PT-0003)."""

from __future__ import annotations

from dataclasses import dataclass

from ptk.sim.data_models import GameData
from ptk.sim.errors import UnknownDifficultyError, UnknownScenarioError
from ptk.sim.ledger import CASH, PARTNERS_CAPITAL, LedgerEntry
from ptk.sim.money import pct_of
from ptk.sim.state import FirmState, GameState, SaveMeta

PLAYER_FIRM_ID = 1


@dataclass(frozen=True, slots=True)
class NewGame:
    state: GameState
    ledger_entries: tuple[LedgerEntry, ...]


def new_game(
    *,
    name: str,
    firm_name: str,
    master_seed: int,
    scenario_id: str,
    difficulty: str,
    data: GameData,
) -> NewGame:
    scenario = data.scenario(scenario_id)
    if scenario is None or not scenario.available:
        raise UnknownScenarioError(f"unknown or unavailable scenario {scenario_id!r}")
    level = data.difficulty(difficulty)
    if level is None:
        raise UnknownDifficultyError(f"unknown difficulty {difficulty!r}")
    meta = SaveMeta(
        name=name,
        master_seed=master_seed,
        scenario_id=scenario.id,
        difficulty=level.id,
        start_ym=scenario.start_ym,
    )
    firm = FirmState(
        id=PLAYER_FIRM_ID,
        name=firm_name,
        is_player=True,
        stage=0,
        founded_turn=0,
        home_city=scenario.home_city,
    )
    state = GameState(save_meta=meta, turn=0, firms=(firm,))
    capital = pct_of(scenario.partners_capital_cents, level.capital_mult_bp)
    entries: tuple[LedgerEntry, ...] = ()
    if capital:
        entries = (
            LedgerEntry.transfer(
                turn=0,
                firm_id=firm.id,
                memo="Founding partners' capital",
                debit=CASH,
                credit=PARTNERS_CAPITAL,
                amount=capital,
            ),
        )
    return NewGame(state=state, ledger_entries=entries)
