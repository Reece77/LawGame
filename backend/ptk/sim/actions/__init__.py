"""Immediate actions (ADR-0014), taken by the player between turns or by delegates in phase 2
(ADR-0015).

Ported from backend/tst/sim/actions/__init__.py @ 02fba2aa (Tech Startup Tycoon) as a
pattern; changed: hiring actions (PT-M1b), client and matter actions (PT-M3a), billing actions
(PT-M3b), the answer to an event (PT-M6), rival-firm actions (PT-M5) and the founder's life
(PT-M17), the press and the directory submission (PT-M16); later milestones
(PT-M3b), the answer to an event (PT-M6), rival-firm actions (PT-M5), the founder's life
(PT-M17), automation (PT-M9) and technology (PT-M14); later milestones
add theirs here.

`apply_action` is pure: it takes the state and returns the new state, any ledger entries and
log items, all belonging to `state.turn`. Randomness inside a player action uses stream
`actions` keyed by the action's `seq` within the turn (ADR-0013); a delegate passes its own
generator (stream `delegate`) through `ptk.sim.interfaces`.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from ptk.sim.automation.actions import (
    AUTOMATION_ACTION_TYPES,
    AutomationAction,
    apply_automation_action,
)
from ptk.sim.billing.actions import (
    BILLING_ACTION_TYPES,
    BillingAction,
    apply_billing_action,
)
from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import GameOverError, InvalidActionError
from ptk.sim.events.actions import EVENT_ACTION_TYPES, ChooseEvent, apply_event_action
from ptk.sim.founder.actions import FOUNDER_ACTION_TYPES, FounderAction, apply_founder_action
from ptk.sim.geo.actions import GEO_ACTION_TYPES, GeoAction, apply_geo_action
from ptk.sim.hiring.actions import (
    CloseSearch,
    HiringAction,
    Interview,
    LayOff,
    MakeOffer,
    OpenSearch,
    Outcome,
    ReferenceCheck,
    Scout,
    SetPayPolicy,
    WithdrawOffer,
    apply_hiring,
)
from ptk.sim.ledger import CASH, LedgerBalances
from ptk.sim.macro_seed import world_data
from ptk.sim.matters.actions import MATTER_ACTION_TYPES, MatterAction, apply_matter_action
from ptk.sim.mergers.actions import MERGER_ACTION_TYPES, MergerAction, apply_merger_action
from ptk.sim.org.pitches import AnswerPitch, answer_pitch
from ptk.sim.org.practices import ENTER_ACTION_TYPES, EnterPractice, enter_practice
from ptk.sim.org.seats import SEAT_ACTION_TYPES, SeatAction, apply_seat_action
from ptk.sim.partnership.actions import (
    PARTNERSHIP_ACTION_TYPES,
    PartnershipAction,
    apply_partnership_action,
)
from ptk.sim.press.actions import STANDING_ACTION_TYPES, StandingAction, apply_standing_action
from ptk.sim.risk.actions import RISK_ACTION_TYPES, RiskAction, apply_risk_action
from ptk.sim.rivals.actions import RIVAL_ACTION_TYPES, RivalAction, apply_rival_action
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState
from ptk.sim.tech.actions import TECH_ACTION_TYPES, TechAction, apply_tech_action

type Action = (
    HiringAction
    | MatterAction
    | BillingAction
    | PartnershipAction
    | ChooseEvent
    | RivalAction
    | SeatAction
    | AnswerPitch
    | FounderAction
    | StandingAction
    | AutomationAction
    | TechAction
    | GeoAction
    | EnterPractice
    | RiskAction
    | MergerAction
)

ACTION_TYPES: dict[str, type[Any]] = {
    "open_search": OpenSearch,
    "close_search": CloseSearch,
    "interview": Interview,
    "reference_check": ReferenceCheck,
    "scout": Scout,
    "make_offer": MakeOffer,
    "withdraw_offer": WithdrawOffer,
    "set_pay_policy": SetPayPolicy,
    "lay_off": LayOff,  # PT-M10
    **MATTER_ACTION_TYPES,  # PT-M3a
    **EVENT_ACTION_TYPES,  # PT-M6
    **BILLING_ACTION_TYPES,  # PT-M3b
    **RIVAL_ACTION_TYPES,  # PT-M5
    **PARTNERSHIP_ACTION_TYPES,  # PT-M4
    **SEAT_ACTION_TYPES,  # PT-M8
    "answer_pitch": AnswerPitch,  # PT-M8
    **FOUNDER_ACTION_TYPES,  # PT-M17
    **STANDING_ACTION_TYPES,  # PT-M16
    **AUTOMATION_ACTION_TYPES,  # PT-M9
    **TECH_ACTION_TYPES,  # PT-M14
    **GEO_ACTION_TYPES,  # PT-M11
    **ENTER_ACTION_TYPES,  # PT-M12
    **RISK_ACTION_TYPES,  # PT-M15
    **MERGER_ACTION_TYPES,  # PT-M13
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
    data = world_data(data, balance, state.save_meta.master_seed)  # PT-M10: the save's world
    draws = lambda: rng.stream(state.turn, "actions", seq)  # noqa: E731
    if type(action) in AUTOMATION_ACTION_TYPES.values():  # PT-M9
        auto = apply_automation_action(
            state,
            action,  # type: ignore[arg-type]
            seq=seq,
            rng=rng,
            b=balance,
            data=data,
            ledger_balances=ledger_balances,
        )
        return Outcome(auto.state, auto.entries, auto.log)
    if type(action) in TECH_ACTION_TYPES.values():  # PT-M14
        return apply_tech_action(state, action, draws, rng, data, balance)  # type: ignore[arg-type]
    if isinstance(action, EnterPractice):  # PT-M12: entering a practice
        return enter_practice(state, action, rng, balance, data)
    if type(action) in GEO_ACTION_TYPES.values():  # PT-M11: offices, admissions, trainees
        return apply_geo_action(
            state,
            action,  # type: ignore[arg-type]
            rng,
            balance,
            data,
            ledger_balances,
        )
    if type(action) in RISK_ACTION_TYPES.values():  # PT-M15: claims, cases, the policy
        cash = ledger_balances.get((state.player.id, CASH), 0)
        return apply_risk_action(state, action, balance, data, cash)  # type: ignore[arg-type]
    if type(action) in MERGER_ACTION_TYPES.values():  # PT-M13: mergers and the verein
        return apply_merger_action(state, action, rng, balance, data)  # type: ignore[arg-type]
    if isinstance(action, ChooseEvent):
        return apply_event_action(state, action, balance, data)
    if isinstance(action, AnswerPitch):  # PT-M8
        answered = answer_pitch(state, action, rng, draws, balance, data, ledger_balances)
        return Outcome(answered.state, answered.entries, answered.log)
    if type(action) in SEAT_ACTION_TYPES.values():  # PT-M8
        seated = apply_seat_action(state, action, balance, data)  # type: ignore[arg-type]
        return Outcome(seated.state, (), seated.log)
    if type(action) in STANDING_ACTION_TYPES.values():  # PT-M16: the press, the submission
        return apply_standing_action(state, action, balance, data)  # type: ignore[arg-type]
    if type(action) in FOUNDER_ACTION_TYPES.values():  # PT-M17
        return apply_founder_action(state, action, draws, balance, data)  # type: ignore[arg-type]
    if type(action) in RIVAL_ACTION_TYPES.values():
        return apply_rival_action(state, action, draws, balance, data)  # type: ignore[arg-type]
    if type(action) in PARTNERSHIP_ACTION_TYPES.values():
        return apply_partnership_action(
            state,
            action,  # type: ignore[arg-type]
            rng,
            draws,
            balance,
            data,
            ledger_balances,
        )
    if type(action) in BILLING_ACTION_TYPES.values():
        return apply_billing_action(state, action, draws, balance, data, rng)  # type: ignore[arg-type]
    if type(action) in MATTER_ACTION_TYPES.values():
        return apply_matter_action(state, action, draws, balance, data)  # type: ignore[arg-type]
    return apply_hiring(state, action, draws, balance, data, ledger_balances)  # type: ignore[arg-type]


def _lists(value: Any) -> Any:
    return [_lists(v) for v in value] if isinstance(value, tuple) else value


def action_payload(action: Action) -> dict[str, Any]:
    """The decision_log payload: the action's fields (tuples as lists)."""
    return {k: _lists(v) for k, v in asdict(action).items()}


def _tuples(value: Any) -> Any:
    """JSON lists back to (nested) tuples, as the action's fields hold them."""
    return tuple(_tuples(v) for v in value) if isinstance(value, list) else value


def action_from_payload(payload: dict[str, Any]) -> Action:
    """Rebuild an action from its decision_log payload (replay, ADR-0014 section 3)."""
    kind = payload.get("kind")
    cls = ACTION_TYPES.get(str(kind))
    if cls is None:
        raise InvalidActionError(f"unknown action kind {kind!r}")
    fields = {k: _tuples(v) for k, v in payload.items()}
    action: Action = cls(**fields)
    return action
