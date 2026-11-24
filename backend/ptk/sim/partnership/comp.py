"""Comp systems and the December allocation (spec 8.5; ADR PT-0003 section 6).

The year's profit (accrual, ADR PT-0003 3) less the retained reserve is the pool. Each equity
partner's share follows the agreement's comp system (`formulas.comp_weights`), weighted by
the months of the year they were an equity partner; guarantees are floors and promised comp
comes off the top, both funded by the other partners. Satisfaction compares each partner's
comp with their sense of contribution (true contribution, plus ego) and their market value.
"""

from __future__ import annotations

from dataclasses import replace

from ptk.sim.data_models import Balance, GameData
from ptk.sim.macro import lateral_heat
from ptk.sim.money import pct_of
from ptk.sim.partnership import formulas as fx
from ptk.sim.partnership.common import book_cents, ym
from ptk.sim.partnership.models import FirmPartnership, Partner, with_partner
from ptk.sim.state import GameState

LOCKSTEP_SYSTEMS = frozenset({"lockstep", "modified_lockstep"})


def year_start_turn(state: GameState, turn: int) -> int:
    return turn - (ym(state, turn)[1] - 1)


def months_as_equity(p: Partner, year_start: int, turn: int) -> int:
    return max(0, min(fx.MONTHS_PER_YEAR, turn - max(p.admitted_turn, year_start) + 1))


def management_credit(
    state: GameState, fp: FirmPartnership, person_id: int, balance: Balance
) -> float:
    cfg = balance.partnership.management_credit
    credit = cfg.mp if fp.mp_id == person_id else 0.0
    leaders = {u.leader_id for u in state.org.firm_units(fp.firm_id)}
    if person_id in leaders and fp.mp_id != person_id:
        credit += cfg.unit_leader
    return credit


def credits(state: GameState, fp: FirmPartnership, balance: Balance) -> dict[int, fx.Credits]:
    """Each equity partner's year: origination (this year's credit), working (their own
    hours' standard value) and management credit."""
    year = ym(state)[0]
    orig = {o.person_id: o.cents for o in state.market.originations if o.year == year}
    return {
        p.person_id: fx.Credits(
            origination_cents=orig.get(p.person_id, 0),
            working_cents=p.working_ytd_cents,
            management=management_credit(state, fp, p.person_id, balance),
        )
        for p in fp.equity_partners
    }


def comp_shares(
    state: GameState, fp: FirmPartnership, pool: int, balance: Balance, system: str | None = None
) -> dict[int, int]:
    """Each equity partner's comp from `pool` under a comp system (the agreement's unless
    given): guarantees and promises first, then the system's weights over the rest."""
    turn = state.turn
    start = year_start_turn(state, turn)
    eq = fp.equity_partners
    if not eq:
        return {}
    months = {p.person_id: months_as_equity(p, start, turn) for p in eq}
    points = {p.person_id: p.points * months[p.person_id] / fx.MONTHS_PER_YEAR for p in eq}
    cr = credits(state, fp, balance)
    weights = fx.comp_weights(
        system or fp.agreement.comp_system,
        points,
        cr,
        {p.person_id: p.adjust_bp for p in eq},
        balance.partnership,
    )
    weights = {k: w * months[k] / fx.MONTHS_PER_YEAR for k, w in weights.items()}
    base = fx.split_cents(pool, weights)
    fixed: dict[int, int] = {}
    for p in eq:
        floor = 0
        if p.guarantee_until_turn is not None and p.guarantee_until_turn >= start:
            floor = p.guarantee_cents * months[p.person_id] // fx.MONTHS_PER_YEAR
        if floor or p.promised_cents:
            fixed[p.person_id] = max(base[p.person_id], floor) + p.promised_cents
    if not fixed:
        return base
    rest = {k: w for k, w in weights.items() if k not in fixed}
    out = dict(fixed)
    out.update(fx.split_cents(pool - sum(fixed.values()), rest) if rest else {})
    return out


def allocate_year(
    state: GameState,
    fp: FirmPartnership,
    revenue_cum: int,
    costs_cum: int,
    working_capital: int,
    balance: Balance,
    data: GameData,
) -> tuple[GameState, FirmPartnership, dict[int, int]]:
    """December: allocate the year's distributable profit (cash basis: the accrual profit
    less the year's growth in working capital, ADR PT-0003 3) and close the year."""
    cfg = balance.partnership
    accrual = (revenue_cum - fp.pnl_closed_revenue_cents) - (costs_cum - fp.pnl_closed_costs_cents)
    profit = accrual - (working_capital - fp.wc_closed_cents)
    retained = pct_of(profit, fp.agreement.retain_bp) if profit > 0 else 0
    pool = profit - retained - fp.allocated_ytd_cents
    allocation = comp_shares(state, fp, pool, balance)
    contrib = fx.contribution_shares(credits(state, fp, balance), cfg)
    lockstep = fp.agreement.comp_system in LOCKSTEP_SYSTEMS
    heat = lateral_heat(state.turn, state.save_meta.start_ym, data, balance)  # PT-M7
    for p in fp.equity_partners:
        person = state.person(p.person_id)
        alloc = allocation.get(p.person_id, 0)
        market = fx.market_value_cents(book_cents(state, person), cfg.flight, heat)
        sat = fx.satisfaction(
            alloc,
            round(max(pool, 0) * contrib.get(p.person_id, 0.0)),
            person.personality["ego"],
            market,
            cfg,
        )
        steps = p.gate_steps if fp.agreement.comp_system == "modified_lockstep" else 0
        points = fx.next_points(p.points + p.promised_points, steps, cfg.lockstep)
        nudge = p.nudge + (cfg.confidence.comp_step * steps if lockstep else 0.0)
        budget = max(0, alloc - p.promised_cents)
        if p.admitted_turn > state.turn:
            # PT-M7c: admitted from January (December's vote), so no share of this year's pool:
            # next year's budget is their points' share of it, as `effects.admit` sets (a zero
            # budget left them seeing no comp, and flight's comp gap took nearly every one)
            total = sum(q.points for q in fp.equity_partners) or 1.0
            budget = round(max(pool, 0) * p.points / total)
        required = max(p.capital_required_cents, pct_of(budget, fp.agreement.capital_share_bp))
        instalment = -(-(required - p.capital_cents) // cfg.capital.pay_in_months)
        fp = with_partner(
            fp,
            replace(
                p,
                current_cents=p.current_cents + alloc - p.drawn_ytd_cents,
                comp_last_cents=alloc,
                drawn_ytd_cents=0,
                satisfaction=sat,
                working_ytd_cents=0,
                gate_steps=0,
                adjust_bp=0,
                promised_cents=0,
                promised_points=0.0,
                points=points,
                nudge=nudge,
                budget_cents=budget,
                budget_base_cents=budget,
                capital_required_cents=required,
                capital_instalment_cents=max(0, instalment),
            ),
        )
    avg_eq = fp.equity_months / fp.months if fp.months else float(len(fp.equity_partners))
    fp = replace(
        fp,
        pnl_closed_revenue_cents=revenue_cum,
        pnl_closed_costs_cents=costs_cum,
        wc_closed_cents=working_capital,
        last_profit_cents=profit,
        last_revenue_cents=revenue_cum - fp.pnl_closed_revenue_cents,
        last_pep_cents=round(profit / avg_eq) if avg_eq > 0 else None,
        equity_months=0,
        months=0,
        allocated_ytd_cents=0,
    )
    return state, fp, allocation
