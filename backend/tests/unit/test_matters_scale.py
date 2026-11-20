"""Acceptance: named matters <= 40 open for a 50-lawyer firm (median), so the player's list
stays manageable (ADR PT-0004 consequences). Printed over seeds 1-5."""

from __future__ import annotations

import statistics

import pytest

from ptk.sim.data_models import Balance, GameData
from tests.matters_support import grown_firm, play, top_up

LAWYERS = 50
WARM_UP = 12  # months before counting (matters run for up to three years)
MONTHS = 48


@pytest.mark.parametrize("seed", (1, 2, 3, 4, 5))
def test_named_matters_stay_manageable_at_50_lawyers(
    seed: int, data: GameData, balance: Balance, capsys: pytest.CaptureFixture[str]
) -> None:
    state = grown_firm(data, balance, LAWYERS, seed)
    counts = []
    for _ in range(MONTHS):
        before = state
        state, _ = play(state, data, balance, 1, seed)
        state = top_up(state, data, balance, before)  # replace leavers: stay at 50 lawyers
        counts.append(len(state.market.open_matters(state.player.id)))
    lawyers = sum(
        1 for p in state.people if p.id in state.staff_ids(1) and data.role(p.role).kind == "lawyer"
    )
    median = statistics.median(counts[WARM_UP:])
    with capsys.disabled():
        print(
            f"\nseed {seed}: {lawyers} lawyers, open named matters median {median}, "
            f"max {max(counts)}"
        )
    assert lawyers == LAWYERS
    assert median <= 40  # tunable-exempt: the brief's target
