"""Org actions (TST ADR-0014): units, leaders, moves, raises, promotions and hiring plans
(TST formulas.md 13.1, 13.7, 13.8, 13.10). They take effect at once.

Ported from backend/tst/sim/actions/org.py @ 02fba2aa (Tech Startup Tycoon); changed: unit
kinds are practice groups (one per practice, from 10 lawyers) and teams; a co-founding
partner may lead and be moved (only the player's own founding partner sits at the root);
promotions follow ADR PT-0006's levels (`org.promote_to`), a class-year step is
"accelerated" and partnership is the vote (PT-M4); raises go through
`interfaces.salary_cents` and `set_salary`;
plans have PT's channels, no equity, an owner who leads a unit or is a recruiting manager,
and campus plans are a practice group's campus target. Divisions, policies, seats and
founder energy are not ported (founder energy arrives with PT-M1b's actions; org actions cost
none until then). One-off morale changes are recorded as `MoraleNudge`s (interfaces.py).

Every rule an action could break raises a `SimError`, changing nothing.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Final, Literal

from ptk.sim import interfaces
from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import (
    NotFoundError,
    OrgActionError,
    OrgRuleError,
    UnknownPlanError,
    UnknownUnitError,
)
from ptk.sim.log import LogItem
from ptk.sim.org.formulas import is_raise_bonus
from ptk.sim.org.models import (
    CAMPUS_LEVEL,
    PLAN_CHANNELS,
    PLAN_FOCUSES,
    UNIT_KINDS,
    HiringPlan,
    Membership,
    MoraleNudge,
    OrgPerson,
    OrgState,
    OrgUnit,
    PlanChannel,
    PlanFocus,
    PlanStatus,
    UnitKind,
)
from ptk.sim.org.rules import practice_groups_unlocked
from ptk.sim.state import GameState

UNIT_NAME_MAX: Final = 64  # tunable-exempt: org_unit.name column width


# --- Action types ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CreateUnit:
    actor_id: int
    unit_kind: UnitKind
    name: str | None = None  # a practice group defaults to its practice's label
    parent_id: int | None = None  # None = the firm root
    practice: str | None = None  # practice groups only
    kind: Literal["create_unit"] = "create_unit"


@dataclass(frozen=True, slots=True)
class DissolveUnit:
    actor_id: int
    unit_id: int
    kind: Literal["dissolve_unit"] = "dissolve_unit"


@dataclass(frozen=True, slots=True)
class RenameUnit:
    actor_id: int
    unit_id: int
    name: str
    kind: Literal["rename_unit"] = "rename_unit"


@dataclass(frozen=True, slots=True)
class MoveUnit:
    """Re-parent a team under a practice group or the firm root (13.7)."""

    actor_id: int
    unit_id: int
    parent_id: int | None
    kind: Literal["move_unit"] = "move_unit"


@dataclass(frozen=True, slots=True)
class SetLeader:
    actor_id: int
    unit_id: int
    person_id: int | None  # None removes the current leader
    kind: Literal["set_leader"] = "set_leader"


@dataclass(frozen=True, slots=True)
class MovePerson:
    actor_id: int
    person_id: int
    unit_id: int | None  # None = the firm root
    kind: Literal["move_person"] = "move_person"


@dataclass(frozen=True, slots=True)
class GiveRaise:
    actor_id: int
    person_id: int
    salary_cents: int  # the new annual salary
    kind: Literal["give_raise"] = "give_raise"


@dataclass(frozen=True, slots=True)
class Promote:
    actor_id: int
    person_id: int
    kind: Literal["promote"] = "promote"


@dataclass(frozen=True, slots=True)
class CreatePlan:
    actor_id: int
    owner_id: int
    role: str
    target: int
    channel: PlanChannel
    ratio_bp: int
    unit_id: int | None = None
    focus: PlanFocus = "current"
    level: str | None = None
    kind: Literal["create_plan"] = "create_plan"


@dataclass(frozen=True, slots=True)
class UpdatePlan:
    """Every editable field of a plan, as it should be after the change."""

    actor_id: int
    plan_id: int
    owner_id: int
    role: str
    target: int
    channel: PlanChannel
    ratio_bp: int
    unit_id: int | None = None
    focus: PlanFocus = "current"
    level: str | None = None
    kind: Literal["update_plan"] = "update_plan"


@dataclass(frozen=True, slots=True)
class ClosePlan:
    actor_id: int
    plan_id: int
    kind: Literal["close_plan"] = "close_plan"


type OrgAction = (
    CreateUnit
    | DissolveUnit
    | RenameUnit
    | MoveUnit
    | SetLeader
    | MovePerson
    | GiveRaise
    | Promote
    | CreatePlan
    | UpdatePlan
    | ClosePlan
)

ACTION_TYPES: Final[dict[str, type[OrgAction]]] = {
    "create_unit": CreateUnit,
    "dissolve_unit": DissolveUnit,
    "rename_unit": RenameUnit,
    "move_unit": MoveUnit,
    "set_leader": SetLeader,
    "move_person": MovePerson,
    "give_raise": GiveRaise,
    "promote": Promote,
    "create_plan": CreatePlan,
    "update_plan": UpdatePlan,
    "close_plan": ClosePlan,
}


@dataclass(frozen=True, slots=True)
class OrgOutcome:
    state: GameState
    log_items: tuple[LogItem, ...] = ()
    unit_id: int | None = None  # a created unit
    plan_id: int | None = None  # a created plan


# --- State helpers ----------------------------------------------------------------------------


def with_org(state: GameState, org: OrgState) -> GameState:
    return replace(state, org=org)


def with_unit(state: GameState, unit: OrgUnit) -> GameState:
    units = (*tuple(u for u in state.org.units if u.id != unit.id), unit)
    return with_org(state, replace(state.org, units=tuple(sorted(units, key=lambda u: u.id))))


def with_plan(state: GameState, plan: HiringPlan) -> GameState:
    plans = (*tuple(p for p in state.org.plans if p.id != plan.id), plan)
    return with_org(state, replace(state.org, plans=tuple(sorted(plans, key=lambda p: p.id))))


def with_org_person(state: GameState, person: OrgPerson) -> GameState:
    people = (*tuple(p for p in state.org.people if p.person_id != person.person_id), person)
    people = tuple(sorted(people, key=lambda p: p.person_id))
    return with_org(state, replace(state.org, people=people))


def place(state: GameState, person_id: int, unit_id: int | None) -> GameState:
    """Put a person in a unit (None: the firm root)."""
    members = tuple(m for m in state.org.members if m.person_id != person_id)
    if unit_id is not None:
        members = tuple(
            sorted((*members, Membership(person_id, unit_id)), key=lambda m: m.person_id)
        )
    return with_org(state, replace(state.org, members=members))


def nudge(state: GameState, person_id: int, points: float, reason: str) -> GameState:
    """Record a one-off morale change for an employee; the founding partner has none."""
    if points == 0 or state.person(person_id).is_founder:
        return state
    item = MoraleNudge(person_id=person_id, turn=state.turn, points=points, reason=reason)
    return with_org(state, replace(state.org, nudges=(*state.org.nudges, item)))


def acting_firm(state: GameState, actor_id: int) -> int:
    firm = state.employer_of(actor_id)
    if firm is None:
        raise NotFoundError(f"person {actor_id} is not on staff and cannot act")
    return firm


def active_unit(state: GameState, firm_id: int, unit_id: int) -> OrgUnit:
    unit = state.org.unit(unit_id)
    if unit is None or unit.firm_id != firm_id or unit.status != "active":
        raise UnknownUnitError(f"no unit {unit_id}")
    return unit


def employee(state: GameState, firm_id: int, person_id: int, what: str) -> None:
    """A staff member other than the founding partner the player plays (who sits at the root)."""
    if state.employer_of(person_id) != firm_id:
        raise NotFoundError(f"person {person_id} is not on staff")
    if state.person(person_id).is_founder:
        raise OrgRuleError(f"the managing founding partner cannot {what}")


def unit_members(state: GameState, unit_id: int) -> tuple[int, ...]:
    """Staff in the unit, ascending."""
    return tuple(
        m.person_id
        for m in state.org.members
        if m.unit_id == unit_id and state.employer_of(m.person_id) is not None
    )


def _clean_name(state: GameState, firm_id: int, name: str, keep: int | None = None) -> str:
    cleaned = " ".join(name.split())
    if not cleaned:
        raise OrgRuleError("a unit needs a name")
    if len(cleaned) > UNIT_NAME_MAX:
        raise OrgRuleError(f"a unit name may have at most {UNIT_NAME_MAX} characters")
    taken = {u.name.casefold() for u in state.org.firm_units(firm_id) if u.id != keep}
    if cleaned.casefold() in taken:
        raise OrgRuleError(f"there is already a unit named {cleaned!r}")
    return cleaned


# --- Units ----------------------------------------------------------------------------------


def create_unit(
    state: GameState, action: CreateUnit, balance: Balance, data: GameData
) -> OrgOutcome:
    firm = acting_firm(state, action.actor_id)
    if action.unit_kind not in UNIT_KINDS:
        raise OrgRuleError(f"unknown unit kind {action.unit_kind!r}")
    if action.unit_kind == "practice_group":
        if action.parent_id is not None:
            raise OrgRuleError("a practice group sits directly under the firm")
        if action.practice not in data.practice_keys:
            raise OrgActionError(f"unknown practice {action.practice!r}")
        if not practice_groups_unlocked(state, firm, data, balance):
            raise OrgRuleError(
                f"practice groups unlock at {balance.org.practice_group_unlock_lawyers} lawyers"
            )
        if any(u.practice == action.practice for u in state.org.firm_units(firm)):
            raise OrgRuleError("the firm already has a group for that practice")
        default = next(p.label for p in data.practices if p.key == action.practice)
        name = _clean_name(state, firm, action.name if action.name is not None else default)
    else:
        if action.practice is not None:
            raise OrgRuleError("only a practice group has a practice")
        if action.parent_id is not None:
            parent = active_unit(state, firm, action.parent_id)
            if parent.kind == "team":
                raise OrgRuleError("a team sits under the firm or a practice group")
        name = _clean_name(state, firm, action.name or "")
    unit = OrgUnit(
        id=state.org.next_unit_id,
        firm_id=firm,
        kind=action.unit_kind,
        name=name,
        parent_id=action.parent_id,
        leader_id=None,
        created_turn=state.turn,
        practice=action.practice,
    )
    state = with_org(state, replace(state.org, next_unit_id=unit.id + 1))
    return OrgOutcome(with_unit(state, unit), unit_id=unit.id)


def dissolve_unit(state: GameState, action: DissolveUnit, balance: Balance) -> OrgOutcome:
    """Members and child teams move to the parent; each member loses morale (13.7)."""
    firm = acting_firm(state, action.actor_id)
    unit = active_unit(state, firm, action.unit_id)
    parent = unit.parent_id
    for pid in unit_members(state, unit.id):
        state = place(state, pid, parent)
        state = nudge(state, pid, balance.org.reorg.dissolve_members, "unit dissolved")
    for child in state.org.firm_units(firm):
        if child.parent_id == unit.id:
            state = with_unit(state, replace(child, parent_id=parent))
    for plan in state.org.firm_plans(firm):
        if plan.unit_id == unit.id:
            state = with_plan(state, replace(plan, unit_id=parent))
    dissolved = replace(unit, status="dissolved", dissolved_turn=state.turn, leader_id=None)
    return OrgOutcome(with_unit(state, dissolved))


def rename_unit(state: GameState, action: RenameUnit) -> OrgOutcome:
    firm = acting_firm(state, action.actor_id)
    unit = active_unit(state, firm, action.unit_id)
    name = _clean_name(state, firm, action.name, keep=unit.id)
    if name == unit.name:
        raise OrgRuleError(f"the unit is already named {name!r}")
    return OrgOutcome(with_unit(state, replace(unit, name=name)))


def move_unit(state: GameState, action: MoveUnit) -> OrgOutcome:
    """A team moves with its members and leader; nobody's morale changes (13.7)."""
    firm = acting_firm(state, action.actor_id)
    unit = active_unit(state, firm, action.unit_id)
    if unit.kind == "practice_group":
        raise OrgRuleError("a practice group sits directly under the firm")
    if action.parent_id is not None:
        parent = active_unit(state, firm, action.parent_id)
        if parent.kind == "team":
            raise OrgRuleError("a team sits under the firm or a practice group")
    if unit.parent_id == action.parent_id:
        raise OrgRuleError(f"{unit.name} is already there")
    return OrgOutcome(with_unit(state, replace(unit, parent_id=action.parent_id)))


