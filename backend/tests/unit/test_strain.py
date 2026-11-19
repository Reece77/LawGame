"""Strain and burnout (spec 5.6; ADR PT-0006 section 3), including the spec's worked example
and the founder's case."""

from __future__ import annotations

from dataclasses import replace

import pytest

from ptk.sim.data_models import Balance, GameData
from ptk.sim.people.formulas import strain_comfort, strain_delta
from ptk.sim.people.founder import FounderSpec
from ptk.sim.people.models import Person, WorkMonth
from ptk.sim.people.strain import (
    burnout_effects_active,
    initial_strain,
    monthly_capacity_tenths,
    strain_month,
)
from ptk.sim.rng import RngFactory
from tests.unit.test_founder import build
from tests.unit.test_people_generation import make


def neutral(data: GameData, balance: Balance, level: str = "associate_4") -> Person:
    """An associate with stamina 10, burnout risk 10, no tags, strain 20 (spec 5.6)."""
    p = make(data, balance, "corporate_ma", level)
    return replace(
        p,
        skills=p.skills.updated({"stamina": 10}),
        hidden=p.hidden.updated({"burnout_risk": 10}),
        tags=(),
        strain=20.0,
    )


def yearly(person: Person, hours_a_year: int, rest: str = "none") -> WorkMonth:
    tenths = round(hours_a_year * 10 / 12)
    return WorkMonth(person.id, (("corporate_ma", tenths),), rest=rest)  # type: ignore[arg-type]


def months_to_burnout(
    person: Person, hours_a_year: int, balance: Balance, limit: int
) -> int | None:
    for month in range(1, limit + 1):
        person = strain_month(person, month, yearly(person, hours_a_year), balance)
        if person.burnt_out:
            return month
    return None


def test_spec_worked_example(data: GameData, balance: Balance) -> None:
    """2,600 hours a year (1.13 x 2,300) adds 60 x 0.13 = 7.8 a month: from 20, burnout in
    about 8 months. At 2,200 hours: never."""
    person = neutral(data, balance)
    first = strain_month(person, 1, yearly(person, 2600), balance)
    assert first.strain - 20 == pytest.approx(7.83, abs=0.01)
    assert months_to_burnout(person, 2600, balance, 24) == 8
    assert months_to_burnout(person, 2200, balance, 360) is None
    steady = strain_month(person, 1, yearly(person, 2200), balance)
    assert steady.strain == pytest.approx(12.0)  # -8 a month under comfort


def test_comfort_and_risk_terms(data: GameData, balance: Balance) -> None:
    cfg = balance.strain
    assert strain_comfort(10, cfg) == pytest.approx(1.0)
    assert strain_comfort(16, cfg) == pytest.approx(1.06)
    args = {"hours_tenths": 2400, "capacity_tenths": 2000.0, "rest": "none", "strain": cfg}
    base = strain_delta(stamina=10, burnout_risk=10, grinder=False, **args)  # type: ignore[arg-type]
    assert base == pytest.approx(60 * 0.2)
    risky = strain_delta(stamina=10, burnout_risk=20, grinder=False, **args)  # type: ignore[arg-type]
    assert risky == pytest.approx(60 * 0.2 * 1.5)
    grinder = strain_delta(stamina=10, burnout_risk=10, grinder=True, **args)  # type: ignore[arg-type]
    assert grinder == pytest.approx(60 * 0.2 * 0.7)
    tough = strain_delta(stamina=20, burnout_risk=10, grinder=False, **args)  # type: ignore[arg-type]
    assert tough == pytest.approx(60 * 0.1)


def test_holiday_and_sabbatical(data: GameData, balance: Balance) -> None:
    person = replace(neutral(data, balance), strain=60.0)
    holiday = strain_month(person, 1, yearly(person, 1000, "holiday"), balance)
    sabbatical = strain_month(person, 1, WorkMonth(person.id, rest="sabbatical"), balance)
    assert holiday.strain == pytest.approx(35.0) and sabbatical.strain == pytest.approx(20.0)
    floor = strain_month(replace(person, strain=5.0), 1, WorkMonth(person.id), balance)
    assert floor.strain == 0.0


def test_burnout_cuts_capacity_and_recovers(data: GameData, balance: Balance) -> None:
    person = neutral(data, balance)
    normal = monthly_capacity_tenths(person, balance)
    assert normal == pytest.approx(23000 / 12)
    for month in range(1, 9):
        person = strain_month(person, month, yearly(person, 2600), balance)
    assert person.burnt_out and person.burnout_since == 8 and person.last_burnout_turn == 8
    assert monthly_capacity_tenths(person, balance) == pytest.approx(normal * 0.7)
    assert burnout_effects_active(person, 13, balance)
    assert not burnout_effects_active(person, 14, balance)
    # pushing on at 2,600 hours against capacity x 0.7 drives strain to the ceiling
    pushed = strain_month(person, 9, yearly(person, 2600), balance)
    assert pushed.strain > person.strain and pushed.burnt_out
    # light months: -8 each, burnout ends once strain falls below 40
    month, rested = 9, person
    while rested.burnt_out:
        rested = strain_month(rested, month, yearly(rested, 1000), balance)
        month += 1
    assert rested.strain < 40 and rested.burnout_since is None
    assert rested.last_burnout_turn == 8 and month - 9 == 6  # 82.6 -> 34.6 in six months


def test_founders_case(data: GameData, balance: Balance) -> None:
    """The founding partner carries the same strain (TST 32.1's stress): starting at 20, with
    an equity partner's 2,200-hour capacity, 2,600 hours burns out sooner than an
    associate's case."""
    founder = build(data, balance, FounderSpec(background="trial_lawyer"))
    founder = replace(
        founder,
        skills=founder.skills.updated({"stamina": 10}),
        hidden=founder.hidden.updated({"burnout_risk": 10}),
        tags=(),
    )
    assert founder.strain == 20.0
    # 2,600 / 2,200 = 1.18: +10.9 a month, burnout in the 6th month
    assert months_to_burnout(founder, 2600, balance, 24) == 6
    assert months_to_burnout(founder, 2100, balance, 360) is None


def test_initial_strain_is_seeded(balance: Balance) -> None:
    rng = RngFactory(8)
    value = initial_strain(rng, 0, 5, balance)
    assert 10 <= value <= 30 and value == initial_strain(rng, 0, 5, balance)
    assert value != initial_strain(rng, 0, 6, balance)
