"""The org's parts of the turn (PT-M2): applying and clearing one-off morale after phase 8.

Delegated hiring (phase 2) is `ptk.sim.org.delegates`; the mentoring multiplier on growth
(phase 8) is `ptk.sim.org.rules.growth_multipliers`.
"""

from __future__ import annotations

from dataclasses import replace

from simcore.kernel.scale import clamp_morale

from ptk.sim.state import GameState, with_person_states


def clear_nudges(state: GameState) -> GameState:
    """Add this turn's one-off morale changes (TST 13.7, 13.8) to each person's current morale,
    after PT-M1b's monthly morale step, then clear them (interfaces.org_morale_changes).
    People whose morale is not tracked (founding partners, leavers) are skipped."""
    if not state.org.nudges:
        return state
    totals: dict[int, float] = {}
    for n in state.org.nudges:
        totals[n.person_id] = totals.get(n.person_id, 0.0) + n.points
    bumped = []
    for pid in sorted(totals):
        ps = state.person_state(pid)
        if ps.morale is not None and state.employer_of(pid) is not None:
            bumped.append(replace(ps, morale=clamp_morale(ps.morale + totals[pid])))
    state = with_person_states(state, bumped)
    return replace(state, org=replace(state.org, nudges=()))
