"""Turn phases 4 and 5 for clients and matters (spec 4.1).

Phase 4 (intake and staffing): January's rate rise (PT-M7a); the month's demand (stream
`demand`); conflicted instructions past their window are declined; teams lose people who
left (a matter whose lead left is re-staffed by the default rule); matters the player has not
staffed are re-planned by the default rule; clients instruct (intake); a named pro bono
matter may arrive (PT-M7a); the month's hours are allocated, named matters first, then flow,
then pro bono. The result is every fee earner's `WorkMonth`, which feeds growth, familiarity,
strain (PT-M1a) and the hours morale term (PT-M1b) in phase 8.

Phase 5 (work): progress, errors, settlement offers and outcomes on named matters; hidden
conflicts; origination credit; relationships. Hours post to matters' WIP at standard value
only (PT-M3b bills them).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from ptk.sim.data_models import Balance, GameData
from ptk.sim.fastcopy import replace
from ptk.sim.log import LogItem
from ptk.sim.matters.failures import fail_clients
from ptk.sim.matters.intake import expire_conflicted, intake, with_matter
from ptk.sim.matters.market import monthly_demand
from ptk.sim.matters.pro_bono import named_intake, record_month
from ptk.sim.matters.progress import work_month
from ptk.sim.matters.rates import yearly_rise
from ptk.sim.matters.staffing import fee_earners, month_hours, planned_load, staff_matter
from ptk.sim.people.models import WorkMonth
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState


@dataclass(frozen=True, slots=True)
class StaffedMonth:
    state: GameState
    work: dict[int, WorkMonth]
    unserved: dict[tuple[int, str], float]
    log: tuple[LogItem, ...]


def prune_teams(state: GameState, firm_id: int, data: GameData, balance: Balance) -> GameState:
    """People who left come off their teams; a matter that lost its lead is re-staffed."""
    staff = set(state.staff_ids(firm_id))
    market = state.market
    for m in market.open_matters(firm_id):
        team = tuple(tm for tm in m.team if tm.person_id in staff)
        if team == m.team and (m.lead_id is None or m.lead_id in staff):
            continue
        matter = replace(m, team=team)
        if matter.lead_id not in staff:
            matter = staff_matter(
                replace(state, market=market), replace(matter, lead_id=None, team=()), data, balance
            )
        market = with_matter(market, matter)
    return replace(state, market=market)


def replan(state: GameState, firm_id: int, data: GameData, balance: Balance) -> GameState:
    """Matters the player has not staffed are re-planned by the default rule, by id (the
    practice leader's month: free capacity goes to matters that need it)."""
    # PT-M11 (T12): the fee earners once; re-planning changes teams, not people, so they change
    # only when an early case assessment's lead moves (its hours are that lead's this month)
    earners = fee_earners(state, firm_id, data, balance)
    # PT-M12 (T12): the firm's planned load once, kept current as teams change (it was summed
    # over every open matter for each matter re-planned)
    load = planned_load(state.market, firm_id)
    for m in state.market.open_matters(firm_id):
        if m.auto_staff:
            staffed = staff_matter(state, m, data, balance, earners, load)
            if staffed != m:
                state = replace(state, market=with_matter(state.market, staffed))
                for tm in m.team:
                    load[tm.person_id] = load.get(tm.person_id, 0) - tm.planned_tenths
                for tm in staffed.team:
                    load[tm.person_id] = load.get(tm.person_id, 0) + tm.planned_tenths
                a = m.assessment
                if a is not None and a.turn == state.turn and staffed.lead_id != m.lead_id:
                    earners = fee_earners(state, firm_id, data, balance)
    return state


def intake_and_staffing(
    state: GameState, rng: RngFactory, data: GameData, balance: Balance
) -> StaffedMonth:
    if not state.market.clients:
        return StaffedMonth(state=state, work={}, unserved={}, log=())
    firm_id = state.player.id
    state, rose = yearly_rise(state, data, balance)  # PT-M7a: January's rate rise
    demand = monthly_demand(rng, state.turn, state, data, balance)
    state = replace(state, market=replace(state.market, demand_cents=demand))
    state, failed = fail_clients(state, data, balance)  # PT-M7: history's failures
    state, declined = expire_conflicted(state, firm_id, balance)
    state = prune_teams(state, firm_id, data, balance)
    state = replan(state, firm_id, data, balance)
    result = intake(state, firm_id, rng, demand, data, balance)
    state, pro_bono = named_intake(result.state, rng, data, balance)  # PT-M7a (spec 7.8)
    hours = month_hours(state, firm_id, result.flow_tenths, data, balance)
    state = replace(state, market=replace(state.market, hours=hours.records))
    state = record_month(state, hours.pro_bono, data, balance)
    return StaffedMonth(
        state=state,
        work=hours.work,
        unserved=hours.unserved,
        log=(*rose, *failed, *declined, *result.log, *pro_bono),
    )


def work_phase(
    state: GameState,
    rng: RngFactory,
    unserved: Mapping[tuple[int, str], float],
    data: GameData,
    balance: Balance,
) -> tuple[GameState, tuple[LogItem, ...]]:
    if not state.market.clients:
        return state, ()
    state, logs = work_month(state, state.player.id, rng, unserved, data, balance)
    return state, tuple(logs)
