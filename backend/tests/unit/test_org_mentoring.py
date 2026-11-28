"""Mentoring and growth (TST formulas.md 13.5): the supervising partner's M_growth multiplies
each employee's monthly growth in phase 8."""

from __future__ import annotations

import pytest

from ptk.sim.data_models import Balance, GameData
from ptk.sim.decisions import Decisions
from ptk.sim.org.actions import CreateUnit, MovePerson, SetLeader
from ptk.sim.org.rules import growth_multipliers, manager_terms, org_view
from ptk.sim.people.models import WorkMonth, role_ability
from ptk.sim.state import GameState
from ptk.sim.streams import RngFactory
from ptk.sim.turn import advance_turn
from tests.matters_support import solvent
from tests.org_support import FIRM, act, founder, game, staff, with_skills, with_tags


def _work(state: GameState) -> tuple[WorkMonth, ...]:
    """Everyone billed 160 substantive corporate hours."""
    out = []
    for p in state.people:
        out.append(WorkMonth(p.id, (("corporate_ma", 1600),), substantive_tenths=1600))
    return tuple(out)


def _led_team(
    data: GameData, balance: Balance, mentoring: float, mentor_tag: bool
) -> tuple[GameState, int, int]:
    """A team led by `lead` with one junior; the lead's mentoring is set, tags cleared."""
    state = game(data, balance)
    for p in staff(state):
        state = with_tags(state, p.id)
    fid = founder(state)
    people = staff(state)
    lead = next(p.id for p in people if p.level == "associate_6")
    junior = next(p.id for p in people if p.level == "associate_1")
    other = next(p.id for p in people if p.level == "associate_2")
    state = act(state, CreateUnit(fid, "team", "Trial"), data, balance)
    team = state.org.firm_units(FIRM)[0].id
    for pid in (lead, junior, other):
        state = act(state, MovePerson(fid, pid, team), data, balance)
    state = act(state, SetLeader(fid, team, lead), data, balance)
    state = with_skills(state, lead, leadership=14, communication=12, mentoring=mentoring)
    if mentor_tag:
        state = with_tags(state, other, "mentor")
    return state, lead, junior


def test_multiplier_reaches_phase_eight(data: GameData, balance: Balance) -> None:
    state, lead, junior = _led_team(data, balance, mentoring=10, mentor_tag=False)
    mult = growth_multipliers(state, balance)
    assert mult[junior] == pytest.approx(1.25)
    assert mult[founder(state)] == 1.0
    view = org_view(state, FIRM)
    assert mult[lead] == manager_terms(state, view, lead, balance).growth
    state2, _, junior2 = _led_team(data, balance, mentoring=10, mentor_tag=True)
    assert growth_multipliers(state2, balance)[junior2] == pytest.approx(1.40)


def _grow(
    data: GameData, balance: Balance, mentoring: float, mentor_tag: bool, months: int
) -> float:
    state, _, junior = _led_team(data, balance, mentoring, mentor_tag)
    rng = RngFactory(state.save_meta.master_seed)
    for _ in range(months):
        state = advance_turn(
            state, Decisions(), rng, solvent(balance), data, {}, _work(state)
        ).new_state
    person = state.person(junior)
    return role_ability(person.skills, data.role(person.role))


def test_a_strong_mentor_grows_juniors_faster(data: GameData, balance: Balance) -> None:
    """Same seed, same hours: only the lead's mentoring differs (seeded)."""
    start, _, junior = _led_team(data, balance, 10, False)
    p0 = start.person(junior)
    ca0 = role_ability(p0.skills, data.role(p0.role))
    weak = _grow(data, balance, mentoring=1, mentor_tag=False, months=12)
    neutral = _grow(data, balance, mentoring=5, mentor_tag=False, months=12)
    strong = _grow(data, balance, mentoring=12, mentor_tag=False, months=12)
    tagged = _grow(data, balance, mentoring=12, mentor_tag=True, months=12)
    assert ca0 < weak < neutral < strong < tagged
    # Growth scales with M_growth: weak 0.8, neutral 1.0, strong 1.35, with a mentor 1.5.
    assert (weak - ca0) / (neutral - ca0) == pytest.approx(0.8, rel=0.05)
    assert (strong - ca0) / (neutral - ca0) == pytest.approx(1.35, rel=0.05)
    assert (tagged - ca0) / (neutral - ca0) == pytest.approx(1.5, rel=0.05)
    # Deterministic: the same run twice gives the same result.
    assert _grow(data, balance, mentoring=12, mentor_tag=False, months=12) == strong


def test_over_span_supervisor_slows_growth(data: GameData, balance: Balance) -> None:
    """The founding partner with 10 direct reports (span 7 at leadership 11) mentors at
    S = 0.7: M_growth = 1 + (10 x 0.7 - 5) / 20 = 1.10 rather than 1.25."""
    state = game(data, balance)
    for p in staff(state):
        state = with_tags(state, p.id)
    fid = founder(state)
    state = with_skills(state, fid, leadership=11, communication=10, mentoring=10)
    some = staff(state)[0].id
    assert growth_multipliers(state, balance)[some] == pytest.approx(1.10)
