"""Span, supervisor quality, the morale term and mentoring (TST formulas.md 13.1-13.5),
including TST 13.12's worked examples in Partner Track's units."""

from __future__ import annotations

import pytest

from ptk.sim.data_models import Balance, GameData
from ptk.sim.org.actions import CreateUnit, MovePerson, SetLeader
from ptk.sim.org.formulas import (
    growth_multiplier,
    manager_label,
    manager_morale_term,
    manager_quality,
    pitch,
    span_factor,
    span_limit,
)
from ptk.sim.org.rules import lawyer_count, manager_terms, org_view, practice_groups_unlocked
from ptk.sim.state import GameState
from tests.org_support import FIRM, act, founder, game, hire, staff, with_skills, with_tags

# --- TST 13.12, formula by formula ------------------------------------------------------------


def test_team_lead_six_reports(balance: Balance) -> None:
    org = balance.org
    assert span_limit(14, org) == 8
    s = span_factor(14, 6, org)
    assert s == 1.0
    q = manager_quality(14, 12, 10, s)
    assert q == pytest.approx(12.5)
    assert manager_morale_term(q, org) == pytest.approx(2.0)
    assert growth_multiplier(10, s, False, org) == pytest.approx(1.25)
    assert growth_multiplier(10, s, True, org) == pytest.approx(1.40)


def test_same_lead_twelve_reports(balance: Balance) -> None:
    org = balance.org
    s = span_factor(14, 12, org)
    assert s == pytest.approx(0.667, abs=1e-3)
    q = manager_quality(14, 12, 10, s)
    assert q == pytest.approx(8.33, abs=1e-2)
    assert manager_morale_term(q, org) == pytest.approx(-1.33, abs=1e-2)


def test_founder_managing_twelve(balance: Balance) -> None:
    org = balance.org
    assert span_limit(11, org) == 7
    s = span_factor(11, 12, org)
    assert s == pytest.approx(0.583, abs=1e-3)
    q = manager_quality(11, 10, 5, s)
    assert q == pytest.approx(5.40, abs=1e-2)
    assert manager_morale_term(q, org) == pytest.approx(-3.68, abs=1e-2)
    assert growth_multiplier(5, s, False, org) == pytest.approx(0.90, abs=1e-2)


def test_founder_with_two_leads(balance: Balance) -> None:
    org = balance.org
    s = span_factor(11, 2, org)
    q = manager_quality(11, 10, 5, s)
    assert (s, q) == (1.0, pytest.approx(9.25))
    assert manager_morale_term(q, org) == pytest.approx(-0.60)


def test_lead_b(balance: Balance) -> None:
    org = balance.org
    assert span_limit(12, org) == 8
    q = manager_quality(12, 11, 7, span_factor(12, 5, org))
    assert q == pytest.approx(10.5)
    assert manager_morale_term(q, org) == pytest.approx(0.40)
    assert growth_multiplier(7, 1.0, False, org) == pytest.approx(1.10)


def test_offer_pitch(balance: Balance) -> None:
    assert pitch(7, balance.org) == pytest.approx(-0.09)
    assert pitch(15, balance.org) == pytest.approx(0.15)


def test_caps_and_labels(balance: Balance) -> None:
    org = balance.org
    assert manager_morale_term(30, org) == 8 and manager_morale_term(-30, org) == -8
    assert growth_multiplier(20, 1.0, True, org) == 1.5
    assert growth_multiplier(0, 1.0, False, org) == 0.75
    assert manager_label(2.0, org) == "strong"
    assert manager_label(0.4, org) == "fine"
    assert manager_label(-3.68, org) == "stretched"


# --- The same examples through a firm's reporting lines ---------------------------------------


def _firm_of_thirteen(data: GameData, balance: Balance) -> GameState:
    """The group-lift firm (founder plus ten) with two more hires: 12 report to the founder."""
    state = game(data, balance)
    state, _ = hire(state, data, balance, "corporate_ma", "associate_2", 1)
    state, _ = hire(state, data, balance, "ip", "associate_3", 2)
    for p in staff(state):
        state = with_tags(state, p.id)  # no stray mentor tags: 13.12 has none
    return with_skills(state, founder(state), leadership=11, communication=10, mentoring=5)