def set_leader(state: GameState, action: SetLeader, balance: Balance) -> OrgOutcome:
    """Any change of leader: -1 for each other member, -5 for the leader who loses the post.
    A plan owner who stops leading any unit (and is no recruiting manager) pauses their plans."""
    firm = acting_firm(state, action.actor_id)
    unit = active_unit(state, firm, action.unit_id)
    old, new = unit.leader_id, action.person_id
    if new is None:
        if old is None:
            raise OrgRuleError(f"{unit.name} has no leader to remove")
    else:
        employee(state, firm, new, "lead a unit")
        if new == old:
            raise OrgRuleError("they already lead this unit")
        if state.org.unit_of(new) != unit.id:
            raise OrgRuleError(f"a leader must be a member of the unit; move them to {unit.name}")
        if state.org.led_unit(new) is not None:
            raise OrgRuleError("a person leads at most one unit")
    reorg = balance.org.reorg
    for pid in unit_members(state, unit.id):
        if pid == new:
            continue
        if pid == old:
            state = nudge(state, pid, reorg.replaced_leader, "replaced as leader")
        else:
            state = nudge(state, pid, reorg.new_leader_members, "new leader")
    state = with_unit(state, replace(unit, leader_id=new))
    return OrgOutcome(pause_unqualified_plans(state, balance))


