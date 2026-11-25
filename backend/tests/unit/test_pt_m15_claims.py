"""PT-M15 sub-task 2: malpractice claims (spec 11.3)."""

from __future__ import annotations

from dataclasses import replace

from ptk.sim.risk import claims as cl
from ptk.sim.risk.common import Books
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState
from tests.risk_support import (
    a_claim,
    busy_firm,
    escaped,
    loaded,
    player_matters,
    with_a_claim,
    with_a_policy,
)


def test_no_escapes_no_claims() -> None:
    data, balance = loaded()
    state = busy_firm()
    out = cl.make_claims(state, state, RngFactory(1), balance, data)
    assert out.risk.claims == state.risk.claims


def test_escaped_errors_make_latent_claims_deterministically() -> None:
    data, balance = loaded()
    start = busy_firm()
    ids = {m.id: 40 for m in player_matters(start)[:3]}
    after = escaped(start, ids)
    a = cl.make_claims(start, after, RngFactory(7), balance, data)
    b = cl.make_claims(start, after, RngFactory(7), balance, data)
    assert a.risk == b.risk
    new = [c for c in a.risk.claims if c not in start.risk.claims]
    assert 0 < len(new) <= 120
    assert all(c.stage == "latent" and c.surfaces_turn > start.turn for c in new)
    assert all(
        0.0 <= c.merit <= 1.0 and c.size_cents > 0 and c.demand_cents >= c.size_cents for c in new
    )
    assert {c.matter_id for c in new} <= set(ids)


def test_real_people_are_never_blamed() -> None:
    data, balance = loaded()
    start = busy_firm()
    real = replace(start, people=tuple(replace(p, real=True) for p in start.people))
    after = escaped(real, {m.id: 40 for m in player_matters(real)[:3]})
    out = cl.make_claims(real, after, RngFactory(3), balance, data)
    assert out.risk.claims != real.risk.claims
    assert all(c.blamed_id is None for c in out.risk.claims if c not in real.risk.claims)


def _run(state: GameState, months: int, seed: int = 1) -> tuple[GameState, Books]:
    data, balance = loaded()
    books = Books(state.player.id, state.turn, 10**12)
    for _ in range(months):
        books.turn = state.turn
        state = cl.claims_month(state, RngFactory(seed), books, balance, data)
        state = replace(state, turn=state.turn + 1)
    return state, books


def test_a_claim_goes_through_its_stages_and_pays_by_the_policy() -> None:
    base = with_a_policy(busy_firm(), limit=500_000_000, deductible=10_000_000)
    seen = set()
    state = with_a_claim(base, a_claim(base, merit=0.9))
    for _ in range(80):
        state, _ = _run(state, 1)
        c = state.risk.claim(1)
        assert c is not None
        seen.add(c.stage)
        if c.stage == "closed":
            break
    assert c.stage == "closed" and c.outcome is not None
    assert {"notice", "investigation"} <= seen
    assert c.paid_cents == c.deductible_paid_cents + c.insurer_paid_cents + c.excess_paid_cents
    assert c.deductible_paid_cents <= 10_000_000 and c.insurer_paid_cents <= 500_000_000


def test_an_unanswered_offer_takes_the_default_rule() -> None:
    base = with_a_policy(busy_firm(), limit=500_000_000, deductible=10_000_000)
    claim = replace(
        a_claim(base, merit=0.5),
        stage="offer",
        noticed_turn=base.turn - 5,
        stage_until=base.turn + 10,
        merit_lo=0.4,
        merit_hi=0.6,
        offer_cents=1,
        offer_expires=base.turn,
        deductible_cents=10_000_000,
        limit_cents=500_000_000,
    )
    state, _ = _run(with_a_claim(base, claim), 1)
    c = state.risk.claim(1)
    assert c is not None and c.outcome == "settled" and c.indemnity_cents == 1
    assert cl.default_answer(replace(claim, offer_cents=10**12)) == "contest"


def test_the_firm_cannot_pay_so_the_partners_pay_in_capital() -> None:
    data, balance = loaded()
    base = with_a_policy(busy_firm(), limit=200_000_000, deductible=0)
    claim = replace(
        a_claim(base),
        stage="trial",
        stage_until=base.turn,
        noticed_turn=base.turn - 9,
        merit=1.0,
        size_cents=900_000_000,
        limit_cents=200_000_000,
    )
    state = with_a_claim(base, claim)
    books = Books(state.player.id, state.turn, 0)
    state = cl.claims_month(state, RngFactory(1), books, balance, data)
    c = state.risk.claim(1)
    assert c is not None and c.outcome == "lost"
    assert c.excess_paid_cents > 0 and c.called_cents == c.excess_paid_cents
    assert any(e.memo.startswith("Capital call") for e in books.entries)
    assert books.cash == 0
