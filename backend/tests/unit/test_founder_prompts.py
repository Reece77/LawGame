"""PT-M17 acceptance: no hidden value reaches a prompt (CLAUDE.md section 10; ADR-0005 4).

A family's members carry planted potential and hidden traits, and partners a planted
confidence; prompts built for every event template carry none of them (the API side is
tests/integration/test_founder_api.py)."""

from __future__ import annotations

from dataclasses import replace

from ptk.events.context import build_prompt
from ptk.events.service import kpis_of
from ptk.sim.data_models import Balance, GameData
from ptk.sim.events.director import eligible_targets
from ptk.sim.family.setup import FamilySpec
from ptk.sim.partnership.models import with_firm_partnership, with_partner
from ptk.sim.state import with_people
from tests.founder_support import start_life
from tests.unit.test_events_context import _events_for_every_template

POTENTIAL = 163.98765
HIDDEN = 18.76543
CONFIDENCE = 47.123456


def test_no_family_or_confidence_value_reaches_a_prompt(data: GameData, balance: Balance) -> None:
    g = start_life(data, balance, seed=5, family=FamilySpec("children", (8, 22)), age=50)
    g.advance(6)
    state = g.state
    members = {m.person_id for m in state.family.members}
    people = [
        replace(
            p,
            potential_ability=POTENTIAL,
            hidden=p.hidden.updated({k: HIDDEN for k, _ in p.hidden.items}),
        )
        for p in state.people
        if p.id in members
    ]
    state = with_people(state, people)
    fp = state.partnership.of(state.player.id)
    assert fp is not None
    for p in fp.partners:
        fp = with_partner(fp, replace(p, confidence=CONFIDENCE))
    state = replace(state, partnership=with_firm_partnership(state.partnership, fp))
    kpis = kpis_of(state, 100_000_00, data)
    for event in _events_for_every_template(state, data):
        template = data.event_template(event.template_id)
        system, user = build_prompt(
            state, event, template, eligible_targets(state, event), kpis, balance, data
        )
        text = system + user
        for marker in (POTENTIAL, HIDDEN, CONFIDENCE):
            assert str(marker) not in text, (event.template_id, marker)
        for pid in members:  # the family is not the firm's business
            p = state.person(pid)
            assert f"{p.first_name} {p.last_name}" not in text
