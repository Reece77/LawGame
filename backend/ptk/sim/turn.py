"""The monthly turn pipeline (ADR-0006's 12 slots with Partner Track's bodies, spec 4.1;
ADR-0012's signature).

Pattern from tst/sim/turn.py @ 02fba2aa: every phase is a pure function
`TurnContext -> TurnContext`, run in a fixed order that `tests/unit/test_turn_order.py`
guards. Phases not yet built are no-ops so the order never changes.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace

from ptk.sim.automation import digest as auto_digest
from ptk.sim.automation import events as auto_events
from ptk.sim.automation.models import AreaDecision
from ptk.sim.automation.run import automation_month, seat_masks
from ptk.sim.billing.kpis import firm_snapshot
from ptk.sim.billing.models import ClientBookEntry
from ptk.sim.billing.phase import billing_month
from ptk.sim.data_models import Balance, GameData
from ptk.sim.decisions import Decisions
from ptk.sim.errors import GameOverError
from ptk.sim.events import colleagues, director, effects
from ptk.sim.events import modifiers as event_modifiers
from ptk.sim.events.models import EventRequest, TextRequest
from ptk.sim.founder import phase as founder_life
from ptk.sim.founder.models import PersonalEntry
from ptk.sim.geo import phase as geo
from ptk.sim.hiring import phases as hiring
from ptk.sim.interfaces import DelegateHiringHook, delegate_hiring
from ptk.sim.ledger import CASH, AccountCode, LedgerBalances, LedgerEntry, apply_entries
from ptk.sim.log import LogItem
from ptk.sim.macro_seed import world_data
from ptk.sim.matters import phase as matters
from ptk.sim.mergers import phase as mergers
from ptk.sim.money import Cents
from ptk.sim.org.delegates import DelegateAction, available_hook, run_delegates
from ptk.sim.org.phase import clear_nudges
from ptk.sim.org.rules import growth_multipliers
from ptk.sim.org.seat_models import SeatDecision
from ptk.sim.org.seat_phase import phase_twelve, phase_two
from ptk.sim.partnership import phase as partnership
from ptk.sim.people.models import WorkMonth
from ptk.sim.people.phase import people_month
from ptk.sim.reputation import turn_hooks as standing
from ptk.sim.risk import phase as risk
from ptk.sim.rivals import phase as rival_phase
from ptk.sim.rivals.models import RivalMove
from ptk.sim.rng import RngFactory
from ptk.sim.snapshot import TurnSnapshot
from ptk.sim.state import GameState
from ptk.sim.tech import adoption as tech_adoption


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
    rival_moves: tuple[RivalMove, ...] = ()  # rival decisions, recomputed on replay (PT-M5)
    seat_decisions: tuple[SeatDecision, ...] = ()  # PT-M8: recomputed on replay (ADR-0015)
    personal_book: tuple[PersonalEntry, ...] = ()  # the players' personal books (PT-M17)
    area_decisions: tuple[AreaDecision, ...] = ()  # PT-M9: recomputed on replay (ADR-0015)


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
    rival_moves: tuple[RivalMove, ...] = ()  # PT-M5
    seat_decisions: tuple[SeatDecision, ...] = ()  # PT-M8
    personal_book: tuple[PersonalEntry, ...] = ()  # PT-M17: the personal books' entries
    area_decisions: tuple[AreaDecision, ...] = ()  # PT-M9

    def take(self, done: rival_phase.Phase) -> TurnContext:
        """Take a rivals phase's results (PT-M5)."""
        ctx = replace(self, state=done.state, rival_moves=self.rival_moves + done.moves)
        return ctx.post(*done.entries).log(*done.log)

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
    """1. Automated areas' owners answer their routine events (PT-M9); last month's other
    unanswered events take their first choice (PT-M6); notices end;
    offers resolve; a signed campus class starts (PT-M1b); votes held this month count
    and lateral partners answer offers (PT-M4)."""
    state, routine, routine_log = auto_events.answer_routine_events(
        ctx.state, ctx.rng, ctx.balance, ctx.data
    )  # PT-M9
    ctx = replace(ctx, state=state).post(*routine).log(*routine_log)
    state, answered, answer_log = effects.auto_resolve(
        ctx.state, ctx.balance, ctx.data, critical=ctx.answer_critical
    )
    ctx = replace(ctx, state=state).post(*answered).log(*answer_log)
    state, left = hiring.end_notices(ctx.state)
    state, entries, resolved = hiring.resolve_offers(state, ctx.rng, ctx.balance, ctx.data)
    state, started = hiring.start_signed(state, ctx.balance, ctx.data)
    talks = mergers.before_votes(state, ctx.rng, ctx.data, ctx.balance)  # PT-M13: answers
    state, voted, votes = partnership.votes_and_offers(talks.state, ctx.rng, ctx.balance, ctx.data)
    closed = mergers.after_votes(state, ctx.rng, ctx.data, ctx.balance)  # PT-M13: closings
    ctx = replace(ctx, state=closed.state).post(*entries, *voted, *closed.entries)
    ctx = ctx.log(*left, *resolved, *started, *talks.log, *votes, *closed.log)
    state, trained, joined = geo.phase_one(ctx.state, ctx.rng, ctx.balance, ctx.data)  # PT-M11
    ctx = replace(ctx, state=state).post(*trained).log(*joined)
    return ctx.take(rival_phase.answer_approaches(ctx.state, ctx.rng, ctx.data, ctx.balance))


