"""Org endpoints and schemas (PT-M2; TST formulas.md 13; ADR-0009, ADR-0014).

The Org screen reads one view of the player's firm: practice groups and teams, who sits
where, each supervising partner's load and how they come across, and the hiring plans.
Every write is one org action in its own transaction, logged to `decision_log`, and returns
the fresh view. Like TST (13.11), a supervisor's quality is a coarse label (strong, fine,
stretched) and an over-span flag; no true skill, quality score or span limit is a field.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel

from ptk import loader
from ptk.config import get_settings
from ptk.db import saves
from ptk.db.org_io import run_org_action
from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import NotFoundError
from ptk.sim.interfaces import delegate_hiring
from ptk.sim.org.actions import (
    ClosePlan,
    CreatePlan,
    CreateUnit,
    DissolveUnit,
    GiveRaise,
    MovePerson,
    MoveUnit,
    OrgAction,
    Promote,
    RenameUnit,
    SetLeader,
    UpdatePlan,
    is_accelerated,
    may_own_plan,
    promotion_target,
)
from ptk.sim.org.delegates import activity_text, available_hook
from ptk.sim.org.formulas import manager_label
from ptk.sim.org.models import HiringPlan, PlanChannel, PlanFocus
from ptk.sim.org.rules import OrgView, lawyer_count, manager_terms, org_view
from ptk.sim.state import GameState

type SupervisorLabel = Literal["strong", "fine", "stretched"]


class PersonRefOut(BaseModel):
    id: int
    name: str


class OrgMemberOut(BaseModel):
    id: int
    name: str
    level: str
    role_label: str
    supervisor_id: int | None  # the supervising partner (TST's manager); None: the founder
    leads_unit_id: int | None


class OrgUnitOut(BaseModel):
    id: int
    kind: Literal["practice_group", "team"]
    name: str
    parent_id: int | None  # None: the firm root
    practice: str | None
    leader: PersonRefOut | None
    members: list[OrgMemberOut]
    campus_target: int | None  # a practice group's campus plan target, if any


class SupervisorOut(BaseModel):
    """A supervising partner's load (TST 13.2-13.4), shown coarsely."""

    person: PersonRefOut
    reports: int
    over_span: bool
    label: SupervisorLabel


class PlanOut(BaseModel):
    id: int
    owner: PersonRefOut
    unit_id: int | None
    unit_name: str  # "Firm" for the root
    role: str
    role_label: str
    target: int
    hired: int
    channel: PlanChannel
    focus: PlanFocus
    level: str | None
    ratio_bp: int
    status: Literal["active", "paused", "filled", "closed"]
    campus: bool
    last_activity: str | None  # what the delegate did in its last active month


class PracticeOut(BaseModel):
    key: str
    label: str


class RoleOut(BaseModel):
    key: str
    label: str
    practice: str | None


class OrgOut(BaseModel):
    firm_name: str
    founder: PersonRefOut | None  # the root's leader
    practice_groups_unlocked: bool
    lawyers: int
    unlock_at: int
    root_members: list[OrgMemberOut]
    units: list[OrgUnitOut]
    supervisors: list[SupervisorOut]
    plans: list[PlanOut]
    open_practices: list[PracticeOut]  # practices without a group yet
    roles: list[RoleOut]  # what a plan may hire
    plan_owners: list[PersonRefOut]  # who may own a plan: unit leaders, recruiting managers
    delegates_ready: bool  # hiring is built, so delegates can work plans (PT-M1b)


class PersonOrgOut(BaseModel):
    """The org panel on a Person profile (own firm only)."""

    unit_id: int | None
    unit_name: str
    supervisor: PersonRefOut | None
    supervisor_label: SupervisorLabel | None
    reports: list[PersonRefOut]
    leads: PersonRefOut | None  # the unit they lead (id and name)
    accelerated_years: int
    promote_to: str | None
    promotion_accelerated: bool
    plans_owned: int


# --- Request bodies -------------------------------------------------------------------------


class CreateUnitIn(BaseModel):
    kind: Literal["practice_group", "team"]
    name: str | None = None
    parent_id: int | None = None
    practice: str | None = None


class RenameUnitIn(BaseModel):
    name: str


class MoveUnitIn(BaseModel):
    parent_id: int | None


class LeaderIn(BaseModel):
    person_id: int | None


class PersonUnitIn(BaseModel):
    unit_id: int | None


class RaiseIn(BaseModel):
    salary_cents: int


class PlanIn(BaseModel):
    owner_id: int
    role: str
    target: int
    channel: PlanChannel
    ratio_bp: int = 10000
    unit_id: int | None = None
    focus: PlanFocus = "current"
    level: str | None = None


# --- Views ----------------------------------------------------------------------------------


def _name(state: GameState, person_id: int) -> str:
    p = state.person(person_id)
    return f"{p.first_name} {p.last_name}"


def _ref(state: GameState, person_id: int | None) -> PersonRefOut | None:
    return None if person_id is None else PersonRefOut(id=person_id, name=_name(state, person_id))


