"""Growth with learning and practice familiarity (spec 5.3; ADR PT-0006 2 and 4)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from ptk.sim.data_models import Balance, GameData
from ptk.sim.people.formulas import fam_factor, familiarity_after, growth_delta, learn_factor
from ptk.sim.people.growth import grow_person
from ptk.sim.people.models import WorkMonth, current_ability
from ptk.sim.people.phase import advance_class_year
from ptk.sim.rng import RngFactory
from tests.unit.test_people_generation import make

H = 10  # tenths per hour


@pytest.mark.parametrize(
    ("age", "ca", "pa", "prof", "per_month"),
    [(24, 106, 160, 14, 0.0737), (38, 120, 128, 10, 0.0030), (58, 130, 132, 12, -0.0150)],
)
def test_tst_worked_examples_at_learn_one(
    balance: Balance, age: int, ca: float, pa: float, prof: float, per_month: float
) -> None:
    """TST formulas.md 3's table holds at learn(h) = 1 (60% substantive hours)."""
    learn = learn_factor(150 * H, 90 * H, balance.growth)
    assert learn == pytest.approx(1.0)
    delta = growth_delta(
        in_role=True,
        age=age,
        ca=ca,
        pa=pa,
        professionalism=prof,
        growth=balance.growth,
        learn=learn,
    )
    assert delta == pytest.approx(per_month, abs=5e-5)


def test_learning_scales_growth_not_decline(balance: Balance) -> None:
    args = {"in_role": True, "ca": 106, "pa": 160, "professionalism": 14}
    base = growth_delta(age=24, growth=balance.growth, **args)  # type: ignore[arg-type]
    fast = growth_delta(age=24, growth=balance.growth, learn=1.4, **args)  # type: ignore[arg-type]
    slow = growth_delta(age=24, growth=balance.growth, learn=0.5, **args)  # type: ignore[arg-type]
    assert fast == pytest.approx(1.4 * base) and slow == pytest.approx(0.5 * base)
    old = {"in_role": True, "ca": 130, "pa": 132, "professionalism": 12}
    # at 58 the growth factor is 0, so only the decline is left, whatever the learning
    assert growth_delta(age=58, growth=balance.growth, learn=1.4, **old) == pytest.approx(  # type: ignore[arg-type]
        -0.015
    )


@pytest.mark.parametrize(
    ("total", "substantive", "learn"),
    [(150, 90, 1.0), (150, 135, 1.4), (150, 30, 0.5), (0, 0, 0.5), (100, 72, 1.2)],
)
def test_learn_factor(balance: Balance, total: int, substantive: int, learn: float) -> None:
    assert learn_factor(total * H, substantive * H, balance.growth) == pytest.approx(learn)


def test_fam_factor(balance: Balance) -> None:
    fam = balance.familiarity
    assert fam_factor(1, fam) == pytest.approx(0.70)
    assert fam_factor(8, fam) == pytest.approx(0.85)
    assert fam_factor(15, fam) == fam_factor(20, fam) == pytest.approx(1.0)


@pytest.mark.parametrize(
    ("current", "peak", "hours", "after"),
    [
        (10.0, 10.0, 100, 10.4),  # 0.4 per 100 hours
        (14.0, 14.0, 150, 14.6),
        (14.8, 14.8, 100, 15.2),  # 0.2 at full rate to 15, then 0.2 x (20 - 15) / 5
        (17.0, 17.0, 100, 17.24),  # above 15: 0.4 x (20 - 17) / 5
        (12.0, 12.0, 0, 11.95),  # -0.05 a month without hours
        (9.02, 12.0, 0, 9.0),  # never below peak - 3
        (8.0, 12.0, 0, 8.0),  # already under the floor: stays
        (1.02, 2.0, 0, 1.0),  # never below 1
    ],
)
def test_familiarity_worked_examples(
    balance: Balance, current: float, peak: float, hours: int, after: float
) -> None:
    assert familiarity_after(current, peak, hours * H, balance.familiarity) == pytest.approx(after)


def test_grow_person_is_seeded_and_learns(data: GameData, balance: Balance) -> None:
    person = make(data, balance, "corporate_ma", "associate_1")
    busy = WorkMonth(person.id, (("corporate_ma", 170 * H),), substantive_tenths=150 * H)
    idle = WorkMonth(person.id)
    rng = RngFactory(3)
    a = grow_person(person, 1, rng, data, balance, busy)
    assert a == grow_person(person, 1, rng, data, balance, busy)
    b = grow_person(person, 1, rng, data, balance, idle)
    gain_busy = current_ability(a, data) - current_ability(person, data)
    gain_idle = current_ability(b, data) - current_ability(person, data)
    assert gain_busy > gain_idle > 0
    assert gain_busy == pytest.approx(gain_idle * 1.4 / 0.5, rel=1e-6)
    assert a.familiarity["corporate_ma"] > person.familiarity["corporate_ma"]
    assert b.familiarity["corporate_ma"] < person.familiarity["corporate_ma"]
    assert a.familiarity_peak["corporate_ma"] == a.familiarity["corporate_ma"]
    assert b.familiarity_peak == person.familiarity_peak


def test_a_year_of_hours_builds_a_new_practice(data: GameData, balance: Balance) -> None:
    person = make(data, balance, "commercial_litigation", "associate_3")
    start = person.familiarity["white_collar"]
    month = WorkMonth(person.id, (("white_collar", 160 * H),), substantive_tenths=96 * H)
    for turn in range(12):
        person = grow_person(person, turn, RngFactory(1), data, balance, month)
    # 1,920 hours at 0.4 per 100: +7.68 (all below the taper from a start of 1-6)
    assert person.familiarity["white_collar"] == pytest.approx(start + 7.68)


def test_class_year_in_september(data: GameData, balance: Balance) -> None:
    person = make(data, balance, "ip", "associate_2")
    start = (2005, 1)
    assert advance_class_year(person, 7, start, balance).level == "associate_2"  # August
    assert advance_class_year(person, 8, start, balance).level == "associate_3"  # September
    eighth = replace(person, level="associate_8")
    assert advance_class_year(eighth, 8, start, balance).level == "associate_8"


def test_people_phase_in_the_turn(data: GameData, balance: Balance) -> None:
    from ptk.sim.decisions import Decisions
    from ptk.sim.setup import new_game
    from ptk.sim.turn import advance_turn

    state = new_game(
        name="t",
        firm_name="F",
        master_seed=4,
        scenario_id="biglaw_spinout",
        difficulty="standard",
        data=data,
        balance=balance,
    ).state
    work = (WorkMonth(3, (("corporate_ma", 180 * H),), substantive_tenths=120 * H),)
    rng = RngFactory(4)
    result = advance_turn(state, Decisions(), rng, balance, data, {}, work)
    after = result.new_state
    assert after.person(3).skills != state.person(3).skills
    assert after.person(3).familiarity["corporate_ma"] > state.person(3).familiarity["corporate_ma"]
    before_rv, after_rv = state.reveal(1, 3), after.reveal(1, 3)
    assert before_rv is not None and after_rv is not None
    assert after_rv.record("writing").hw < before_rv.record("writing").hw
    founder_rv = after.reveal(1, 1)
    assert founder_rv is not None and founder_rv.record("writing").hw == 0
    again = advance_turn(state, Decisions(), rng, balance, data, {}, work).new_state
    assert again == after  # seeded
