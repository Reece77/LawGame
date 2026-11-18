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
    revenue_cents: Cents = 0  # fees recognised this month (PT-M3b)

    def kpis(self) -> dict[str, int | float | None]:
        return {"cash_cents": self.cash_cents, "revenue_cents": self.revenue_cents}


@dataclass(frozen=True, slots=True)
class TurnSnapshot:
    turn: int
    firms: tuple[FirmSnapshot, ...]
