"""The org in a save (schema v3): round trips, the decision log, one transaction per action."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import select

from ptk.db import saves
from ptk.db.core import make_sessionmaker, shared_engine
from ptk.db.models import DecisionLogRow
from ptk.db.org_io import action_from_payload, run_org_action
from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import OrgRuleError, SimError
from ptk.sim.org.actions import CreateUnit, MovePerson, Promote, SetLeader


def _new(save_dir: Path, data: GameData, balance: Balance) -> Path:
    saves.create_save(
        save_dir,
        "org",
        firm_name="Org LLP",
        scenario_id="group_lift",
        difficulty="standard",
        data=data,
        balance=balance,
        seed=11,
    )
    return saves.open_save(save_dir, "org")


def test_org_round_trips_through_the_save(save_dir: Path, data: GameData, balance: Balance) -> None:
    path = _new(save_dir, data, balance)
    state, _ = saves.read_state(path)
    fid = state.founder_of(1)
    assert fid is not None
    a = next(p.id for p in state.people if not p.is_founder and p.level == "associate_5")
    out = run_org_action(
        path, CreateUnit(fid, "practice_group", practice="corporate_ma"), balance, data
    )
    gid = out.unit_id
    assert gid is not None
    run_org_action(path, MovePerson(fid, a, gid), balance, data)
    run_org_action(path, SetLeader(fid, gid, a), balance, data)
    run_org_action(path, Promote(fid, a), balance, data)
    loaded, _ = saves.read_state(path)
    assert loaded.org.unit(gid).leader_id == a  # type: ignore[union-attr]
    assert loaded.org.unit_of(a) == gid
    assert loaded.person(a).level == "associate_6"
    assert loaded.org.person(a).accelerated_years == 1
    assert [n.reason for n in loaded.org.nudges] == ["moved", "promoted"]
    # A turn keeps the org and clears this turn's one-off morale changes after phase 8.
    saves.run_turn(path, balance, data)
    after, _ = saves.read_state(path)
    assert after.org.units == loaded.org.units and after.org.members == loaded.org.members
    assert after.org.nudges == ()
    # The decision log holds each action in seq order, and payloads load back.
    with make_sessionmaker(shared_engine(path))() as session:
        rows = session.scalars(select(DecisionLogRow).order_by(DecisionLogRow.id)).all()
    rows = [r for r in rows if r.source != "rival"]  # PT-M5: rivals' decisions are logged too
    assert [(r.turn, r.seq, r.source) for r in rows] == [(0, i, "player") for i in (1, 2, 3, 4)]
    assert action_from_payload(rows[2].payload_json) == SetLeader(fid, gid, a)
    assert json.loads(rows[0].payload_json)["kind"] == "create_unit"


def test_a_refused_action_writes_nothing(save_dir: Path, data: GameData, balance: Balance) -> None:
    path = _new(save_dir, data, balance)
    state, _ = saves.read_state(path)
    fid = state.founder_of(1)
    assert fid is not None
    with pytest.raises(SimError):
        run_org_action(path, SetLeader(fid, 1, fid), balance, data)
    with pytest.raises(OrgRuleError):
        run_org_action(path, MovePerson(fid, fid, None), balance, data)
    after, _ = saves.read_state(path)
    assert after.org == state.org
    with make_sessionmaker(shared_engine(path))() as session:
        assert session.scalars(select(DecisionLogRow)).all() == []
