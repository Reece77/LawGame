"""PT-M17 sub-task 1: the founder's personal book (spec 2.3; TST 32.2; ADR PT-0003 4-5).

The book balances every month, never mixes with the firm's, and reconciles: the draws and
true-up it records are exactly what the partnership paid the founder (read from PT-M4's
sub-ledgers), and after-tax income is draws + true-up - tax."""

from __future__ import annotations

from collections import defaultdict

import pytest

from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import UnbalancedEntryError
from ptk.sim.founder import personal
from ptk.sim.founder.actions import Invest
from ptk.sim.founder.models import (
    CAPITAL_LOAN,
    FIRM_CAPITAL,
    INCOME_TAX,
    INVESTMENTS,
    PERSONAL_CASH,
    PersonalEntry,
    PersonalLine,
)
from ptk.sim.founder.personal import income_statement
from ptk.sim.interfaces import PartnerAccountView
from ptk.sim.ledger import LedgerEntry, LedgerLine
from tests.founder_support import start_life

MONTHS = 30  # tunable-exempt: two Decembers and two true-up seasons


def _paid(before: PartnerAccountView | None, after: PartnerAccountView | None, december: bool):
    """What the partnership paid the founder this month, from its own sub-ledger: draws
    (drawn_ytd's change; in December the identity current' = current + allocation - drawn
    - draw) and the true-up (the current account's fall, January-April)."""
    if before is None or after is None or not after.partner:
        return 0, 0
    if december:
        draw = before.current_cents + after.comp_last_cents - before.drawn_ytd_cents
        draw -= after.current_cents
        return draw, 0
    return after.drawn_ytd_cents - before.drawn_ytd_cents, max(
        0, before.current_cents - after.current_cents
    )


@pytest.mark.parametrize("seed", [1, 4])
def test_book_reconciles_with_the_partnership(data: GameData, balance: Balance, seed: int) -> None:
    g = start_life(data, balance, seed=seed)
    g.advance(MONTHS)
    you = g.founder
    book = g.state.founder_life.book(you)
    assert book is not None
    # the running balances equal the entries' sums
    sums: dict[str, int] = defaultdict(int)
    for e in g.personal:
        if e.person_id == you:
            for ln in e.lines:
                sums[ln.account] += ln.amount
    assert {k: v for k, v in sums.items() if v} == dict(book.balances)
    # the book balances: debits = credits
    assert sum(v for _, v in book.balances) == 0
    # each month's draws and true-up are what the partnership paid
    from ptk.sim.calendar import turn_to_ym

    total_draws = total_true_up = 0
    for turn, before, after in g.accounts:
        december = turn_to_ym(turn, g.state.save_meta.start_ym)[1] == 12
        d, t = _paid(before, after, december)
        month = income_statement(g.personal, you, turn, turn)
        assert month.draws_cents == max(0, d), turn
        assert month.true_up_cents == t, turn
        assert month.tax_cents == round((max(0, d) + t) * balance.founder_life.personal.tax_rate)
        total_draws += max(0, d)
        total_true_up += t
    stmt = income_statement(g.personal, you)
    assert stmt.draws_cents == total_draws > 0
    assert stmt.true_up_cents == total_true_up
    assert stmt.after_tax_cents == stmt.draws_cents + stmt.true_up_cents - stmt.tax_cents
    assert -book.bal(INCOME_TAX) == -stmt.tax_cents  # tax is the 9310 balance


def test_capital_is_funded_by_a_loan_in_the_book(data: GameData, balance: Balance) -> None:
    """ADR PT-0003 5: the founder's capital in the firm sits in their book against a bank
    loan; the loan is repaid over time from personal cash."""
    g = start_life(data, balance)
    g.advance(1)
    you = g.founder
    book = g.state.founder_life.book(you)
    assert book is not None
    fp = g.fp
    p = fp.partner(you)
    assert p is not None
    assert book.bal(FIRM_CAPITAL) == p.capital_cents > 0
    loan0 = -book.bal(CAPITAL_LOAN)
    assert 0 < loan0 <= p.capital_cents
    g.advance(12)
    book = g.state.founder_life.book(you)
    assert book is not None
    assert -book.bal(CAPITAL_LOAN) < loan0 + (book.bal(FIRM_CAPITAL) - p.capital_cents)


def test_no_personal_account_in_a_firm_entry() -> None:
    with pytest.raises(UnbalancedEntryError):
        LedgerEntry(0, 1, "x", (LedgerLine(PERSONAL_CASH, 5), LedgerLine("1000_cash", -5)))
    with pytest.raises(UnbalancedEntryError):
        PersonalEntry(
            0, 1, "x", "x", (PersonalLine("1000_cash", 5), PersonalLine(PERSONAL_CASH, -5))
        )
    with pytest.raises(UnbalancedEntryError):
        PersonalEntry(
            0, 1, "x", "x", (PersonalLine(INVESTMENTS, 5), PersonalLine(PERSONAL_CASH, -4))
        )


def test_actions_entries_reach_the_turn_and_investments_return(
    data: GameData, balance: Balance
) -> None:
    g = start_life(data, balance, seed=2)
    g.advance(3)
    you = g.founder
    g.act(Invest(you, 1_000_000))
    book = g.state.founder_life.book(you)
    assert book is not None and book.bal(INVESTMENTS) == 1_000_000
    pending = g.state.founder_life.pending
    assert len(pending) == 1
    g.advance(1)  # the founder support asserts the turn took them
    assert g.state.founder_life.pending == ()
    book = g.state.founder_life.book(you)
    assert book is not None and book.bal(INVESTMENTS) != 1_000_000  # a month's return
    g.act(Invest(you, -book.bal(INVESTMENTS)))
    book = g.state.founder_life.book(you)
    assert book is not None and book.bal(INVESTMENTS) == 0


def test_mirror_of_a_departed_partner_returns_capital(balance: Balance) -> None:
    """A retired founder's capital and current account come back as the partnership repays
    them; the loan is repaid in full once the capital is back."""
    book, _ = personal.open_book(1, 0, 0, _view(capital=1_000_000, current=0))
    # retired: the return holds capital 1,000,000 and current 200,000
    book = personal.mirror(
        book, _view(partner=False, ret_cur=200_000, ret_cap=1_000_000), 1, (2005, 1), balance
    ).book
    book = personal.mirror(
        book, _view(partner=False, ret_cur=0, ret_cap=500_000), 2, (2005, 1), balance
    ).book
    book = personal.mirror(
        book, _view(partner=False, ret_cur=0, ret_cap=0), 3, (2005, 1), balance
    ).book
    assert book.bal(FIRM_CAPITAL) == 0
    assert book.bal(CAPITAL_LOAN) == 0
    assert sum(v for _, v in book.balances) == 0


def _view(
    *, partner: bool = True, capital: int = 0, current: int = 0, ret_cur: int = 0, ret_cap: int = 0
) -> PartnerAccountView:
    return PartnerAccountView(
        1, 1, partner, partner, 0, current, capital if partner else 0, 0, ret_cur, ret_cap
    )
