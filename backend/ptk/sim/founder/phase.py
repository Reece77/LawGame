"""PT-M17's turn steps (spec 4.1), beside the partnership's (lane C, read through
`ptk.sim.interfaces`):

- phase 7, after the partnership's financing (`financing`): each player's personal book
  mirrors their draws, true-up and capital (the book opens on the first month); the capital
  loan, tax and investment returns; annuities paid (2600); the month's bar-politics spend
  (6950); partners at the retirement age retire;
- phase 10, after the partnership's stage checks (`month`): the persona's sources, drift and
  effects; bar politics and its elections; December's foundation grants and the firm's best
  year; the family's month; the adviser; succession (triggers, the due date, the vote and the
  hand-over);
- after the energy reset (`month_start`): a committee seat's and family time's energy.

Ported from backend/tst/sim/founder/phase.py @ 121d318a (Tech Startup Tycoon) as a pattern;
changed: Partner Track's phases and systems (see each module).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace

from simcore.kernel.calendar import turn_to_ym
from simcore.kernel.money import Cents

from ptk.sim import interfaces as ix
from ptk.sim.data_models import Balance, GameData
from ptk.sim.family import adviser, succession
from ptk.sim.family.phase import family_month, head_active
from ptk.sim.founder import foundation, influence, persona, personal, retirement
from ptk.sim.founder.models import (
    FAMILY_OFFICE,
    INVESTMENTS,
    FounderLife,
    FounderLifeState,
    PersonalBook,
    PersonalEntry,
    with_book,
    with_life,
)
from ptk.sim.ledger import CASH, LOBBYING, AccountCode, LedgerEntry, apply_entries
from ptk.sim.log import LogItem, inbox_item
from ptk.sim.state import GameState, with_person_states
from ptk.sim.streams import RngFactory

DECEMBER = 12  # tunable-exempt: the firm's year ends in December (ADR PT-0002)


@dataclass(frozen=True, slots=True)
class LifeMonth:
    state: GameState
    entries: tuple[LedgerEntry, ...] = ()
    personal: tuple[PersonalEntry, ...] = ()
    log: tuple[LogItem, ...] = ()


def ensure_player(
    state: GameState, balance: Balance, marks: GameState | None = None
) -> tuple[GameState, tuple[PersonalEntry, ...]]:
    """The player's life and personal book exist (opened on the first month they play). The
    book's marks come from `marks` (phase 7: the state before the partnership's financing,
    so the month's draws are mirrored)."""
    pid = state.founder_of(state.player.id)
    if pid is None:
        return state, ()
    fl = state.founder_life
    entries: tuple[PersonalEntry, ...] = ()
    if fl.life(pid) is None:
        fl = with_life(fl, persona.new_life(pid, state.turn, balance))
    if fl.book(pid) is None:
        book, entries = personal.open_book(
            pid,
            state.turn,
            balance.founder_life.personal.start_cents,
            ix.partner_account(marks or state, state.player.id, pid),
        )
        fl = with_book(fl, book)
    return replace(state, founder_life=fl), entries


def financing(
    state: GameState,
    before: GameState,
    rng: RngFactory,
    balances: Mapping[tuple[int, AccountCode], Cents],
    balance: Balance,
    data: GameData,
) -> LifeMonth:
    pend = state.founder_life.pending  # actions' entries since the last turn
    state = replace(state, founder_life=replace(state.founder_life, pending=()))
    if state.partnership.of(state.player.id) is None:
        return LifeMonth(state, personal=pend)
    state, opened = ensure_player(state, balance, before)
    out: list[PersonalEntry] = [*pend, *opened]
    firm = state.player.id
    fl = state.founder_life
    start = state.save_meta.start_ym
    for book in fl.books:
        m = personal.mirror(
            book, ix.partner_account(state, firm, book.person_id), state.turn, start, balance
        )
        b, more = (
            personal.returns(
                m.book,
                state.turn,
                personal.investment_stream(rng, state.turn, book.person_id),
                balance,
            )
            if _invested(m.book)
            else (m.book, ())
        )
        fl = with_book(fl, b)
        out += m.entries
        out += more
    state = replace(state, founder_life=fl)
    entries: list[LedgerEntry] = []
    running = dict(balances)
    paid = retirement.pay_annuities(state, running)
    state = paid.state
    entries += paid.entries
    out += paid.personal
    running = apply_entries(running, paid.entries)
    you = state.founder_of(firm)
    life = state.founder_life.life(you) if you is not None else None
    if life is not None and life.bar_spend_cents > 0:
        entries.append(
            LedgerEntry.transfer(
                turn=state.turn,
                firm_id=firm,
                memo="Bar politics",
                debit=LOBBYING,
                credit=CASH,
                amount=life.bar_spend_cents,
            )
        )
        running = apply_entries(running, entries[-1:])
    gone = retirement.retirements(state, rng, balance, data, running)
    state = gone.state
    entries += gone.entries
    return LifeMonth(state, tuple(entries), tuple(out), gone.log)


