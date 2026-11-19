"""PT-M1b: every money movement balances (brief acceptance criterion; ADR-0003, PT-0003).

Hypothesis plays random hiring months (searches on every channel, interviews, offers at any
ratio, pay policies) for random seeds and checks every entry: two or more integer-cent lines
summing to zero, firm accounts only (no client money, no personal book), known accounts,
and costs debited against cash. Cash at the end is the capital less everything paid.
"""

from __future__ import annotations

import contextlib

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import SimError
from ptk.sim.hiring.actions import Interview, MakeOffer, OpenSearch, SetPayPolicy
from tests.hiring_helpers import start

CHANNELS = ("referral", "job_post", "recruiter", "campus")
ROLES = ("corporate_ma", "commercial_litigation", "paralegal", "ip")
POLICIES = (("match", 10_000), ("lag", 8_000), ("lead", 11_000))


@settings(
    max_examples=12, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    seed=st.integers(0, 2**32),
    months=st.lists(
        st.tuples(
            st.sampled_from(CHANNELS),
            st.sampled_from(ROLES),
            st.floats(0.8, 1.3),
            st.sampled_from(POLICIES),
        ),
        min_size=1,
        max_size=16,
    ),
)
def test_every_money_movement_balances(
    data: GameData,
    balance: Balance,
    seed: int,
    months: list[tuple[str, str, float, tuple[str, int]]],
) -> None:
    game = start(data, balance, seed=seed % 1000)
    fid = game.founder_id
    accounts = {a.code for a in data.accounts if a.book == "firm"}
    for channel, role, ratio, (mode, pct) in months:
        for action in (
            OpenSearch(fid, role, channel),  # type: ignore[arg-type]
            SetPayPolicy(fid, mode, pct),  # type: ignore[arg-type]
        ):
            # out of season, out of energy, a duplicate campus search: no effect
            with contextlib.suppress(SimError):
                game.act(action)
        for c in [c for c in game.state.candidates if c.status == "open"][:3]:
            with contextlib.suppress(SimError):
                game.act(Interview(fid, c.person_id))
                game.act(MakeOffer(fid, c.person_id, max(1, int(c.ask_cents * ratio))))
        game.advance()
    capital = 0
    paid = 0
    for entry in game.entries:
        assert len(entry.lines) >= 2
        assert sum(line.amount for line in entry.lines) == 0
        for line in entry.lines:
            assert isinstance(line.amount, int) and not isinstance(line.amount, bool)
            assert line.account in accounts
            if line.account.startswith(("5", "6")):
                assert line.amount >= 0  # costs are debits
        cash = sum(ln.amount for ln in entry.lines if ln.account == "1000_cash")
        if entry.memo == "Founding partners' capital":
            capital += cash
        else:
            assert cash <= 0  # PT-M1b moves money out of the firm only
            paid -= cash
    assert sum(game.balances.values()) == 0
    assert game.cash() == capital - paid
