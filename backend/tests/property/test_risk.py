"""PT-M15 properties: claims arise only from escaped errors and lost high-stakes cases; every
claim payment splits exactly into deductible, insurer and excess; entries balance."""

from __future__ import annotations

from dataclasses import replace

from hypothesis import given, settings
from hypothesis import strategies as st

from ptk.sim.risk import claims as cl
from ptk.sim.risk.common import Books
from ptk.sim.risk.formulas import split_payment
from ptk.sim.streams import RngFactory
from tests.risk_support import (
    a_claim,
    busy_firm,
    escaped,
    loaded,
    player_matters,
    with_a_claim,
    with_a_policy,
)

OUTCOMES = st.sampled_from(["won", "settled", "closed", "done", None])


@settings(max_examples=40, deadline=None)
@given(
    seed=st.integers(1, 10_000),
    changes=st.lists(st.tuples(st.integers(0, 30), st.integers(0, 50), OUTCOMES), max_size=8),
)
def test_claims_come_only_from_escapes_and_lost_cases(seed: int, changes: list) -> None:
    """Any month's changes to matters other than an escaped error or a lost case (hours,
    caught errors, wins, settlements) bring no claim."""
    data, balance = loaded()
    start = busy_firm()
    matters = player_matters(start)
    market = start.market
    by_id = {m.id: m for m in market.matters}
    for index, caught, outcome in changes:
        m = by_id[matters[index % len(matters)].id]
        by_id[m.id] = replace(
            m,
            errors_caught=m.errors_caught + caught,
            worked_tenths=m.worked_tenths + caught,
            outcome=outcome,
        )
    after = replace(start, market=replace(market, matters=tuple(by_id[k] for k in sorted(by_id))))
    out = cl.make_claims(start, after, RngFactory(seed), balance, data)
    assert out.risk.claims == start.risk.claims


@settings(max_examples=40, deadline=None)
@given(seed=st.integers(1, 10_000), n=st.integers(0, 60))
def test_claims_at_most_one_per_escape(seed: int, n: int) -> None:
    data, balance = loaded()
    start = busy_firm()
    after = escaped(start, {player_matters(start)[0].id: n})
    out = cl.make_claims(start, after, RngFactory(seed), balance, data)
    assert len(out.risk.claims) - len(start.risk.claims) <= n


@given(amount=st.integers(0, 10**12), ded=st.integers(0, 10**10), lim=st.integers(0, 10**11))
def test_split_is_exact(amount: int, ded: int, lim: int) -> None:
    s = split_payment(amount, ded, lim)
    assert s.deductible + s.insurer + s.excess == amount
    assert 0 <= s.deductible <= ded and 0 <= s.insurer <= lim and s.excess >= 0
    assert s.excess == 0 or (s.deductible == ded and s.insurer == lim)


@settings(max_examples=25, deadline=None)
@given(
    seed=st.integers(1, 10_000),
    merit=st.floats(0.0, 1.0),
    size=st.integers(1_000_000, 3_000_000_000),
    limit=st.sampled_from([0, 200_000_000, 1_000_000_000]),
    ded=st.sampled_from([0, 2_500_000, 25_000_000]),
    cash=st.integers(0, 10**10),
)
def test_claim_payments_reconcile(
    seed: int, merit: float, size: int, limit: int, ded: int, cash: int
) -> None:
    """Every claim's payments = the insurer's share + the deductible + the excess; the firm's
    part is posted (6310) and an unpaid part becomes a capital call; every entry balances."""
    data, balance = loaded()
    base = with_a_policy(busy_firm(), limit=limit, deductible=ded)
    state = with_a_claim(base, a_claim(base, merit=merit, size=size))
    books = Books(state.player.id, state.turn, cash)
    for _ in range(80):
        books.turn = state.turn
        state = cl.claims_month(state, RngFactory(seed), books, balance, data)
        state = replace(state, turn=state.turn + 1)
        if state.risk.claim(1).stage == "closed":  # type: ignore[union-attr]
            break
    c = state.risk.claim(1)
    assert c is not None
    assert c.paid_cents == c.deductible_paid_cents + c.insurer_paid_cents + c.excess_paid_cents
    assert c.deductible_paid_cents <= ded and c.insurer_paid_cents <= limit
    posted = sum(e.lines[0].amount for e in books.entries if e.lines[0].account == "6310_claims")
    assert posted == c.firm_paid_cents
    called = sum(e.lines[0].amount for e in books.entries if e.memo.startswith("Capital call"))
    assert called == c.called_cents
    assert books.cash >= 0 or c.called_cents == 0
    for e in books.entries:
        assert sum(line.amount for line in e.lines) == 0
