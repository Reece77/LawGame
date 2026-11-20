"""Turn phases 4 and 5 for clients and matters (spec 4.1).

Phase 4 (intake and staffing): the month's demand (stream `demand`); conflicted
instructions past their window are declined; teams lose people who left (a matter whose lead
left is re-staffed by the default rule); clients instruct (intake); the month's hours are
allocated, named matters first, then flow. The result is every fee earner's `WorkMonth`, which
feeds growth, familiarity, strain (PT-M1a) and the hours morale term (PT-M1b) in phase 8.

Phase 5 (work): progress, errors, settlement offers and outcomes on named matters; hidden
conflicts; origination credit; relationships. Hours post to matters' WIP at standard value
only (PT-M3b bills them).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace

from ptk.sim.data_models import Balance, GameData
from ptk.sim.log import LogItem
from ptk.sim.matters.intake import expire_conflicted, intake, with_matter
from ptk.sim.matters.market import monthly_demand
from ptk.sim.matters.progress import work_month
from ptk.sim.matters.staffing import month_hours, staff_matter
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


def intake_and_staffing(
    state: GameState, rng: RngFactory, data: GameData, balance: Balance
) -> StaffedMonth:
    if not state.market.clients:
        return StaffedMonth(state=state, work={}, unserved={}, log=())
    firm_id = state.player.id
    demand = monthly_demand(rng, state.turn, state, data)
    state = replace(state, market=replace(state.market, demand_cents=demand))
    state, declined = expire_conflicted(state, firm_id, balance)
    state = prune_teams(state, firm_id, data, balance)
    result = intake(state, firm_id, rng, demand, data, balance)
    state = result.state
    hours = month_hours(state, firm_id, result.flow_tenths, data, balance)
    state = replace(state, market=replace(state.market, hours=hours.records))
    return StaffedMonth(
        state=state, work=hours.work, unserved=hours.unserved, log=(*declined, *result.log)
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
