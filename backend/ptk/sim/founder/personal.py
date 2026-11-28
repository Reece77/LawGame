"""The founding partner's personal book (spec 2.3; TST formulas.md 32.2; ADR PT-0003 4-5).

Ported from backend/tst/sim/founder/personal.py @ 121d318a (Tech Startup Tycoon); changed:
income is the founder's draws, true-up, capital returned and annuity, mirrored each month
from the partnership's sub-ledgers (PT-M4, read through `ptk.sim.interfaces`); the founder's
capital in the firm is an asset funded by a capital loan in their own book (ADR PT-0003 5);
income tax at `founder_life.personal.tax_rate` on the profit share as it is paid out
(draws and the true-up: estimated payments each month, so tax is never owed on profit the
firm could not distribute); investments and a family office earn a seeded monthly
return (stream `investments`, id 52).

The book is its own double entry: every movement is a `PersonalEntry` on 9-accounts only,
and a firm `LedgerEntry` refuses a 9-account (ledger.py). `PersonalBook.balances` is the sum
of a player's entries (a property test holds it).

After-tax income (the reconciliation): draws + true-up - income tax.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace
from math import isfinite

import numpy as np
from simcore.kernel.calendar import turn_to_ym

from ptk.sim.data_models import Balance
from ptk.sim.founder.models import (
    ANNUITY,
    CAPITAL_LOAN,
    DRAWS,
    FAMILY_OFFICE,
    FIRM_CAPITAL,
    GAINS,
    INCOME_TAX,
    INVESTMENTS,
    LOAN_INTEREST,
    LOSSES,
    OPENING,
    PERSONAL_CASH,
    TRUE_UP,
    PersonalBook,
    PersonalEntry,
)
from ptk.sim.interfaces import PartnerAccountView
from ptk.sim.streams import RngFactory

DECEMBER = 12  # tunable-exempt: the firm's year ends in December (ADR PT-0002)
MONTHS = 12  # tunable-exempt: months a year


def investment_stream(rng: RngFactory, turn: int, person_id: int) -> np.random.Generator:
    """The one call site of stream `investments` (id 52): a player's month of returns."""
    return rng.stream(turn, "investments", person_id)


class Poster:
    """Collects one player's entries and keeps their book's balances in step."""

    def __init__(self, book: PersonalBook, turn: int):
        self.book = book
        self.turn = turn
        self.entries: list[PersonalEntry] = []

    def move(self, memo: str, source: str, debit: str, credit: str, cents: int) -> None:
        if cents == 0:
            return
        if cents < 0:
            debit, credit, cents = credit, debit, -cents
        entry = PersonalEntry.transfer(
            self.turn, self.book.person_id, memo, source, debit, credit, cents
        )
        self.entries.append(entry)
        self.book = self.book.posted((entry,))

    @property
    def cash(self) -> int:
        return self.book.cash


def open_book(
    person_id: int,
    turn: int,
    savings_cents: int,
    account: PartnerAccountView | None,
) -> tuple[PersonalBook, tuple[PersonalEntry, ...]]:
    """A player's book opens: their savings, and their capital in the firm funded by a
    capital loan (ADR PT-0003 5). The partnership's marks are taken as they stand."""
    poster = Poster(PersonalBook(person_id=person_id, opened_turn=turn), turn)
    poster.move("Savings", "opening", PERSONAL_CASH, OPENING, savings_cents)
    if account is not None:
        capital = account.capital_cents + account.return_capital_cents
        poster.move(
            "Capital in the firm (bank loan)", "capital", FIRM_CAPITAL, CAPITAL_LOAN, capital
        )
    book = _marks(poster.book, account)
    return book, tuple(poster.entries)


def _marks(book: PersonalBook, account: PartnerAccountView | None) -> PersonalBook:
    if account is None:
        return book
    return replace(
        book,
        seen_drawn_ytd=account.drawn_ytd_cents,
        seen_current=account.current_cents,
        seen_capital=account.capital_cents,
        seen_return_current=account.return_current_cents,
        seen_return_capital=account.return_capital_cents,
    )


