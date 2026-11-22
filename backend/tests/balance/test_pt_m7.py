"""PT-M7's balance targets (docs/balance-targets.md) through the runner (`ptk.balance`).

The full run (five strategies x seeds 1-10 x 132 turns, T5's difficulty runs and the T8/T9
variants) is `nightly`: it prints every target and fails on a pass/fail target (T1, T2, T11,
T12) that is not a recorded known miss within its bound; bands print and are carried in the
brief's "Decisions made". A short smoke run checks the runner itself in `make check`.
"""

from __future__ import annotations

import pytest

from ptk.balance.known_misses import verdict
from ptk.balance.report import evaluate, play, run_all, runs_table, shock_table, table
from ptk.balance.strategies import PLAYABLE, STRATEGIES


def test_the_runner_plays_every_script_and_reports() -> None:
    """Every script plays a year without error; the same seed gives the same run."""
    results = [play(name, 1, turns=12) for name in PLAYABLE]
    assert all(len(r.months) == 12 or r.dissolved for r in results)
    again = play("steady", 1, turns=12)
    steady = next(r for r in results if r.strategy == "steady")
    assert [m.revenue_cents for m in again.months] == [m.revenue_cents for m in steady.months]
    assert [m.lawyers for m in again.months] == [m.lawyers for m in steady.months]
    rows = evaluate(results)
    assert {r.target for r in rows} >= {"T1", "T2", "T7.realisation", "T10.steady"}
    assert table(rows) and runs_table(results)


def test_do_nothing_does_nothing() -> None:
    """The do-nothing script makes no move at all (its game is the unmanaged firm's)."""
    run = play("do-nothing", 2, turns=24)
    assert run.refused == {}
    assert run.class_size == 0


@pytest.mark.nightly
def test_balance_targets(capsys: pytest.CaptureFixture[str]) -> None:
    results = run_all(strategies=tuple(STRATEGIES), jobs=4, long_runs=True)  # PT-M10: to 2034
    rows = evaluate(results)
    with capsys.disabled():
        print("\n" + runs_table(results) + "\n\n" + shock_table(results) + "\n\n" + table(rows))
    failed = [r.target for r in rows if r.gate and verdict(r) == "fail"]
    assert not failed, f"pass/fail targets failed: {failed}"
