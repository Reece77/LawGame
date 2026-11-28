"""Invariants for people over many months (CLAUDE.md 8): attributes and familiarity stay in
1-20, peaks never fall, strain stays in 0-100."""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from ptk.sim.data_models import Balance, GameData
from ptk.sim.people.growth import grow_person
from ptk.sim.people.models import WorkMonth
from ptk.sim.people.strain import strain_month
from ptk.sim.streams import RngFactory
from tests.conftest import DATA_DIR
from tests.unit.test_people_generation import make

ROLES = ("corporate_ma", "ip", "employment", "paralegal", "it")
LEVEL_OF = {"paralegal": "paralegal", "it": "staff"}


def months(practices: tuple[str, ...]) -> st.SearchStrategy[list[tuple[str, int, int, int]]]:
    return st.lists(
        st.tuples(
            st.sampled_from(practices),
            st.integers(0, 4000),  # tenths in the practice: up to 400 hours
            st.integers(0, 4000),  # substantive tenths (clamped to the total)
            st.integers(0, 1000),  # other tenths
        ),
        min_size=1,
        max_size=36,
    )


def _check(
    data: GameData, balance: Balance, role: str, seed: int, plan: list[tuple[str, int, int, int]]
) -> None:
    level = LEVEL_OF.get(role, "associate_1")
    person = make(data, balance, role, level, seed=seed, practice="ip")
    for turn, (practice, tenths, sub, other) in enumerate(plan):
        work = WorkMonth(
            person.id, ((practice, tenths),), substantive_tenths=sub, other_tenths=other
        )
        before = person
        person = grow_person(person, turn, RngFactory(seed), data, balance, work)
        person = strain_month(person, turn, work, balance)
        assert 0.0 <= person.strain <= 100.0
        assert (person.burnout_since is not None) <= (person.last_burnout_turn is not None)
        values = [*person.skills.as_dict().values(), *person.familiarity.as_dict().values()]
        assert all(1.0 <= v <= 20.0 for v in values)
        for key in data.practice_keys:
            assert person.familiarity_peak[key] >= before.familiarity_peak[key]
            assert person.familiarity_peak[key] >= person.familiarity[key]
            floor = min(before.familiarity[key], max(1.0, person.familiarity_peak[key] - 3))
            assert person.familiarity[key] >= floor - 1e-12


@settings(max_examples=60, deadline=None)
@given(
    st.sampled_from(ROLES),
    st.integers(0, 2**32),
    st.data(),
)
@pytest.mark.nightly  # PT-M11: over 60 s; check's runtime (product manager, 2026-11-23)
def test_growth_keeps_attributes_in_range(role: str, seed: int, draw: st.DataObject) -> None:
    from ptk.loader import load_balance, load_game_data

    data, balance = load_game_data(DATA_DIR), load_balance(DATA_DIR)
    plan = draw.draw(months(data.practice_keys))
    _check(data, balance, role, seed, plan)


# --- PT-M2: the mentoring multiplier (TST formulas.md 13.5) ----------------------------------


@settings(max_examples=200, deadline=None)
@given(
    leadership=st.floats(1, 20),
    communication=st.floats(1, 20),
    mentoring=st.floats(1, 20),
    reports=st.integers(0, 40),
    mentor=st.booleans(),
)
@pytest.mark.nightly  # PT-M11: over 60 s; check's runtime (product manager, 2026-11-23)
def test_org_terms_stay_in_bounds(
    leadership: float, communication: float, mentoring: float, reports: int, mentor: bool
) -> None:
    from ptk.loader import load_balance
    from ptk.sim.org.formulas import (
        growth_multiplier,
        manager_morale_term,
        manager_quality,
        span_factor,
    )

    org = load_balance(DATA_DIR).org
    s = span_factor(leadership, reports, org)
    assert 0 < s <= 1
    q = manager_quality(leadership, communication, mentoring, s)
    assert -8 <= manager_morale_term(q, org) <= 8
    assert 0.75 <= growth_multiplier(mentoring, s, mentor, org) <= 1.5