@dataclass(frozen=True, slots=True)
class Mirror:
    book: PersonalBook
    entries: tuple[PersonalEntry, ...]
    draws_cents: int
    true_up_cents: int
    allocation_cents: int | None  # December: the year's profit share
    tax_cents: int  # tax paid on this month's draws and true-up


def mirror(
    book: PersonalBook,
    account: PartnerAccountView | None,
    turn: int,
    start_ym: tuple[int, int],
    balance: Balance,
) -> Mirror:
    """Phase 7: post the month's draws, true-up and capital movements from the partnership's
    sub-ledgers and the tax on them, then the loan's interest and principal."""
    cfg = balance.founder_life.personal
    poster = Poster(book, turn)
    month = turn_to_ym(turn, start_ym)[1]
    draws = true_up = tax = 0
    allocation: int | None = None
    if account is not None and account.partner:
        if month == DECEMBER:
            allocation = account.comp_last_cents
            # current' = current - true-up + allocation - (drawn + this month's draw)
            # (the true-up is paid January-April, never in December)
            draws = book.seen_current + allocation - book.seen_drawn_ytd - account.current_cents
            draws = max(0, draws)
        else:
            draws = max(0, account.drawn_ytd_cents - book.seen_drawn_ytd)
            true_up = max(0, book.seen_current - account.current_cents)
        poster.move("Draws from the firm", "draws", PERSONAL_CASH, DRAWS, draws)
        poster.move("True-up from the firm", "true_up", PERSONAL_CASH, TRUE_UP, true_up)
        added = account.capital_cents - book.seen_capital
        if added > 0:  # instalments (and capital calls) are funded by the loan
            poster.move("Capital paid in (bank loan)", "capital", FIRM_CAPITAL, CAPITAL_LOAN, added)
        elif added < 0:
            poster.move("Capital reduced", "capital", PERSONAL_CASH, FIRM_CAPITAL, -added)
    elif account is not None:
        # a departed partner (retired, or left): the capital return runs (spec 8.4)
        if (
            book.seen_return_current == 0
            and book.seen_return_capital == 0
            and (book.seen_capital or book.seen_current)
        ):
            # the month after leaving: an overdraft set off against capital is income given back
            lost = book.seen_capital - account.return_capital_cents
            if lost > 0 and account.return_current_cents == 0:
                poster.move("Overdrawn account set off", "true_up", TRUE_UP, FIRM_CAPITAL, lost)
            book_seen = replace(
                poster.book,
                seen_return_current=account.return_current_cents,
                seen_return_capital=account.return_capital_cents,
            )
            poster.book = book_seen
        cur = max(0, poster.book.seen_return_current - account.return_current_cents)
        cap = max(0, poster.book.seen_return_capital - account.return_capital_cents)
        true_up = cur
        poster.move("Current account repaid", "true_up", PERSONAL_CASH, TRUE_UP, cur)
        poster.move("Capital returned", "capital", PERSONAL_CASH, FIRM_CAPITAL, cap)
    # the profit share is taxed as it is paid out (draws and true-up: estimated payments)
    tax = round((draws + true_up) * cfg.tax_rate)
    poster.move("Income tax on the profit share", "tax", INCOME_TAX, PERSONAL_CASH, tax)
    _loan(poster, cfg.loan_rate, cfg.loan_months)
    out = _marks(poster.book, account)
    if account is None:
        out = replace(out, seen_drawn_ytd=0, seen_current=0, seen_capital=0)
    return Mirror(out, tuple(poster.entries), draws, true_up, allocation, tax)


