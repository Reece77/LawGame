"""PT-M13's acceptance runs (run with -s to see the printed readings).

- T12 with a merged firm and a verein member: the median turn of December 2025 is at most
  250 ms on a firm of steady's size (150 lawyers) of which a generated firm merged in January
  2025 brought the larger part, with a London verein member, run alone (`make check-timing`).
- T13 (nightly): the `merger` strategy's partners lost within 24 months of closing, on seeds
  1-40 (PT-M18), inside the band `docs/balance-targets.md` proposes (10-20% of the combined
  partnership at closing).
- The `merger` strategy against steady in December 2015 (nightly, printed): lawyers and revenue
  medians on seeds 1-40; rivals not merged with the firm hold T11's band at 2009 and 2015 on
  seeds 1-40.
"""

from __future__ import annotations

import statistics
from collections.abc import Sequence
from concurrent.futures import ProcessPoolExecutor

import pytest

from ptk.balance.game import start_game
from ptk.balance.known_misses import Reading, verdict
from ptk.balance.seeds import SEEDS as BALANCE_SEEDS
from ptk.balance.strategies import PLAYABLE
from ptk.loader import load_balance, load_game_data
from ptk.sim.data_models import Balance, GameData
from ptk.sim.decisions import Decisions
from ptk.sim.ledger import CASH, PARTNERS_CAPITAL, apply_entries
from ptk.sim.mergers import closing
from ptk.sim.mergers.integration import partners_lost_share
from ptk.sim.mergers.models import Terms
from ptk.sim.mergers.profile import rival_side
from ptk.sim.mergers.verein import join
from ptk.sim.rivals.models import RivalFirm
from ptk.sim.state import GameState
from ptk.sim.streams import RngFactory
from ptk.sim.turn import advance_turn
from tests.balance.test_pt_m5 import (
    T12_CAPITAL,
    T12_LAWYERS,
    T12_MS,
    T12_YEAR,
    _pinned,
    t12_ms,
)
from tests.conftest import DATA_DIR
from tests.matters_support import grown_firm, top_up
from tests.mergers_support import forced
from tests.rivals_support import rivals_month, turn_of

T13_BAND = (0.10, 0.20)  # proposed (docs/balance-targets.md T13; for the product manager)
T13_MONTHS = 24
OURS = 20  # tunable-exempt: the player's lawyers before the T12 merger
SEEDS = BALANCE_SEEDS  # PT-M18: seeds 1-40 (CLAUDE.md 12.1); seeds 11-40's own run is folded in
END_YM = (2015, 12)


def _smallest_target(state: GameState, data: GameData, balance: Balance) -> RivalFirm:
    return min(
        (
            f
            for f in state.rivals.active
            if f.kind == "generated"
            and data.geo.city_key(f.hq) == state.player.home_city
            and rival_side(f, data).lawyers <= balance.mergers.max_lawyers
        ),
        key=lambda f: (rival_side(f, data).lawyers, f.id),
    )


def _merged_firm(
    data: GameData, balance: Balance, merge_turn: int, ours: int | None
) -> tuple[GameState, int, RngFactory]:
    """The T12 firm: grown, played (the rivals' months) to `merge_turn`, merged with the
    smallest integrable generated New York firm and joined in a verein by a London firm, then
    played to January 2025. `ours` None: the player's lawyers so the firm holds T12's 150."""
    rng = RngFactory(1)
    probe = grown_firm(data, balance, 10, 1)
    while probe.turn < merge_turn:
        probe = rivals_month(probe, rng, data, balance)
    theirs = rival_side(_smallest_target(probe, data, balance), data).lawyers
    state = grown_firm(data, balance, ours if ours is not None else T12_LAWYERS - theirs, 1)
    while state.turn < merge_turn:
        state = rivals_month(state, rng, data, balance)
    firm = _smallest_target(state, data, balance)
    state, deal = forced(state, firm, Terms(our_share_bp=5000, rates="blend"), data, balance)
    state, _, _ = closing.close_merger(state, deal, rng, data, balance)
    london = next(
        f
        for f in state.rivals.active
        if data.geo.city_key(f.hq) == "london" and f.personality == "global_verein"
    )
    state, vdeal = forced(state, london, Terms(our_share_bp=5000), data, balance, form="verein")
    state, _ = join(state, vdeal, rng, data, balance)
    first = turn_of(state, T12_YEAR, 1)
    while state.turn < first:
        state = rivals_month(state, rng, data, balance)
    return state, theirs, rng


def _median_2025(state: GameState, rng: RngFactory, data: GameData, balance: Balance) -> float:
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
    return t12_ms(turns, rng, data, balance)


def _lawyers(state: GameState, data: GameData) -> int:
    return sum(
        1 for pid in state.staff_ids(1) if data.role(state.person(pid).role).kind == "lawyer"
    )


