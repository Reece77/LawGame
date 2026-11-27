"""PT-M8's printed acceptance runs (run with -s; nightly in CI).

1. Strong practice group leaders (seat score 16) against weak ones (6), every group's leader
   set alike: the groups' associates' morale and the groups' utilisation (pooled), averaged
   over 24 months, on seeds 1-40 (PT-M18). The brief asks at least 5 morale points and 3 utilisation
   points better (the median gap). Every group, not one, because a group already at capacity
   cannot show the diary effect and choosing the slack one would pick the answer.
2. A 100-lawyer firm with every seat filled and given authority: pitches a quarter over a
   year on seeds 1-40; the median is in 2-6, and no holder pitches twice in a quarter.

Both run the stage-3 led firm of `tests.seats_support` with resignations and partner flight
off, so the arms keep the same people (the grown fixture sheds a fifth of its people a year,
on main as here).
"""

from __future__ import annotations

import statistics
from concurrent.futures import ProcessPoolExecutor

import pytest

from ptk.balance.seeds import SEEDS as BALANCE_SEEDS
from ptk.sim.data_models import Balance, GameData
from ptk.sim.org.authority import _members
from ptk.sim.org.seat_models import PGL
from ptk.sim.state import GameState
from tests.seats_support import led_firm, run, steady, with_score

SEEDS = BALANCE_SEEDS  # PT-M18: seeds 1-40 (CLAUDE.md 12.1), each seed in a worker
MONTHS = 24
STRONG, WEAK = 16.0, 6.0  # tunable-exempt: the brief's seat scores
MORALE_GAP, UTIL_GAP = 5.0, 3.0  # tunable-exempt: the brief's gaps (points)
PITCHES = (2, 6)  # tunable-exempt: the brief's band, a quarter


def _groups(state: GameState) -> list[int]:
    return [
        u.id
        for u in state.org.firm_units(state.player.id)
        if u.kind == "practice_group" and u.leader_id is not None
    ]


def _arm(base: GameState, score: float, data: GameData, b: Balance) -> tuple[float, float]:
    """Every practice group leader at `score`; the groups' associates' mean morale and the
    groups' utilisation (hours over capacity, pooled), averaged over the months."""
    state = base
    units = _groups(base)
    for unit in units:
        leader = base.org.unit(unit).leader_id  # type: ignore[union-attr]
        assert leader is not None
        state = with_score(state, data, leader, PGL, score)
    morale: list[float] = []
    util: list[float] = []
    balances = None
    for _ in range(MONTHS):
        state, _, balances = run(state, data, b, 1, balances)
        people = tuple(p for u in units for p in _members(state, u))
        assoc = [p for p in people if state.person(p).level.startswith("associate")]
        values = [m for p in assoc if (m := state.person_state(p).morale) is not None]
        if values:
            morale.append(sum(values) / len(values))
        capacity = _capacity(state, people, data, b)
        wanted = set(people)
        hours = sum(r.tenths for r in state.market.hours if r.person_id in wanted)
        if capacity:
            util.append(100 * hours / capacity)
    return statistics.fmean(morale), statistics.fmean(util)


def _loaded() -> tuple[GameData, Balance]:
    from ptk.loader import load_balance, load_game_data
    from tests.conftest import DATA_DIR

    return load_game_data(DATA_DIR), load_balance(DATA_DIR)


def _leader_arms(seed: int) -> tuple[tuple[float, float], tuple[float, float]]:
    """One seed (a worker process): the strong and the weak arm."""
    data, balance = _loaded()
    b = steady(balance)
    base = led_firm(data, b, seed)
    return _arm(base, STRONG, data, b), _arm(base, WEAK, data, b)


def _pitches(seed: int) -> tuple[list[int], bool]:
    """One seed (a worker process): pitches by quarter, and whether a holder pitched twice in a
    quarter."""
    data, balance = _loaded()
    b = steady(balance)
    state = led_firm(data, b, seed, lawyers=100)
    after, _, _ = run(state, data, b, 12)
    counts = [0, 0, 0, 0]
    seen: set[tuple[int, int]] = set()
    twice = False
    for p in after.leadership.pitches:
        q = p.made_turn // 3
        twice = twice or (p.person_id, q) in seen
        seen.add((p.person_id, q))
        counts[q] += 1
    return counts, twice


def _capacity(state: GameState, people: tuple[int, ...], data: GameData, b: Balance) -> int:
    from ptk.sim.matters.staffing import fee_earners

    wanted = set(people)
    return sum(f.capacity for f in fee_earners(state, state.player.id, data, b) if f.id in wanted)


@pytest.mark.nightly
@pytest.mark.xfail(
    strict=True,
    reason="PT-M18: seed variance (the product manager's decision on PR #22, 2026-11-22). "
    "The utilisation gap reads 2.83 on seeds 1-10 on PT-M16 (needs 3.0); on seeds 11-40 "
    "main 2.61, PT-M16 2.58 (morale 7.29 and 7.31): below 3.0 on both, within 0.5 of main",
)
def test_a_strong_group_leader_lifts_morale_and_utilisation(
    data: GameData, balance: Balance
) -> None:
    with ProcessPoolExecutor() as pool:
        arms = list(pool.map(_leader_arms, SEEDS))
    gaps: list[tuple[float, float]] = []
    for seed, (strong, weak) in zip(SEEDS, arms, strict=True):
        gaps.append((strong[0] - weak[0], strong[1] - weak[1]))
        print(
            f"seed {seed}: morale {strong[0]:.1f} vs {weak[0]:.1f}, "
            f"utilisation {strong[1]:.1f}% vs {weak[1]:.1f}%"
        )
    morale_gap = statistics.median(g[0] for g in gaps)
    util_gap = statistics.median(g[1] for g in gaps)
    print(f"median gaps: morale {morale_gap:.1f} points, utilisation {util_gap:.1f} points")
    assert morale_gap >= MORALE_GAP
    assert util_gap >= UTIL_GAP


@pytest.mark.nightly
def test_a_100_lawyer_firm_sees_two_to_six_pitches_a_quarter(
    data: GameData, balance: Balance
) -> None:
    with ProcessPoolExecutor() as pool:
        seeded = list(pool.map(_pitches, SEEDS))
    per_quarter: list[int] = []
    for seed, (counts, twice) in zip(SEEDS, seeded, strict=True):
        assert not twice  # at most one a quarter per holder
        per_quarter += counts
        print(f"seed {seed}: pitches by quarter {counts}")
    median = statistics.median(per_quarter)
    print(f"median pitches a quarter: {median}")
    assert PITCHES[0] <= median <= PITCHES[1]
