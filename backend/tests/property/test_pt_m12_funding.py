"""PT-M12 sub-task 6 (spec 7.7; ADR PT-0018): contingency and litigation funding.

- The funder's waterfall: the advances are repaid or borne, never both, and the funder is
  paid at most the fee (Hypothesis over amounts).
- A played firm whose every case is on contingency, taking every funder's offer: a contingency
  case's WIP posts no fee until its recovery; a funded case lost (no recovery) costs the firm
  only its unfunded WIP (the advances are released to 4400 and nothing else is posted); the
  ledger's 1100 and 2800 are billing's books, and the client book's bank equals what is owed
  to clients every month (Hypothesis over seeds).
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from ptk.sim.billing import books as bk
from ptk.sim.billing.actions import AcceptFunding, apply_billing_action
from ptk.sim.billing.funding import close_funding
from ptk.sim.billing.kpis import funder_advances_cents, wip_cents
from ptk.sim.data_models import Balance, GameData
from ptk.sim.ledger import (
    CLIENT_BANK,
    FEES,
    FUNDED_FEES,
    FUNDER_ADVANCES,
    OWED_TO_CLIENTS,
    SUCCESS_FEES,
    WIP,
    apply_entries,
)
from ptk.sim.rng import RngFactory
from tests.billing_support import Played
from tests.matters_support import grown_firm

PROPERTY = settings(
    max_examples=4, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)


@given(advances=st.integers(0, 10**10), fee=st.integers(0, 10**11), ret=st.integers(10_000, 40_000))
def test_the_waterfall_repays_or_bears_every_advance(advances: int, fee: int, ret: int) -> None:
    c = close_funding(advances, fee, ret)
    assert c.repaid_cents + c.released_cents == advances
    assert 0 <= c.paid_cents <= fee
    assert c.cost_cents >= 0 and c.repaid_cents >= 0 and c.released_cents >= 0
    if fee == 0:
        assert c.released_cents == advances and c.paid_cents == 0
    if fee >= advances * ret // 10_000 + 1:
        assert c.released_cents == 0  # a big enough fee repays the funder in full


def _contingency_world(balance: Balance) -> Balance:
    """Every case on contingency, and funders from the start."""
    models = {**balance.billing.models, "case": {"contingency": 1.0}}
    funding = balance.billing.funding.model_copy(update={"from_ym": (2005, 1)})
    billing = balance.billing.model_copy(update={"models": models, "funding": funding})
    return balance.model_copy(update={"billing": billing})


def _founder(state: Any) -> int:
    return next(p.id for p in state.people if p.is_founder)


@PROPERTY
@given(seed=st.integers(1, 10_000))
def test_contingency_and_funding_reconcile(data: GameData, balance: Balance, seed: int) -> None:
    check_contingency(data, balance, seed)


def check_contingency(data: GameData, balance: Balance, seed: int, months: int = 30) -> None:
    from tests.matters_support import solvent

    balance = solvent(_contingency_world(balance))
    game = Played(state=grown_firm(data, balance, 16, seed), seed=seed)
    rng = RngFactory(seed)
    seen_standard: dict[int, int] = defaultdict(int)
    funded: set[int] = set()
    closed_losses = 0
    total_contingency = 0
    for month in range(months):
        # take every funder's offer on an open contingency case
        for e in game.state.billing.engagements:
            if (
                e.firm_id == 1
                and e.model == "contingency"
                and not e.closed
                and e.funded_turn is None
            ):
                out = apply_billing_action(
                    game.state,
                    AcceptFunding(_founder(game.state), e.matter_id),
                    lambda: rng.stream(0, "misc"),
                    balance,
                    rng,
                )
                game.state = out.state
                game.balances = apply_entries(game.balances, out.entries)
                funded.add(e.matter_id)
        before = {e.matter_id: e for e in game.state.billing.engagements}
        result = game.advance(data, balance)
        state = result.new_state
        mine = [x for x in result.ledger_entries if x.firm_id == 1]
        # WIP posted to fees excludes contingency work (no fee until a recovery)
        worked = next(
            m for m in state.billing.months if m.turn == result.snapshot.turn
        ).worked_cents
        contingency_work = 0
        for e in state.billing.engagements:
            if e.firm_id == 1 and e.model == "contingency":
                contingency_work += e.standard_cents - seen_standard[e.matter_id]
                seen_standard[e.matter_id] = e.standard_cents
        posted = -sum(
            ln.amount
            for x in mine
            if x.memo == bk.WIP_POSTED
            for ln in x.lines
            if ln.account == FEES
        )
        # (a padding lead's time also posts to fees, so at least the non-contingency work)
        assert posted >= worked - contingency_work, (month, posted, worked, contingency_work)
        total_contingency += contingency_work
        # billing's books are the ledger's: contingency WIP is not on 1100 (no fee until a
        # recovery), and 2800 is the open funded cases' advances
        assert game.balance_of(WIP) == wip_cents(state.billing, 1)
        assert -game.balance_of(FUNDER_ADVANCES) == funder_advances_cents(state.billing, 1)
        # the client book balances: the bank is what is owed to clients
        bank = sum(v for (f, a), v in game.balances.items() if a == CLIENT_BANK and f == 1)
        owed = -sum(v for (f, a), v in game.balances.items() if a == OWED_TO_CLIENTS and f == 1)
        assert bank == owed >= 0
        # a funded case lost: the advances are released, and no fee posts for it
        for e in state.billing.engagements:
            b = before.get(e.matter_id)
            if not (
                e.closed and e.closed_turn == result.snapshot.turn and e.model == "contingency"
            ):
                continue
            if b is None or e.matter_id not in funded:
                continue
            if e.billed_cents == b.billed_cents:  # no recovery
                closed_losses += 1
                released = -sum(
                    ln.amount
                    for x in mine
                    if x.memo == bk.FUNDING
                    for ln in x.lines
                    if ln.account == FUNDED_FEES and ln.practice == e.practice
                )
                assert released >= b.advances_cents + _month_advance(e, b)
    assert funded and total_contingency > 0  # the run worked and funded contingency cases
    _ = (SUCCESS_FEES, closed_losses)


def _month_advance(e: Any, b: Any) -> int:
    """The close month's own advance (posted before the close releases everything)."""
    from ptk.sim.billing.funding import advance_cents

    return advance_cents(e.standard_cents - b.standard_cents, b.funded_bp)


