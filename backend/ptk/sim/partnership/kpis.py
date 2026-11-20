"""PEP and the partnership's KPIs (spec 8.1-8.2), derived from the trailing twelve months'
P&L points and billing's ratios, never stored.

The Explain panel's decomposition (spec 8.1):
    PEP = RPL x margin x leverage
    RPL = hours per lawyer x average rate x realisation x collection
"""

from __future__ import annotations

from dataclasses import dataclass

from ptk.sim.billing.kpis import collection_bp, realisation_bp, trailing
from ptk.sim.money import BP_DENOMINATOR
from ptk.sim.partnership import formulas as fx
from ptk.sim.partnership.common import profit_12m, revenue_12m
from ptk.sim.partnership.models import FirmPartnership
from ptk.sim.state import GameState

TENTHS = 10  # tunable-exempt: ADR PT-0005's tenths of an hour


@dataclass(frozen=True, slots=True)
class Explain:
    pep_cents: int | None
    rpl_cents: int | None
    margin_bp: int | None
    leverage: float | None
    revenue_cents: int
    profit_cents: int
    lawyers: float
    equity_partners: float
    hours_per_lawyer: float | None  # billable, trailing twelve months
    average_rate_cents: int | None  # standard value per billable hour
    realisation_bp: int | None
    collection_bp: int | None


def averages(fp: FirmPartnership) -> tuple[float, float]:
    """Average lawyers and equity partners over the trailing months' points."""
    pts = fp.pnl[1:] or fp.pnl
    if not pts:
        return 0.0, 0.0
    return (
        sum(p.lawyers for p in pts) / len(pts),
        sum(p.equity_partners for p in pts) / len(pts),
    )


def explain(state: GameState, fp: FirmPartnership) -> Explain:
    lawyers, partners = averages(fp)
    ident = fx.PepIdentity(revenue_12m(fp), profit_12m(fp), lawyers, partners)
    months = trailing(state.billing, fp.firm_id, state.turn)
    tenths = sum(m.billable_tenths for m in months)
    standard = sum(m.standard_cents for m in months)
    n = len(months)
    hours = None
    if n and lawyers > 0:
        hours = tenths / TENTHS / lawyers * fx.MONTHS_PER_YEAR / n
    rate = round(standard * TENTHS / tenths) if tenths > 0 else None
    return Explain(
        pep_cents=ident.pep_cents,
        rpl_cents=ident.rpl_cents,
        margin_bp=ident.margin_bp,
        leverage=ident.leverage,
        revenue_cents=ident.revenue_cents,
        profit_cents=ident.profit_cents,
        lawyers=lawyers,
        equity_partners=partners,
        hours_per_lawyer=hours,
        average_rate_cents=rate,
        realisation_bp=realisation_bp(months),
        collection_bp=collection_bp(months),
    )


def leverage_bp(e: Explain) -> int | None:
    return None if e.leverage is None else round(e.leverage * BP_DENOMINATOR)
