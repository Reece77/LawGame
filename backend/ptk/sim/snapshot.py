"""Month-end KPI snapshot per firm, persisted to turn_snapshot by the caller.

Ported from tst/sim/snapshot.py @ 02fba2aa; changed: Partner Track's KPIs (spec 8.2), added
by the milestones that compute them."""

from __future__ import annotations

from dataclasses import dataclass

from ptk.sim.money import Cents


@dataclass(frozen=True, slots=True)
class FirmSnapshot:
    firm_id: int
    cash_cents: Cents  # 1000_cash balance at month end
    revenue_cents: Cents = 0  # fees recognised this month, accrual view (PT-M3b)
    # PT-M3b: the revenue chain (spec 8.2; ADR PT-0005 4), derived by ptk.sim.billing.kpis
    collections_cents: Cents = 0  # cash collected this month (the cash view's revenue)
    wip_cents: Cents = 0  # unbilled WIP at standard value, month end
    receivables_cents: Cents = 0  # open bills outstanding, month end
    utilisation_bp: int | None = None  # billable / capacity, the month
    realisation_bp: int | None = None  # billed / standard, trailing 12 months
    collection_bp: int | None = None  # collected / invoiced, trailing 12 months
    lockup_days: int | None = None  # (WIP + receivables) / trailing daily fees
    open_disputes: int = 0
    # PT-M4: the partnership (spec 8.1-8.2), trailing twelve months (ptk.sim.partnership.kpis)
    pep_cents: int | None = None
    rpl_cents: int | None = None
    margin_bp: int | None = None
    leverage_bp: int | None = None  # lawyers per equity partner x 10,000
    equity_partners: int = 0
    revolver_cents: Cents = 0  # drawn at month end

    def kpis(self) -> dict[str, int | float | None]:
        return {
            "cash_cents": self.cash_cents,
            "revenue_cents": self.revenue_cents,
            "collections_cents": self.collections_cents,
            "wip_cents": self.wip_cents,
            "receivables_cents": self.receivables_cents,
            "utilisation_bp": self.utilisation_bp,
            "realisation_bp": self.realisation_bp,
            "collection_bp": self.collection_bp,
            "lockup_days": self.lockup_days,
            "open_disputes": self.open_disputes,
            "pep_cents": self.pep_cents,
            "rpl_cents": self.rpl_cents,
            "margin_bp": self.margin_bp,
            "leverage_bp": self.leverage_bp,
            "equity_partners": self.equity_partners,
            "revolver_cents": self.revolver_cents,
        }


@dataclass(frozen=True, slots=True)
class TurnSnapshot:
    turn: int
    firms: tuple[FirmSnapshot, ...]
