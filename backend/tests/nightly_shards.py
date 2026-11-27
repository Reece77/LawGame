"""The nightly's tests in parallel jobs (PT-M18 sub-task 2; loaded by tests/conftest.py).

`--nightly-shard K/N` keeps the K-th (0-based) of N shards of the selected tests. Tests are
dealt by expected duration, longest first, each to the least loaded shard (LPT), so the shards
finish together; tests that share an `xdist_group` (a shared, cached run) stay together. The
expected durations are `tests/nightly_durations.json` (seconds by node id, recorded from a
nightly run with `--nightly-durations-out`); a test not in it counts as the recorded median.
The deal depends only on the selected node ids and that file, so every job computes the same
shards and each test runs in exactly one (`tests/unit/test_nightly_shards.py`).
"""

from __future__ import annotations

import json
import statistics
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

DURATIONS = Path(__file__).resolve().parent / "nightly_durations.json"
DEFAULT_SECONDS = 60.0  # tunable-exempt: an unrecorded test's weight before any record exists


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--nightly-shard",
        default=None,
        metavar="K/N",
        help="run only the K-th (0-based) of N duration-balanced shards of the selected tests",
    )
    parser.addoption(
        "--nightly-durations-out",
        default=None,
        metavar="PATH",
        help="write each test's duration (seconds, setup + call + teardown) to PATH as JSON",
    )


def group_of(item: pytest.Item) -> str:
    marker = item.get_closest_marker("xdist_group")
    if marker is not None:
        name = marker.args[0] if marker.args else marker.kwargs.get("name", "")
        return f"group:{name}"
    return item.nodeid


def deal(
    groups: Mapping[str, Sequence[str]], durations: Mapping[str, float], n: int
) -> list[list[str]]:
    """Groups (name -> node ids) dealt over n shards by expected duration, longest first."""
    known = [s for s in durations.values() if s > 0]
    fallback = statistics.median(known) if known else DEFAULT_SECONDS
    cost = {g: sum(durations.get(i, fallback) for i in ids) for g, ids in groups.items()}
    loads = [0.0] * n
    shards: list[list[str]] = [[] for _ in range(n)]
    for g in sorted(groups, key=lambda g: (-cost[g], g)):
        k = min(range(n), key=lambda i: (loads[i], i))
        shards[k].append(g)
        loads[k] += cost[g]
    return shards


def load_durations(path: Path = DURATIONS) -> dict[str, float]:
    if not path.exists():
        return {}
    raw = json.loads(path.read_text())
    return {str(k): float(v) for k, v in raw.items()}


@pytest.hookimpl(trylast=True)  # after -m and -k have deselected
def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    option = config.getoption("--nightly-shard")
    if option is None:
        return
    k, n = (int(x) for x in str(option).split("/"))
    if not 0 <= k < n:
        raise pytest.UsageError(f"--nightly-shard {option}: K must be in 0..{n - 1}")
    groups: dict[str, list[str]] = {}
    for item in items:
        groups.setdefault(group_of(item), []).append(item.nodeid)
    mine = set(deal(groups, load_durations(), n)[k])
    keep = [i for i in items if group_of(i) in mine]
    drop = [i for i in items if group_of(i) not in mine]
    if drop:
        config.hook.pytest_deselected(items=drop)
    items[:] = keep


_SECONDS: dict[str, float] = {}


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    _SECONDS[report.nodeid] = _SECONDS.get(report.nodeid, 0.0) + report.duration


def pytest_sessionfinish(session: pytest.Session) -> None:
    out = session.config.getoption("--nightly-durations-out")
    if out is None or hasattr(session.config, "workerinput"):  # the xdist controller writes
        return
    path = Path(str(out))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({k: round(v, 1) for k, v in sorted(_SECONDS.items())}, indent=1))