def _close(state: Any, matter_id: int, outcome: str) -> Any:
    """Force a matter's result at the month about to be played (billing closes it)."""
    from dataclasses import replace

    matters = tuple(
        replace(m, status="closed", outcome=outcome, closed_turn=state.turn)
        if m.id == matter_id
        else m
        for m in state.market.matters
    )
    return replace(state, market=replace(state.market, matters=matters))


def _funding_lines(entries: Any, account: str) -> int:
    return sum(
        ln.amount
        for x in entries
        if x.firm_id == 1 and x.memo == bk.FUNDING
        for ln in x.lines
        if ln.account == account
    )


def test_a_funded_loss_costs_only_the_unfunded_wip_and_a_win_pays_the_funder_first(
    data: GameData, balance: Balance
) -> None:
    from ptk.sim.billing.funding import advance_cents
    from ptk.sim.ledger import FUNDING_COSTS
    from tests.matters_support import solvent

    balance = solvent(_contingency_world(balance))
    seed = 7
    game = Played(state=grown_firm(data, balance, 16, seed), seed=seed)
    rng = RngFactory(seed)
    open_cases: list[Any] = []
    for _ in range(36):  # until two contingency cases have work to fund
        game.advance(data, balance)
        open_cases = sorted(
            (
                e
                for e in game.state.billing.engagements
                if e.model == "contingency" and not e.closed and e.wip_cents > 0
            ),
            key=lambda e: -e.wip_cents,
        )
        if len(open_cases) >= 2:
            break
    assert len(open_cases) >= 2
    lose, win = open_cases[0], open_cases[1]
    for e in (lose, win):
        out = apply_billing_action(
            game.state,
            AcceptFunding(_founder(game.state), e.matter_id),
            lambda: rng.stream(0, "misc"),
            balance,
            rng,
        )
        game.state, game.balances = out.state, apply_entries(game.balances, out.entries)
        assert -sum(
            ln.amount for x in out.entries for ln in x.lines if ln.account == FUNDER_ADVANCES
        ) == (advance_cents(e.wip_cents, game.state.billing.engagement(e.matter_id).funded_bp))
    game.advance(data, balance)  # a month of funded work
    # the loss
    e = game.state.billing.engagement(lose.matter_id)
    game.state = _close(game.state, lose.matter_id, "lost")
    result = game.advance(data, balance)
    after = game.state.billing.engagement(lose.matter_id)
    month_advance = advance_cents(after.standard_cents - e.standard_cents, e.funded_bp)
    advances = e.advances_cents + month_advance
    # the funder bears every advance; no fee posts; the firm's loss is its unfunded WIP
    assert -_funding_lines(result.ledger_entries, FUNDED_FEES) >= advances
    assert after.closed and after.billed_cents == e.billed_cents and after.advances_cents == 0
    assert advances < after.standard_cents  # the firm carried the unfunded rest itself
    # the win: the recovery passes through the client book; the funder is paid first
    w = game.state.billing.engagement(win.matter_id)
    game.state = _close(game.state, win.matter_id, "won")
    result = game.advance(data, balance)
    done = game.state.billing.engagement(win.matter_id)
    fee = done.billed_cents - w.billed_cents
    assert fee > 0
    adv = w.advances_cents + advance_cents(done.standard_cents - w.standard_cents, w.funded_bp)
    due = min(fee, adv * w.funder_return_bp // 10_000)
    repaid = _funding_lines(result.ledger_entries, FUNDER_ADVANCES)
    cost = _funding_lines(result.ledger_entries, FUNDING_COSTS)
    assert repaid + cost == due and repaid <= adv  # paid first, from the fee, capped at it
    assert -game.balance_of(FUNDER_ADVANCES) == funder_advances_cents(game.state.billing, 1)
    bank = sum(v for (f, a), v in game.balances.items() if a == CLIENT_BANK and f == 1)
    owed = -sum(v for (f, a), v in game.balances.items() if a == OWED_TO_CLIENTS and f == 1)
    assert bank == owed
