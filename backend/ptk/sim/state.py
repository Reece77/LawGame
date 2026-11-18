"""Immutable game state. Cash is never a field: it is derived from ledger balances (ADR-0003).

Pattern from tst/sim/state.py @ 02fba2aa: frozen dataclasses, tuples sorted by id, new
objects returned rather than mutated. Partner Track's own fields; later milestones add
theirs (people, matters, clients, rivals) as sorted tuples with empty defaults.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ptk.sim.calendar import YearMonth

# ADR PT-0007 section 4: a game ends when the campaign completes or the firm dissolves.
type GameOutcome = Literal["active", "campaign_complete", "dissolved"]


@dataclass(frozen=True, slots=True)
class SaveMeta:
    name: str
    master_seed: int
    scenario_id: str
    difficulty: str
    start_ym: YearMonth  # turn 0 (ADR PT-0002)
    game_state: GameOutcome = "active"
    ended_turn: int | None = None


@dataclass(frozen=True, slots=True)
class FirmState:
    id: int
    name: str
    is_player: bool
    stage: int  # spec section 3: 0 founding .. 5 global
    founded_turn: int
    home_city: str


@dataclass(frozen=True, slots=True)
class GameState:
    save_meta: SaveMeta
    turn: int  # the next turn to be played; 0 = the scenario's start month
    firms: tuple[FirmState, ...]  # sorted by id

    @property
    def ended(self) -> bool:
        return self.save_meta.game_state != "active"

    @property
    def player(self) -> FirmState:
        for firm in self.firms:
            if firm.is_player:
                return firm
        raise LookupError("no player firm")
