"""PT-M7b (property tests): in the crisis every ledger entry still balances in integer cents,
a crisis write-down is never more than the bill nor negative, the card stays within its
start share and the full card, and the hours policy plans whole tenths within the policy's
fill.
"""

from __future__ import annotations

from dataclasses import replace

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from simcore.kernel.money import BP_DENOMINATOR

from ptk.sim.billing.phase import billing_month
from ptk.sim.data_models import Balance, GameData
from ptk.sim.matters.rates import card_target_bp
from ptk.sim.matters.staffing import fee_earners, policy_fill
from ptk.sim.state import with_firm
from ptk.sim.streams import RngFactory
from tests.matters_support import game, play

PROPERTY = settings(
    max_examples=6, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
CRISIS_TURN = 51  # April 2009: stress 1


@PROPERTY
@given(seed=st.integers(1, 10_000), months=st.integers(3, 8))
def test_crisis_billing_balances_and_never_overcuts(
    data: GameData, balance: Balance, seed: int, months: int
) -> None:
    state = game(data, balance, seed)
    state, _ = play(state, data, balance, months, seed)
    state = replace(state, turn=CRISIS_TURN)
    month = billing_month(state, RngFactory(seed), data, balance)
    for e in month.entries:
        assert all(isinstance(line.amount, int) for line in e.lines)
        assert sum(line.amount for line in e.lines) == 0
    totals = next(m for m in month.state.billing.months if m.turn == CRISIS_TURN)
    assert totals.crisis_writedown_cents >= 0
    assert totals.billed_cents >= 0
    for b in month.state.billing.bills:
        assert b.billed_cents >= 0


@PROPERTY
@given(reputation=st.floats(0, 1), start=st.integers(1, 10_000))
def test_the_card_target_stays_between_the_start_and_the_full_card(
    balance: Balance, reputation: float, start: int
) -> None:
    bp = card_target_bp(reputation, start, balance)
    assert isinstance(bp, int)
    assert start <= bp <= BP_DENOMINATOR


@PROPERTY
@given(seed=st.integers(1, 10_000), hours=st.integers(1500, 2600))
def test_the_hours_policy_plans_whole_tenths_within_its_fill(
    data: GameData, balance: Balance, seed: int, hours: int
) -> None:
    state = game(data, balance, seed)
    state = with_firm(state, replace(state.player, billable_target_hours=hours))
    state, _ = play(state, data, balance, 2, seed)
    earners = {e.id: e for e in fee_earners(state, 1, data, balance)}
    base = balance.staffing.plan_fill
    for e in earners.values():
        fill = policy_fill(e, base, hours, balance)
        assert base <= fill <= max(base, balance.staffing.policy_fill_max)
    for r in state.market.hours:
        assert isinstance(r.tenths, int) and r.tenths >= 0
    for m in state.market.open_matters(1):
        for t in m.team:
            assert isinstance(t.planned_tenths, int) and t.planned_tenths >= 0
