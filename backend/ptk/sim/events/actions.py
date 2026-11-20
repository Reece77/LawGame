"""The player's answer to an event (ADR-0014): an immediate action, logged in decision_log.

Ported from the choose_event action of backend/tst/sim/actions/events.py @ 02fba2aa (Tech
Startup Tycoon); changed: Partner Track's effects (ptk.sim.events.effects)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ptk.sim.data_models import Balance, GameData
from ptk.sim.events.effects import choose
from ptk.sim.hiring.actions import Outcome
from ptk.sim.state import GameState


@dataclass(frozen=True, slots=True)
class ChooseEvent:
    event_id: int
    choice: str  # "A", "B" or "C"
    kind: Literal["choose_event"] = "choose_event"


EVENT_ACTION_TYPES: dict[str, type[ChooseEvent]] = {"choose_event": ChooseEvent}


def apply_event_action(
    state: GameState, action: ChooseEvent, balance: Balance, data: GameData
) -> Outcome:
    new, entries, logs = choose(state, action.event_id, action.choice, balance, data)
    return Outcome(new, entries, logs)
