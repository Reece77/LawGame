"""Load and write the org (schema v3, PT-M2). Current-state tables, rewritten in place."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ptk.db.models import (
    DecisionLogRow,
    HiringPlanRow,
    OrgMemberRow,
    OrgMoraleNudgeRow,
    OrgPersonRow,
    OrgUnitRow,
)
from ptk.db.session import make_sessionmaker, shared_engine
from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import GameOverError
from ptk.sim.org.actions import ACTION_TYPES, OrgAction, OrgOutcome, apply_org_action
from ptk.sim.org.delegates import DelegateAction
from ptk.sim.org.models import (
    HiringPlan,
    Membership,
    MoraleNudge,
    OrgPerson,
    OrgState,
    OrgUnit,
    PlanActivity,
)
from ptk.sim.state import GameState


def load_org(session: Session) -> OrgState:
    units = tuple(
        OrgUnit(
            id=r.id,
            firm_id=r.firm_id,
            kind=r.kind,  # type: ignore[arg-type]
            name=r.name,
            parent_id=r.parent_id,
            leader_id=r.leader_id,
            created_turn=r.created_turn,
            practice=r.practice,
            status=r.status,  # type: ignore[arg-type]
            dissolved_turn=r.dissolved_turn,
        )
        for r in session.scalars(select(OrgUnitRow).order_by(OrgUnitRow.id))
    )
    plans = tuple(
        _plan(r) for r in session.scalars(select(HiringPlanRow).order_by(HiringPlanRow.id))
    )
    return OrgState(
        units=units,
        members=tuple(
            Membership(person_id=r.person_id, unit_id=r.unit_id)
            for r in session.scalars(select(OrgMemberRow).order_by(OrgMemberRow.person_id))
        ),
        plans=plans,
        people=tuple(
            OrgPerson(
                person_id=r.person_id,
                last_raise_turn=r.last_raise_turn,
                accelerated_years=r.accelerated_years,
                last_promoted_turn=r.last_promoted_turn,
            )
            for r in session.scalars(select(OrgPersonRow).order_by(OrgPersonRow.person_id))
        ),
        nudges=tuple(
            MoraleNudge(person_id=r.person_id, turn=r.turn, points=r.points, reason=r.reason)
            for r in session.scalars(select(OrgMoraleNudgeRow).order_by(OrgMoraleNudgeRow.id))
        ),
        next_unit_id=max((u.id for u in units), default=0) + 1,
        next_plan_id=max((p.id for p in plans), default=0) + 1,
    )


def _plan(r: HiringPlanRow) -> HiringPlan:
    activity = json.loads(r.activity_json) if r.activity_json else None
    return HiringPlan(
        id=r.id,
        firm_id=r.firm_id,
        owner_id=r.owner_id,
        unit_id=r.unit_id,
        role=r.role,
        target=r.target,
        channel=r.channel,  # type: ignore[arg-type]
        ratio_bp=r.ratio_bp,
        created_turn=r.created_turn,
        status=r.status,  # type: ignore[arg-type]
        hired=r.hired,
        closed_turn=r.closed_turn,
        last_activity=PlanActivity(**activity) if activity is not None else None,
        focus=r.focus,  # type: ignore[arg-type]
        level=r.level,
        hires=tuple(json.loads(r.hires_json)),
    )


def write_org(session: Session, state: GameState) -> None:
    """Upsert units, plans and people records; rewrite membership and one-off morale."""
    org = state.org
    for u in org.units:
        session.merge(
            OrgUnitRow(
                id=u.id,
                firm_id=u.firm_id,
                kind=u.kind,
                name=u.name,
                parent_id=u.parent_id,
                leader_id=u.leader_id,
                practice=u.practice,
                created_turn=u.created_turn,
                status=u.status,
                dissolved_turn=u.dissolved_turn,
            )
        )
    session.flush()
    session.execute(delete(OrgMemberRow))
    session.add_all(OrgMemberRow(person_id=m.person_id, unit_id=m.unit_id) for m in org.members)
    for p in org.plans:
        session.merge(
            HiringPlanRow(
                id=p.id,
                firm_id=p.firm_id,
                owner_id=p.owner_id,
                unit_id=p.unit_id,
                role=p.role,
                target=p.target,
                channel=p.channel,
                ratio_bp=p.ratio_bp,
                created_turn=p.created_turn,
                status=p.status,
                hired=p.hired,
                closed_turn=p.closed_turn,
                focus=p.focus,
                level=p.level,
                hires_json=json.dumps(list(p.hires)),
                activity_json=json.dumps(asdict(p.last_activity)) if p.last_activity else None,
            )
        )
    for op in org.people:
        session.merge(
            OrgPersonRow(
                person_id=op.person_id,
                last_raise_turn=op.last_raise_turn,
                accelerated_years=op.accelerated_years,
                last_promoted_turn=op.last_promoted_turn,
            )
        )
    session.execute(delete(OrgMoraleNudgeRow))
    session.add_all(
        OrgMoraleNudgeRow(person_id=n.person_id, turn=n.turn, points=n.points, reason=n.reason)
        for n in org.nudges
    )


# --- Org actions in their own transaction (TST ADR-0014) ------------------------------------


def action_payload(action: OrgAction) -> str:
    return json.dumps(asdict(action), sort_keys=True)


def action_from_payload(payload: str) -> OrgAction:
    fields = json.loads(payload)
    return ACTION_TYPES[fields["kind"]](**fields)


def log_decision(session: Session, turn: int, source: str, payload: str) -> None:
    """Append a decision_log row with the turn's next seq (1, 2, 3, ...)."""
    last = session.scalar(select(func.max(DecisionLogRow.seq)).where(DecisionLogRow.turn == turn))
    session.add(DecisionLogRow(turn=turn, seq=(last or 0) + 1, source=source, payload_json=payload))


def run_org_action(path: Path, action: OrgAction, balance: Balance, data: GameData) -> OrgOutcome:
    """Load, apply one org action, write the state and the decision log: one transaction."""
    from ptk.db.state_io import load_state, write_people

    sessions = make_sessionmaker(shared_engine(path))
    with sessions() as session, session.begin():
        state = load_state(session)
        if state.ended:
            raise GameOverError("the game is over")
        outcome = apply_org_action(state, action, balance, data)
        write_people(session, outcome.state)
        write_org(session, outcome.state)
        log_decision(session, state.turn, "player", action_payload(action))
    return outcome


def write_delegate_actions(
    session: Session, turn: int, actions: tuple[DelegateAction, ...]
) -> None:
    """Delegate steps go to the decision log for history (ADR-0015 5); replay recomputes them."""
    for action in actions:
        log_decision(session, turn, "delegate", json.dumps(action.payload(), sort_keys=True))
