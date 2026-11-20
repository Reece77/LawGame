"""Rival invariants (PT-M5): pools never go negative, every key person's attributes stay in
1-20, every rival ledger entry balances and leaves rivals' cash at zero."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from ptk.sim.data_models import Balance, GameData
from ptk.sim.ledger import CASH
from ptk.sim.rivals.people import person_of
from tests.rivals_support import play_until, start


@settings(deadline=None, max_examples=5)
@given(st.integers(0, 2**64 - 1), st.integers(1, 30))
def test_rivals_stay_sane(data: GameData, balance: Balance, seed: int, turns: int) -> None:
    state = start(data, balance, seed)
    state, results = play_until(state, data, balance, turns, seed)
    for firm in state.rivals.firms:
        for pool in firm.pools:
            assert pool.equity >= 0 and pool.partners >= 0 and pool.associates >= 0
        assert firm.rate_index > 0 and firm.demand_cents >= 0
    for m in state.rivals.members[::25]:
        p = person_of(state, m, data, balance)
        for attrs in (p.skills, p.personality, p.hidden, p.familiarity):
            assert all(1.0 <= v <= 20.0 for _, v in attrs.items)
    rival_ids = {f.id for f in state.rivals.firms}
    for r in results:
        for e in r.ledger_entries:
            assert sum(ln.amount for ln in e.lines) == 0
            if e.firm_id in rival_ids:
                assert sum(ln.amount for ln in e.lines if ln.account == CASH) == 0
