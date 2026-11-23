"""PT-M3b acceptance: a steady-state firm's realisation is 84-92%, collection 93-98% and
lockup 90-150 days (spec 6, balance target T7). Printed over seeds 1-10; the brief's bands
hold for the median of the seeds.

The firm is PT-M3a's acceptance firm (the group-lift scenario grown to 30 lawyers on panels
worth its capacity, leavers replaced), played for three years; the KPIs are measured over
months 13-36, once the first year's matters and bills have filled the pipeline.
"""

from __future__ import annotations

import statistics

import pytest

from ptk.sim.billing.kpis import collection_bp, realisation_bp
from ptk.sim.data_models import Balance, GameData
from tests.billing_support import played

LAWYERS = 30
MONTHS = 36
WARM_UP = 12
SEEDS = tuple(range(1, 11))
REALISATION = (8400, 9200)  # tunable-exempt: the brief's bands, bp and days
COLLECTION = (9300, 9800)  # tunable-exempt
LOCKUP = (90, 150)  # tunable-exempt


def _kpis(seed: int, data: GameData, balance: Balance) -> tuple[int, int, float, int]:
    game = played(data, balance, LAWYERS, MONTHS, seed)
    window = tuple(
        m
        for r in game.results[WARM_UP:]
        for m in r.new_state.billing.months
        if m.turn == r.snapshot.turn
    )
    lockups = [r.snapshot.firms[0].lockup_days for r in game.results[WARM_UP:]]
    util = [r.snapshot.firms[0].utilisation_bp for r in game.results[WARM_UP:]]
    real, coll = realisation_bp(window), collection_bp(window)
    assert real is not None and coll is not None and None not in lockups and None not in util
    return real, coll, statistics.median(lockups), int(statistics.median(util))  # type: ignore[type-var]


@pytest.mark.nightly  # PT-M11: over 60 s; check's runtime (product manager, 2026-11-23)
def test_steady_state_ratios_are_in_the_real_bands(
    data: GameData, balance: Balance, capsys: pytest.CaptureFixture[str]
) -> None:
    rows = {seed: _kpis(seed, data, balance) for seed in SEEDS}
    with capsys.disabled():
        print(f"\nPT-M3b steady state, {LAWYERS} lawyers, months {WARM_UP + 1}-{MONTHS}:")
        for seed, (real, coll, lock, util) in rows.items():
            print(
                f"  seed {seed:2}: realisation {real / 100:.1f}%, collection {coll / 100:.1f}%, "
                f"lockup {lock:.0f} days, utilisation {util / 100:.1f}%"
            )
    real = statistics.median(r[0] for r in rows.values())
    coll = statistics.median(r[1] for r in rows.values())
    lock = statistics.median(r[2] for r in rows.values())
    with capsys.disabled():
        print(
            f"  median: realisation {real / 100:.1f}%, collection {coll / 100:.1f}%, "
            f"lockup {lock:.0f} days"
        )
    assert REALISATION[0] <= real <= REALISATION[1]
    assert COLLECTION[0] <= coll <= COLLECTION[1]
    assert LOCKUP[0] <= lock <= LOCKUP[1]