def delegate_and_rival_decisions(ctx: TurnContext) -> TurnContext:
    """2. Seat holders with authority act and pitch, the MP's seat moves confidence (PT-M8);
    automated areas decide (PT-M9: a seat whose area is automated runs its rule once, as the
    area); delegates run their hiring plans (ADR-0015, PT-M2); rival firms (PT-M5) decide."""
    masked = seat_masks(ctx.state, ctx.balance)
    seats = phase_two(ctx.state, ctx.rng, ctx.balance, ctx.data, ctx.balances, masked)
    ctx = replace(ctx, state=seats.state, seat_decisions=ctx.seat_decisions + seats.decisions)
    ctx = ctx.post(*seats.entries).log(*seats.log)
    auto = automation_month(ctx.state, ctx.rng, ctx.balance, ctx.data, ctx.balances)  # PT-M9
    ctx = replace(ctx, state=auto.state, area_decisions=ctx.area_decisions + auto.decisions)
    ctx = ctx.post(*auto.entries).log(*auto.log)
    state, entries, logs, taken = run_delegates(
        ctx.state, ctx.rng, ctx.balance, ctx.data, ctx.balances, ctx.hiring_hook
    )
    ctx = replace(ctx, state=state, delegate_actions=ctx.delegate_actions + taken)
    ctx = ctx.post(*entries).log(*logs)
    return ctx.take(rival_phase.decide(ctx.state, ctx.rng, ctx.data, ctx.balance))  # PT-M5


def knowledge_progress(ctx: TurnContext) -> TurnContext:
    """3. Knowledge and AI adoption (PT-M14): subscriptions, platform amortisation and the
    training programme post to 6100; each era's adoption moves toward its target."""
    state, entries, logs = tech_adoption.month(ctx.state, ctx.data, ctx.balance)
    return replace(ctx, state=state).post(*entries).log(*logs)


def intake_and_staffing(ctx: TurnContext) -> TurnContext:
    """4. Clients instruct, conflicts are checked, hours are allocated (PT-M3a). A person
    given a month of work as a test input keeps it (`advance_turn`'s `work`)."""
    ctx = ctx.take(rival_phase.rfps_before_intake(ctx.state, ctx.rng, ctx.data, ctx.balance))
    ctx = ctx.take(rival_phase.after_intake(ctx.state, ctx.rng, ctx.data, ctx.balance))
    state = geo.before_intake(ctx.state, ctx.rng, ctx.balance, ctx.data)  # PT-M11: cities
    month = matters.intake_and_staffing(state, ctx.rng, ctx.data, ctx.balance)
    work = {**month.work, **ctx.work_override}
    state, phv, phv_log = geo.after_staffing(month.state, ctx.data)  # PT-M11: pro hac vice
    ctx = replace(ctx, state=state, work=work, unserved=month.unserved).post(*phv)
    return ctx.log(*month.log, *phv_log)


def work_and_billing(ctx: TurnContext) -> TurnContext:
    """5. Hours to WIP at standard value, progress and outcomes, relationships (PT-M3a);
    bills and collections (PT-M3b)."""
    state, logs = matters.work_phase(ctx.state, ctx.rng, ctx.unserved, ctx.data, ctx.balance)
    month = billing_month(state, ctx.rng, ctx.data, ctx.balance)
    ctx = replace(ctx, state=month.state, client_book=ctx.client_book + month.book)
    return ctx.post(*month.entries).log(*logs, *month.log)


def payroll_and_operating_costs(ctx: TurnContext) -> TurnContext:
    """6. Salaries, benefits, rent per head, recruiting; December bonuses (PT-M1b); the
    offices' leases (PT-M11); risk: claims, the insurance policy and its premium (PT-M15)."""
    entries, logs = hiring.payroll(ctx.state, ctx.balance, ctx.data)
    state, leases, _ = geo.phase_six(ctx.state, ctx.balance, ctx.data)  # PT-M11: offices
    shared = mergers.phase_six(state, ctx.balances, ctx.balance)  # PT-M13: the verein's costs
    ctx = replace(ctx, state=shared.state).post(*entries, *leases, *shared.entries).log(*logs)
    month = risk.month(
        ctx.state, ctx.start or ctx.state, ctx.rng, ctx.balance, ctx.data, ctx.balances
    )
    ctx = replace(ctx, state=month.state, client_book=ctx.client_book + month.book)
    return ctx.post(*month.entries).log(*month.log)  # PT-M15


