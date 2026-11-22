"""PT-M10 sub-tasks 3-4: the seeded world after history (ptk.sim.macro_seed) and the layoff
action (sub-task 0's pyramid rule)."""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from ptk.loader import load_balance, load_game_data
from ptk.sim.data_models import Balance, GameData
from ptk.sim.hiring.actions import LayOff
from ptk.sim.macro import level, market_rise
from ptk.sim.macro_data import SERIES
from ptk.sim.macro_seed import fit_series, recessions, world_data
from ptk.sim.rng import RngFactory
from tests.conftest import DATA_DIR

MONTHS = [(y, m) for y in range(2005, 2035) for m in range(1, 13)]


def test_every_index_has_a_value_every_month_2005_to_2034(data: GameData, balance: Balance) -> None:
    world = world_data(data, balance, 7)
    for series in SERIES:
        values = [level(world.macro, series, ym) for ym in MONTHS]
        assert all(v > 0 for v in values), series
    # the seeded months are points of their own (not a held last value)
    seeded = [p.ym for p in world.macro.points if p.ym >= (2026, 1)]
    assert seeded[0] == (2026, 1) and seeded[-1] == (2034, 12) and len(seeded) == 108


def test_history_is_pinned_to_december_2025_and_seeds_diverge_after(
    data: GameData, balance: Balance
) -> None:
    a, b = world_data(data, balance, 1), world_data(data, balance, 2)
    for series in SERIES:
        for ym in MONTHS:
            hist = level(data.macro, series, ym)
            if ym <= (2025, 12):
                assert level(a.macro, series, ym) == hist == level(b.macro, series, ym)
    after = [(s, ym) for s in SERIES for ym in MONTHS if ym >= (2026, 1)]
    assert sum(level(a.macro, s, ym) != level(b.macro, s, ym) for s, ym in after) > len(after) // 2
    assert all(
        market_rise(y, a, balance) == market_rise(y, data, balance) for y in range(2006, 2026)
    )
    assert any(market_rise(y, a, balance) != market_rise(y, b, balance) for y in range(2026, 2035))


def test_the_same_seed_gives_the_same_world(data: GameData, balance: Balance) -> None:
    from ptk.sim import macro_seed

    first = world_data(data, balance, 11)
    macro_seed._WORLDS.clear()  # a fresh draw, not the memo
    again = world_data(data, balance, 11)
    assert first is not again
    assert first.macro == again.macro and first.salary_scale == again.salary_scale
    assert world_data(first, balance, 12) is first  # a world is never re-seeded


def test_fits_are_stable_and_recessions_follow_history(data: GameData, balance: Balance) -> None:
    cfg = balance.macro.seeded
    assert cfg is not None
    for series in SERIES:
        fit = fit_series(data.macro, series, cfg)
        assert 0.0 <= fit.phi < 1.0 and fit.sigma >= 0.0
        assert len(fit.falls) == len(cfg.episodes)
    assert fit_series(data.macro, "ma", cfg).falls[0] < 0  # deals fell in 2008-2009
    # history's frequency: 2 recessions in 21 years; over 200 seeds of 9 years about 0.86 each
    counts = [len(recessions(RngFactory(s), cfg)) for s in range(200)]
    assert 0.5 < sum(counts) / len(counts) < 1.2
    starts = [r.start for s in range(50) for r in recessions(RngFactory(s), cfg)]
    assert all(r >= 2026 * 12 for r in starts)


def test_the_salary_scale_never_falls_and_steps_only_when_hot(
    data: GameData, balance: Balance
) -> None:
    cfg = balance.macro.seeded
    assert cfg is not None
    stepped = 0
    for seed in range(30):
        world = world_data(data, balance, seed)
        rows = world.salary_scale.scale
        assert [r.from_ym for r in rows[: len(data.salary_scale.scale)]] == [
            r.from_ym for r in data.salary_scale.scale
        ]
        for a, b in zip(rows, rows[1:], strict=False):
            assert b.salaries[0] >= a.salaries[0]
        for row in rows[len(data.salary_scale.scale) :]:
            stepped += 1
            year = row.from_ym[0]
            assert row.from_ym == (year, cfg.scale.month)
            assert market_rise(year, world, balance) >= cfg.scale.rate_from
    assert stepped > 0  # the market does raise after 2025 on some seeds


_LOADED = (load_game_data(DATA_DIR), load_balance(DATA_DIR))


@settings(max_examples=25, deadline=None)
@given(seed=st.integers(min_value=0, max_value=2**32))
def test_seeded_values_stay_positive_and_bounded(seed: int) -> None:
    data, balance = _LOADED
    world = world_data(data, balance, seed)
    cfg = balance.macro.seeded
    assert cfg is not None
    for p in world.macro.points:
        assert all(0 < v < 20 for v in p.values.values())
    lo, hi = cfg.rate_range
    assert all(lo <= world.macro.rate_rise[y] <= hi for y in range(2026, 2035))


# --- the layoff action (sub-task 0) ---------------------------------------------------------


def test_a_layoff_pays_severance_gives_notice_and_costs_morale(
    data: GameData, balance: Balance
) -> None:
    from ptk.balance.game import start_game

    g = start_game(data, balance, 3)
    associate = next(p for p in g.lawyers() if p.level.startswith("associate"))
    other = next(
        p
        for p in g.lawyers()
        if p.id != associate.id and g.state.person_state(p.id).morale is not None
    )
    salary = g.state.employment_of(associate.id).salary_cents  # type: ignore[union-attr]
    morale = g.state.person_state(other.id).morale
    cash = g.cash
    assert g.act(LayOff(g.founder_id, associate.id))
    severance = salary // 12 * balance.pay.severance_months
    assert cash - g.cash == pytest.approx(severance, abs=balance.pay.severance_months)
    employment = g.state.employment_of(associate.id)
    assert employment is not None and employment.status == "notice"
    assert employment.end_reason == "fired"
    assert g.state.person_state(other.id).morale == pytest.approx(
        max(0.0, (morale or 0) + balance.morale.layoff_penalty)
    )
    g.turn()
    g.turn()
    assert associate.id not in g.state.staff_ids(1)


def test_a_founder_or_partner_cannot_be_laid_off(data: GameData, balance: Balance) -> None:
    from ptk.balance.game import start_game

    g = start_game(data, balance, 3)
    partners = [p for p in g.lawyers() if p.level in ("equity_partner", "income_partner")]
    assert partners
    for p in partners:
        assert not g.act(LayOff(g.founder_id, p.id))
    assert g.refused["lay_off"] == len(partners)