def _member(state: GameState, view: OrgView, pid: int, data: GameData) -> OrgMemberOut:
    person = state.person(pid)
    led = state.org.led_unit(pid)
    return OrgMemberOut(
        id=pid,
        name=_name(state, pid),
        level=person.level,
        role_label=data.role(person.role).label,
        supervisor_id=view.manager_of.get(pid),
        leads_unit_id=led.id if led else None,
    )


def _plan_out(state: GameState, plan: HiringPlan, data: GameData) -> PlanOut:
    unit = state.org.unit(plan.unit_id) if plan.unit_id is not None else None
    role = data.role(plan.role)
    activity = plan.last_activity
    return PlanOut(
        id=plan.id,
        owner=PersonRefOut(id=plan.owner_id, name=_name(state, plan.owner_id)),
        unit_id=plan.unit_id,
        unit_name=unit.name if unit else "Firm",
        role=plan.role,
        role_label=role.label,
        target=plan.target,
        hired=plan.hired,
        channel=plan.channel,
        focus=plan.focus,
        level=plan.level,
        ratio_bp=plan.ratio_bp,
        status=plan.status,
        campus=plan.campus,
        last_activity=(
            activity_text(activity, role.label.lower(), plan.focus)
            if activity and activity.acted
            else None
        ),
    )


def org_out(state: GameState, data: GameData, balance: Balance) -> OrgOut:
    firm = state.player
    view = org_view(state, firm.id)
    units = state.org.firm_units(firm.id)
    plans = state.org.firm_plans(firm.id)
    supervisors = []
    for sid, reports in sorted(view.reports.items()):
        terms = manager_terms(state, view, reports[0], balance)
        supervisors.append(
            SupervisorOut(
                person=PersonRefOut(id=sid, name=_name(state, sid)),
                reports=len(reports),
                over_span=terms.span < 1,
                label=manager_label(terms.morale, balance.org),
            )
        )
    taken = {u.practice for u in units if u.practice}
    return OrgOut(
        firm_name=firm.name,
        founder=_ref(state, view.founder_id),
        practice_groups_unlocked=lawyer_count(state, firm.id, data)
        >= balance.org.practice_group_unlock_lawyers,
        lawyers=lawyer_count(state, firm.id, data),
        unlock_at=balance.org.practice_group_unlock_lawyers,
        root_members=[
            _member(state, view, pid, data)
            for pid in view.members.get(None, ())
            if pid != view.founder_id
        ],
        units=[
            OrgUnitOut(
                id=u.id,
                kind=u.kind,
                name=u.name,
                parent_id=u.parent_id,
                practice=u.practice,
                leader=_ref(state, u.leader_id),
                members=[_member(state, view, pid, data) for pid in view.members.get(u.id, ())],
                campus_target=next(
                    (p.target for p in plans if p.campus and p.unit_id == u.id), None
                ),
            )
            for u in units
        ],
        supervisors=supervisors,
        plans=[_plan_out(state, p, data) for p in plans],
        open_practices=[
            PracticeOut(key=p.key, label=p.label) for p in data.practices if p.key not in taken
        ],
        roles=[RoleOut(key=r.key, label=r.label, practice=r.practice) for r in data.roles],
        plan_owners=[
            PersonRefOut(id=pid, name=_name(state, pid))
            for pid in state.staff_ids(firm.id)
            if pid != view.founder_id and may_own_plan(state, pid, balance)
        ],
        delegates_ready=available_hook(delegate_hiring) is not None,
    )


def person_org(state: GameState, person_id: int, data: GameData, balance: Balance) -> PersonOrgOut:
    firm = state.player.id
    if person_id not in state.staff_ids(firm):
        raise NotFoundError(f"person {person_id} is not on your firm's books")
    view = org_view(state, firm)
    unit_id = view.unit_of.get(person_id)
    unit = state.org.unit(unit_id) if unit_id is not None else None
    terms = manager_terms(state, view, person_id, balance)
    led = state.org.led_unit(person_id)
    person = state.person(person_id)
    target = None if person.is_founder else promotion_target(person.level, balance)
    return PersonOrgOut(
        unit_id=unit_id,
        unit_name=unit.name if unit else "Firm",
        supervisor=_ref(state, terms.manager_id),
        supervisor_label=(
            manager_label(terms.morale, balance.org) if terms.manager_id is not None else None
        ),
        reports=[PersonRefOut(id=r, name=_name(state, r)) for r in view.reports.get(person_id, ())],
        leads=PersonRefOut(id=led.id, name=led.name) if led else None,
        accelerated_years=state.org.person(person_id).accelerated_years,
        promote_to=target,
        promotion_accelerated=target is not None and is_accelerated(person.level, target, balance),
        plans_owned=sum(1 for p in state.org.firm_plans(firm) if p.owner_id == person_id),
    )


# --- Router ---------------------------------------------------------------------------------


def _path(slug: str) -> Path:
    return saves.open_save(get_settings().resolved_save_dir(), slug)


