"""What a passed vote does (ADR PT-0007 2; spec 5.5, 8.4, 8.6)."""

from __future__ import annotations

import statistics
from dataclasses import replace

import numpy as np

from ptk.sim.data_models import Balance, GameData
from ptk.sim.ledger import (
    CASH,
    DRAWINGS,
    PARTNER_CURRENT,
    PARTNERS_CAPITAL,
    UNDISTRIBUTED_PROFIT,
    LedgerEntry,
)
from ptk.sim.log import LogItem, inbox_item
from ptk.sim.partnership import formulas as fx
from ptk.sim.partnership.books import capital_required_cents
from ptk.sim.partnership.common import firm_partnership, name, put
from ptk.sim.partnership.models import (
    CapitalReturn,
    FirmPartnership,
    Partner,
    Vote,
    with_capital_return,
    with_partner,
)
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState, with_employment, with_people

EQUITY = "equity_partner"
INCOME = "income_partner"
PURPOSE_DEEQUITY = 1  # stream `partnership` purposes (ADR PT-0012)
PURPOSE_UP_OR_OUT = 2


def partnership_stream(rng: RngFactory, turn: int, purpose: int, key: int) -> np.random.Generator:
    """The one call site of stream `partnership` (ADR PT-0012): (purpose, id)."""
    return rng.stream(turn, "partnership", purpose, key)


def apply_vote(
    state: GameState, vote: Vote, rng: RngFactory, balance: Balance, data: GameData
) -> tuple[GameState, list[LedgerEntry], list[LogItem]]:
    fp = firm_partnership(state, vote.firm_id)
    entries: list[LedgerEntry] = []
    logs: list[LogItem] = []
    if vote.kind == "terms":
        term, value = vote.param("term"), vote.param("value")
        assert isinstance(term, str) and value is not None
        state = put(state, replace(fp, agreement=fp.agreement.with_term(term, value)))
    elif vote.kind == "capital_call":
        amount = vote.param("amount_cents")
        assert isinstance(amount, int)
        eq = fp.equity_partners
        shares = fx.split_cents(amount, {p.person_id: p.points for p in eq})
        for p in eq:
            add = shares[p.person_id]
            fp = with_partner(
                fp,
                replace(
                    p,
                    capital_cents=p.capital_cents + add,
                    capital_required_cents=p.capital_required_cents + add,
                ),
            )
        entries.append(
            LedgerEntry.transfer(
                turn=state.turn,
                firm_id=fp.firm_id,
                memo="Capital call paid in",
                debit=CASH,
                credit=PARTNERS_CAPITAL,
                amount=amount,
            )
        )
        state = put(state, fp)
    elif vote.kind == "admission" and vote.subject_id is not None:
        track = str(vote.param("track"))
        state, log = admit(state, fp.firm_id, vote.subject_id, track, balance, data)
        logs.append(log)
    elif vote.kind == "deequity" and vote.subject_id is not None:
        state, more_entries, more_logs = deequitise(
            state, fp.firm_id, vote.subject_id, str(vote.param("mode")), rng, balance, data
        )
        entries += more_entries
        logs += more_logs
    return state, entries, logs