def financing(ctx: TurnContext) -> TurnContext:
    """7. Capital in and out, revolver interest, draws, the December allocation and true-up,
    the revolver's draws and covenants, insolvency (PT-M4); the founder's personal book
    mirrors their draws, true-up and capital, annuities are paid, partners at the retirement
    age retire (PT-M17)."""
    before = ctx.state
    month = partnership.financing(ctx.state, ctx.balances, ctx.balance, ctx.data)
    state = mergers.phase_seven(month.state, ctx.balance)  # PT-M13: merged partners' budgets
    ctx = replace(ctx, state=state).post(*month.entries).log(*month.log)
    life = founder_life.financing(ctx.state, before, ctx.rng, ctx.balances, ctx.balance, ctx.data)
    ctx = replace(ctx, state=life.state, personal_book=ctx.personal_book + life.personal)
    return ctx.post(*life.entries).log(*life.log)


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
    merged = mergers.phase_eight(state, ctx.rng, ctx.balance)  # PT-M13: integration
    ctx = replace(ctx, state=clear_nudges(merged.state)).post(*flight).log(*merged.log)
    ctx = ctx.log(*departures, *tags, *moves)
    state, _, geo_logs = geo.phase_eight(ctx.state, ctx.rng, ctx.balance, ctx.data)  # PT-M11
    ctx = replace(ctx, state=state).log(*geo_logs)
    return ctx.take(rival_phase.people(ctx.state, ctx.rng, ctx.data, ctx.balance))  # PT-M5


def market_and_macro_update(ctx: TurnContext) -> TurnContext:
    """9. The salary scale moves (PT-M1b: history to 2015); rivals' dated history, collapses
    and boutiques (PT-M5); legal demand and rates (PT-M7)."""
    ctx = replace(ctx, state=hiring.apply_scale(ctx.state, ctx.data))
    ctx = ctx.take(rival_phase.market(ctx.state, ctx.rng, ctx.data, ctx.balance))
    step = mergers.phase_nine(ctx.state, ctx.rng, ctx.data, ctx.balance)  # PT-M13
    ctx = replace(ctx, state=step.state, rival_moves=ctx.rival_moves + step.moves)
    return ctx.log(*step.log)


def stage_checks(ctx: TurnContext) -> TurnContext:
    """10. Stages, the month's P&L, partner confidence, petitions and elections, dissolution
    (PT-M4); the founder's persona, bar politics, foundation, family, adviser and succession
    (PT-M17); reputation moves, the rankings and tables publish (PT-M16)."""
    state, logs = partnership.stage_checks(ctx.state, ctx.rng, ctx.balances, ctx.balance, ctx.data)
    ctx = replace(ctx, state=state).log(*logs)
    life = founder_life.month(
        ctx.state, ctx.start or ctx.state, ctx.rng, ctx.balances, ctx.balance, ctx.data
    )
    ctx = replace(ctx, state=life.state, personal_book=ctx.personal_book + life.personal)
    ctx = ctx.post(*life.entries).log(*life.log)
    state, logs = standing.month(ctx.state, ctx.start or ctx.state, ctx.rng, ctx.balance, ctx.data)
    return replace(ctx, state=state).log(*logs)  # PT-M16: reputation, rankings


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
    and this month's read-only texts (PT-M6); the automation digest (PT-M9)."""
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
    seats = phase_twelve(state, ctx.balance, ctx.data)  # PT-M8: committee, meeting, reports
    state, texts = seats.state, texts + seats.texts
    digest = auto_digest.digest_item(state, ctx.turn, ctx.balance, ctx.data)  # PT-M9
    month_end = (*seats.log, digest) if digest is not None else seats.log
    ctx = replace(
        ctx,
        state=state,
        event_requests=ctx.event_requests + requests,
        text_requests=ctx.text_requests + texts,
    )
    return ctx.log(*batches, *pools, *month_end)


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
    data = world_data(data, balance, state.save_meta.master_seed)  # PT-M10: the save's world
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
    next_state = founder_life.month_start(next_state, balance)  # PT-M17: committee, family time
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
        rival_moves=ctx.rival_moves,
        seat_decisions=ctx.seat_decisions,
        personal_book=ctx.personal_book,
        area_decisions=ctx.area_decisions,
    )
