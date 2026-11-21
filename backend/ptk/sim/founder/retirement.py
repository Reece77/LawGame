"""Mandatory retirement and retired partners' annuities (spec 2.5, 8.4, 8.6).

Partner Track's own (TST has no partnership). Every partner of the player's firm but the
player retires in phase 7 of the first month at or past the agreement's `retirement_age`
(changeable by vote, PT-M4's terms vote); the player's own retirement is a succession
(`ptk.sim.family.succession`). A retiring partner leaves through PT-M4's departure (reason
"retired", no suitor: clients pass to a colleague; capital and current account repaid over
three years).

Annuities, as the agreement grants (default none; `founder_life.annuity`, or the terms the
partnership voted, `FounderLifeState.annuity_terms`): `share_bp` of the retiree's last
December allocation a year, for `years`. The whole obligation is booked to 2600 at
retirement (against undistributed profit, 3100: an unfunded promise the partners carry,
Dewey's trap) and paid monthly from cash as cash allows (what cash cannot pay stays owed).
A retiree with a personal book (a former player) receives it there.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace

from ptk.sim import interfaces as ix
from ptk.sim.calendar import MONTHS_PER_YEAR
from ptk.sim.data_models import Balance, GameData
from ptk.sim.founder import personal
from ptk.sim.founder.models import (
    Annuity,
    AnnuityTerms,
    PersonalEntry,
    with_annuity,
    with_book,
    with_life,
)
from ptk.sim.founder.streams import RETIREMENT, life_stream
from ptk.sim.ledger import (
    ANNUITIES,
    CASH,
    UNDISTRIBUTED_PROFIT,
    AccountCode,
    LedgerEntry,
    apply_entries,
)
from ptk.sim.log import LogItem, inbox_item
from ptk.sim.money import BP_DENOMINATOR, Cents
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState


@dataclass(frozen=True, slots=True)
class Retired:
    state: GameState
    entries: tuple[LedgerEntry, ...] = ()
    personal: tuple[PersonalEntry, ...] = ()
    log: tuple[LogItem, ...] = ()


def terms(state: GameState, balance: Balance) -> AnnuityTerms:
    t = state.founder_life.annuity_terms
    if t is not None:
        return t
    a = balance.founder_life.annuity
    return AnnuityTerms(a.granted, a.share_bp, a.years)


def retire(
    state: GameState,
    person_id: int,
    rng: RngFactory,
    balance: Balance,
    data: GameData,
    balances: Mapping[tuple[int, AccountCode], Cents],
) -> Retired:
    firm = state.player.id
    account = ix.partner_account(state, firm, person_id)
    if account is None or not account.partner:
        return Retired(state)
    res = ix.retire_partner(
        state,
        person_id,
        draws=lambda: life_stream(rng, state.turn, RETIREMENT, person_id),
        balance=balance,
        data=data,
        balances=balances,
    )
    state = res.state
    entries = list(res.entries)
    logs = list(res.log)
    t = terms(state, balance)
    if t.granted and account.equity and account.comp_last_cents > 0 and t.share_bp > 0:
        yearly = account.comp_last_cents * t.share_bp // BP_DENOMINATOR
        monthly = yearly // MONTHS_PER_YEAR
        months = t.years * MONTHS_PER_YEAR
        total = monthly * months
        if total > 0:
            entries.append(
                LedgerEntry.transfer(
                    turn=state.turn,
                    firm_id=firm,
                    memo="Retired partner's annuity booked",
                    debit=UNDISTRIBUTED_PROFIT,
                    credit=ANNUITIES,
                    amount=total,
                )
            )
            start = state.turn + 1
            ann = Annuity(person_id, firm, monthly, total, start, start + months)
            state = replace(state, founder_life=with_annuity(state.founder_life, ann))
            p = state.person(person_id)
            logs.append(
                inbox_item(
                    state.turn,
                    firm,
                    "annuity_granted",
                    link_kind="person",
                    link_id=person_id,
                    name=f"{p.first_name} {p.last_name}",
                    monthly_cents=monthly,
                    years=t.years,
                )
            )
    fl = state.founder_life
    life = fl.life(person_id)
    if life is not None:
        fl = with_life(
            fl, replace(life, status="retired", until_turn=life.until_turn or state.turn)
        )
        state = replace(state, founder_life=fl)
    return Retired(state, tuple(entries), (), tuple(logs))


def retirements(
    state: GameState,
    rng: RngFactory,
    balance: Balance,
    data: GameData,
    balances: Mapping[tuple[int, AccountCode], Cents],
) -> Retired:
    """Phase 7: partners at or past the retirement age retire (the player aside)."""
    firm = state.player.id
    age_limit = ix.retirement_age(state, firm, balance)
    you = state.founder_of(firm)
    entries: list[LedgerEntry] = []
    logs: list[LogItem] = []
    running = dict(balances)
    for pid in ix.partner_ids(state, firm):
        if pid == you:
            continue
        e = state.employment_of(pid)
        if e is None or e.status != "active" or state.person(pid).age(state.turn) < age_limit:
            continue
        done = retire(state, pid, rng, balance, data, running)
        state = done.state
        entries += done.entries
        logs += done.log
        running = apply_entries(running, done.entries)
    return Retired(state, tuple(entries), (), tuple(logs))


def pay_annuities(state: GameState, balances: Mapping[tuple[int, AccountCode], Cents]) -> Retired:
    """Phase 7: each annuity due pays a month from cash (2600 down), as cash allows."""
    fl = state.founder_life
    entries: list[LedgerEntry] = []
    personal_entries: list[PersonalEntry] = []
    cash = balances.get((state.player.id, CASH), 0)
    for ann in fl.annuities:
        if ann.start_turn > state.turn or ann.remaining_cents <= 0:
            continue
        due = ann.remaining_cents if state.turn >= ann.end_turn - 1 else ann.monthly_cents
        pay = min(due, ann.remaining_cents, max(0, cash))
        if pay <= 0:
            continue
        cash -= pay
        entries.append(
            LedgerEntry.transfer(
                turn=state.turn,
                firm_id=ann.firm_id,
                memo="Retired partner's annuity paid",
                debit=ANNUITIES,
                credit=CASH,
                amount=pay,
            )
        )
        fl = with_annuity(fl, replace(ann, remaining_cents=ann.remaining_cents - pay))
        book = fl.book(ann.person_id)
        if book is not None:
            book, entry = personal.credit_annuity(book, state.turn, pay)
            fl = with_book(fl, book)
            personal_entries.append(entry)
    return Retired(replace(state, founder_life=fl), tuple(entries), tuple(personal_entries))
