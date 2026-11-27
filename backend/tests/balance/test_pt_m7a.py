"""PT-M7a's acceptance firm (sub-task 2), printed (run with -s) and checked.

PT-M3a's 50-lawyer grown firm (`tests.matters_support.grown_firm`), leavers replaced, months
13-48 on seeds 1-40 (PT-M18; PT-M7a read seeds 1-5): the median of the seeds' median
utilisation is in T7's band (75-90%), associates' burnout starts are at most 5% a year
(pooled), and closed named matters take their planned months (median ratio at most 1.5).
Before PT-M7a: utilisation medians 0.761, 0.643, 0.605, 0.680, 0.684 (median 0.680); matters
took about 11 months against 6 planned.
"""

from __future__ import annotations

import statistics
from concurrent.futures import ProcessPoolExecutor

import pytest

from ptk.balance.seeds import SEEDS as BALANCE_SEEDS
from ptk.sim.data_models import Balance, GameData
from tests.matters_support import grown_firm, play, top_up

SEEDS = BALANCE_SEEDS  # PT-M18: seeds 1-40 (CLAUDE.md 12.1; PT-M7a read seeds 1-5)
LAWYERS = 50
WARM_UP = 12
MONTHS = 48
UTILISATION = (0.75, 0.90)  # tunable-exempt: T7's band
BURNOUT = 0.05  # tunable-exempt: the brief's ceiling, a year
DURATION = 1.5  # tunable-exempt: the brief's ceiling on closed matters' months / planned


def _seed(seed: int, data: GameData, balance: Balance) -> tuple[float, int, int, float]:
    state = grown_firm(data, balance, LAWYERS, seed)
    utils: list[float] = []
    burnouts = associate_months = 0
    firm = state.player.id
    for month in range(MONTHS):
        before = state
        state, results = play(state, data, balance, 1, seed)
        snap = results[-1].snapshot.firms[0]
        staff = set(state.staff_ids(firm))
        assoc = [p for p in state.people if p.id in staff and p.level.startswith("associate")]
        if month >= WARM_UP:
            assert snap.utilisation_bp is not None
            utils.append(snap.utilisation_bp / 10000)
            associate_months += len(assoc)
            burnouts += sum(1 for p in assoc if p.burnout_since == state.turn - 1)
        state = top_up(state, data, balance, before)
    ratios = [
        (m.closed_turn - m.opened_turn) / m.planned_months
        for m in state.market.matters
        if m.firm_id == firm
        and m.closed_turn is not None
        and m.opened_turn >= WARM_UP // 2
        and not m.pro_bono
    ]
    return statistics.median(utils), burnouts, associate_months, statistics.median(ratios)


def _worker(seed: int) -> tuple[float, int, int, float]:
    from ptk.loader import load_balance, load_game_data
    from tests.conftest import DATA_DIR

    return _seed(seed, load_game_data(DATA_DIR), load_balance(DATA_DIR))


@pytest.fixture(scope="module")
def rows() -> dict[int, tuple[float, int, int, float]]:
    with ProcessPoolExecutor() as pool:  # PT-M18: forty seeds, in parallel
        return dict(zip(SEEDS, pool.map(_worker, SEEDS), strict=True))


@pytest.mark.nightly  # PT-M11: over 60 s; check's runtime (product manager, 2026-11-23)
def test_the_acceptance_firm_is_busy_without_burning_out(
    rows: dict[int, tuple[float, int, int, float]], capsys: pytest.CaptureFixture[str]
) -> None:
    with capsys.disabled():
        print("\nPT-M7a acceptance firm, 50 lawyers, months 13-48:")
        for seed, (util, burn, months, ratio) in rows.items():
            print(
                f"  seed {seed}: utilisation {util:.1%}, burnout {burn / (months / 12):.1%} a "
                f"year, closed matters {ratio:.2f} x planned"
            )
    util = statistics.median(r[0] for r in rows.values())
    burn = sum(r[1] for r in rows.values()) / (sum(r[2] for r in rows.values()) / 12)
    duration = statistics.median(r[3] for r in rows.values())
    with capsys.disabled():
        print(f"  median utilisation {util:.1%}, burnout {burn:.1%} a year, {duration:.2f} x")
    assert UTILISATION[0] <= util <= UTILISATION[1]
    assert burn <= BURNOUT
    assert duration <= DURATION
