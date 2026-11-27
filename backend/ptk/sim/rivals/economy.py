"""A rival's month: demand, capacity, revenue, costs and its ledger (spec 10; ADR PT-0008).

Demand is an annual run-rate of work. While a real rival is **pinned** (to December of
`rivals.pin.end_year`, if firms.yaml has its path), demand is its path's revenue run-rate
times an AR(1) shock, plus the player's effects (`offset_cents`, which decays at
`pin.recovery_per_year`). Otherwise (generated firms, boutiques, real firms after the pin)
demand grows with the market (`rivals.market_growth`), the personality's growth bias and its
own pricing, times the shock's change, and the player's effects move it directly.

Capacity is lawyers x revenue per lawyer at capacity x the rate index; the month's fees are
min(demand, capacity) / 12. Costs are lawyers x cost per lawyer (growing at
`rivals.cost_growth` each January) plus extra offices. Every month each rival posts one
balanced entry: fees in, costs out and the month's profit to the partners' drawings, so its
cash stays at zero (rivals hold no reserves; ADR-0003's balance holds).
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property

from ptk.sim import dmath
from ptk.sim.calendar import turn_to_ym
from ptk.sim.data_models import Balance, GameData
from ptk.sim.fastcopy import replace
from ptk.sim.ledger import CASH, DRAWINGS, FEES, GENERAL_ADMIN, SALARIES, LedgerEntry, LedgerLine
from ptk.sim.rivals.data import FirmDef, HistoryEventDef, PersonalityDef
from ptk.sim.rivals.models import RivalFirm
from ptk.sim.rivals.path import Path, build_path, market_factor, path_value, time_of

MONTHS = 12  # tunable-exempt: months in a year
JANUARY = 1  # tunable-exempt


@dataclass(frozen=True)
class Month:
    """What a rival's month needs from the turn: time, data and history lookups."""

    turn: int
    start: tuple[int, int]
    data: GameData
    balance: Balance

    @cached_property  # PT-M18 (T12): fixed for the month, read for every rival
    def ym(self) -> tuple[int, int]:
        return turn_to_ym(self.turn, self.start)

    @cached_property
    def t(self) -> float:
        return time_of(self.turn, self.start)

    @cached_property
    def defs(self) -> dict[str, FirmDef]:
        return {f.key: f for f in self.data.rivals.firms.firms}

    @cached_property
    def events(self) -> tuple[HistoryEventDef, ...]:
        return self.data.rivals.firms.events

    @cached_property
    def _paths(self) -> dict[str, Path | None]:
        """PT-M18 (T12): each real firm's path once a month (`build_path` is pure in the
        firm's definition and the events, fixed for the month; it hashed both per call)."""
        return {}

    def path(self, firm: RivalFirm) -> Path | None:
        if firm.kind != "real":
            return None
        memo = self._paths
        if firm.key in memo:
            return memo[firm.key]
        fdef = self.defs.get(firm.key)
        p = None if fdef is None else build_path(fdef, self.events)
        out = p if p is not None and p.revenue else None
        memo[firm.key] = out
        return out

    def pinned(self, firm: RivalFirm) -> bool:
        p = self.path(firm)
        if p is None or self.ym[0] > self.balance.rivals.pin.end_year:
            return False
        return len(p.revenue) > 1 or firm.anchor is not None  # a path, not a lone 2005 point

    def anchor(self, firm: RivalFirm) -> tuple[float, float] | None:
        if firm.anchor is None:
            return None
        return (time_of(firm.anchor[0], self.start), firm.anchor[1])

    def path_revenue(self, firm: RivalFirm, t: float | None = None) -> float | None:
        p = self.path(firm)
        if p is None:
            return None
        return path_value(
            p, "revenue", self.t if t is None else t, self.balance.rivals, self.anchor(firm)
        )

    def path_lawyers(self, firm: RivalFirm) -> float | None:
        p = self.path(firm)
        if p is None:
            return None
        lawyer_anchor = None
        if firm.anchor is not None:
            lawyer_anchor = (time_of(firm.anchor[0], self.start), firm.lawyers_anchor)
        return path_value(p, "lawyers", self.t, self.balance.rivals, lawyer_anchor)

    def personality(self, firm: RivalFirm) -> PersonalityDef:
        return self.balance.rivals.personalities[firm.personality]


def capacity_cents(firm: RivalFirm) -> float:
    return firm.lawyers * firm.rpl_cap_cents * firm.rate_index


