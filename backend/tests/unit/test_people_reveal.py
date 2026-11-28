"""Revealed ranges (ADR-0007, formulas.md 4; ADR PT-0006 2). Seeded."""

from __future__ import annotations

from dataclasses import replace

import pytest

from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import UnknownKnowledgeActionError
from ptk.sim.people.formulas import displayed_range, potential_phrase
from ptk.sim.people.models import PA_KEY, RevealRecord, fam_key
from ptk.sim.people.reveal import (
    apply_knowledge_action,
    new_reveal_state,
    reveal_keys,
    revealed_range,
)
from ptk.sim.streams import RngFactory
from tests.unit.test_people_generation import make


def test_worked_example_skill(balance: Balance) -> None:
    """TST formulas.md 4: true 14, offset +0.2, scout judgment 12 (scout factor 0.8)."""
    cfg = balance.reveal
    hw = cfg.initial_hw.skill
    shown = [displayed_range(14, hw, 0.2, 1, 20)]
    steps = ["job_post_screen", "interview", *["employed_month"] * 6]
    hws = []
    for action in steps:
        hw *= 1 - cfg.strength[action] * (cfg.scout_base + 12 / cfg.scout_divisor)
        hws.append(hw)
    shown += [displayed_range(14, hws[0], 0.2, 1, 20), displayed_range(14, hws[1], 0.2, 1, 20)]
    shown.append(displayed_range(14, hws[-1], 0.2, 1, 20))
    assert [round(h, 2) for h in (hws[0], hws[1], hws[-1])] == [4.2, 3.02, 2.03]
    assert shown == [(8, 18), (8, 18), (10, 17), (11, 16)]


def test_potential_phrase() -> None:
    bounds = (70.0, 100.0, 130.0, 160.0)
    assert potential_phrase(60, 193, bounds) == "limited to outstanding"
    assert potential_phrase(105, 128, bounds) == "good"


def test_stranger_ranges_hold_the_truth(data: GameData, balance: Balance) -> None:
    person = make(data, balance, "white_collar", "associate_4")
    rng = RngFactory(7)
    state = new_reveal_state(
        observer_firm_id=1, person=person, turn=3, rng=rng, data=data, balance=balance
    )
    assert [k for k, _ in state.attributes] == reveal_keys(data)
    assert state.profile_revealed_turn is None and state.revealed_tags == ()
    for key, _rec in state.attributes:
        lo, hi = revealed_range(person, state, key)
        true = (
            person.potential_ability
            if key == PA_KEY
            else person.familiarity[key[4:]]
            if key.startswith("fam:")
            else person.skills[key]
            if key in person.skills
            else person.personality[key]
        )
        assert lo <= true <= hi
    fam = state.record(fam_key("white_collar"))
    assert fam.hw == balance.reveal.initial_hw.familiarity < balance.reveal.initial_hw.skill
    again = new_reveal_state(
        observer_firm_id=1, person=person, turn=3, rng=rng, data=data, balance=balance
    )
    assert again == state  # seeded
    other = new_reveal_state(
        observer_firm_id=2, person=person, turn=3, rng=rng, data=data, balance=balance
    )
    assert other.attributes != state.attributes


def test_own_founders_known_exactly(data: GameData, balance: Balance) -> None:
    person = make(data, balance, "corporate_ma", "equity_partner")
    state = new_reveal_state(
        observer_firm_id=1,
        person=person,
        turn=0,
        rng=RngFactory(1),
        data=data,
        balance=balance,
        knows_exactly=True,
    )
    skill = data.skill_keys[0]
    assert revealed_range(person, state, skill) == (round(person.skills[skill]),) * 2
    assert state.record(PA_KEY).hw == balance.reveal.founder_pa_hw
    assert state.profile_revealed_turn == 0


def test_actions_narrow_never_widen(data: GameData, balance: Balance) -> None:
    person = make(data, balance, "ip", "associate_2")
    state = new_reveal_state(
        observer_firm_id=1, person=person, turn=0, rng=RngFactory(1), data=data, balance=balance
    )
    skills = frozenset(data.skill_keys)
    after = apply_knowledge_action(state, "interview", 10, balance, turn=1, skill_keys=skills)
    for (key, before), (_, now) in zip(state.attributes, after.attributes, strict=True):
        assert now.hw < before.hw, key
        assert now.offset == before.offset
    assert after.profile_revealed_turn == 1
    refs = apply_knowledge_action(state, "reference_check", 10, balance, turn=1, skill_keys=skills)
    assert refs.record(fam_key("ip")) == state.record(fam_key("ip"))  # not on a reference
    with pytest.raises(UnknownKnowledgeActionError):
        apply_knowledge_action(state, "rival_approach", 10, balance, turn=1, skill_keys=skills)


def test_familiarity_range_follows_growth(data: GameData, balance: Balance) -> None:
    person = make(data, balance, "ip", "associate_2")
    state = new_reveal_state(
        observer_firm_id=1, person=person, turn=0, rng=RngFactory(1), data=data, balance=balance
    )
    attrs = tuple(
        (k, RevealRecord(0.0, r.offset, 0) if k == fam_key("ip") else r)
        for k, r in state.attributes
    )
    state = replace(state, attributes=attrs)
    grown = replace(person, familiarity=person.familiarity.updated({"ip": 17.2}))
    assert revealed_range(grown, state, fam_key("ip")) == (17, 17)
