"""The revenue chain's KPIs (spec 8.2; ADR PT-0005 4): derived from billing's books, never
stored. Utilisation is the month's; realisation, collection and lockup use the trailing
twelve months played (fewer at the start of a game).

- utilisation = billable tenths / fee earners' capacity tenths (the month)
- realisation = fees billed for time / standard value of the work those bills relieved
  (success and contingency premiums, account 4100, are not realisation)
- collection = cash collected / invoiced, over the bills resolved in the window
- lockup days = (unbilled WIP + receivables) / trailing daily fees (accrual revenue)
"""

from __future__ import annotations

from typing import Final

from ptk.sim.billing.models import BillingState, MonthTotals
from ptk.sim.money import BP_DENOMINATOR, round_half_even
from ptk.sim.snapshot import FirmSnapshot

DAYS_PER_MONTH: Final = 30.4  # tunable-exempt: an average month's days (lockup's unit)
TRAILING: Final = 12  # tunable-exempt: the trailing window, months


def trailing(billing: BillingState, firm_id: int, turn: int) -> tuple[MonthTotals, ...]:
    return tuple(m for m in billing.months if m.firm_id == firm_id and m.turn <= turn)


def wip_cents(billing: BillingState, firm_id: int) -> int:
    return sum(
        e.wip_cents for e in billing.engagements if e.firm_id == firm_id and not e.closed
    ) + sum(f.wip_cents for f in billing.flows if f.firm_id == firm_id)


def receivables_cents(billing: BillingState, firm_id: int) -> int:
    return sum(b.outstanding_cents for b in billing.bills if b.firm_id == firm_id and b.is_open)


def ratio_bp(numerator: int, denominator: int) -> int | None:
    if denominator <= 0:
        return None
    return round_half_even(numerator * BP_DENOMINATOR, denominator)


def lockup_days(wip: int, receivables: int, months: tuple[MonthTotals, ...]) -> int | None:
    fees = sum(m.fees_cents for m in months)
    if not months or fees <= 0:
        return None
    daily = fees / (len(months) * DAYS_PER_MONTH)
    return round((wip + receivables) / daily)


def realisation_bp(months: tuple[MonthTotals, ...]) -> int | None:
    """Fees billed for time (success and contingency premiums excluded) / standard value."""
    billed = sum(m.billed_cents - m.premium_cents for m in months)
    return ratio_bp(billed, sum(m.standard_cents for m in months))


def collection_bp(months: tuple[MonthTotals, ...]) -> int | None:
    """Cash collected / invoiced, over the bills resolved (paid or written off) in the window,
    so the ratio does not swing with the timing of payments."""
    return ratio_bp(
        sum(m.resolved_paid_cents for m in months), sum(m.resolved_billed_cents for m in months)
    )


def firm_snapshot(billing: BillingState, firm_id: int, turn: int, cash: int) -> FirmSnapshot:
    """A firm's month-end snapshot with the revenue chain's KPIs after turn `turn`."""
    months = trailing(billing, firm_id, turn)
    this = next((m for m in months if m.turn == turn), None)
    wip = wip_cents(billing, firm_id)
    ar = receivables_cents(billing, firm_id)
    return FirmSnapshot(
        firm_id=firm_id,
        cash_cents=cash,
        revenue_cents=this.fees_cents if this else 0,
        collections_cents=this.collected_cents if this else 0,
        wip_cents=wip,
        receivables_cents=ar,
        utilisation_bp=ratio_bp(this.billable_tenths, this.capacity_tenths) if this else None,
        realisation_bp=realisation_bp(months),
        collection_bp=collection_bp(months),
        lockup_days=lockup_days(wip, ar, months),
        open_disputes=sum(
            1 for b in billing.bills if b.firm_id == firm_id and b.dispute is not None
        ),
    )
