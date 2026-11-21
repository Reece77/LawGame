"""The partnership's turn steps (spec 4.1):

- phase 1: votes held this month count (governance), lateral offers resolve (laterals);
- phase 7: capital, draws, the true-up, the revolver, insolvency (books);
- phase 8: partner flight: approaches, decisions, departures, clients following (flight);
  up or out; lateral books arrive;
- phase 10: stages, the month's P&L point, working credit, confidence, petitions and
  elections, dissolution (governance, election).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace

from ptk.sim.billing.kpis import receivables_cents, wip_cents
from ptk.sim.data_models import Balance, GameData
from ptk.sim.interfaces import month_hours
from ptk.sim.ledger import CASH, PARTNERS_CAPITAL, REVOLVER, AccountCode, LedgerEntry
from ptk.sim.log import LogItem, inbox_item
from ptk.sim.partnership import formulas as fx
from ptk.sim.partnership.books import MoneyMonth, drawn_cents, financing_month
from ptk.sim.partnership.careers import assign_sponsors, december, moving_on_month
from ptk.sim.partnership.common import cumulative_pnl, lawyers, put
from ptk.sim.partnership.election import election_month
from ptk.sim.partnership.flight import flight_month, with_hint
from ptk.sim.partnership.governance import confidence_month, resolve_votes
from ptk.sim.partnership.kpis import explain, leverage_bp
from ptk.sim.partnership.laterals import books_arrive
from ptk.sim.partnership.laterals import resolve_offers as resolve_lateral_offers
from ptk.sim.partnership.models import FirmPartnership, PnlPoint, with_approach, with_partner
from ptk.sim.rng import RngFactory
from ptk.sim.snapshot import FirmSnapshot
from ptk.sim.state import GameState, with_firm

PNL_POINTS = 13  # tunable-exempt: twelve months of differences


def votes_and_offers(
    state: GameState, rng: RngFactory, balance: Balance, data: GameData
) -> tuple[GameState, tuple[LedgerEntry, ...], tuple[LogItem, ...]]:
    """Phase 1: this month's votes count; lateral partners answer offers."""
    month = resolve_votes(state, rng, balance, data)
    state, entries, logs = resolve_lateral_offers(month.state, rng, balance, data)
    return state, (*month.entries, *entries), (*month.log, *logs)


def people_month(
    state: GameState,
    rng: RngFactory,
    balance: Balance,
    data: GameData,
    balances: Mapping[tuple[int, AccountCode], int],
) -> tuple[GameState, tuple[LedgerEntry, ...], tuple[LogItem, ...]]:
    """Phase 8: approaches, decisions and departures; clients follow; associates told to
    move on leave; lateral books arrive."""
    state, entries, logs = flight_month(state, rng, balance, data, balances)
    state, moved = moving_on_month(state, data)
    state, arrived = books_arrive(state, balance)
    return state, entries, (*logs, *moved, *arrived)


def stage_checks(
    state: GameState,
    rng: RngFactory,
    balances: Mapping[tuple[int, AccountCode], int],
    balance: Balance,
    data: GameData,
) -> tuple[GameState, tuple[LogItem, ...]]:
    """Phase 10: the month's books and stage, confidence, sponsors, December's up or out,
    the MP's term and elections, approach bands, and dissolution."""
    state, logs = month_end(state, balances, balance)
    state = confidence_month(state, balance)
    state = assign_sponsors(state, balance, data)
    state, told = december(state, rng, balance)
    state, elected = election_month(state, rng, balance, data)
    state = refresh_hints(state, balance)
    state, dissolved = partners_dissolve(state, balance)
    return state, (*logs, *told, *elected, *dissolved)


def refresh_hints(state: GameState, balance: Balance) -> GameState:
    for fp in state.partnership.firms:
        for a in fp.approaches:
            if a.status in ("open", "countered"):
                fp = with_approach(fp, with_hint(state, a, balance))
        state = put(state, fp)
    return state


def partners_dissolve(state: GameState, balance: Balance) -> tuple[GameState, tuple[LogItem, ...]]:
    """A stricken firm (out of cash after the revolver) whose restless partners reach
    dissolve_restless_bp of the equity partners (the MP aside) votes to dissolve."""
    cfg = balance.partnership
    logs: list[LogItem] = []
    for fp in state.partnership.firms:
        if state.ended:
            break
        stricken = fp.insolvent_months >= cfg.dissolve_vote_months
        others = [p for p in fp.equity_partners if p.person_id != fp.mp_id]
        if not stricken or len(others) < 2:  # tunable-exempt: a vote needs partners
            continue
        restless = sum(1 for p in others if p.confidence < cfg.confidence.restless)
        if restless * 10_000 >= cfg.dissolve_restless_bp * len(others):  # tunable-exempt: bp
            state = dissolve(state, fp.firm_id)
            logs.append(
                inbox_item(state.turn, fp.firm_id, "partners_dissolve", link_kind="finance")
            )
    return state, tuple(logs)