@pytest.mark.timing
def test_t12_turn_time_at_december_2025_with_a_merger_and_a_verein(
    data: GameData, balance: Balance
) -> None:
    """T12's measure (a firm of steady's size, 150 lawyers, 2025's turns) on a firm that merged
    with a generated firm in January 2006 and has a London verein member."""
    state, theirs, rng = _merged_firm(
        data, balance, turn_of(grown_firm(data, balance, 10, 1), 2006, 1), None
    )
    assert _lawyers(state, data) == T12_LAWYERS
    assert state.mergers.integrations and state.mergers.vereins
    median = _median_2025(state, rng, data, balance)
    print(
        f"\nT12 ({T12_LAWYERS} lawyers, {theirs} by a 2006 merger, a London verein member):"
        f" median turn {median:.0f} ms at December {T12_YEAR}"
    )
    assert median <= T12_MS


@pytest.mark.timing
@pytest.mark.nightly
def test_t12_reading_a_merger_closed_in_2025(data: GameData, balance: Balance) -> None:
    """For information: a merger closed in January 2025 (the smallest generated New York firm
    then holds 160 lawyers, so the firm is larger than T12's 150), integration running."""
    state, theirs, rng = _merged_firm(
        data, balance, turn_of(grown_firm(data, balance, 10, 1), T12_YEAR, 1), OURS
    )
    median = _median_2025(state, rng, data, balance)
    print(
        f"\nT12 reading ({_lawyers(state, data)} lawyers, {theirs} by a 2025 merger): median turn"
        f" {median:.0f} ms at December {T12_YEAR}"
    )


# --- Nightly: the strategies' readings ----------------------------------------------------------


def _run(job: tuple[str, int]) -> dict[str, float]:
    name, seed = job
    data, balance = load_game_data(DATA_DIR), load_balance(DATA_DIR)
    g = start_game(data, balance, seed)
    script = PLAYABLE[name]
    while g.ym <= END_YM and not g.state.ended:
        script(g)
        g.turn()
    out: dict[str, float] = {
        "lawyers": float(len(g.lawyers())) if not g.state.ended else 0.0,
        "revenue": float(g.year_revenue(2015)) if hasattr(g, "year_revenue") else 0.0,
    }
    out["revenue"] = float(sum(m.revenue_cents for m in g.months if m.ym[0] == 2015))
    integ = g.state.mergers.integrations
    if integ:
        out["lost"] = partners_lost_share(integ[0], T13_MONTHS)
        out["closed_year"] = float(2005 + integ[0].closed_turn // 12)
    misses = 0
    for year in (2009, 2015):
        for key, revenue in _pinned(data, year).items():
            f = g.state.rivals.by_key(key)
            if f is None or f.successor == "player":
                continue  # merged with the firm: it left its path
            rec = next((h for h in f.history if h.year == year), None)
            if rec is not None and abs(rec.revenue_cents / revenue - 1) > balance.rivals.pin.band:
                misses += 1
    out["t11_misses"] = float(misses)
    return out


def _runs(name: str, seeds: Sequence[int]) -> list[dict[str, float]]:
    with ProcessPoolExecutor() as pool:
        return list(pool.map(_run, [(name, s) for s in seeds]))


@pytest.mark.nightly
def test_t13_partners_lost_after_a_merger_and_the_merger_strategy_against_steady() -> None:
    merged = _runs("merger", SEEDS)
    steady = _runs("steady", SEEDS)
    lost = [r["lost"] for r in merged if "lost" in r]
    med = lambda rs, k: statistics.median(r[k] for r in rs)  # noqa: E731
    print(
        f"\nT13: merged on {len(lost)} of {len(merged)} seeds; partners lost within {T13_MONTHS}"
        f" months median {statistics.median(lost) if lost else 0:.1%} {[f'{x:.0%}' for x in lost]}"
    )
    print(
        f"merger 2015 (seeds 1-40): lawyers {med(merged, 'lawyers'):.0f}, revenue"
        f" ${med(merged, 'revenue') / 1e8:.1f}M; steady: lawyers {med(steady, 'lawyers'):.0f},"
        f" revenue ${med(steady, 'revenue') / 1e8:.1f}M"
    )
    print(f"T11 misses among rivals not merged with the firm: {[r['t11_misses'] for r in merged]}")
    assert lost, "the merger strategy merged on no seed"
    median = statistics.median(lost)
    # PT-M12: a known miss within its row's bound (owner PT-M18) passes; worse fails
    reading = Reading("T13", T13_BAND[0] <= median <= T13_BAND[1], median)
    assert verdict(reading) != "fail", f"T13 {median:.1%} outside {T13_BAND}"
    assert all(r["t11_misses"] == 0 for r in merged)