def test_flat_firm_founder_manages_everyone(data: GameData, balance: Balance) -> None:
    state = _firm_of_thirteen(data, balance)
    view = org_view(state, FIRM)
    fid = founder(state)
    assert len(view.reports[fid]) == 12
    assert view.manager_of[fid] is None
    some = staff(state)[0].id
    terms = manager_terms(state, view, some, balance)
    assert terms.manager_id == fid and terms.span_limit == 7
    assert terms.quality == pytest.approx(5.40, abs=1e-2)
    assert terms.morale == pytest.approx(-3.68, abs=1e-2)
    assert terms.growth == pytest.approx(0.90, abs=1e-2)
    # The founding partner has no supervisor: neutral terms.
    own = manager_terms(state, view, fid, balance)
    assert (own.manager_id, own.morale, own.growth) == (None, 0.0, 1.0)


def test_two_team_leads_remove_the_penalty(data: GameData, balance: Balance) -> None:
    state = _firm_of_thirteen(data, balance)
    fid = founder(state)
    people = [p.id for p in staff(state)]
    lead_a, lead_b = people[0], people[1]
    state = with_skills(state, lead_a, leadership=14, communication=12, mentoring=10)
    state = with_skills(state, lead_b, leadership=12, communication=11, mentoring=7)
    state = act(state, CreateUnit(fid, "team", "Team A"), data, balance)
    state = act(state, CreateUnit(fid, "team", "Team B"), data, balance)
    team_a, team_b = (u.id for u in state.org.firm_units(FIRM))
    a_members = [lead_a, *people[2:8]]  # lead plus 6 reports
    b_members = [lead_b, *people[8:13]]  # lead plus 5 reports
    for pid in a_members:
        state = act(state, MovePerson(fid, pid, team_a), data, balance)
    for pid in b_members:
        state = act(state, MovePerson(fid, pid, team_b), data, balance)
    state = act(state, SetLeader(fid, team_a, lead_a), data, balance)
    state = act(state, SetLeader(fid, team_b, lead_b), data, balance)
    view = org_view(state, FIRM)
    assert view.reports[fid] == tuple(sorted((lead_a, lead_b)))
    lead_terms = manager_terms(state, view, lead_a, balance)
    assert lead_terms.manager_id == fid
    assert lead_terms.quality == pytest.approx(9.25)
    assert lead_terms.morale == pytest.approx(-0.60)
    a_report = manager_terms(state, view, people[2], balance)
    assert (a_report.manager_id, a_report.reports) == (lead_a, 6)
    assert a_report.morale == pytest.approx(2.0)
    assert a_report.growth == pytest.approx(1.25)
    b_report = manager_terms(state, view, people[8], balance)
    assert b_report.morale == pytest.approx(0.40)
    assert b_report.growth == pytest.approx(1.10)
    # A mentor in Team A lifts the others' growth to 1.40 (13.5), not the mentor's own.
    state = with_tags(state, people[3], "mentor")
    view = org_view(state, FIRM)
    assert manager_terms(state, view, people[2], balance).growth == pytest.approx(1.40)
    assert manager_terms(state, view, people[3], balance).growth == pytest.approx(1.25)


def test_leaderless_unit_looks_up(data: GameData, balance: Balance) -> None:
    state = game(data, balance)
    fid = founder(state)
    state = act(state, CreateUnit(fid, "practice_group", practice="corporate_ma"), data, balance)
    group = state.org.firm_units(FIRM)[0].id
    state = act(state, CreateUnit(fid, "team", "Deals", parent_id=group), data, balance)
    team = state.org.firm_units(FIRM)[1].id
    a, b = (p.id for p in staff(state)[:2])
    state = act(state, MovePerson(fid, a, group), data, balance)
    state = act(state, MovePerson(fid, b, team), data, balance)
    view = org_view(state, FIRM)
    assert view.manager_of[b] == fid  # team and group have no leader: up to the root
    state = act(state, SetLeader(fid, group, a), data, balance)
    view = org_view(state, FIRM)
    assert view.manager_of[b] == a  # the group's leader supervises the leaderless team
    assert view.manager_of[a] == fid  # a leader looks one level up
    assert view.unit_chain(team) == (team, group)


def test_practice_groups_unlock_at_ten_lawyers(data: GameData, balance: Balance) -> None:
    small = game(data, balance, scenario="biglaw_spinout")
    assert lawyer_count(small, FIRM, data) == 4
    assert not practice_groups_unlocked(small, FIRM, data, balance)
    lift = game(data, balance)
    assert lawyer_count(lift, FIRM, data) == 10  # the paralegal does not count
    assert practice_groups_unlocked(lift, FIRM, data, balance)
