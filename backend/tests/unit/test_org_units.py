"""Units, leaders and moves (TST formulas.md 13.1, 13.7) and their rules."""

from __future__ import annotations

import pytest

from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import NotFoundError, OrgActionError, OrgRuleError, UnknownUnitError
from ptk.sim.org.actions import (
    CreateUnit,
    DissolveUnit,
    MovePerson,
    MoveUnit,
    RenameUnit,
    SetLeader,
)
from ptk.sim.state import GameState
from tests.org_support import FIRM, act, founder, game, staff


def _group(
    state: GameState, data: GameData, balance: Balance, practice: str
) -> tuple[GameState, int]:
    state = act(
        state, CreateUnit(founder(state), "practice_group", practice=practice), data, balance
    )
    return state, state.org.firm_units(FIRM)[-1].id


def test_practice_group_defaults_to_its_practice(data: GameData, balance: Balance) -> None:
    state, gid = _group(game(data, balance), data, balance, "commercial_litigation")
    unit = state.org.unit(gid)
    assert unit is not None
    assert (unit.kind, unit.name, unit.practice, unit.parent_id) == (
        "practice_group",
        "Commercial litigation",
        "commercial_litigation",
        None,
    )


def test_practice_group_rules(data: GameData, balance: Balance) -> None:
    state = game(data, balance)
    fid = founder(state)
    state, _ = _group(state, data, balance, "corporate_ma")
    with pytest.raises(OrgRuleError, match="already has a group"):
        act(state, CreateUnit(fid, "practice_group", practice="corporate_ma"), data, balance)
    with pytest.raises(OrgActionError):
        # PT-M12: tax is a practice now; an unknown key still fails
        act(state, CreateUnit(fid, "practice_group", practice="aviation"), data, balance)
    small = game(data, balance, scenario="biglaw_spinout")
    with pytest.raises(OrgRuleError, match="unlock at 10 lawyers"):
        act(small, CreateUnit(founder(small), "practice_group", practice="ip"), data, balance)
    # Teams need no unlock.
    assert act(small, CreateUnit(founder(small), "team", "Deals"), data, balance).org.units


def test_team_placement_rules(data: GameData, balance: Balance) -> None:
    state, gid = _group(game(data, balance), data, balance, "corporate_ma")
    fid = founder(state)
    state = act(state, CreateUnit(fid, "team", "Deals", parent_id=gid), data, balance)
    team = state.org.firm_units(FIRM)[-1].id
    with pytest.raises(OrgRuleError, match="under the firm or a practice group"):
        act(state, CreateUnit(fid, "team", "Sub", parent_id=team), data, balance)
    with pytest.raises(OrgRuleError, match="already a unit"):
        act(state, CreateUnit(fid, "team", " deals "), data, balance)
    with pytest.raises(OrgRuleError):
        act(state, MoveUnit(fid, gid, team), data, balance)
    state = act(state, MoveUnit(fid, team, None), data, balance)
    assert state.org.unit(team).parent_id is None  # type: ignore[union-attr]
    state = act(state, RenameUnit(fid, team, "Transactions"), data, balance)
    assert state.org.unit(team).name == "Transactions"  # type: ignore[union-attr]


def test_leader_rules_and_morale(data: GameData, balance: Balance) -> None:
    state, gid = _group(game(data, balance), data, balance, "corporate_ma")
    fid = founder(state)
    a, b, c = (p.id for p in staff(state)[:3])
    with pytest.raises(OrgRuleError, match="member of the unit"):
        act(state, SetLeader(fid, gid, a), data, balance)
    for pid in (a, b, c):
        state = act(state, MovePerson(fid, pid, gid), data, balance)
    assert [(n.person_id, n.points) for n in state.org.nudges] == [(a, -2), (b, -2), (c, -2)]
    state = act(state, SetLeader(fid, gid, a), data, balance)
    assert [(n.person_id, n.points) for n in state.org.nudges[3:]] == [(b, -1), (c, -1)]
    state = act(state, SetLeader(fid, gid, b), data, balance)  # a replaced, stays in the unit
    assert [(n.person_id, n.points) for n in state.org.nudges[5:]] == [(a, -5), (c, -1)]
    with pytest.raises(OrgRuleError, match="lead"):
        act(state, MovePerson(fid, b, None), data, balance)
    with pytest.raises(OrgRuleError, match="managing founding partner"):
        act(state, SetLeader(fid, gid, fid), data, balance)
    with pytest.raises(OrgRuleError, match="managing founding partner"):
        act(state, MovePerson(fid, fid, gid), data, balance)
    with pytest.raises(NotFoundError):
        act(state, MovePerson(fid, 999, gid), data, balance)
    with pytest.raises(UnknownUnitError):
        act(state, MovePerson(fid, c, 999), data, balance)
    state = act(state, SetLeader(fid, gid, None), data, balance)  # b removed, stays
    assert state.org.nudges[-2].points == -5 and state.org.unit(gid).leader_id is None  # type: ignore[union-attr]
    with pytest.raises(OrgRuleError, match="no leader to remove"):
        act(state, SetLeader(fid, gid, None), data, balance)


def test_a_person_leads_at_most_one_unit(data: GameData, balance: Balance) -> None:
    state = game(data, balance)
    fid = founder(state)
    state = act(state, CreateUnit(fid, "team", "One"), data, balance)
    state = act(state, CreateUnit(fid, "team", "Two"), data, balance)
    one, two = (u.id for u in state.org.firm_units(FIRM))
    a = staff(state)[0].id
    state = act(state, MovePerson(fid, a, one), data, balance)
    state = act(state, SetLeader(fid, one, a), data, balance)
    with pytest.raises(OrgRuleError, match="replace or remove"):
        act(state, MovePerson(fid, a, two), data, balance)


def test_dissolve_moves_members_and_teams_up(data: GameData, balance: Balance) -> None:
    state, gid = _group(game(data, balance), data, balance, "corporate_ma")
    fid = founder(state)
    state = act(state, CreateUnit(fid, "team", "Deals", parent_id=gid), data, balance)
    team = state.org.firm_units(FIRM)[-1].id
    a, b = (p.id for p in staff(state)[:2])
    state = act(state, MovePerson(fid, a, gid), data, balance)
    state = act(state, MovePerson(fid, b, team), data, balance)
    state = act(state, SetLeader(fid, gid, a), data, balance)
    before = len(state.org.nudges)
    state = act(state, DissolveUnit(fid, gid), data, balance)
    assert state.org.unit_of(a) is None and state.org.unit_of(b) == team
    assert state.org.unit(team).parent_id is None  # type: ignore[union-attr]
    dissolved = state.org.unit(gid)
    assert dissolved is not None and dissolved.status == "dissolved" and dissolved.leader_id is None
    assert [(n.person_id, n.points) for n in state.org.nudges[before:]] == [(a, -2)]
    assert [u.id for u in state.org.firm_units(FIRM)] == [team]
    # A dissolved practice's group may be created again.
    state, again = _group(state, data, balance, "corporate_ma")
    assert again != gid