def move_person(state: GameState, action: MovePerson, balance: Balance) -> OrgOutcome:
    firm = acting_firm(state, action.actor_id)
    employee(state, firm, action.person_id, "leave the firm root")
    if action.unit_id is not None:
        active_unit(state, firm, action.unit_id)
    if state.org.unit_of(action.person_id) == action.unit_id:
        raise OrgRuleError("they are already in that unit")
    leads = state.org.led_unit(action.person_id)
    if leads is not None:
        raise OrgRuleError(f"they lead {leads.name}; replace or remove them as leader first")
    state = place(state, action.person_id, action.unit_id)
    return OrgOutcome(nudge(state, action.person_id, balance.org.reorg.move, "moved"))


# --- Pay and level --------------------------------------------------------------------------


def raise_morale_change(
    old_cents: int, new_cents: int, last_raise_turn: int | None, turn: int, balance: Balance
) -> float:
    """+3 for a raise of at least 5% (once per 12 turns), -10 for any cut, else 0 (13.8)."""
    org = balance.org
    if new_cents < old_cents:
        return org.pay_cut_morale
    cooled = last_raise_turn is None or turn - last_raise_turn >= org.raise_cooldown_turns
    if cooled and is_raise_bonus(old_cents, new_cents, org):
        return org.raise_morale
    return 0.0


