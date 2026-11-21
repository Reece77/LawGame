"""PT-M7a sub-task 4: early case assessment (spec 7.6). The revealed range always holds the
true merits, narrows with a better lead, costs energy and the lead's hours, and feeds the
outlook band; the merits themselves never reach a view."""

from __future__ import annotations

from dataclasses import replace

import pytest

from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import MatterActionError
from ptk.sim.matters.actions import AssessCase
from ptk.sim.matters.assessment import half_width, merits_range, merits_words
from ptk.sim.matters.intake import with_matter
from ptk.sim.matters.models import Matter
from ptk.sim.matters.staffing import fee_earners
from ptk.sim.people.models import Person
from ptk.sim.rng import RngFactory
from tests.hiring_helpers import Game, start


def _with_skills(person: Person, value: float, balance: Balance) -> Person:
    return replace(
        person, skills=person.skills.updated(dict.fromkeys(balance.assessment.skills, value))
    )


def test_the_range_holds_the_merits_on_1000_cases(data: GameData, balance: Balance) -> None:
    g = start(data, balance)
    lead = g.state.person(g.founder_id)
    gen = RngFactory(7).stream(0, "misc")
    for _ in range(1000):
        merits = balance.outcomes.merits_sd * float(gen.standard_normal())
        lo, hi = merits_range(merits, lead, float(gen.random()), balance)
        assert lo <= merits <= hi
        assert hi - lo == pytest.approx(2 * half_width(lead, balance))


def test_a_better_lead_narrows_the_range(data: GameData, balance: Balance) -> None:
    g = start(data, balance)
    lead = g.state.person(g.founder_id)
    weak, strong = _with_skills(lead, 6.0, balance), _with_skills(lead, 18.0, balance)
    assert half_width(strong, balance) < half_width(weak, balance)
    assert (
        half_width(_with_skills(lead, 20.0, balance), balance) >= balance.assessment.min_half_width
    )


def test_words_for_the_range() -> None:
    assert merits_words(-2.0, -1.5) == "weak"
    assert merits_words(-0.5, 0.2) == "leaning against us to even"


def _case(g: Game) -> Matter:
    for _ in range(36):
        cases = [
            m
            for m in g.state.market.open_matters(g.state.player.id)
            if g.data.market.kinds[m.kind].outcome == "case" and m.lead_id is not None
        ]
        if cases:
            return cases[0]
        g.advance()
    raise AssertionError("no case in three years")


def test_assessment_costs_energy_and_the_leads_hours(data: GameData, balance: Balance) -> None:
    g = start(data, balance, seed=4, scenario="group_lift")
    m = _case(g)
    assert m.lead_id is not None
    energy = g.state.person_state(g.founder_id).energy
    other = {e.id: e.other for e in fee_earners(g.state, 1, data, balance)}[m.lead_id]
    g.act(AssessCase(g.founder_id, m.id))
    assessed = g.state.market.matter(m.id)
    assert assessed is not None and assessed.assessment is not None
    a = assessed.assessment
    assert a.turn == g.state.turn and a.lo <= assessed.merits <= a.hi
    assert energy is not None
    assert (
        g.state.person_state(g.founder_id).energy == energy - balance.energy.cost["case_assessment"]
    )
    after = {e.id: e.other for e in fee_earners(g.state, 1, data, balance)}[m.lead_id]
    assert after == other + balance.assessment.lead_hours * 10
    assert any(i.kind == "case_assessed" for i in g.log)
    with pytest.raises(MatterActionError):  # once per case
        g.act(AssessCase(g.founder_id, m.id))


def test_only_cases_with_a_lead_can_be_assessed(data: GameData, balance: Balance) -> None:
    g = start(data, balance, seed=4, scenario="group_lift")
    m = _case(g)
    g.state = replace(g.state, market=with_matter(g.state.market, replace(m, lead_id=None)))
    with pytest.raises(MatterActionError):
        g.act(AssessCase(g.founder_id, m.id))
    deal = replace(m, kind="deal")  # a deal's outcome is not a case's
    g.state = replace(g.state, market=with_matter(g.state.market, deal))
    with pytest.raises(MatterActionError):
        g.act(AssessCase(g.founder_id, m.id))
