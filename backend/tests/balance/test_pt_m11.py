"""PT-M11's acceptance runs (run with -s to see the printed readings).

1. T11 extended to London: every UK rival's revenue within +-15% of its sourced path in
   December 2009, 2015 and 2025 (the firms alive then in history), on seeds 1-10 (printed;
   nightly: `check`'s T11 in test_pt_m5.py checks every pinned rival, these included).
2. A firm that opens London in January 2007 with a 10-lawyer team lift (`london-lift`) reaches
   a positive office profit (its profit since opening, lease and fit-out included) within
   3 years on at least 6 of 10 seeds; one that opens with an organic start of one partner
   (`london-organic`) takes longer (both printed; nightly: twenty five-year runs).
3. T12 with two offices: the median turn of December 2025 is at most 250 ms on a firm of
   steady's size (150 lawyers) with offices in London (a team lift) and Washington (a lateral
   group), run alone (`make check-timing`).
"""

from __future__ import annotations

import statistics
import time
from concurrent.futures import ProcessPoolExecutor

import pytest

from ptk.balance.offices import OfficeRun, office_run
from ptk.sim.data_models import Balance, GameData
from ptk.sim.decisions import Decisions
from ptk.sim.geo.cities import rival_region
from ptk.sim.ledger import CASH, PARTNERS_CAPITAL, apply_entries
from ptk.sim.rng import RngFactory
from ptk.sim.turn import advance_turn
from tests.balance.test_pt_m5 import T12_CAPITAL, T12_LAWYERS, T12_MS, T12_TIMED, T12_YEAR, _pinned
from tests.geo_support import open_london
from tests.matters_support import grown_firm, top_up
from tests.rivals_support import play_until, rivals_month, start, turn_of

SEEDS = range(1, 11)
UK_YEARS = (2009, 2015, 2025)
LIFT_SEEDS = 6  # tunable-exempt: the brief's "at least 6 of 10 seeds"
WITHIN_MONTHS = 36  # tunable-exempt: "within 3 years"


@pytest.mark.nightly  # `check` runs T11 for every rival, UK rivals included (test_pt_m5.py)
@pytest.mark.parametrize("seed", SEEDS)
def test_t11_uk_rivals_hold_history(seed: int, data: GameData, balance: Balance) -> None:
    band = balance.rivals.pin.band
    uk = {f.key for f in data.rivals.firms.firms if rival_region(data, f.hq) == "uk"}
    state = start(data, balance, seed)
    state, _ = play_until(state, data, balance, turn_of(state, UK_YEARS[-1] + 1, 1), seed)
    worst, misses, checked = 0.0, [], 0
    for year in UK_YEARS:
        for key, revenue in _pinned(data, year).items():
            if key not in uk:
                continue
            firm = state.rivals.by_key(key)
            assert firm is not None
            record = next((h for h in firm.history if h.year == year), None)
            if record is None:
                misses.append(f"{key} {year}: gone")
                continue
            checked += 1
            gap = record.revenue_cents / revenue - 1
            worst = max(worst, abs(gap))
            if abs(gap) > band:
                misses.append(f"{key} {year}: {gap:+.0%}")
    print(f"\nT11 (London) seed {seed}: {checked} points, worst gap {worst:.1%}, misses {misses}")
    assert checked >= len(UK_YEARS) * 8  # tunable-exempt: most UK rivals have the three points
    assert not misses


def _run(args: tuple[int, str]) -> OfficeRun:
    from ptk.loader import load_balance, load_game_data
    from tests.conftest import DATA_DIR

    seed, how = args
    return office_run(load_game_data(DATA_DIR), load_balance(DATA_DIR), seed, how, months=60)


@pytest.mark.nightly
def test_a_london_team_lift_pays_within_three_years_and_organic_is_slower() -> None:
    jobs = [(s, h) for h in ("team_lift", "organic") for s in SEEDS]
    with ProcessPoolExecutor() as pool:
        runs = list(pool.map(_run, jobs))
    lift = [r for r in runs if r.how == "team_lift"]
    organic = [r for r in runs if r.how == "organic"]

    def show(rs: list[OfficeRun]) -> str:
        def m(v: int | None) -> str:
            return str(v) if v is not None else ">60"

        return ", ".join(f"s{r.seed}:{m(r.payback_months())}/{m(r.months_to_profit())}" for r in rs)

    print("\nLondon 2007, months to a positive office profit since opening / over 12 months:")
    print(f"team lift: {show(lift)}")
    print(f"organic start: {show(organic)}")
    paid = sum(1 for r in lift if (m := r.payback_months()) is not None and m <= WITHIN_MONTHS)
    lift_m = [r.payback_months() or 61 for r in lift]
    org_m = [r.payback_months() or 61 for r in organic]
    print(
        f"team lift: {paid} of 10 within {WITHIN_MONTHS} months "
        f"(median {statistics.median(lift_m)});"
        f" organic: median {statistics.median(org_m)} months"
    )
    assert all(r.opened for r in lift)
    assert paid >= LIFT_SEEDS
    assert statistics.median(org_m) > statistics.median(lift_m)


@pytest.mark.timing
def test_t12_turn_time_at_december_2025_with_two_offices(data: GameData, balance: Balance) -> None:
    state = grown_firm(data, balance, T12_LAWYERS, 1)
    rng = RngFactory(1)
    first = turn_of(state, T12_YEAR, 1)
    while state.turn < first:
        state = rivals_month(state, rng, data, balance)
    state = open_london(state, data, balance, partners=3, associates=9, seats=25).state
    state = open_london(
        state, data, balance, how="lateral_group", city="washington_dc", partners=2, associates=4
    ).state
    assert len(state.geo.firm_offices(1)) == 2
    balances: dict[tuple[int, str], int] = {
        (1, CASH): T12_CAPITAL,
        (1, PARTNERS_CAPITAL): -T12_CAPITAL,
    }
    times = []
    end = turn_of(state, T12_YEAR + 1, 1)
    while state.turn < end and not state.ended:
        before = state
        t0 = time.perf_counter()
        result = advance_turn(state, Decisions(), rng, balance, data, balances)
        times.append(time.perf_counter() - t0)
        balances = dict(apply_entries(balances, result.ledger_entries))
        state = top_up(result.new_state, data, balance, before)
    assert len(times) >= T12_TIMED
    median = statistics.median(times[-T12_TIMED:]) * 1000
    print(f"\nT12 (two offices): median turn {median:.0f} ms at December {T12_YEAR}")
    assert median <= T12_MS