def give_raise(state: GameState, action: GiveRaise, balance: Balance) -> OrgOutcome:
    """The new salary applies from the next payroll (phase 6)."""
    firm = acting_firm(state, action.actor_id)
    employee(state, firm, action.person_id, "be given a raise")
    if action.salary_cents <= 0:
        raise OrgActionError("salary must be positive")
    old = interfaces.salary_cents(state, action.person_id)
    if old is None:
        raise OrgRuleError("salaries arrive with payroll (PT-M1b)")
    if action.salary_cents == old:
        raise OrgActionError("that is their current salary")
    record = state.org.person(action.person_id)
    change = raise_morale_change(
        old, action.salary_cents, record.last_raise_turn, state.turn, balance
    )
    state = interfaces.set_salary(state, action.person_id, action.salary_cents)
    last = state.turn if change > 0 else record.last_raise_turn
    state = with_org_person(state, replace(record, last_raise_turn=last))
    reason = "pay cut" if change < 0 else "raise"
    return OrgOutcome(nudge(state, action.person_id, change, reason))


def promotion_target(level: str, balance: Balance) -> str | None:
    return balance.org.promote_to.get(level)


def is_accelerated(level: str, target: str, balance: Balance) -> bool:
    """A promotion to the class year September would bring anyway skips a year ahead."""
    return balance.people.levels[level].next_level == target


