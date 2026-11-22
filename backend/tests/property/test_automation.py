"""Every owner action is within its limits (PT-M9's acceptance; TST formulas.md 40.9): over
random per-decision and monthly limits, an owner never applies a decision committing at or
above its per-decision limit, and an area's month never commits past its monthly limit; one-offs
are never applied."""

from __future__ import annotations

from dataclasses import replace

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from ptk.sim.automation.run import with_automation
from ptk.sim.data_models import Balance, GameData
from tests.automation_support import automated_firm
from tests.seats_support import run, steady

ACTED = ("decision", "mistake")


@pytest.fixture(scope="module")
def firm(data: GameData, balance: Balance):  # type: ignore[no-untyped-def]
    b = steady(balance)
    return automated_firm(data, b), b


@settings(
    max_examples=8, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    limits=st.lists(
        st.tuples(st.integers(0, 40_000_000), st.integers(0, 3)), min_size=13, max_size=13
    )
)
def test_owners_stay_within_their_limits(firm, data: GameData, limits) -> None:  # type: ignore[no-untyped-def]
    state, b = firm
    owners_ = tuple(
        replace(o, limit_cents=limit, monthly_cents=limit * (1 + mult))
        for o, (limit, mult) in zip(state.automation.owners, limits * 3, strict=False)
    )
    state = with_automation(state, replace(state.automation, owners=owners_))
    by_key = {(o.area, o.slot): o for o in owners_}
    _, results, _ = run(state, data, b, 2)
    for r in results:
        month: dict[tuple[str, int], int] = {}
        for d in r.area_decisions:
            if d.kind not in ACTED:
                continue
            o = by_key[(d.area, d.slot)]
            assert d.commitment_cents == 0 or d.commitment_cents < o.limit_cents
            month[(d.area, d.slot)] = month.get((d.area, d.slot), 0) + d.commitment_cents
        for key, total in month.items():
            assert total <= by_key[key].monthly_cents


def test_no_applied_decision_is_a_one_off(firm, data: GameData) -> None:  # type: ignore[no-untyped-def]
    from ptk.sim.actions import ACTION_TYPES
    from ptk.sim.org.actions import ACTION_TYPES as ORG_TYPES

    state, b = firm
    _, results, _ = run(state, data, b, 3)
    kinds = {d.action for r in results for d in r.area_decisions if d.kind in ACTED}
    # (a partnership admission is a propose_partner on the equity or income track: the unit
    # test enumerating spec 9.4's one-offs covers it; a second look is within the area)
    one_off_kinds = {"deequitise", "capital_call", "propose_terms", "exco_term", "counter"}
    assert not kinds & one_off_kinds
    assert kinds <= set(ACTION_TYPES) | set(ORG_TYPES)
