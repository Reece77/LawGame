"""PT-M17 acceptance: the personal book balances every month and never mixes with the firm's
(property tests).

Hypothesis plays random months of the founder's life (investments in and out, a family
office, a foundation and gifts, bar politics, retirement of a partner, annuities granted) over
random seeds and checks after every month: no firm entry posts a personal (9-) account; every
personal entry posts only 9-accounts and balances; each player's book equals the sum of their
entries and balances to zero; the firm's ledger balances (with annuities on 2600 equal to
what is still owed)."""

from __future__ import annotations

import contextlib
from collections import defaultdict
from dataclasses import replace

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import SimError
from ptk.sim.founder.actions import (
    BarSpend,
    CreateFoundation,
    FamilyOffice,
    GiveToFoundation,
    Invest,
)
from ptk.sim.founder.models import PERSONAL_ACCOUNTS, AnnuityTerms
from ptk.sim.founder.personal import mirror, open_book
from ptk.sim.interfaces import PartnerAccountView
from ptk.sim.ledger import ANNUITIES, PERSONAL_DIGIT
from tests.founder_support import LifeGame, set_age, start_life

MOVES = ("nothing", "invest", "divest", "office", "foundation", "gift", "bar", "retire")


def check(g: LifeGame) -> None:
    for e in g.entries:
        assert all(not ln.account.startswith(PERSONAL_DIGIT) for ln in e.lines)
    sums: dict[tuple[int, str], int] = defaultdict(int)
    for e in g.personal:
        assert all(ln.account in PERSONAL_ACCOUNTS for ln in e.lines)
        assert sum(ln.amount for ln in e.lines) == 0
        for ln in e.lines:
            sums[(e.person_id, ln.account)] += ln.amount
    for book in g.state.founder_life.books:
        mine = {a: v for (p, a), v in sums.items() if p == book.person_id and v}
        assert mine == dict(book.balances)
        assert sum(v for _, v in book.balances) == 0
    assert sum(g.balances.values()) == 0
    owed = sum(a.remaining_cents for a in g.state.founder_life.annuities)
    assert -g.bal(ANNUITIES) == owed


@settings(
    max_examples=8, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    seed=st.integers(0, 10_000),
    moves=st.lists(st.sampled_from(MOVES), min_size=1, max_size=20),
)
def test_personal_book_balances_and_stays_apart(
    data: GameData, balance: Balance, seed: int, moves: list[str]
) -> None:
    g = start_life(data, balance, seed=seed)
    terms = AnnuityTerms(True, 2500, 10)  # granted, so retirements book 2600
    g.state = replace(g.state, founder_life=replace(g.state.founder_life, annuity_terms=terms))
    g.advance(1)
    for move in moves:
        you = g.founder
        book = g.state.founder_life.book(you)
        assert book is not None
        with contextlib.suppress(SimError):
            if move == "invest":
                g.act(Invest(you, max(1, book.cash // 3)))
            elif move == "divest":
                g.act(Invest(you, -max(1, book.bal("9110_investments") // 2)))
            elif move == "office":
                g.act(FamilyOffice(you, "balanced", book.cash // 4))
            elif move == "foundation":
                g.act(CreateFoundation(you, "access_to_justice"))
            elif move == "gift":
                g.act(GiveToFoundation(you, max(1, book.cash // 5)))
            elif move == "bar":
                g.act(BarSpend(you, 5_000_00))
            elif move == "retire":
                other = next((p.person_id for p in g.fp.partners if p.person_id != you), None)
                if other is not None:
                    g.state = set_age(g.state, other, 70)
        g.advance(1)
        check(g)
        if g.state.ended:
            break


@settings(max_examples=200, deadline=None)
@given(
    steps=st.lists(
        st.tuples(
            st.integers(0, 50_000_000),  # drawn ytd's rise
            st.integers(-20_000_000, 20_000_000),  # current account's change
            st.integers(0, 5_000_000),  # capital paid in
            st.booleans(),  # December
        ),
        min_size=1,
        max_size=24,
    )
)
@pytest.mark.nightly  # PT-M11: over 60 s; check's runtime (product manager, 2026-11-23)
def test_mirror_always_balances(steps: list[tuple[int, int, int, bool]]) -> None:
    """Whatever the partnership shows, the mirror's entries balance and stay personal."""
    from ptk.loader import load_balance
    from tests.conftest import DATA_DIR

    balance = load_balance(DATA_DIR)
    view = PartnerAccountView(1, 1, True, True, 0, 0, 1_000_000, 0, 0, 0)
    book, opened = open_book(1, 0, 10_000_000, view)
    entries = list(opened)
    drawn = current = 0
    capital = 1_000_000
    for turn, (rise, change, paid, december) in enumerate(steps, start=1):
        drawn += rise
        current += change
        capital += paid
        alloc = max(0, change) if december else 0
        view = PartnerAccountView(
            1, 1, True, True, 0 if december else drawn, current, capital, alloc, 0, 0
        )
        if december:
            drawn = 0
        month = 12 if december else 6  # tunable-exempt: a December or a June
        start = (2005, (month - 1 - turn) % 12 + 1)  # so that `turn` falls in `month`
        m = mirror(book, view, turn, start, balance)
        book = m.book
        entries += m.entries
        assert all(sum(ln.amount for ln in e.lines) == 0 for e in m.entries)
        assert all(ln.account in PERSONAL_ACCOUNTS for e in m.entries for ln in e.lines)
        assert sum(v for _, v in book.balances) == 0
        assert book.cash >= 0  # the loan and tax are paid only from what cash allows
