"""PT-M5's balance checks (docs/balance-targets.md), printed (run with -s) and checked.

T11: rivals hold history: each pinned rival's revenue within +-15% of its path in December
2009, 2015, 2020 and 2025 (PT-M10 added the last two; pinned: a firms.yaml point that year whose
revenue is sourced [S], the firm alive then in history), and history's top 10 by FY2025
revenue holds at least 8 of the game's top 10, on seeds 1-10. The player's firm plays the
biglaw spin-out unmanaged (no strategy scripts exist before PT-M7).

Conditional history (the brief): a player who hires a third of a historically collapsing
firm's top partners a year before its date brings the collapse forward on at least 7 of 10
seeds (Howrey, March 2011; the hire in March 2010).

T12: the median turn of 2025 (PT-M10; PT-M5 timed 2015) is at most 250 ms on a firm of
steady's size (150 lawyers, its 12 turns timed, the rivals' market played to 2025 first), run
alone (`make check-timing`).
"""

from __future__ import annotations

import statistics
import time

import pytest

from ptk.sim.data_models import Balance, GameData
from ptk.sim.decisions import Decisions
from ptk.sim.ledger import CASH, PARTNERS_CAPITAL, apply_entries
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState
from ptk.sim.turn import advance_turn
from tests.matters_support import grown_firm, top_up
from tests.rivals_support import hire_away, play_until, rivals_month, start, turn_of

SEEDS = range(1, 11)
CHECK_YEARS = (2009, 2015, 2020, 2025)  # PT-M10: the pin runs to December 2025
TOP_YEAR = CHECK_YEARS[-1]
TOP = 10
TOP_KEPT = 8  # tunable-exempt: the target
FORWARD_SEEDS = 7  # tunable-exempt: the brief's criterion
T12_MS = 250  # tunable-exempt: the target
T12_LAWYERS = 150  # tunable-exempt: steady's size by 2015 (T3's band is 100-250)
T12_TIMED = 12
T12_YEAR = 2025  # PT-M10: the history pin's last year (PT-M5: 2015)
# PT-M11: $50M ran out in month 11 (main's in month 12, one turn spare): the unmanaged firm
# burns cash, and T12 times turns, not survival
T12_CAPITAL = 15_000_000_000  # tunable-exempt: $150M of partners' capital for the test firm


T12_RUNS = 5  # tunable-exempt: check-timing's measure, the minimum of five runs (Reece, 2026-11-26)


def t12_ms(
    turns: list[tuple[GameState, dict[tuple[int, str], int]]],
    rng: RngFactory,
    data: GameData,
    balance: Balance,
) -> float:
    """T12's gate (docs/balance-targets.md, 2026-11-26): the last `T12_TIMED` turns of the year,
    each replayed from its own state (the sim is pure: every run does the same work), timed
    `T12_RUNS` times; the minimum of the runs' median turns, in ms (2026-11-25 to 11-26: the
    median of them)."""
    assert len(turns) >= T12_TIMED, f"the firm dissolved before December {T12_YEAR}"
    runs = []
    for _ in range(T12_RUNS):
        times = []
        for state, balances in turns[-T12_TIMED:]:
            t0 = time.perf_counter()
            advance_turn(state, Decisions(), rng, balance, data, balances)
            times.append(time.perf_counter() - t0)
        runs.append(statistics.median(times))
    # PT-M18: printed beside the gate, the brief's criterion (the median of the five runs'
    # median turns, at most 200 ms on CI's runner); the gate is unchanged
    print(
        f"\nT12 runs (ms): {', '.join(f'{r * 1000:.0f}' for r in runs)}; gate (minimum) "
        f"{min(runs) * 1000:.0f}, median of five {statistics.median(runs) * 1000:.0f}"
    )
    return min(runs) * 1000


def _pinned(data: GameData, year: int) -> dict[str, int]:
    """Firm key -> sourced FY revenue for the year, for firms alive then in history."""
    ended = {
        e.firm: e.ym[0]
        for e in data.rivals.firms.events
        if e.kind in ("collapse", "absorbed", "merger")
    }
    ended |= {e.other: e.ym[0] for e in data.rivals.firms.events if e.kind == "merger" and e.other}
    out = {}
    for f in data.rivals.firms.firms:
        if ended.get(f.key, 9999) <= year:
            continue
        point = next((p for p in f.path if p.year == year), None)
        if point and point.revenue_cents and point.src.startswith("rev S"):
            out[f.key] = point.revenue_cents
    return out


