"""PT-M4 acceptance: capital accounts, draws and the true-up balance (property tests).

Hypothesis plays random partnership months (laterals joining with guarantees, partners
leaving, capital calls, draws suspended and restored, the revolver repaid) over random
seeds and checks after every month: every entry balances; each partner's capital and
current account (with leavers' balances still owed) sum to the ledger's 3000 and 2700;
drawings (3200) are the partners' draws this year; nothing is left in drawings after a
December allocation.
"""

from __future__ import annotations

import contextlib

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from ptk.sim.calendar import turn_to_ym
from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import SimError
from ptk.sim.partnership.actions import CapitalCall, RepayRevolver, SetDraws
from tests.partnership_support import Game, add_partner, depart, start

MOVES = ("nothing", "lateral", "leave", "capital_call", "draws", "repay")


def check(g: Game) -> None:
    fp = g.fp
    capital = sum(p.capital_cents for p in fp.partners) + sum(
        r.remaining_capital_cents for r in fp.capital_returns
    )
    current = sum(p.current_cents for p in fp.partners) + sum(
        r.remaining_current_cents for r in fp.capital_returns
    )
    assert capital == -g.bal("3000_partners_capital")
    assert current == -g.bal("2700_partner_current_accounts")
    assert sum(p.drawn_ytd_cents for p in fp.partners) == g.bal("3200_drawings")
    assert all(r.remaining_capital_cents >= 0 for r in fp.capital_returns)
    assert sum(g.balances.values()) == 0


@settings(
    max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    seed=st.integers(0, 10_000),
    moves=st.lists(st.sampled_from(MOVES), min_size=1, max_size=30),
)
def test_capital_draws_and_true_up_balance(
    data: GameData, balance: Balance, seed: int, moves: list[str]
) -> None:
    g = start(data, balance, seed=seed % 997)
    n = 0
    for move in moves:
        others = [p.person_id for p in g.fp.partners if p.person_id != g.founder]
        with contextlib.suppress(SimError):
            if move == "lateral":
                n += 1
                add_partner(g, "corporate_ma", 40_000_000, guarantee_years=n % 3, clients=1, n=n)
            elif move == "leave" and others:
                depart(g, others[seed % len(others)])
            elif move == "capital_call":
                g.act(CapitalCall(g.founder, 20_000_000))
            elif move == "draws":
                g.act(SetDraws(g.founder, not g.fp.draws_suspended))
            elif move == "repay":
                g.act(RepayRevolver(g.founder, 10_000_000))
        check(g)
        if g.state.ended:
            break
        december = turn_to_ym(g.state.turn, g.state.save_meta.start_ym)[1] == 12
        g.advance()
        check(g)
        for entry in g.entries:
            assert sum(line.amount for line in entry.lines) == 0
        if december:
            assert g.bal("3200_drawings") == 0
