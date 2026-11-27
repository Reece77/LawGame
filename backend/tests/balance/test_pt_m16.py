"""PT-M16's printed acceptance runs (run with -s; nightly in CI): the steady firm on seeds 1-40
(PT-M18) to December 2015 (`ptk.standing_pace`).

1. A new firm cannot bill at the top card in its first five years on any of seeds 1-40.
2. Printed: each seed's years to the market's top decile in a practice (the brief's pace:
   8-12 years for a well-run firm), and T3's lawyers and T4's steady PEP in 2015.
"""

from __future__ import annotations

import statistics

import pytest

from ptk.balance.seeds import SEEDS
from ptk.sim.money import BP_DENOMINATOR
from ptk.standing_pace import run_all

pytestmark = pytest.mark.nightly


def test_the_steady_firm_earns_its_card_and_prints_its_pace() -> None:
    rows = run_all(SEEDS)  # PT-M18: seeds 1-40
    for r in rows:
        print(
            f"seed {r.seed}: {r.game_state}; top decile after {r.years_to_top} years; "
            f"card max in five years {r.card_max_first_years} bp; lawyers 2015 {r.lawyers_2015}; "
            f"PEP 2015 {r.pep_2015}"
        )
    print("median lawyers 2015", statistics.median(r.lawyers_2015 for r in rows))
    assert all(r.card_max_first_years < BP_DENOMINATOR for r in rows)
