"""PT-M18 sub-task 2: the nightly's shards (tests/nightly_shards.py) and the balance runner's
seed ranges (ptk.balance.report.seed_range): every test or seed in exactly one shard."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from ptk.balance.report import seed_range
from tests.nightly_shards import deal


@given(st.integers(1, 60), st.integers(1, 12))
def test_seed_ranges_cover_every_seed_once(count: int, n: int) -> None:
    seeds = list(range(1, count + 1))
    ranges = [seed_range(seeds, k, n) for k in range(n)]
    assert [s for r in ranges for s in r] == seeds  # contiguous, in order, each once
    sizes = [len(r) for r in ranges]
    assert max(sizes) - min(sizes) <= 1


@given(
    st.dictionaries(
        st.text("abcdef", min_size=1, max_size=4),
        st.lists(st.text("xyz", min_size=1, max_size=3), min_size=1, max_size=3, unique=True),
        min_size=1,
        max_size=30,
    ),
    st.integers(1, 8),
)
def test_deal_puts_every_group_in_one_shard(groups: dict[str, list[str]], n: int) -> None:
    durations = {i: float(len(i)) for ids in groups.values() for i in ids}
    shards = deal(groups, durations, n)
    assert sorted(g for s in shards for g in s) == sorted(groups)
    assert deal(groups, durations, n) == shards  # the same deal in every job


def test_deal_balances_by_duration() -> None:
    groups = {f"t{i}": [f"t{i}"] for i in range(6)}
    durations = {"t0": 100.0, "t1": 60.0, "t2": 50.0, "t3": 40.0, "t4": 10.0, "t5": 10.0}
    shards = deal(groups, durations, 2)
    loads = [sum(durations[g] for g in s) for s in shards]
    assert sorted(loads) == [130.0, 140.0]


def test_every_target_and_guard_reads_seeds_1_to_40() -> None:
    """PT-M18 sub-task 1 (CLAUDE.md 12.1): the runner, the nightly guards and the readings
    tools judge on seeds 1-40."""
    import importlib
    import inspect

    from ptk.balance import report
    from ptk.balance.seeds import SEEDS, at_least, at_most
    from ptk.standing_pace import run_all as pace

    assert tuple(SEEDS) == tuple(range(1, 41))
    assert inspect.signature(report.run_all).parameters["seeds"].default == SEEDS
    for name in ("test_pt_m5", "test_pt_m7a", "test_pt_m8", "test_pt_m9", "test_pt_m11",
                 "test_pt_m13", "test_pt_m15"):  # fmt: skip
        module = importlib.import_module(f"tests.balance.{name}")
        assert tuple(module.SEEDS) == SEEDS, name
    from tests.unit import test_partnership_flight as flight  # PT-M4's exodus guard

    assert tuple(flight.SEEDS) == SEEDS
    assert inspect.signature(pace).parameters["seeds"].default == SEEDS
    assert (at_least(0.9, 40), at_most(0.6, 40), at_least(0.7, 40), at_most(0.1, 40)) == (
        36,
        24,
        28,
        4,
    )
    assert (at_least(0.9, 10), at_most(0.6, 10)) == (9, 6)  # the old counts, as shares