def _actor(path: Path) -> int:
    state = saves.read_state(path)[0]
    founder = state.founder_of(state.player.id)
    if founder is None:
        raise NotFoundError("the firm has no managing founding partner to act")
    return founder


def _act(slug: str, build: Any) -> OrgOut:
    path = _path(slug)
    action: OrgAction = build(_actor(path))
    data, balance = loader.game_data(), loader.balance()
    out = run_org_action(path, action, balance, data)
    return org_out(out.state, data, balance)


def make_org_router(errors: dict[int | str, dict[str, Any]]) -> APIRouter:
    router = APIRouter()
    base = "/api/saves/{slug}/org"

    @router.get(base, response_model=OrgOut, responses=errors, operation_id="getOrg")
    def get_org(slug: str) -> OrgOut:
        state = saves.read_state(_path(slug))[0]
        return org_out(state, loader.game_data(), loader.balance())

    @router.get(
        base + "/people/{person_id}",
        response_model=PersonOrgOut,
        responses=errors,
        operation_id="getPersonOrg",
    )
    def get_person_org(slug: str, person_id: int) -> PersonOrgOut:
        state = saves.read_state(_path(slug))[0]
        return person_org(state, person_id, loader.game_data(), loader.balance())

    @router.post(
        base + "/units", response_model=OrgOut, responses=errors, operation_id="createUnit"
    )
    def create_unit(slug: str, body: CreateUnitIn) -> OrgOut:
        return _act(
            slug, lambda a: CreateUnit(a, body.kind, body.name, body.parent_id, body.practice)
        )

    @router.post(
        base + "/units/{unit_id}/rename",
        response_model=OrgOut,
        responses=errors,
        operation_id="renameUnit",
    )
    def rename_unit(slug: str, unit_id: int, body: RenameUnitIn) -> OrgOut:
        return _act(slug, lambda a: RenameUnit(a, unit_id, body.name))

    @router.post(
        base + "/units/{unit_id}/move",
        response_model=OrgOut,
        responses=errors,
        operation_id="moveUnit",
    )
    def move_unit(slug: str, unit_id: int, body: MoveUnitIn) -> OrgOut:
        return _act(slug, lambda a: MoveUnit(a, unit_id, body.parent_id))

    @router.delete(
        base + "/units/{unit_id}",
        response_model=OrgOut,
        responses=errors,
        operation_id="dissolveUnit",
    )
    def dissolve_unit(slug: str, unit_id: int) -> OrgOut:
        return _act(slug, lambda a: DissolveUnit(a, unit_id))

    @router.put(
        base + "/units/{unit_id}/leader",
        response_model=OrgOut,
        responses=errors,
        operation_id="setLeader",
    )
    def set_leader(slug: str, unit_id: int, body: LeaderIn) -> OrgOut:
        return _act(slug, lambda a: SetLeader(a, unit_id, body.person_id))

    @router.put(
        base + "/people/{person_id}/unit",
        response_model=OrgOut,
        responses=errors,
        operation_id="movePerson",
    )
    def move_person(slug: str, person_id: int, body: PersonUnitIn) -> OrgOut:
        return _act(slug, lambda a: MovePerson(a, person_id, body.unit_id))

    @router.post(
        base + "/people/{person_id}/promote",
        response_model=OrgOut,
        responses=errors,
        operation_id="promote",
    )
    def promote(slug: str, person_id: int) -> OrgOut:
        return _act(slug, lambda a: Promote(a, person_id))

    @router.post(
        base + "/people/{person_id}/raise",
        response_model=OrgOut,
        responses=errors,
        operation_id="giveRaise",
    )
    def give_raise(slug: str, person_id: int, body: RaiseIn) -> OrgOut:
        return _act(slug, lambda a: GiveRaise(a, person_id, body.salary_cents))

    @router.post(
        base + "/plans", response_model=OrgOut, responses=errors, operation_id="createPlan"
    )
    def create_plan(slug: str, body: PlanIn) -> OrgOut:
        return _act(
            slug,
            lambda a: CreatePlan(
                a,
                body.owner_id,
                body.role,
                body.target,
                body.channel,
                body.ratio_bp,
                body.unit_id,
                body.focus,
                body.level,
            ),
        )

    @router.put(
        base + "/plans/{plan_id}",
        response_model=OrgOut,
        responses=errors,
        operation_id="updatePlan",
    )
    def update_plan(slug: str, plan_id: int, body: PlanIn) -> OrgOut:
        return _act(
            slug,
            lambda a: UpdatePlan(
                a,
                plan_id,
                body.owner_id,
                body.role,
                body.target,
                body.channel,
                body.ratio_bp,
                body.unit_id,
                body.focus,
                body.level,
            ),
        )

    @router.delete(
        base + "/plans/{plan_id}", response_model=OrgOut, responses=errors, operation_id="closePlan"
    )
    def close_plan(slug: str, plan_id: int) -> OrgOut:
        return _act(slug, lambda a: ClosePlan(a, plan_id))

    return router
