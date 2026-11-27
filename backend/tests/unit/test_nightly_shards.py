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