def with_kpis(
    snap: FirmSnapshot, state: GameState, balances: Mapping[tuple[int, AccountCode], int]
) -> FirmSnapshot:
    """Phase 11: the partnership's KPIs on a firm's snapshot."""
    fp = state.partnership.of(snap.firm_id)
    if fp is None:
        return snap
    e = explain(state, fp)
    return replace(
        snap,
        pep_cents=e.pep_cents,
        rpl_cents=e.rpl_cents,
        margin_bp=e.margin_bp,
        leverage_bp=leverage_bp(e),
        equity_partners=len(fp.equity_partners),
        revolver_cents=drawn_cents(balances, snap.firm_id),
    )


def financing(
    state: GameState,
    balances: Mapping[tuple[int, AccountCode], int],
    balance: Balance,
    data: GameData,
) -> MoneyMonth:
    ar = {
        fp.firm_id: receivables_cents(state.billing, fp.firm_id) for fp in state.partnership.firms
    }
    wip = {fp.firm_id: wip_cents(state.billing, fp.firm_id) for fp in state.partnership.firms}
    return financing_month(state, balances, ar, wip, balance, data)


def cfo_forecast(
    fp: FirmPartnership, turn: int, balance: Balance
) -> tuple[FirmPartnership, tuple[LogItem, ...]]:
    """PT-M7b: the CFO's forecast warning (spec 8.7), at most once a cooldown: a covenant the
    trailing trend breaks within `forecast_months` (`fx.forecast_breach`)."""
    cfg = balance.partnership.revolver
    if fp.called_turn is not None or fp.breach_months > 0:
        return fp, ()
    cooled = (
        fp.last_forecast_turn is None
        or turn - fp.last_forecast_turn >= balance.partnership.cfo_warning_cooldown
    )
    if not cooled:
        return fp, ()
    departed = sum(
        d.book_cents for d in fp.departures if d.equity and turn - d.turn < fx.MONTHS_PER_YEAR
    )
    found = fx.forecast_breach(fp.pnl, departed, cfg)
    if found is None:
        return fp, ()
    item = inbox_item(
        turn,
        fp.firm_id,
        "cfo_forecast",
        link_kind="finance",
        covenant=found.covenant,
        months=found.months,
        drawn_cents=found.drawn_cents,
    )
    return replace(fp, last_forecast_turn=turn), (item,)


def month_end(
    state: GameState, balances: Mapping[tuple[int, AccountCode], int], balance: Balance
) -> tuple[GameState, tuple[LogItem, ...]]:
    """Phase 10 bookkeeping: working credit, the P&L point, the year's equity months, the
    firm's stage (spec 3: by lawyers, never back down), and dissolution."""
    logs: list[LogItem] = []
    hours: dict[int, int] = {}
    for fp in state.partnership.firms:
        for r in month_hours(state, fp.firm_id):
            hours[r.person_id] = hours.get(r.person_id, 0) + r.value_cents
        for p in fp.partners:
            if hours.get(p.person_id):
                fp = with_partner(
                    fp, replace(p, working_ytd_cents=p.working_ytd_cents + hours[p.person_id])
                )
        revenue, costs = cumulative_pnl(balances, fp.firm_id)
        n_law = lawyers(state, fp.firm_id, balance)
        point = PnlPoint(
            state.turn,
            revenue,
            costs,
            len(fp.equity_partners),
            n_law,
            drawn_cents=-balances.get((fp.firm_id, REVOLVER), 0),  # PT-M7b: the forecast's
            capital_cents=-balances.get((fp.firm_id, PARTNERS_CAPITAL), 0),
            cash_cents=balances.get((fp.firm_id, CASH), 0),
        )
        fp = replace(
            fp,
            pnl=(*fp.pnl, point)[-PNL_POINTS:],
            equity_months=fp.equity_months + len(fp.equity_partners),
            months=fp.months + 1,
        )
        fp, forecast = cfo_forecast(fp, state.turn, balance)  # PT-M7b (spec 8.7)
        logs.extend(forecast)
        state = put(state, fp)
        firm = state.firm(fp.firm_id)
        stage = max(firm.stage, fx.stage_for(n_law, balance.partnership.stages))
        if stage != firm.stage:
            state = with_firm(state, replace(firm, stage=stage))
            logs.append(
                inbox_item(state.turn, firm.id, "stage_reached", link_kind="finance", stage=stage)
            )
        if fp.insolvent_months >= balance.partnership.insolvency_months:
            state = dissolve(state, fp.firm_id)
            logs.append(inbox_item(state.turn, fp.firm_id, "firm_dissolved", link_kind="finance"))
    return state, tuple(logs)


def dissolve(state: GameState, firm_id: int) -> GameState:
    """The firm dissolves (ADR PT-0007 4): for the player's firm the game is over."""
    if firm_id != state.player.id or state.ended:
        return state
    meta = replace(state.save_meta, game_state="dissolved", ended_turn=state.turn)
    return replace(state, save_meta=meta)