def promote(state: GameState, action: Promote, balance: Balance) -> OrgOutcome:
    """One level up (ADR PT-0006 1); +5 morale once (13.8). The new level's market pay
    applies from then on, so promote and raise together."""
    firm = acting_firm(state, action.actor_id)
    employee(state, firm, action.person_id, "be promoted")
    person = state.person(action.person_id)
    target = promotion_target(person.level, balance)
    if target is None:
        if person.level in ("counsel", "income_partner"):
            raise OrgRuleError("partnership comes by the partnership vote (PT-M4)")
        raise OrgRuleError(f"{person.level.replace('_', ' ')} is as far as a promotion goes")
    record = state.org.person(person.id)
    accelerated = record.accelerated_years + (
        1 if is_accelerated(person.level, target, balance) else 0
    )
    state = replace(
        state,
        people=tuple(replace(p, level=target) if p.id == person.id else p for p in state.people),
    )
    state = with_org_person(
        state, replace(record, accelerated_years=accelerated, last_promoted_turn=state.turn)
    )
    return OrgOutcome(nudge(state, person.id, balance.org.promote_morale, "promoted"))


# --- Hiring plans ---------------------------------------------------------------------------


def may_own_plan(state: GameState, person_id: int, balance: Balance) -> bool:
    """A delegate leads a unit or is a recruiting manager (`org.delegates.plan_owner_roles`)."""
    if state.org.led_unit(person_id) is not None:
        return True
    return state.person(person_id).role in balance.org.delegates.plan_owner_roles


def _check_plan(
    state: GameState,
    firm: int,
    owner_id: int,
    role: str,
    target: int,
    channel: str,
    ratio_bp: int,
    unit_id: int | None,
    focus: str,
    level: str | None,
    balance: Balance,
    data: GameData,
    plan_id: int | None = None,
) -> str | None:
    """Validate a plan's fields; return the level it searches at (a campus plan's is fixed)."""
    employee(state, firm, owner_id, "own a hiring plan (it needs a delegate)")
    if not may_own_plan(state, owner_id, balance):
        raise OrgRuleError("a plan's owner leads a unit or is a recruiting manager")
    if focus not in PLAN_FOCUSES:
        raise OrgActionError(f"unknown focus {focus!r}")
    if role not in {r.key for r in data.roles}:
        raise OrgActionError(f"unknown role {role!r}")
    if target < 1:
        raise OrgActionError("a plan needs a target of at least one hire")
    if channel not in PLAN_CHANNELS:
        raise OrgActionError(f"unknown channel {channel!r}")
    max_ratio = balance.org.delegates.max_ratio_bp
    if not 0 < ratio_bp <= max_ratio:
        raise OrgActionError(f"the salary ratio must be above 0 and at most {max_ratio} bp")
    if level is not None and level not in balance.people.levels:
        raise OrgActionError(f"unknown level {level!r}")
    unit = active_unit(state, firm, unit_id) if unit_id is not None else None
    if channel != "campus":
        return level
    # A campus plan is a practice group's campus target: next September's first years.
    if unit is None or unit.kind != "practice_group":
        raise OrgRuleError("a campus target belongs to a practice group")
    if data.role(role).practice != unit.practice:
        raise OrgRuleError("a campus target hires the group's own practice")
    for other in state.org.firm_plans(firm):
        if other.id != plan_id and other.campus and other.unit_id == unit.id:
            raise OrgRuleError(f"{unit.name} already has a campus target")
    return CAMPUS_LEVEL


