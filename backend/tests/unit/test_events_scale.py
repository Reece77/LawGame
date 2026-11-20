"""Acceptance (the brief): at most 6 non-critical events a month for a 50-lawyer firm (median),
every event written and answered as a player's Continue would. Printed over seeds 1-5."""

from __future__ import annotations

import statistics
from collections import Counter

import pytest

from ptk.sim.data_models import Balance, GameData
from tests.matters_support import grown_firm, play, top_up

LAWYERS = 50
MONTHS = 36
TARGET = 6  # tunable-exempt: the brief's target


@pytest.mark.parametrize("seed", (1, 2, 3, 4, 5))
def test_non_critical_events_a_month_at_50_lawyers(
    seed: int, data: GameData, balance: Balance, capsys: pytest.CaptureFixture[str]
) -> None:
    state = grown_firm(data, balance, LAWYERS, seed)
    for _ in range(MONTHS):
        before = state
        state, _ = play(state, data, balance, 1, seed, write_events=True)
        state = top_up(state, data, balance, before)  # replace leavers: stay at 50 lawyers
    shown = Counter(e.turn for e in state.events.events if e.severity != "critical")
    counts = [shown.get(turn, 0) for turn in range(1, MONTHS + 1)]
    median = statistics.median(counts)
    with capsys.disabled():
        print(f"\nseed {seed}: non-critical events a month median {median}, max {max(counts)}")
    assert median <= TARGET