def _invested(book: PersonalBook) -> bool:
    return book.bal(INVESTMENTS) > 0 or book.bal(FAMILY_OFFICE) > 0


def month(
    state: GameState,
    start: GameState,
    rng: RngFactory,
    balances: Mapping[tuple[int, AccountCode], Cents],
    balance: Balance,
    data: GameData,
) -> LifeMonth:
    if state.partnership.of(state.player.id) is None or state.ended:
        return LifeMonth(state)
    state, opened = ensure_player(state, balance)
    firm = state.player.id
    you = state.founder_of(firm)
    if you is None:  # the player's partner left the firm this month (PT-M4's flight)
        return LifeMonth(state, personal=opened)
    logs: list[LogItem] = []
    out: list[PersonalEntry] = list(opened)
    entries: list[LedgerEntry] = []
    fl = state.founder_life
    life = fl.life(you)
    assert life is not None
    is_mp = ix.managing_partner(state, firm) == you
    life = replace(life, status="managing_partner" if is_mp else "partner")
    life = _sources(life, state, start, balances, balance)
    life = persona.drift(life, balance)
    life = influence.month(life, state.turn, balance)
    life, won = influence.election(life, state.turn, state.save_meta.start_ym, rng, balance)
    if won is not None:
        logs.append(
            inbox_item(
                state.turn, firm, "bar_office_won" if won else "bar_office_lost", link_kind=None
            )
        )
    fl = with_life(fl, life)
    fl, grants, granted = foundation.grants_month(fl, state.turn, state.save_meta.start_ym, balance)
    out += grants
    for name, cents, cause in granted:
        logs.append(
            inbox_item(
                state.turn,
                firm,
                "foundation_grants",
                link_kind=None,
                name=name,
                amount_cents=cents,
                cause=cause,
            )
        )
    fl = _best_year(fl, state, firm)
    state = replace(state, founder_life=fl)
    if is_mp:
        points = persona.confidence_points(fl.life(you), balance) + influence.confidence_points(
            fl.life(you), balance
        )
        if points:
            state = ix.confidence_change(state, firm, points)
    state, fam_entries, fam_logs = family_month(state, rng, balance, data)
    out += fam_entries
    logs += fam_logs
    state, advice = adviser.adviser_month(state, balance)
    logs += advice
    trig = succession.month(state, rng, balance)
    state = succession.due(trig.state, balance, data)
    logs += trig.log
    done = succession.count(state, rng, balance, data, balances)
    state = done.state
    entries += done.entries
    out += done.personal
    logs += done.log
    return LifeMonth(state, tuple(entries), tuple(out), tuple(logs))


def _best_year(fl: FounderLifeState, state: GameState, firm: int) -> FounderLifeState:
    view = ix.partnership_month(state, firm, {})
    if view is None or view.last_revenue_cents is None:
        return fl
    if view.last_revenue_cents > fl.best_revenue_cents:
        return replace(fl, best_revenue_cents=view.last_revenue_cents)
    return fl


