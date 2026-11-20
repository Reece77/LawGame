"""The player's rival-firm actions (ADR-0014): pitch for an RFP, approach a rival's key
people (or a collapsed firm's free agents), and counter a rival's approach.

Each is taken by a person of the player's firm (`actor_id`) and spends their energy
(balance `energy.cost`: pitch, approach_rival; a counter costs nothing). Randomness: the
action's own stream (`actions`, keyed by seq; ADR-0013).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Literal

import numpy as np

from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import InvalidActionError
from ptk.sim.hiring.actions import Outcome, acting_firm, spend_energy
from ptk.sim.rivals import poaching, rfp
from ptk.sim.state import GameState

type Draws = Callable[[], np.random.Generator]


@dataclass(frozen=True, slots=True)
class PitchRfp:
    """Pitch for an open RFP the firm is invited to (spec 7.2): a team (the lead first) and
    claims (rfp.CLAIMS); a claim the firm cannot substantiate counts against it."""

    actor_id: int
    rfp_id: int
    team: tuple[int, ...]
    claims: tuple[str, ...] = ()
    kind: Literal["pitch_rfp"] = "pitch_rfp"


@dataclass(frozen=True, slots=True)
class ApproachRival:
    """Approach 2-4 of a rival's key people (one practice, or its best): they become the
    firm's candidates (TST 15.6's poach search)."""

    actor_id: int
    firm_id: int
    practice: str | None = None
    kind: Literal["approach_rival"] = "approach_rival"


@dataclass(frozen=True, slots=True)
class ApproachFreeAgents:
    """Approach the people a collapsed or failed rival left looking for work."""

    actor_id: int
    kind: Literal["approach_free_agents"] = "approach_free_agents"


@dataclass(frozen=True, slots=True)
class CounterApproach:
    """Match a rival's offer to one of the firm's people (spec 8.7's counter-offer)."""

    actor_id: int
    approach_id: int
    kind: Literal["counter_approach"] = "counter_approach"


type RivalAction = PitchRfp | ApproachRival | ApproachFreeAgents | CounterApproach

RIVAL_ACTION_TYPES: dict[str, type[RivalAction]] = {
    "pitch_rfp": PitchRfp,
    "approach_rival": ApproachRival,
    "approach_free_agents": ApproachFreeAgents,
    "counter_approach": CounterApproach,
}


def _player(state: GameState, actor_id: int) -> int:
    firm = acting_firm(state, actor_id)
    if firm != state.player.id:
        raise InvalidActionError("only the player's firm acts here")
    return firm


def apply_rival_action(
    state: GameState, action: RivalAction, draws: Draws, balance: Balance, data: GameData
) -> Outcome:
    _player(state, action.actor_id)
    match action:
        case PitchRfp():
            state = rfp.pitch(state, action.rfp_id, action.team, action.claims, balance)
            return Outcome(spend_energy(state, action.actor_id, "pitch", balance))
        case ApproachRival():
            if action.practice is not None and action.practice not in data.practice_keys:
                raise InvalidActionError(f"unknown practice {action.practice!r}")
            state, _ = poaching.approach_rival(
                state, action.firm_id, action.practice, action.actor_id, draws(), data, balance
            )
            return Outcome(spend_energy(state, action.actor_id, "approach_rival", balance))
        case ApproachFreeAgents():
            state, _ = poaching.approach_free_agents(state, action.actor_id, draws(), data, balance)
            return Outcome(spend_energy(state, action.actor_id, "approach_rival", balance))
        case CounterApproach():
            approach = next(
                (a for a in state.rivals.approaches if a.id == action.approach_id), None
            )
            if approach is None or state.employer_of(approach.person_id) != state.player.id:
                raise InvalidActionError(f"no approach {action.approach_id} to the firm's people")
            return Outcome(poaching.counter(state, action.approach_id, balance))
    raise InvalidActionError(f"unknown rival action {action!r}")


_UNUSED = replace
