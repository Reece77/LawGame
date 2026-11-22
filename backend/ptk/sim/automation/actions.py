"""The player's automation actions (spec 9.4; TST formulas.md 40.1-40.2, 40.8; ADR-0014).

Ported from backend/tst/sim/automation/actions.py @ 80a38079 (Tech Startup Tycoon); changed:
Partner Track's areas and owners; the managing partner gives and takes back areas
(`automation.change_energy`); proposals are automation's own and approving one runs its action
as the MP through `ptk.sim.actions.apply_action` (the player's own stream), so the MP's energy
is spent as if they had acted. No subsidiaries.

- `GiveArea`: an area (a practice group's staffing: its slot) to an eligible owner with a
  per-decision and a monthly limit (defaults: `default_limit_bp` of cash, and
  `monthly_limit_mult` x that), a priority and guardrails. Giving a seat's area also gives the
  seat its PT-M8 authority (TST 40.12's one setting); its monthly rule then runs once, as the
  area.
- `TakeOverArea`: the player runs it again ("Take over"); the seat's authority is withdrawn; a
  high-ego owner loses `take_back_morale` once when it is within `take_back_months`.
- `SetAreaSettings`: limits, priority, the routine-events switch, guardrails (free).
- `AnswerProposal`: approve (run the action as the MP) or decline a pending proposal.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from typing import Any, Literal

from ptk.sim.automation import owners
from ptk.sim.automation.models import AreaOwner, AutoProposal
from ptk.sim.automation.run import with_automation
from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import (
    AutomationError,
    InsufficientEnergyError,
    NotManagingPartnerError,
    SimError,
    UnknownAreaError,
    UnknownProposalError,
)
from ptk.sim.ledger import CASH, LedgerBalances, LedgerEntry
from ptk.sim.log import LogItem, inbox_item
from ptk.sim.org.models import MoraleNudge
from ptk.sim.org.seat_models import SeatAuthority
from ptk.sim.org.seats import managing_partner, with_authority
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState, with_person_states


@dataclass(frozen=True, slots=True)
class GiveArea:
    actor_id: int
    area: str
    person_id: int
    slot: int = 0
    limit_cents: int | None = None  # None: the default (TST 40.2)
    monthly_cents: int | None = None  # None: monthly_limit_mult x the limit
    priority: int | None = None  # None: after the owner's other areas
    answer_events: bool = True
    guardrails: tuple[tuple[str, int], ...] = ()
    kind: Literal["give_area"] = "give_area"


@dataclass(frozen=True, slots=True)
class TakeOverArea:
    actor_id: int
    area: str
    slot: int = 0
    kind: Literal["take_over_area"] = "take_over_area"


@dataclass(frozen=True, slots=True)
class SetAreaSettings:
    actor_id: int
    area: str
    slot: int = 0
    limit_cents: int | None = None  # None: unchanged
    monthly_cents: int | None = None
    priority: int | None = None
    answer_events: bool | None = None
    guardrails: tuple[tuple[str, int], ...] | None = None
    kind: Literal["set_area_settings"] = "set_area_settings"


@dataclass(frozen=True, slots=True)
class AnswerProposal:
    actor_id: int
    proposal_id: int
    approve: bool
    kind: Literal["answer_proposal"] = "answer_proposal"


type AutomationAction = GiveArea | TakeOverArea | SetAreaSettings | AnswerProposal

AUTOMATION_ACTION_TYPES: dict[str, type[Any]] = {
    "give_area": GiveArea,
    "take_over_area": TakeOverArea,
    "set_area_settings": SetAreaSettings,
    "answer_proposal": AnswerProposal,
}


@dataclass(frozen=True, slots=True)
class AutoOutcome:
    state: GameState
    entries: tuple[LedgerEntry, ...] = ()
    log: tuple[LogItem, ...] = ()


def _firm(state: GameState, actor_id: int) -> int:
    firm = state.player.id
    if managing_partner(state, firm) != actor_id:
        raise NotManagingPartnerError("only the managing partner directs automation")
    return firm


def _spend(state: GameState, actor_id: int, b: Balance) -> GameState:
    cost = b.automation.change_energy
    ps = state.person_state(actor_id)
    if ps.energy is None or cost == 0:
        return state
    if ps.energy < cost:
        raise InsufficientEnergyError(f"that needs {cost} energy; {ps.energy} left this month")
    return with_person_states(state, [replace(ps, energy=ps.energy - cost)])


def _check_area(area: str, b: Balance) -> None:
    if area not in b.automation.areas:
        raise UnknownAreaError(f"no area {area!r}")


def _check_rails(
    area: str, rails: tuple[tuple[str, int], ...], b: Balance, data: GameData
) -> tuple[tuple[str, int], ...]:
    known = {k: (lo, hi) for k, _l, _d, lo, hi in owners.guardrails(area, b, data)}
    for key, value in rails:
        if key not in known:
            raise AutomationError(f"area {area} has no guardrail {key!r}")
        lo, hi = known[key]
        if not lo <= value <= hi:
            raise AutomationError(f"{key} must be {lo} to {hi}")
    return tuple(sorted(dict(rails).items()))


def _check_limits(limit: int, monthly: int) -> None:
    if limit < 0 or monthly < 0:
        raise AutomationError("limits are never negative")
    if monthly < limit:
        raise AutomationError("the monthly limit is at least the per-decision limit")


def _sorted(state: GameState, items: list[AreaOwner], b: Balance) -> tuple[AreaOwner, ...]:
    return tuple(sorted(items, key=lambda o: (o.firm_id, owners.area_index(b, o.area), o.slot)))


def _seat_authority(state: GameState, o: AreaOwner, enabled: bool, b: Balance) -> GameState:
    a = owners.area_def(b, o.area)
    if not a.seat_rule or a.seat is None:
        return state
    current = state.leadership.authority(o.firm_id, a.seat, o.slot)
    rails = current.guardrails if current is not None else ()
    return with_authority(state, SeatAuthority(o.firm_id, a.seat, o.slot, enabled, rails))


def give_area(state: GameState, a: GiveArea, b: Balance, data: GameData, cash: int) -> AutoOutcome:
    firm = _firm(state, a.actor_id)
    _check_area(a.area, b)
    if not owners.may_own(state, firm, a.area, a.slot, a.person_id, b, data):
        why = owners.cant_automate(state, firm, a.area, a.slot, b, data)
        raise AutomationError(why or "that person may not own this area")
    limit = owners.default_limit(cash, b) if a.limit_cents is None else a.limit_cents
    monthly = (
        b.automation.monthly_limit_mult * limit if a.monthly_cents is None else a.monthly_cents
    )
    _check_limits(limit, monthly)
    rails = _check_rails(a.area, a.guardrails, b, data)
    state = _spend(state, a.actor_id, b)
    auto = state.automation
    rest = [o for o in auto.owners if not (o.firm_id == firm and o.key == (a.area, a.slot))]
    mine = [o.priority for o in rest if o.person_id == a.person_id]
    priority = a.priority if a.priority is not None else (max(mine) + 1 if mine else 0)
    owner = AreaOwner(
        firm,
        a.area,
        a.slot,
        a.person_id,
        limit,
        monthly,
        priority,
        state.turn,
        a.answer_events,
        rails,
    )
    state = with_automation(state, replace(auto, owners=_sorted(state, [*rest, owner], b)))
    state = _seat_authority(state, owner, True, b)
    p = state.person(a.person_id)
    item = inbox_item(
        state.turn, firm, "area_given", link_kind="automation", link_id=0,
        name=f"{p.first_name} {p.last_name}", area=owners.area_def(b, a.area).label,
        limit_cents=limit,
    )  # fmt: skip
    return AutoOutcome(state, (), (item,))


def take_over(state: GameState, a: TakeOverArea, b: Balance) -> AutoOutcome:
    firm = _firm(state, a.actor_id)
    _check_area(a.area, b)
    o = state.automation.owner(firm, a.area, a.slot)
    if o is None:
        raise AutomationError("you already run that area")
    state = _spend(state, a.actor_id, b)
    auto = state.automation
    state = with_automation(
        state, replace(auto, owners=tuple(x for x in auto.owners if x is not o))
    )
    state = _seat_authority(state, o, False, b)
    person = state.person(o.person_id)
    if (
        state.turn - o.since_turn < b.automation.take_back_months
        and person.personality["ego"] >= b.automation.high_ego
        and state.employer_of(o.person_id) == firm
    ):
        nudge = MoraleNudge(
            o.person_id, state.turn, -b.automation.take_back_morale, "area taken back"
        )
        state = replace(state, org=replace(state.org, nudges=(*state.org.nudges, nudge)))
    return AutoOutcome(state)


def set_settings(state: GameState, a: SetAreaSettings, b: Balance, data: GameData) -> AutoOutcome:
    firm = _firm(state, a.actor_id)
    _check_area(a.area, b)
    o = state.automation.owner(firm, a.area, a.slot)
    if o is None:
        raise AutomationError("that area is not automated")
    new = replace(
        o,
        limit_cents=o.limit_cents if a.limit_cents is None else a.limit_cents,
        monthly_cents=o.monthly_cents if a.monthly_cents is None else a.monthly_cents,
        priority=o.priority if a.priority is None else a.priority,
        answer_events=o.answer_events if a.answer_events is None else a.answer_events,
        guardrails=o.guardrails
        if a.guardrails is None
        else _check_rails(a.area, a.guardrails, b, data),
    )
    _check_limits(new.limit_cents, new.monthly_cents)
    auto = state.automation
    owners_ = tuple(new if x is o else x for x in auto.owners)
    return AutoOutcome(with_automation(state, replace(auto, owners=owners_)))


def _with_proposal(state: GameState, p: AutoProposal) -> GameState:
    auto = state.automation
    return with_automation(
        state, replace(auto, proposals=tuple(p if x.id == p.id else x for x in auto.proposals))
    )


def answer_proposal(
    state: GameState,
    a: AnswerProposal,
    *,
    seq: int,
    rng: RngFactory,
    b: Balance,
    data: GameData,
    ledger_balances: LedgerBalances,
) -> AutoOutcome:
    """Approve runs the proposed action as the MP (their energy spent, the player's `actions`
    stream); it is marked failed when a rule now refuses it. Decline closes it."""
    from ptk.sim.actions import action_from_payload, apply_action
    from ptk.sim.hiring.actions import Outcome
    from ptk.sim.org.actions import ACTION_TYPES as ORG_ACTION_TYPES
    from ptk.sim.org.actions import apply_org_action

    firm = _firm(state, a.actor_id)
    p = state.automation.proposal(a.proposal_id)
    if p is None or p.firm_id != firm:
        raise UnknownProposalError(f"no proposal {a.proposal_id}")
    if p.status != "pending":
        raise AutomationError(f"that proposal is {p.status}")
    name = _name(state, p.person_id)
    if not a.approve:
        state = _with_proposal(state, replace(p, status="declined", resolved_turn=state.turn))
        return AutoOutcome(state, (), (_answered(state, p, name, "declined"),))
    payload = json.loads(p.action_json)
    if "actor_id" in payload:
        payload["actor_id"] = a.actor_id
    try:
        if payload.get("kind") in ORG_ACTION_TYPES:  # an org action (a hiring plan)
            org = apply_org_action(state, ORG_ACTION_TYPES[payload["kind"]](**payload), b, data)
            out = Outcome(org.state, (), org.log_items)
        else:
            out = apply_action(
                state,
                action_from_payload(payload),
                seq=seq,
                rng=rng,
                balance=b,
                data=data,
                ledger_balances=ledger_balances,
            )
    except SimError as exc:
        state = _with_proposal(state, replace(p, status="failed", resolved_turn=state.turn))
        item = _answered(state, p, name, f"could not go ahead: {exc.message}")
        return AutoOutcome(state, (), (item,))
    state = _with_proposal(out.state, replace(p, status="approved", resolved_turn=state.turn))
    return AutoOutcome(state, out.entries, (*out.log, _answered(state, p, name, "approved")))


def _answered(state: GameState, p: AutoProposal, name: str, outcome: str) -> LogItem:
    return inbox_item(
        state.turn, p.firm_id, "auto_proposal_answered", link_kind="automation", link_id=p.id,
        name=name, what=p.title, outcome=outcome,
    )  # fmt: skip


def _name(state: GameState, pid: int) -> str:
    person = state.person(pid)
    return f"{person.first_name} {person.last_name}"


def apply_automation_action(
    state: GameState,
    action: AutomationAction,
    *,
    seq: int,
    rng: RngFactory,
    b: Balance,
    data: GameData,
    ledger_balances: LedgerBalances,
) -> AutoOutcome:
    match action:
        case GiveArea():
            cash = ledger_balances.get((state.player.id, CASH), 0)
            return give_area(state, action, b, data, cash)
        case TakeOverArea():
            return take_over(state, action, b)
        case SetAreaSettings():
            return set_settings(state, action, b, data)
        case AnswerProposal():
            return answer_proposal(
                state, action, seq=seq, rng=rng, b=b, data=data, ledger_balances=ledger_balances
            )
