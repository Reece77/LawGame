"""Statements over the ledger (ADR PT-0003 section 3; spec 8.2, 16's Finance screen).

The accrual view is the ledger's income and cost accounts. The cash view is cash itself:
revenue is what was collected (cash debited against receivables, client money's transfers
included); costs are what was paid (cash credited against a cost account); the change in
WIP, receivables, provisions and deferred income is left out. Both are queries; nothing here
is stored.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from ptk.sim.ledger import CASH, RECEIVABLES, AccountCode, LedgerEntry

INCOME = "4"
COSTS = ("5", "6")


@dataclass(frozen=True, slots=True)
class Pnl:
    revenue_cents: int
    costs_cents: int
    lines: tuple[tuple[AccountCode, int], ...]  # (account, amount: income positive, costs positive)

    @property
    def profit_cents(self) -> int:
        return self.revenue_cents - self.costs_cents


def accrual_pnl(entries: Iterable[LedgerEntry]) -> Pnl:
    by_account: dict[AccountCode, int] = {}
    for entry in entries:
        for line in entry.lines:
            if line.account.startswith(INCOME):
                by_account[line.account] = by_account.get(line.account, 0) - line.amount
            elif line.account.startswith(COSTS):
                by_account[line.account] = by_account.get(line.account, 0) + line.amount
    revenue = sum(v for a, v in by_account.items() if a.startswith(INCOME))
    costs = sum(v for a, v in by_account.items() if a.startswith(COSTS))
    return Pnl(revenue, costs, tuple(sorted(by_account.items())))


def cash_pnl(entries: Iterable[LedgerEntry]) -> Pnl:
    """Collections as revenue; cash paid against cost accounts as costs, by account."""
    by_account: dict[AccountCode, int] = {}
    revenue = 0
    for entry in entries:
        cash = sum(line.amount for line in entry.lines if line.account == CASH)
        if cash == 0:
            continue
        if cash > 0 and any(ln.account == RECEIVABLES and ln.amount < 0 for ln in entry.lines):
            received = sum(min(ln.amount, 0) for ln in entry.lines if ln.account == RECEIVABLES)
            revenue += min(cash, -received)
            continue
        for line in entry.lines:
            if line.account.startswith(COSTS) and cash < 0:
                by_account[line.account] = by_account.get(line.account, 0) + line.amount
    costs = sum(by_account.values())
    return Pnl(revenue, costs, (("collections", revenue), *sorted(by_account.items())))


def balance_sheet(
    balances: Mapping[tuple[int, AccountCode], int], firm_id: int
) -> tuple[tuple[AccountCode, int], ...]:
    """Asset, liability and equity accounts with a balance (debits positive), by code."""
    return tuple(
        sorted(
            (a, v) for (f, a), v in balances.items() if f == firm_id and a[0] in "123" and v != 0
        )
    )
