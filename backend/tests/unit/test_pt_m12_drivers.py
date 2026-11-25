"""PT-M12 sub-task 3: the v2 practices' demand drivers move as the dossier says (seeds 1-10).

Each practice's New York demand (spec 6: D0 x G x (1 + beta (I - 1)) x eps, stream `demand`)
summed over 12 months: 2009 against 2008 falls for the pro-cyclical new practices and rises for
the counter-cyclical ones (docs/research/practices-v2.md s4), and Dodd-Frank (21 July 2010), the
2017 tax reform (22 December 2017) and GDPR (25 May 2018) show in their practices' demand
within a year. Medians over seeds 1-10 (the brief); every seed is printed.
"""

from __future__ import annotations

import statistics
from types import SimpleNamespace
from typing import Any

import pytest

from ptk.loader import load_balance, load_game_data
from ptk.sim.calendar import ym_to_turn
from ptk.sim.matters.market import monthly_demand
from ptk.sim.rng import RngFactory
from tests.pt_m12_support import DATA

START = (2005, 1)
SEEDS = range(1, 11)
PRO_CYCLICAL = ("tax", "antitrust", "energy", "technology_privacy", "private_client")
COUNTER_CYCLICAL = ("international_arbitration", "financial_regulation", "insurance")
# (practice, the first month after the event): the year after against the year before
EVENTS = (
    ("financial_regulation", (2010, 8), "Dodd-Frank"),
    ("tax", (2018, 1), "the TCJA"),
    ("technology_privacy", (2018, 6), "GDPR"),
)
EVENT_RISE = 0.10  # at least +10% in the year after (each index rises 20-30%: v2 s4)


@pytest.fixture(scope="module")
def world() -> tuple[Any, Any]:
    return load_game_data(DATA), load_balance(DATA)


def _demand(world: tuple[Any, Any], seed: int, practice: str, first: tuple[int, int]) -> int:
    """Twelve months of the practice's demand from `first`."""
    data, balance = world
    state: Any = SimpleNamespace(save_meta=SimpleNamespace(start_ym=START))
    index = data.practice_keys.index(practice)
    rng = RngFactory(seed)
    t0 = ym_to_turn(*first, START)
    return sum(monthly_demand(rng, t, state, data, balance)[index] for t in range(t0, t0 + 12))


def _ratio(
    world: tuple[Any, Any], practice: str, after: tuple[int, int], before: tuple[int, int]
) -> float:
    ratios = [
        _demand(world, s, practice, after) / _demand(world, s, practice, before) for s in SEEDS
    ]
    print(practice, after, [f"{r - 1:+.1%}" for r in ratios])
    return statistics.median(ratios)


@pytest.mark.parametrize("practice", PRO_CYCLICAL)
def test_pro_cyclical_practices_fall_in_2009(world: tuple[Any, Any], practice: str) -> None:
    assert _ratio(world, practice, (2009, 1), (2008, 1)) < 1.0


@pytest.mark.parametrize("practice", COUNTER_CYCLICAL)
def test_counter_cyclical_practices_rise_in_2009(world: tuple[Any, Any], practice: str) -> None:
    assert _ratio(world, practice, (2009, 1), (2008, 1)) > 1.0


@pytest.mark.parametrize(("practice", "first", "event"), EVENTS)
def test_policy_events_show_within_a_year(
    world: tuple[Any, Any], practice: str, first: tuple[int, int], event: str
) -> None:
    before = (first[0] - 1, first[1])
    assert _ratio(world, practice, first, before) >= 1.0 + EVENT_RISE, event
