"""Immediate actions (ADR-0014), taken by the player between turns or by delegates in phase 2
(ADR-0015).

Ported from backend/tst/sim/actions/__init__.py @ 02fba2aa (Tech Startup Tycoon) as a
pattern; changed: hiring actions (PT-M1b), client and matter actions (PT-M3a), billing actions
(PT-M3b), the answer to an event (PT-M6) and rival-firm actions (PT-M5); later milestones
add theirs here.

`apply_action` is pure: it takes the state and returns the new state, any ledger entries and
log items, all belonging to `state.turn`. Randomness inside a player action uses stream
`actions` keyed by the action's `seq` within the turn (ADR-0013); a delegate passes its own
generator (stream `delegate`) through `ptk.sim.interfaces`.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from ptk.sim.billing.actions import (
    BILLING_ACTION_TYPES,
    BillingAction,
    apply_billing_action,
)
from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import GameOverError, InvalidActionError
from ptk.sim.events.actions import EVENT_ACTION_TYPES, ChooseEvent, apply_event_action
from ptk.sim.hiring.actions import (
    CloseSearch,
    HiringAction,
    Interview,
    MakeOffer,
    OpenSearch,
    Outcome,
    ReferenceCheck,
    Scout,
    SetPayPolicy,
    WithdrawOffer,
    apply_hiring,
)
from ptk.sim.ledger import LedgerBalances
from ptk.sim.matters.actions import MATTER_ACTION_TYPES, MatterAction, apply_matter_action
from ptk.sim.rivals.actions import RIVAL_ACTION_TYPES, RivalAction, apply_rival_action
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState

type Action = HiringAction | MatterAction | BillingAction | ChooseEvent | RivalAction

ACTION_TYPES: dict[str, type[Any]] = {
    "open_search": OpenSearch,
    "close_search": CloseSearch,
    "interview": Interview,
    "reference_check": ReferenceCheck,
    "scout": Scout,
    "make_offer": MakeOffer,
    "withdraw_offer": WithdrawOffer,
    "set_pay_policy": SetPayPolicy,
    **MATTER_ACTION_TYPES,  # PT-M3a
    **EVENT_ACTION_TYPES,  # PT-M6
    **BILLING_ACTION_TYPES,  # PT-M3b
    **RIVAL_ACTION_TYPES,  # PT-M5
}


def apply_action(
    state: GameState,
    action: Action,
    *,
    seq: int,
    rng: RngFactory,
    balance: Balance,
    data: GameData,
    ledger_balances: LedgerBalances,
) -> Outcome:
    """Apply one player action at once. Raises a `SimError` and changes nothing if a rule
    forbids it."""
    if state.ended:
        raise GameOverError("the game is over")
    draws = lambda: rng.stream(state.turn, "actions", seq)  # noqa: E731
    if isinstance(action, ChooseEvent):
        return apply_event_action(state, action, balance, data)
    if type(action) in RIVAL_ACTION_TYPES.values():
        return apply_rival_action(state, action, draws, balance, data)  # type: ignore[arg-type]
    if type(action) in BILLING_ACTION_TYPES.values():
        return apply_billing_action(state, action, draws, balance)  # type: ignore[arg-type]
    if type(action) in MATTER_ACTION_TYPES.values():
        return apply_matter_action(state, action, draws, balance, data)  # type: ignore[arg-type]
    return apply_hiring(state, action, draws, balance, data, ledger_balances)  # type: ignore[arg-type]


def action_payload(action: Action) -> dict[str, Any]:
    """The decision_log payload: the action's fields (tuples as lists)."""
    return {k: list(v) if isinstance(v, tuple) else v for k, v in asdict(action).items()}


def action_from_payload(payload: dict[str, Any]) -> Action:
    """Rebuild an action from its decision_log payload (replay, ADR-0014 section 3)."""
    kind = payload.get("kind")
    cls = ACTION_TYPES.get(str(kind))
    if cls is None:
        raise InvalidActionError(f"unknown action kind {kind!r}")
    fields = {k: tuple(v) if isinstance(v, list) else v for k, v in payload.items()}
    action: Action = cls(**fields)
    return action
