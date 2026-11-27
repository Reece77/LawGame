"""PT-M18's thirty-year target T18 (the product manager's approval, 2026-11-27; nightly).

T18, the AI era, on seeds 1-40 (PT-M14's criteria 2 and 4, read by `tools/tech_readings.py`):
(a) a fully adopted firm's AI-exposed tasks take 40-70% fewer hours by December 2030 on every
seed; (b) the 2030 junior cohort's growth falls without training when AI removes their review
hours (median), and training restores at least half of the loss (median of the seeds with a
cohort that lost). T15-T17 are rows of the balance run (`ptk.balance.report`).
"""

from __future__ import annotations

import statistics
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pytest

from ptk.balance.seeds import SEEDS

TOOLS = Path(__file__).resolve().parents[3] / "tools"
SAVING = (0.40, 0.70)  # tunable-exempt: T18 (a), PT-M14 criterion 2's band
RESTORED = 0.5  # tunable-exempt: T18 (b), PT-M14 criterion 4's "at least half"


def _seed(seed: int) -> tuple[int, float, tuple[float, float, float], int]:
    """PT-M14's criteria 2 and 4 as `tools/tech_readings.py run_seed` reads them, without its
    `never` and `ai-fixed` branches (criterion 3's): steady to December 2015 (the saving at
    full adoption), `ai-hourly` to December 2029, then 2030 with AI off, untrained and
    trained. The same plays and the same numbers (test_t18_reader_matches_tech_readings)."""
    import copy
    from dataclasses import replace

    sys.path.insert(0, str(TOOLS))
    import tech_readings as tr  # tools/tech_readings.py (PT-M14's readings)

    from ptk.balance.game import start_game
    from ptk.balance.report import SCENARIO
    from ptk.balance.strategies import PLAYABLE
    from ptk.loader import load_balance, load_game_data
    from ptk.sim.tech import efficiency as ef
    from tests.conftest import DATA_DIR

    data, balance = load_game_data(DATA_DIR), load_balance(DATA_DIR)
    base = start_game(data, balance, seed, SCENARIO, "standard")
    tr._play(base, PLAYABLE["steady"], (2015, 12), {})
    full = ef.full_efficiency(base.state, data, (2030, 12))
    exposed = [x.key for x in data.market.tasks if x.ai_exposure >= balance.tech.exposed_min]
    saving = 1 - sum(full[x] for x in exposed) / len(exposed)
    stash = copy.deepcopy(base)
    tr._play(stash, PLAYABLE["ai-hourly"], (2029, 12), {})
    start = tr._juniors(stash)
    learn = []
    for name in ("off", "ai-untrained", "ai-hourly"):
        g = copy.deepcopy(stash)
        if name == "off":
            g.state = replace(g.state, tech=type(g.state.tech)())
            script = PLAYABLE["never"]
        else:
            script = PLAYABLE[name]
        tr._play(g, script, (2030, 12), {})
        end = tr._juniors(g)
        both = [pid for pid in start if pid in end]
        learn.append((both, {pid: end[pid] - start[pid] for pid in both}))
    common = set(learn[0][0]) & set(learn[1][0]) & set(learn[2][0])
    growth = tuple(sum(d[pid] for pid in common) / len(common) if common else 0.0 for _, d in learn)
    return seed, saving, growth, len(common)  # type: ignore[return-value]


@pytest.mark.nightly
def test_t18_the_ai_era() -> None:
    with ProcessPoolExecutor() as pool:
        rows = sorted(pool.map(_seed, SEEDS))
    savings = [s for _, s, _, _ in rows]
    shares, losses = [], []
    for seed, saving, (off, untrained, trained), cohort in rows:
        lost = off - untrained
        share = (trained - untrained) / lost if cohort and lost > 0 else None
        if cohort:
            losses.append(lost)
        if share is not None:
            shares.append(share)
        print(
            f"\nT18 seed {seed}: exposed tasks {saving:.1%} fewer hours; cohort {cohort}: "
            f"growth off {off:.3f}, untrained {untrained:.3f}, trained {trained:.3f}"
            + (f", restored {share:.2f}" if share is not None else "")
        )
    median_share = statistics.median(shares) if shares else None
    print(
        f"\nT18: exposed-task saving {min(savings):.1%}-{max(savings):.1%} (band "
        f"{SAVING[0]:.0%}-{SAVING[1]:.0%}); median loss without training "
        f"{statistics.median(losses) if losses else 0:.3f}; median restored share "
        f"{median_share if median_share is not None else float('nan'):.2f} over {len(shares)} seeds"
    )
    assert all(SAVING[0] <= s <= SAVING[1] for s in savings)
    assert losses and statistics.median(losses) > 0
    assert median_share is not None and median_share >= RESTORED
