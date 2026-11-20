"""PT-M3b acceptance: the cash view's revenue equals collections; accrual revenue equals the
billed value plus the change in WIP net of provisions (and of deferred retainer income), month
by month and over the whole run; receivables move by exactly what was invoiced, collected,
credited and written off.
"""

from __future__ import annotations

import pytest

from ptk.sim.billing import statements
from ptk.sim.data_models import Balance, GameData
from ptk.sim.ledger import (
    DEFERRED_FEES,
    RECEIVABLES,
    WIP,
    WIP_PROVISION,
    apply_entries,
)
from tests.billing_support import played


@pytest.mark.parametrize("seed", (1, 2, 3))
def test_revenue_reconciles_month_by_month(seed: int, data: GameData, balance: Balance) -> None:
    game = played(data, balance, 20, 24, seed)
    balances: dict[tuple[int, str], int] = {}
    total_rev = total_cash = total_collected = 0
    for result in game.results:
        before = dict(balances)
        balances = apply_entries(balances, result.ledger_entries)
        month = next(m for m in result.new_state.billing.months if m.turn == result.snapshot.turn)

        def delta(account: str, before=before, balances=balances) -> int:  # type: ignore[no-untyped-def]
            return balances.get((1, account), 0) - before.get((1, account), 0)

        accrual = statements.accrual_pnl(result.ledger_entries)
        fees = sum(v for a, v in accrual.lines if a.startswith("4"))
        cash = statements.cash_pnl(result.ledger_entries)
        # cash view: revenue is collections
        assert cash.revenue_cents == month.collected_cents
        # accrual view: billed (net of credit notes) + ΔWIP - Δprovision - Δdeferred
        billed = month.invoiced_cents - month.credited_cents
        assert fees == month.fees_cents
        assert fees == (billed + delta(WIP) + delta(WIP_PROVISION) + delta(DEFERRED_FEES)), (
            result.snapshot.turn
        )
        # receivables move by what was invoiced, collected, credited and written off
        assert delta(RECEIVABLES) == (
            month.invoiced_cents
            - month.collected_cents
            - month.credited_cents
            - month.written_off_cents
        )
        total_rev += fees
        total_cash += cash.revenue_cents
        total_collected += month.collected_cents
    assert total_cash == total_collected > 0
    assert total_rev > 0
    # over the whole run (from empty books): revenue is everything billed net of credit
    # notes, plus what is still unbilled, less the provision and the unearned retainers
    months = [
        m for r in game.results for m in r.new_state.billing.months if m.turn == r.snapshot.turn
    ]
    billed = sum(m.invoiced_cents - m.credited_cents for m in months)
    end = game.balances
    assert total_rev == billed + sum(
        end.get((1, a), 0) for a in (WIP, WIP_PROVISION, DEFERRED_FEES)
    )