def _loan(poster: Poster, rate: float, months: int) -> None:
    """The capital loan: a month's interest (capitalised if cash is short), then principal of
    loan / months (all of it once the capital is back), as cash allows."""
    loan = -poster.book.bal(CAPITAL_LOAN)
    if loan <= 0:
        return
    interest = round(loan * rate / MONTHS)
    if poster.cash >= interest:
        poster.move("Capital loan interest", "loan", LOAN_INTEREST, PERSONAL_CASH, interest)
    else:
        poster.move("Capital loan interest (added)", "loan", LOAN_INTEREST, CAPITAL_LOAN, interest)
    loan = -poster.book.bal(CAPITAL_LOAN)
    due = loan if poster.book.bal(FIRM_CAPITAL) <= 0 else -(-loan // months)
    pay = min(due, max(0, poster.cash))
    poster.move("Capital loan repaid", "loan", CAPITAL_LOAN, PERSONAL_CASH, pay)


def credit_annuity(book: PersonalBook, turn: int, cents: int) -> tuple[PersonalBook, PersonalEntry]:
    entry = PersonalEntry.transfer(
        turn, book.person_id, "Retired partner's annuity", "annuity", PERSONAL_CASH, ANNUITY, cents
    )
    return book.posted((entry,)), entry


def returns(
    book: PersonalBook, turn: int, gen: np.random.Generator, balance: Balance
) -> tuple[PersonalBook, tuple[PersonalEntry, ...]]:
    """A month of investment returns (TST 37.1-37.4 simplified): self-managed investments at
    the yearly expected return with noise; the family office by its mandate, less its fee.
    One draw for each account, in this order, every month (ADR-0013)."""
    cfg = balance.founder_life
    poster = Poster(book, turn)
    held = book.bal(INVESTMENTS)
    u1 = float(gen.normal(0.0, 1.0))
    u2 = float(gen.normal(0.0, 1.0))
    if held > 0:
        r = cfg.personal.invest_return / MONTHS + cfg.personal.invest_vol * u1
        _gain(poster, INVESTMENTS, round(held * r) if isfinite(r) else 0)
    office = book.bal(FAMILY_OFFICE)
    if office > 0 and book.mandate is not None:
        m = cfg.family_office.mandates[book.mandate]
        r = (m.expected - cfg.family_office.fee) / MONTHS + m.vol * u2
        _gain(poster, FAMILY_OFFICE, round(office * r) if isfinite(r) else 0)
    return poster.book, tuple(poster.entries)


def _gain(poster: Poster, account: str, cents: int) -> None:
    if cents > 0:
        poster.move("Investment gains", "invest", account, GAINS, cents)
    elif cents < 0:
        loss = min(-cents, poster.book.bal(account))
        poster.move("Investment losses", "invest", LOSSES, account, loss)


@dataclass(frozen=True, slots=True)
class IncomeStatement:
    draws_cents: int
    true_up_cents: int
    annuity_cents: int
    tax_cents: int
    gains_cents: int  # investment gains less losses

    @property
    def after_tax_cents(self) -> int:
        """The founder's after-tax income from the firm: draws + true-up - income tax."""
        return self.draws_cents + self.true_up_cents - self.tax_cents


def income_statement(
    entries: Iterable[PersonalEntry],
    person_id: int,
    since_turn: int = 0,
    until_turn: int | None = None,
) -> IncomeStatement:
    totals: dict[str, int] = {}
    for e in entries:
        if e.person_id != person_id or e.turn < since_turn:
            continue
        if until_turn is not None and e.turn > until_turn:
            continue
        for line in e.lines:
            totals[line.account] = totals.get(line.account, 0) + line.amount
    return IncomeStatement(
        draws_cents=-totals.get(DRAWS, 0),
        true_up_cents=-totals.get(TRUE_UP, 0),
        annuity_cents=-totals.get(ANNUITY, 0),
        tax_cents=totals.get(INCOME_TAX, 0),
        gains_cents=-totals.get(GAINS, 0) - totals.get(LOSSES, 0),
    )