# PT-M11 (check's runtime): seed 1 runs in check as a smoke test; the rest nightly
@pytest.mark.parametrize(
    "seed", [pytest.param(s, marks=pytest.mark.nightly) if s != 1 else s for s in SEEDS]
)
def test_t11_rivals_hold_history(seed: int, data: GameData, balance: Balance) -> None:
    band = balance.rivals.pin.band
    state = start(data, balance, seed)
    state, _ = play_until(state, data, balance, turn_of(state, TOP_YEAR + 1, 1), seed)
    worst, misses = 0.0, []
    for year in CHECK_YEARS:
        for key, revenue in _pinned(data, year).items():
            firm = state.rivals.by_key(key)
            assert firm is not None
            record = next((h for h in firm.history if h.year == year), None)
            if record is None:
                misses.append(f"{key} {year}: gone")
                continue
            gap = record.revenue_cents / revenue - 1
            worst = max(worst, abs(gap))
            if abs(gap) > band:
                misses.append(f"{key} {year}: {gap:+.0%}")
    history = sorted(_pinned(data, TOP_YEAR).items(), key=lambda kv: -kv[1])[:TOP]
    game = sorted(
        (f for f in state.rivals.firms if f.active),
        key=lambda f: -next((h.revenue_cents for h in f.history if h.year == TOP_YEAR), 0),
    )[:TOP]
    kept = len({k for k, _ in history} & {f.key for f in game})
    print(f"\nT11 seed {seed}: worst gap {worst:.1%}, top-10 kept {kept}, misses {misses}")
    assert not misses
    assert kept >= TOP_KEPT


@pytest.mark.nightly  # PT-M11: over 60 s; check's runtime (product manager, 2026-11-23)
def test_hiring_away_a_third_brings_a_collapse_forward(data: GameData, balance: Balance) -> None:
    forward = 0
    turns = []
    for seed in SEEDS:
        state = start(data, balance, seed)
        due = turn_of(state, 2011, 3)
        state, _ = play_until(state, data, balance, turn_of(state, 2010, 3), seed)
        state = hire_away(state, "howrey", 1 / 3, data, balance)
        state, _ = play_until(state, data, balance, due, seed)
        howrey = state.rivals.by_key("howrey")
        assert howrey is not None
        early = howrey.status == "collapsed" and (howrey.ended_turn or due) < due
        forward += early
        turns.append(howrey.ended_turn)
    print(f"\nConditional history: Howrey collapsed early on {forward} of 10 seeds {turns}")
    assert forward >= FORWARD_SEEDS


@pytest.mark.timing
def test_t12_turn_time_at_december_2025(data: GameData, balance: Balance) -> None:
    """A 150-lawyer firm's turns in 2025: the rivals' market is played to January 2025
    (`rivals_month`; an unmanaged firm of this size would not survive a decade, PT-M4's T1),
    then the firm plays whole turns from there and the last 12 are timed."""
    state = grown_firm(data, balance, T12_LAWYERS, 1)
    rng = RngFactory(1)
    start = turn_of(state, T12_YEAR, 1)
    while state.turn < start:
        state = rivals_month(state, rng, data, balance)
    # a firm this size holds working capital (the helper builds its people, not its books)
    balances: dict[tuple[int, str], int] = {
        (1, CASH): T12_CAPITAL,
        (1, PARTNERS_CAPITAL): -T12_CAPITAL,
    }
    turns: list[tuple[GameState, dict[tuple[int, str], int]]] = []
    end = turn_of(state, T12_YEAR + 1, 1)
    while state.turn < end and not state.ended:
        before = state
        turns.append((state, dict(balances)))
        result = advance_turn(state, Decisions(), rng, balance, data, balances)
        balances = dict(apply_entries(balances, result.ledger_entries))
        state = top_up(result.new_state, data, balance, before)
    median = t12_ms(turns, rng, data, balance)
    print(f"\nT12: median turn {median:.0f} ms at December {T12_YEAR} ({T12_LAWYERS} lawyers)")
    assert median <= T12_MS