def _sources(
    life: FounderLife,
    state: GameState,
    start: GameState,
    balances: Mapping[tuple[int, AccountCode], Cents],
    balance: Balance,
) -> FounderLife:
    """Spec 2.3's sources this month (only while the player is the MP: the firm's choices
    are theirs)."""
    firm = state.player.id
    if ix.managing_partner(state, firm) != life.person_id:
        return life
    pb = balance.founder_life.persona
    turn = state.turn
    view = ix.partnership_month(state, firm, balances)
    if view is None:
        return life
    if view.deequitisations:
        life = persona.apply_source(life, "deequitisation", turn, balance, view.deequitisations)
    hostile = sum(1 for pid, _ in view.laterals_hired if _from_rival(state, pid))
    hostile += _rival_arrivals(state, start, {pid for pid, _ in view.laterals_hired})
    if hostile:
        life = persona.apply_source(life, "hostile_lateral", turn, balance, hostile)
    guarantees = sum(1 for _, years in view.laterals_hired if years > 0) + view.counter_guarantees
    if guarantees:
        life = persona.apply_source(life, "guarantee", turn, balance, guarantees)
    if view.breach_started:
        life = persona.apply_source(life, "covenant_breach", turn, balance)
    if (
        view.facility_cents > 0
        and view.revolver_drawn_cents > pb.leverage_share * view.facility_cents
    ):
        life = persona.leverage(life, turn, state.save_meta.start_ym, balance)
    staff = state.staff_ids(firm)
    before = {e.person_id for e in start.employments if e.firm_id == firm and e.status == "active"}
    fired = sum(
        1
        for e in state.employments
        if e.firm_id == firm
        and e.person_id in before
        and e.end_reason == "fired"
        and e.status != "active"
    )
    if before and fired >= pb.layoff_share * len(before) and fired > 1:
        life = persona.apply_source(life, "layoffs", turn, balance)
    raised = sum(1 for p in state.org.people if p.last_raise_turn == turn and p.person_id in staff)
    if staff and raised >= pb.raise_share * len(staff):
        life = persona.apply_source(life, "raises", turn, balance)
    for u in state.org.units:
        if u.firm_id != firm or u.created_turn != turn or u.practice is None:
            continue
        earlier = any(
            x.practice == u.practice
            and x.id != u.id
            and x.created_turn < turn
            and x.firm_id == firm
            for x in state.org.units
        )
        if not earlier:
            life = persona.apply_source(life, "new_practice", turn, balance)
    if turn_to_ym(turn, state.save_meta.start_ym)[1] == DECEMBER:
        if state.firm(firm).pro_bono_avg_tenths >= pb.pro_bono_tenths:
            life = persona.apply_source(life, "pro_bono", turn, balance)
        if view.equity_partners >= 2 and view.unhappy == 0:  # tunable-exempt: others to judge
            life = persona.apply_source(life, "comp_fairness", turn, balance)
    return life


def _from_rival(state: GameState, person_id: int) -> bool:
    return any(e.person_id == person_id and e.firm_id != state.player.id for e in state.employments)


def _rival_arrivals(state: GameState, start: GameState, laterals: set[int]) -> int:
    """Partners who joined this turn from a rival through PT-M5's approaches (the lateral
    market's hires are counted from `laterals_hired`)."""
    firm = state.player.id
    had = set(start.staff_ids(firm))
    return sum(
        1
        for pid in ix.partner_ids(state, firm)
        if pid not in had and pid not in laterals and _from_rival(state, pid)
    )


def month_start(state: GameState, balance: Balance) -> GameState:
    """After the energy reset: a committee seat and family time take their energy."""
    pid = state.founder_of(state.player.id)
    if pid is None:
        return state
    cost = 0
    life = state.founder_life.life(pid)
    if life is not None and life.committee:
        cost += balance.founder_life.energy.committee
    if head_active(state):
        family = state.family.family
        assert family is not None
        cost += family.family_time
    if not cost:
        return state
    ps = state.person_state(pid)
    if ps.energy is None:
        return state
    return with_person_states(state, [replace(ps, energy=max(0, ps.energy - cost))])
