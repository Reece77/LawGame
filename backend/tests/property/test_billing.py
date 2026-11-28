"""PT-M3b acceptance (property tests): for random seeds and firm sizes,

- for every matter, WIP at standard = Σ tenths x rate / 10, each (person, matter, month)
  rounded once (ADR PT-0005 3), and billing's WIP books match the ledger's 1100;
- every entry balances, in integer cents, on firm accounts only;
- the client book's bank equals Σ owed to clients at every month end, and no client's
  balance is ever overdrawn (ADR PT-0003 section 7).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from simcore.kernel.money import round_half_even

from ptk.sim.billing.kpis import receivables_cents, wip_cents
from ptk.sim.data_models import Balance, GameData
from ptk.sim.ledger import (
    BAD_DEBT_PROVISION,
    CLIENT_BANK,
    DEFERRED_FEES,
    OWED_TO_CLIENTS,
    RECEIVABLES,
    WIP,
    WIP_PROVISION,
)
from ptk.sim.matters import formulas as fx
from ptk.sim.matters.models import PRO_BONO_CLIENT_ID
from ptk.sim.matters.rates import client_indexes, indexed_rate
from tests.billing_support import Played, played

PROPERTY = settings(
    max_examples=6, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)


@PROPERTY
@given(seed=st.integers(1, 10_000), lawyers=st.integers(8, 24), months=st.integers(6, 15))
def test_wip_at_standard_is_hours_times_rate(
    data: GameData, balance: Balance, seed: int, lawyers: int, months: int
) -> None:
    game = played(data, balance, lawyers, months, seed)
    worked: dict[int, int] = defaultdict(int)
    for before, result in zip(game.befores, game.results, strict=True):
        people = {p.id: p for p in before.people}
        # PT-M7c: the month's card by client tier, as the staffing rule read it
        # PT-M15: with the relationships staffing read (a claim's notice in phase 6 can end
        # a book client's relationship after the month's hours were priced)
        month = replace(
            result.new_state,
            turn=before.turn,
            market=replace(result.new_state.market, relationships=before.market.relationships),
        )
        cards = client_indexes(month, month.firm(1), balance)
        for r in result.new_state.market.hours:
            if r.turn != before.turn:
                continue
            if r.client_id == PRO_BONO_CLIENT_ID:  # PT-M7a: pro bono has no value
                assert r.value_cents == 0
                continue
            rate = indexed_rate(
                fx.rate_cents(data.practice(r.practice), people[r.person_id].level, data),
                # PT-M7a: the card after January's rise; PT-M7b: the practice's card share;
                # PT-M7c: the client's tier
                cards(r.practice, r.client_id),
            )
            assert r.value_cents == round_half_even(r.tenths * rate, fx.TENTHS)
            if r.matter_id is not None:
                worked[r.matter_id] += r.value_cents
    state = game.state
    for e in state.billing.engagements:
        # all work so far at standard is exactly the matter's hours x rate (a padding lead's
        # time is billing's, never hours, and is checked in tests/unit/test_billing.py)
        assert e.standard_cents == worked[e.matter_id] or _has_padder(game, e.matter_id)
    # billing's books are the ledger's
    assert game.balance_of(WIP) == wip_cents(state.billing, 1)
    assert game.balance_of(RECEIVABLES) == receivables_cents(state.billing, 1)
    assert -game.balance_of(WIP_PROVISION) == state.billing.wip_provision_cents
    assert -game.balance_of(BAD_DEBT_PROVISION) == state.billing.bad_debt_provision_cents
    assert -game.balance_of(DEFERRED_FEES) == state.billing.deferred_cents
    assert state.billing.wip_provision_cents >= 0 and state.billing.bad_debt_provision_cents >= 0


def _has_padder(game: Played, matter_id: int) -> bool:
    m = game.state.market.matter(matter_id)
    if m is None or m.lead_id is None:
        return False
    lead = next((p for p in game.state.people if p.id == m.lead_id), None)
    return lead is not None and "rule_bender" in lead.tags


@PROPERTY
@given(seed=st.integers(1, 10_000), lawyers=st.integers(8, 24), months=st.integers(6, 18))
def test_every_entry_balances_and_the_client_book_is_whole(
    data: GameData, balance: Balance, seed: int, lawyers: int, months: int
) -> None:
    game = played(data, balance, lawyers, months, seed)
    firm_accounts = {a.code for a in data.accounts if a.book == "firm"}
    for entry in game.entries:
        assert len(entry.lines) >= 2 and sum(ln.amount for ln in entry.lines) == 0
        for line in entry.lines:
            assert type(line.amount) is int and line.account in firm_accounts
    assert sum(game.balances.values()) == 0
    # the client book, month by month
    bank: dict[int, int] = defaultdict(int)
    owed: dict[int, int] = defaultdict(int)
    by_turn: dict[int, list] = defaultdict(list)  # type: ignore[type-arg]
    for entry in game.book:
        by_turn[entry.turn].append(entry)
    for turn in sorted({r.snapshot.turn for r in game.results}):
        for entry in by_turn.get(turn, []):
            assert sum(ln.amount for ln in entry.lines) == 0
            for line in entry.lines:
                assert line.account in (CLIENT_BANK, OWED_TO_CLIENTS)
                (bank if line.account == CLIENT_BANK else owed)[line.client_id] += line.amount
        assert sum(bank.values()) == -sum(owed.values())  # bank = Σ owed to clients
        assert all(v <= 0 for v in owed.values())  # no client is ever overdrawn
    funds = {f.client_id: f.owed_cents for f in game.state.billing.funds}
    assert funds == {c: -v for c, v in owed.items() if v != 0}