def target_lawyers(firm: RivalFirm, month: Month) -> float:
    """Pinned: the path's lawyers scaled by demand against the path's revenue (the shock and
    the player's effects move headcount too). Free: what demand needs at the personality's
    utilisation."""
    if month.pinned(firm):
        lawyers, revenue = month.path_lawyers(firm), month.path_revenue(firm)
        if lawyers and revenue:
            return lawyers * firm.demand_cents / revenue
    u = month.personality(firm).utilisation
    return firm.demand_cents / (firm.rpl_cap_cents * firm.rate_index * u)


def rate_gap(firm: RivalFirm, month: Month) -> float:
    """Relative rate change the firm needs: pinned, to bill the path's revenue per lawyer at
    its utilisation; free, utilisation against its target."""
    u = month.personality(firm).utilisation
    if month.pinned(firm):
        lawyers, revenue = month.path_lawyers(firm), month.path_revenue(firm)
        if lawyers and revenue:
            needed = revenue / lawyers / (firm.rpl_cap_cents * u)
            return needed / firm.rate_index - 1.0
    return (firm.utilisation - u) / u


def update_demand(firm: RivalFirm, z: float, month: Month) -> RivalFirm:
    """The month's demand (one standard normal z from the firm's rival_firm generator)."""
    pin = month.balance.rivals.pin
    shock = pin.noise_phi * firm.shock + pin.noise_sd * z
    rb = month.balance.rivals
    if month.pinned(firm):
        revenue = month.path_revenue(firm) or firm.demand_cents
        offset = firm.offset_cents * (1.0 - pin.recovery_per_year / MONTHS)
        demand = max(0.0, revenue * dmath.exp(shock) + offset)
        return replace(firm, shock=shock, offset_cents=offset, demand_cents=demand)
    pdef = month.personality(firm)
    t = month.t
    growth = market_factor(t - 1.0 / MONTHS, t, rb)
    bias = (
        pdef.growth_bias + firm.growth_bias - rb.rate_elasticity * max(0.0, firm.rate_index - 1.0)
    )
    factor = growth * dmath.pow(1.0 + bias, 1.0 / MONTHS) * dmath.exp(shock - firm.shock)
    demand = max(0.0, firm.demand_cents * factor + firm.offset_cents)
    return replace(firm, shock=shock, offset_cents=0.0, demand_cents=demand)


def january(firm: RivalFirm, month: Month) -> RivalFirm:
    """Costs per lawyer rise each January; free play's revenue per lawyer rises with the
    market's rate inflation."""
    if month.ym[1] != JANUARY or month.turn == 0:
        return firm
    rb = month.balance.rivals
    firm = replace(firm, cost_per_lawyer_cents=firm.cost_per_lawyer_cents * (1.0 + rb.cost_growth))
    if not month.pinned(firm):
        firm = replace(firm, rpl_cap_cents=firm.rpl_cap_cents * (1.0 + rb.rate_inflation))
    return firm


@dataclass(frozen=True, slots=True)
class Books:
    firm: RivalFirm
    entry: LedgerEntry | None


def book_month(firm: RivalFirm, month: Month) -> Books:
    """Fees, costs and profit for the month, and the ledger entry."""
    rb = month.balance.rivals
    capacity = capacity_cents(firm)
    billed = min(firm.demand_cents, capacity)
    utilisation = billed / capacity if capacity > 0 else 0.0
    fees = round(billed / MONTHS)
    extra_offices = max(0, firm.offices - firm.base_offices)
    staff_cost = round(firm.lawyers * firm.cost_per_lawyer_cents / MONTHS)
    office_cost = round(extra_offices * rb.office_cost_cents / MONTHS)
    profit = fees - staff_cost - office_cost
    firm = replace(
        firm,
        utilisation=utilisation,
        revenue=(*firm.revenue, fees)[-MONTHS:],
        profit=(*firm.profit, profit)[-MONTHS:],
    )
    lines = [
        LedgerLine(CASH, fees - staff_cost - office_cost - profit),  # always 0: nothing kept
        LedgerLine(FEES, -fees),
        LedgerLine(SALARIES, staff_cost),
        LedgerLine(GENERAL_ADMIN, office_cost),
        LedgerLine(DRAWINGS, profit),
    ]
    lines = [ln for ln in lines if ln.amount != 0]
    entry = None
    if len(lines) >= 2:  # tunable-exempt: a ledger entry's minimum
        entry = LedgerEntry(
            turn=month.turn, firm_id=firm.id, memo=f"{firm.short}: month", lines=tuple(lines)
        )
    return Books(firm=firm, entry=entry)
