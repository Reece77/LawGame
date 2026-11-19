"""Org invariants under any sequence of reorganising actions (TST formulas.md 13.1, 13.7):
every leader is a member of the unit they lead and leads one unit; members sit in active
units; teams sit under the root or a practice group; one group per practice; no cycles."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from ptk.loader import load_balance, load_game_data
from ptk.sim.errors import SimError
from ptk.sim.org.actions import (
    CreateUnit,
    DissolveUnit,
    MovePerson,
    MoveUnit,
    OrgAction,
    SetLeader,
    apply_org_action,
)
from ptk.sim.org.rules import org_view
from tests.conftest import DATA_DIR
from tests.org_support import FIRM, founder, game

DATA = load_game_data(DATA_DIR)
BALANCE = load_balance(DATA_DIR)
START = game(DATA, BALANCE)
FID = founder(START)
PEOPLE = sorted(START.staff_ids(FIRM))
PRACTICES = ("corporate_ma", "commercial_litigation", "white_collar")

step = st.one_of(
    st.builds(lambda p: CreateUnit(FID, "practice_group", practice=p), st.sampled_from(PRACTICES)),
    st.builds(
        lambda n, parent: CreateUnit(FID, "team", f"Team {n}", parent_id=parent),
        st.integers(0, 3),
        st.one_of(st.none(), st.integers(1, 8)),
    ),
    st.builds(lambda u: DissolveUnit(FID, u), st.integers(1, 8)),
    st.builds(
        lambda u, parent: MoveUnit(FID, u, parent),
        st.integers(1, 8),
        st.one_of(st.none(), st.integers(1, 8)),
    ),
    st.builds(
        lambda p, u: MovePerson(FID, p, u),
        st.sampled_from(PEOPLE),
        st.one_of(st.none(), st.integers(1, 8)),
    ),
    st.builds(
        lambda u, p: SetLeader(FID, u, p),
        st.integers(1, 8),
        st.one_of(st.none(), st.sampled_from(PEOPLE)),
    ),
)


@settings(max_examples=150, deadline=None)
@given(st.lists(step, max_size=40))
def test_org_invariants(actions: list[OrgAction]) -> None:
    state = START
    for action in actions:
        try:
            state = apply_org_action(state, action, BALANCE, DATA).state
        except SimError:
            continue  # a refused action changes nothing
    org = state.org
    active = {u.id: u for u in org.firm_units(FIRM)}
    for unit in active.values():
        if unit.leader_id is not None:
            assert org.unit_of(unit.leader_id) == unit.id
            assert sum(1 for u in active.values() if u.leader_id == unit.leader_id) == 1
        if unit.kind == "practice_group":
            assert unit.parent_id is None and unit.practice is not None
        elif unit.parent_id is not None:
            assert active[unit.parent_id].kind == "practice_group"
    practices = [u.practice for u in active.values() if u.kind == "practice_group"]
    assert len(practices) == len(set(practices))
    for m in org.members:
        assert m.unit_id in active and m.person_id != FID
    view = org_view(state, FIRM)
    for pid in PEOPLE:  # every chain ends at the founding partner, without a cycle
        seen, cur = set(), pid
        while view.manager_of[cur] is not None:
            assert cur not in seen
            seen.add(cur)
            cur = view.manager_of[cur]  # type: ignore[assignment]
        assert cur == FID
    assert all(n.points < 0 for n in org.nudges)  # reorganising only ever costs morale