def admit(
    state: GameState, firm_id: int, person_id: int, track: str, balance: Balance, data: GameData
) -> tuple[GameState, LogItem]:
    """Admission takes effect from January (spec 5.5): equity partners join next year's
    allocation and draws; income partners move to the income-partner salary."""
    from ptk.sim.partnership.laterals import income_partner_salary

    cfg = balance.partnership
    fp = firm_partnership(state, firm_id)
    person = state.person(person_id)
    e = state.employment_of(person_id)
    assert e is not None
    start = state.turn + 1
    if track == "equity":
        total = sum(p.points for p in fp.equity_partners)
        last = max(fp.last_profit_cents or 0, 0)
        budget = round(last * cfg.lockstep.start_points / (total + cfg.lockstep.start_points))
        required = capital_required_cents(budget, fp.agreement)
        old = fp.partner(person_id)
        partner = Partner(
            person_id=person_id,
            firm_id=firm_id,
            klass="equity",
            admitted_turn=start,
            points=cfg.lockstep.start_points,
            capital_required_cents=required,
            capital_instalment_cents=-(-required // cfg.capital.pay_in_months),
            budget_cents=budget,
            confidence=old.confidence if old else cfg.confidence.start,
        )
        state = with_people(state, [replace(person, level=EQUITY)])
        state = with_employment(state, replace(e, salary_cents=0))
    else:
        partner = Partner(
            person_id=person_id,
            firm_id=firm_id,
            klass="income",
            admitted_turn=start,
            confidence=cfg.confidence.start,
        )
        salary = income_partner_salary(data, balance, state.firm(firm_id).home_city)
        state = with_people(state, [replace(person, level=INCOME)])
        state = with_employment(state, replace(e, salary_cents=max(e.salary_cents, salary)))
    fp = with_partner(firm_partnership(state, firm_id), partner)
    fp = replace(fp, moving_on=tuple(m for m in fp.moving_on if m.person_id != person_id))
    state = put(state, fp)
    log = inbox_item(
        state.turn,
        firm_id,
        "partner_admitted",
        link_kind="person",
        link_id=person_id,
        name=name(person),
        track=track,
    )
    return state, log


def deequitise(
    state: GameState,
    firm_id: int,
    person_id: int,
    mode: str,
    rng: RngFactory,
    balance: Balance,
    data: GameData,
) -> tuple[GameState, list[LedgerEntry], list[LogItem]]:
    """Spec 5.5: an equity partner moves to income partner, or out. Partners whose own
    contribution is below the median fear for themselves."""
    from ptk.sim.partnership.flight import depart_partner
    from ptk.sim.partnership.governance import contribution
    from ptk.sim.partnership.laterals import income_partner_salary

    cfg = balance.partnership
    fp = firm_partnership(state, firm_id)
    shares = contribution(state, fp, balance)
    median = statistics.median(shares.values()) if shares else 0.0
    for p in fp.equity_partners:
        if p.person_id != person_id and shares.get(p.person_id, 0.0) < median:
            fp = with_partner(fp, replace(p, nudge=p.nudge - cfg.confidence.deequity_fear))
    state = put(state, fp)
    entries: list[LedgerEntry] = []
    logs: list[LogItem] = []
    person = state.person(person_id)
    if mode == "out":
        gen = partnership_stream(rng, state.turn, PURPOSE_DEEQUITY, person_id)
        res = depart_partner(state, person_id, None, "de_equitised", gen, balance, data)
        return res.state, list(res.entries), list(res.log)
    old = fp.partner(person_id)
    assert old is not None
    p = old
    # their draws are their share this year; capital and current account come back over 3 years
    if p.drawn_ytd_cents:
        for memo, debit, credit in (
            ("De-equitised partner's draws allocated", UNDISTRIBUTED_PROFIT, PARTNER_CURRENT),
            ("De-equitised partner's drawings closed", PARTNER_CURRENT, DRAWINGS),
        ):
            entries.append(
                LedgerEntry.transfer(
                    turn=state.turn,
                    firm_id=firm_id,
                    memo=memo,
                    debit=debit,
                    credit=credit,
                    amount=p.drawn_ytd_cents,
                )
            )
        fp = replace(fp, allocated_ytd_cents=fp.allocated_ytd_cents + p.drawn_ytd_cents)
    current = max(0, p.current_cents)
    capital = p.capital_cents + min(0, p.current_cents)
    if p.current_cents < 0:
        entries.append(
            LedgerEntry.transfer(
                turn=state.turn,
                firm_id=firm_id,
                memo="Overdrawn account set off",
                debit=PARTNERS_CAPITAL,
                credit=PARTNER_CURRENT,
                amount=min(p.capital_cents, -p.current_cents),
            )
        )
    fp = with_capital_return(
        fp,
        CapitalReturn(
            person_id=person_id,
            monthly_cents=-(-(current + max(capital, 0)) // cfg.capital.return_months),
            remaining_capital_cents=max(capital, 0),
            remaining_current_cents=current,
            start_turn=state.turn + 1,
        ),
    )
    fp = with_partner(
        fp,
        Partner(
            person_id=person_id,
            firm_id=firm_id,
            klass="income",
            admitted_turn=p.admitted_turn,
            confidence=max(0.0, p.confidence - cfg.confidence.deequity_fear),
        ),
    )
    state = put(state, fp)
    e = state.employment_of(person_id)
    assert e is not None
    salary = income_partner_salary(data, balance, state.firm(firm_id).home_city)
    state = with_people(state, [replace(person, level=INCOME)])
    state = with_employment(state, replace(e, salary_cents=salary))
    logs.append(
        inbox_item(
            state.turn,
            firm_id,
            "partner_deequitised",
            link_kind="person",
            link_id=person_id,
            name=name(person),
        )
    )
    return state, entries, logs


def fp_or_none(state: GameState, firm_id: int) -> FirmPartnership | None:
    return state.partnership.of(firm_id)
