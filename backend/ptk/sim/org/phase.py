"""The org's parts of the turn (PT-M2): clearing one-off morale changes after phase 8.

Delegated hiring (phase 2) is `ptk.sim.org.delegates`; the mentoring multiplier on growth
(phase 8) is `ptk.sim.org.rules.growth_multipliers`.
"""

from __future__ import annotations

from dataclasses import replace

from ptk.sim.state import GameState


def clear_nudges(state: GameState) -> GameState:
    """One-off morale changes live until phase 8 of their turn (interfaces.py); morale
    (PT-M1b) has read them by then."""
    if not state.org.nudges:
        return state
    return replace(state, org=replace(state.org, nudges=()))