def create_plan(
    state: GameState, action: CreatePlan, balance: Balance, data: GameData
) -> OrgOutcome:
    firm = acting_firm(state, action.actor_id)
    level = _check_plan(
        state, firm, action.owner_id, action.role, action.target, action.channel,
        action.ratio_bp, action.unit_id, action.focus, action.level, balance, data,
    )  # fmt: skip
    plan = HiringPlan(
        id=state.org.next_plan_id,
        firm_id=firm,
        owner_id=action.owner_id,
        unit_id=action.unit_id,
        role=action.role,
        target=action.target,
        channel=action.channel,
        ratio_bp=action.ratio_bp,
        created_turn=state.turn,
        focus=action.focus,
        level=level,
    )
    state = with_org(state, replace(state.org, next_plan_id=plan.id + 1))
    return OrgOutcome(with_plan(state, plan), plan_id=plan.id)


def live_plan(state: GameState, firm_id: int, plan_id: int) -> HiringPlan:
    plan = state.org.plan(plan_id)
    if plan is None or plan.firm_id != firm_id or plan.status == "closed":
        raise UnknownPlanError(f"no hiring plan {plan_id}")
    return plan


def update_plan(
    state: GameState, action: UpdatePlan, balance: Balance, data: GameData
) -> OrgOutcome:
    """A paused plan with a qualified owner, or a filled plan with room, becomes active."""
    firm = acting_firm(state, action.actor_id)
    plan = live_plan(state, firm, action.plan_id)
    level = _check_plan(
        state, firm, action.owner_id, action.role, action.target, action.channel,
        action.ratio_bp, action.unit_id, action.focus, action.level, balance, data, plan.id,
    )  # fmt: skip
    status: PlanStatus = "active" if plan.hired < action.target else "filled"
    updated = replace(
        plan,
        owner_id=action.owner_id,
        role=action.role,
        target=action.target,
        channel=action.channel,
        ratio_bp=action.ratio_bp,
        unit_id=action.unit_id,
        status=status,
        focus=action.focus,
        level=level,
    )
    return OrgOutcome(with_plan(state, updated))


def close_plan(state: GameState, action: ClosePlan) -> OrgOutcome:
    """Free. Offers already made still resolve; the delegate closes the plan's searches in
    phase 2 (TST 13.10)."""
    firm = acting_firm(state, action.actor_id)
    plan = live_plan(state, firm, action.plan_id)
    return OrgOutcome(with_plan(state, replace(plan, status="closed", closed_turn=state.turn)))


def pause_unqualified_plans(state: GameState, balance: Balance) -> GameState:
    """Plans whose owner left the firm or may no longer own a plan pause (ADR-0015)."""
    for plan in state.org.plans:
        if plan.status not in ("active", "filled"):
            continue
        on_staff = state.employer_of(plan.owner_id) == plan.firm_id
        if not on_staff or not may_own_plan(state, plan.owner_id, balance):
            state = with_plan(state, replace(plan, status="paused"))
    return state


# --- Dispatch -------------------------------------------------------------------------------


def apply_org_action(
    state: GameState, action: OrgAction, balance: Balance, data: GameData
) -> OrgOutcome:
    """Apply one org action at once (ADR-0014). Pure: no randomness, no clock."""
    match action:
        case CreateUnit():
            return create_unit(state, action, balance, data)
        case DissolveUnit():
            return dissolve_unit(state, action, balance)
        case RenameUnit():
            return rename_unit(state, action)
        case MoveUnit():
            return move_unit(state, action)
        case SetLeader():
            return set_leader(state, action, balance)
        case MovePerson():
            return move_person(state, action, balance)
        case GiveRaise():
            return give_raise(state, action, balance)
        case Promote():
            return promote(state, action, balance)
        case CreatePlan():
            return create_plan(state, action, balance, data)
        case UpdatePlan():
            return update_plan(state, action, balance, data)
        case ClosePlan():
            return close_plan(state, action)
