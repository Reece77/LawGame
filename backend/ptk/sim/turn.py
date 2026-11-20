"""The monthly turn pipeline (ADR-0006's 12 slots with Partner Track's bodies, spec 4.1;
ADR-0012's signature).

Pattern from tst/sim/turn.py @ 02fba2aa: every phase is a pure function
`TurnContext -> TurnContext`, run in a fixed order that `tests/unit/test_turn_order.py`
guards. Phases not yet built are no-ops so the order never changes.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace

from ptk.sim.billing.kpis import firm_snapshot
from ptk.sim.billing.models import ClientBookEntry
from ptk.sim.billing.phase import billing_month
from ptk.sim.data_models import Balance, GameData
from ptk.sim.decisions import Decisions
from ptk.sim.errors import GameOverError
from ptk.sim.events import colleagues, director, effects
from ptk.sim.events import modifiers as event_modifiers
from ptk.sim.events.models import EventRequest, TextRequest
from ptk.sim.hiring import phases as hiring
from ptk.sim.interfaces import DelegateHiringHook, delegate_hiring
from ptk.sim.ledger import CASH, AccountCode, LedgerBalances, LedgerEntry, apply_entries
from ptk.sim.log import LogItem
from ptk.sim.matters import phase as matters
from ptk.sim.money import Cents
from ptk.sim.org.delegates import DelegateAction, available_hook, run_delegates
from ptk.sim.org.phase import clear_nudges
from ptk.sim.org.rules import growth_multipliers
from ptk.sim.partnership import phase as partnership
from ptk.sim.people.models import WorkMonth
from ptk.sim.people.phase import people_month
from ptk.sim.rng import RngFactory
from ptk.sim.snapshot import TurnSnapshot
from ptk.sim.state import GameState


@dataclass(frozen=True, slots=True)
class TurnResult:
    new_state: GameState
    ledger_entries: tuple[LedgerEntry, ...]
    log_items: tuple[LogItem, ...]
    snapshot: TurnSnapshot
    event_requests: tuple[EventRequest, ...]
    delegate_actions: tuple[DelegateAction, ...] = ()  # recomputed on replay (ADR-0015)
    text_requests: tuple[TextRequest, ...] = ()  # PT-M6: read-only texts to write
    client_book: tuple[ClientBookEntry, ...] = ()  # client-money entries (PT-M3b)


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
    work_override: Mapping[int, WorkMonth] = field(default_factory=dict)  # test input (PT-M1a)
    unserved: Mapping[tuple[int, str], float] = field(default_factory=dict)  # PT-M3a flow
    hiring_hook: DelegateHiringHook | None = None  # PT-M1b's, for delegates (PT-M2)
    delegate_actions: tuple[DelegateAction, ...] = ()
    start: GameState | None = None  # the state the turn began from (PT-M6 triggers)
    answer_critical: bool = False  # PT-M6: scripts answer written critical events too
    text_requests: tuple[TextRequest, ...] = ()
    client_book: tuple[ClientBookEntry, ...] = ()  # PT-M3b: the client-money book's entries

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
    """1. Last month's unanswered events take their first choice (PT-M6); notices end;
    offers resolve; a signed campus class starts (PT-M1b); votes held this month count
    and lateral partners answer offers (PT-M4)."""
    state, answered, answer_log = effects.auto_resolve(
        ctx.state, ctx.balance, ctx.data, critical=ctx.answer_critical
    )
    ctx = replace(ctx, state=state).post(*answered).log(*answer_log)
    state, left = hiring.end_notices(ctx.state)
    state, entries, resolved = hiring.resolve_offers(state, ctx.rng, ctx.balance, ctx.data)
    state, started = hiring.start_signed(state, ctx.balance, ctx.data)
    state, voted, votes = partnership.votes_and_offers(state, ctx.rng, ctx.balance, ctx.data)
    ctx = replace(ctx, state=state).post(*entries, *voted)
    return ctx.log(*left, *resolved, *started, *votes)


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
    """4. Clients instruct, conflicts are checked, hours are allocated (PT-M3a). A person
    given a month of work as a test input keeps it (`advance_turn`'s `work`)."""
    month = matters.intake_and_staffing(ctx.state, ctx.rng, ctx.data, ctx.balance)
    work = {**month.work, **ctx.work_override}
    return replace(ctx, state=month.state, work=work, unserved=month.unserved).log(*month.log)


def work_and_billing(ctx: TurnContext) -> TurnContext:
    """5. Hours to WIP at standard value, progress and outcomes, relationships (PT-M3a);
    bills and collections (PT-M3b)."""
    state, logs = matters.work_phase(ctx.state, ctx.rng, ctx.unserved, ctx.data, ctx.balance)
    month = billing_month(state, ctx.rng, ctx.data, ctx.balance)
    ctx = replace(ctx, state=month.state, client_book=ctx.client_book + month.book)
    return ctx.post(*month.entries).log(*logs, *month.log)


def payroll_and_operating_costs(ctx: TurnContext) -> TurnContext:
    """6. Salaries, benefits, rent per head, recruiting; December bonuses (PT-M1b); insurance
    and technology arrive later."""
    entries, logs = hiring.payroll(ctx.state, ctx.balance, ctx.data)
    return ctx.post(*entries).log(*logs)


def financing(ctx: TurnContext) -> TurnContext:
    """7. Capital in and out, revolver interest, draws, the December allocation and true-up,
    the revolver's draws and covenants, insolvency (PT-M4)."""
    month = partnership.financing(ctx.state, ctx.balances, ctx.balance, ctx.data)
    return replace(ctx, state=month.state).post(*month.entries).log(*month.log)


def people_updates(ctx: TurnContext) -> TurnContext:
    """8. Strain, growth (times the supervising partner's mentoring, PT-M2), familiarity,
    class years, reveals (PT-M1a); morale, resignations and tag reveals (PT-M1b); the org's
    one-off morale changes are cleared (PT-M2); partner flight, up or out and lateral
    books (PT-M4)."""
    mentoring = growth_multipliers(ctx.state, ctx.balance)  # TST 13.5, before anyone grows
    state = people_month(ctx.state, ctx.rng, ctx.data, ctx.balance, ctx.work, mentoring)
    state, departures = hiring.morale_and_departures(
        state, ctx.rng, ctx.balance, ctx.data, ctx.work
    )
    state, tags = hiring.monthly_tag_reveals(state, ctx.rng, ctx.balance, ctx.data)
    state, flight, moves = partnership.people_month(
        state, ctx.rng, ctx.balance, ctx.data, ctx.balances
    )
    ctx = replace(ctx, state=clear_nudges(state)).post(*flight)
    return ctx.log(*departures, *tags, *moves)


def market_and_macro_update(ctx: TurnContext) -> TurnContext:
    """9. The salary scale moves (PT-M1b: history to 2015); legal demand and rates (PT-M7)."""
    return replace(ctx, state=hiring.apply_scale(ctx.state, ctx.data))


def stage_checks(ctx: TurnContext) -> TurnContext:
    """10. Stages, the month's P&L, partner confidence, petitions and elections, dissolution
    (PT-M4)."""
    state, logs = partnership.stage_checks(ctx.state, ctx.rng, ctx.balances, ctx.balance, ctx.data)
    return replace(ctx, state=state).log(*logs)


def snapshot_and_month_end_report(ctx: TurnContext) -> TurnContext:
    """11. KPIs per firm."""
    firms = tuple(
        partnership.with_kpis(
            firm_snapshot(ctx.state.billing, f.id, ctx.turn, ctx.balances.get((f.id, CASH), 0)),
            ctx.state,
            ctx.balances,
        )
        for f in ctx.state.firms
    )
    return replace(ctx, snapshot=TurnSnapshot(turn=ctx.turn, firms=firms))


def event_director_requests(ctx: TurnContext) -> TurnContext:
    """12. Candidates leave; lateral batches, the campus pools and the summer programme
    (PT-M1b); modifiers expire, colleagues' relationships move, then events for next month
    and this month's read-only texts (PT-M6)."""
    state = hiring.expire_candidates(ctx.state)
    state, batches = hiring.lateral_batches(state, ctx.rng, ctx.balance, ctx.data)
    state, pools = hiring.campus_pools(state, ctx.rng, ctx.balance, ctx.data)
    state = hiring.summer_month(state, ctx.balance, ctx.data)
    state, _expired = event_modifiers.expire(state)
    state = colleagues.colleagues_month(state, ctx.balance.colleagues)
    cash = ctx.balances.get((state.player.id, CASH), 0)
    state, requests = director.direct(
        state, ctx.start or ctx.state, ctx.rng, ctx.balance, ctx.data, cash
    )
    texts = director.text_requests(state, ctx.balance)
    ctx = replace(
        ctx,
        state=state,
        event_requests=ctx.event_requests + requests,
        text_requests=ctx.text_requests + texts,
    )
    return ctx.log(*batches, *pools)


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
    *,
    answer_critical: bool = False,
) -> TurnResult:
    """Resolve turn `state.turn` and return the next state plus everything to persist.

    `work` (PT-M1a): each person's month of hours, a test input until PT-M3a staffs matters
    (the brief); a person without one worked no hours. `hiring_hook` (PT-M2): the hiring
    system delegates drive; by default PT-M1b's (`interfaces.delegate_hiring`), if built.
    `answer_critical` (PT-M6): a written critical event takes its first choice instead of
    refusing the turn (scripts, the golden seeds, Holiday later); the player's Continue is
    refused while one waits (spec 15)."""
    if state.ended:
        raise GameOverError(f"the game is over ({state.save_meta.game_state.replace('_', ' ')})")
    if not answer_critical:
        effects.check_continue(state)
    ctx = TurnContext(
        state=state,
        decisions=decisions,
        rng=rng,
        balance=balance,
        data=data,
        opening_balances=ledger_balances,
        balances=dict(ledger_balances),
        work={w.person_id: w for w in work},
        work_override={w.person_id: w for w in work},
        hiring_hook=hiring_hook or available_hook(delegate_hiring),
        start=state,
        answer_critical=answer_critical,
    )
    for _name, phase in PHASES:
        ctx = phase(ctx)
    if ctx.snapshot is None:
        raise RuntimeError("snapshot phase did not run")
    # The founding partner's energy resets after phase 12 for the new month (ADR-0014).
    next_state = hiring.reset_energy(replace(ctx.state, turn=state.turn + 1), balance)
    next_state = close_at_campaign_end(next_state, balance)
    return TurnResult(
        new_state=next_state,
        ledger_entries=ctx.entries,
        log_items=ctx.log_items,
        snapshot=ctx.snapshot,
        event_requests=ctx.event_requests,
        delegate_actions=ctx.delegate_actions,
        text_requests=ctx.text_requests,
        client_book=ctx.client_book,
    )
