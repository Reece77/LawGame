"""The monthly turn pipeline (ADR-0006's 12 slots with Partner Track's bodies, spec 4.1;
ADR-0012's signature).

Pattern from tst/sim/turn.py @ 02fba2aa: every phase is a pure function
`TurnContext -> TurnContext`, run in a fixed order that `tests/unit/test_turn_order.py`
guards. Phases not yet built are no-ops so the order never changes.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace

from ptk.sim.data_models import Balance, GameData
from ptk.sim.decisions import Decisions
from ptk.sim.errors import GameOverError
from ptk.sim.interfaces import DelegateHiringHook, delegate_hiring
from ptk.sim.ledger import CASH, AccountCode, LedgerBalances, LedgerEntry, apply_entries
from ptk.sim.log import LogItem
from ptk.sim.money import Cents
from ptk.sim.org.delegates import DelegateAction, available_hook, run_delegates
from ptk.sim.org.phase import clear_nudges
from ptk.sim.org.rules import growth_multipliers
from ptk.sim.people.models import WorkMonth
from ptk.sim.people.phase import people_month
from ptk.sim.rng import RngFactory
from ptk.sim.snapshot import FirmSnapshot, TurnSnapshot
from ptk.sim.state import GameState


@dataclass(frozen=True, slots=True)
class EventRequest:
    """Filled by the event director (PT-M6)."""


@dataclass(frozen=True, slots=True)
class TurnResult:
    new_state: GameState
    ledger_entries: tuple[LedgerEntry, ...]
    log_items: tuple[LogItem, ...]
    snapshot: TurnSnapshot
    event_requests: tuple[EventRequest, ...]
    delegate_actions: tuple[DelegateAction, ...] = ()  # recomputed on replay (ADR-0015)


@dataclass(frozen=True, slots=True)
class TurnContext:
    state: GameState
    decisions: Decisions
    rng: RngFactory
    balance: Balance
    data: GameData
    opening_balances: LedgerBalances
    balances: Mapping[tuple[int, AccountCode], Cents]  # running: opening + entries so far
    entries: tuple[LedgerEntry, ...] = ()
    log_items: tuple[LogItem, ...] = ()
    snapshot: TurnSnapshot | None = None
    event_requests: tuple[EventRequest, ...] = ()
    work: Mapping[int, WorkMonth] = field(default_factory=dict)  # person id -> month (PT-M1a)
    hiring_hook: DelegateHiringHook | None = None  # PT-M1b's, for delegates (PT-M2)
    delegate_actions: tuple[DelegateAction, ...] = ()

    @property
    def turn(self) -> int:
        return self.state.turn

    def post(self, *entries: LedgerEntry) -> TurnContext:
        return replace(
            self, entries=self.entries + entries, balances=apply_entries(self.balances, entries)
        )

    def log(self, *items: LogItem) -> TurnContext:
        return replace(self, log_items=self.log_items + items)


type Phase = Callable[[TurnContext], TurnContext]


# --- Phases, in ADR-0006 order (spec 4.1) --------------------------------------------------


def apply_player_decisions(ctx: TurnContext) -> TurnContext:
    """1. Offers and laterals resolve; votes held this month count (PT-M1b, PT-M4)."""
    return ctx


def delegate_and_rival_decisions(ctx: TurnContext) -> TurnContext:
    """2. Delegates run their hiring plans (ADR-0015, PT-M2); automated areas (v2) and rival
    firms (PT-M5) decide."""
    state, entries, logs, taken = run_delegates(
        ctx.state, ctx.rng, ctx.balance, ctx.data, ctx.balances, ctx.hiring_hook
    )
    ctx = replace(ctx, state=state, delegate_actions=ctx.delegate_actions + taken)
    return ctx.post(*entries).log(*logs)


def knowledge_progress(ctx: TurnContext) -> TurnContext:
    """3. Knowledge and AI adoption (v2)."""
    return ctx


def intake_and_staffing(ctx: TurnContext) -> TurnContext:
    """4. Clients instruct, conflicts are checked, hours are allocated (PT-M3a)."""
    return ctx


def work_and_billing(ctx: TurnContext) -> TurnContext:
    """5. Hours to WIP, progress and outcomes, bills, collections (PT-M3a, PT-M3b)."""
    return ctx


def payroll_and_operating_costs(ctx: TurnContext) -> TurnContext:
    """6. Salaries, bonuses, rent, insurance (PT-M1b)."""
    return ctx


def financing(ctx: TurnContext) -> TurnContext:
    """7. Revolver, draws, capital, true-up, insolvency (PT-M4)."""
    return ctx


def people_updates(ctx: TurnContext) -> TurnContext:
    """8. Strain, growth (times the supervising partner's mentoring, PT-M2), familiarity,
    class years, reveals (PT-M1a); morale and departures (PT-M1b); the org's one-off morale
    changes are cleared last (PT-M2)."""
    mentoring = growth_multipliers(ctx.state, ctx.balance)  # TST 13.5, before anyone grows
    state = people_month(ctx.state, ctx.rng, ctx.data, ctx.balance, ctx.work, mentoring)
    return replace(ctx, state=clear_nudges(state))


def market_and_macro_update(ctx: TurnContext) -> TurnContext:
    """9. Legal demand indices, rates, salary scale (PT-M7)."""
    return ctx


def stage_checks(ctx: TurnContext) -> TurnContext:
    """10. Stages, partner confidence, elections, unlocks (PT-M4)."""
    return ctx


def snapshot_and_month_end_report(ctx: TurnContext) -> TurnContext:
    """11. KPIs per firm."""
    firms = tuple(
        FirmSnapshot(firm_id=f.id, cash_cents=ctx.balances.get((f.id, CASH), 0))
        for f in ctx.state.firms
    )
    return replace(ctx, snapshot=TurnSnapshot(turn=ctx.turn, firms=firms))


def event_director_requests(ctx: TurnContext) -> TurnContext:
    """12. Events for next month; candidate pools (PT-M1b, PT-M6)."""
    return ctx


PHASES: tuple[tuple[str, Phase], ...] = (
    ("apply_player_decisions", apply_player_decisions),
    ("delegate_and_rival_decisions", delegate_and_rival_decisions),
    ("knowledge_progress", knowledge_progress),
    ("intake_and_staffing", intake_and_staffing),
    ("work_and_billing", work_and_billing),
    ("payroll_and_operating_costs", payroll_and_operating_costs),
    ("financing", financing),
    ("people_updates", people_updates),
    ("market_and_macro_update", market_and_macro_update),
    ("stage_checks", stage_checks),
    ("snapshot_and_month_end_report", snapshot_and_month_end_report),
    ("event_director_requests", event_director_requests),
)


def close_at_campaign_end(state: GameState, balance: Balance) -> GameState:
    """A standard campaign ends after its last turn (December 2034 from a 2005 start)."""
    if state.turn < balance.campaign.standard_turns or state.ended:
        return state
    meta = replace(state.save_meta, game_state="campaign_complete", ended_turn=state.turn - 1)
    return replace(state, save_meta=meta)


def advance_turn(
    state: GameState,
    decisions: Decisions,
    rng: RngFactory,
    balance: Balance,
    data: GameData,
    ledger_balances: LedgerBalances,
    work: tuple[WorkMonth, ...] = (),
    hiring_hook: DelegateHiringHook | None = None,
) -> TurnResult:
    """Resolve turn `state.turn` and return the next state plus everything to persist.

    `work` (PT-M1a): each person's month of hours, a test input until PT-M3a staffs matters
    (the brief); a person without one worked no hours. `hiring_hook` (PT-M2): the hiring
    system delegates drive; by default PT-M1b's (`interfaces.delegate_hiring`), if built."""
    if state.ended:
        raise GameOverError(f"the game is over ({state.save_meta.game_state.replace('_', ' ')})")
    ctx = TurnContext(
        state=state,
        decisions=decisions,
        rng=rng,
        balance=balance,
        data=data,
        opening_balances=ledger_balances,
        balances=dict(ledger_balances),
        work={w.person_id: w for w in work},
        hiring_hook=hiring_hook or available_hook(delegate_hiring),
    )
    for _name, phase in PHASES:
        ctx = phase(ctx)
    if ctx.snapshot is None:
        raise RuntimeError("snapshot phase did not run")
    next_state = close_at_campaign_end(replace(ctx.state, turn=state.turn + 1), balance)
    return TurnResult(
        new_state=next_state,
        ledger_entries=ctx.entries,
        log_items=ctx.log_items,
        snapshot=ctx.snapshot,
        event_requests=ctx.event_requests,
        delegate_actions=ctx.delegate_actions,
    )
