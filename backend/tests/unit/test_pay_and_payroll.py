"""PT-M1b sub-tasks 3-4: the salary scale, bonuses and payroll (spec 5.4, 8.3; TST 8)."""

from __future__ import annotations

from dataclasses import replace

import pytest
from simcore.kernel.calendar import turn_to_ym

from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import InvalidActionError
from ptk.sim.hiring.actions import SetPayPolicy
from ptk.sim.hiring.formulas import benefits_cents, monthly_salary_cents
from ptk.sim.hiring.models import PayPolicy
from ptk.sim.hiring.pay import (
    band_cents,
    class_index,
    firm_scale_cents,
    market_bonus_cents,
    market_scale_cents,
    prorated,
)
from ptk.sim.hiring.phases import apply_scale, monthly_cost_lines
from tests.hiring_helpers import start


def test_scale_history(data: GameData) -> None:
    """Spec 5.4: $125,000 for a first-year in 2005, $160,000 from 2007; PT-M10: history to 2025
    ($225,000 from 2024), held in the unseeded data after it (a save's world seeds 2026 on)."""
    assert market_scale_cents(data, (2005, 6), "associate_1") == 12_500_000
    assert market_scale_cents(data, (2007, 1), "associate_1") == 16_000_000
    assert market_scale_cents(data, (2015, 12), "associate_1") == 16_000_000
    assert market_scale_cents(data, (2021, 7), "associate_1") == 20_500_000  # Davis Polk's step
    assert market_scale_cents(data, (2030, 1), "associate_1") == 22_500_000
    assert class_index("senior_associate") == 7
    assert market_scale_cents(data, (2007, 1), "senior_associate") == market_scale_cents(
        data, (2007, 1), "associate_8"
    )
    assert data.salary_scale.market_bonuses(2008)[0] < data.salary_scale.market_bonuses(2007)[0]
    # a year without a row pays the latest row's (PT-M10: 2013 repeated 2012's, research s4d)
    assert data.salary_scale.market_bonuses(2013) == data.salary_scale.market_bonuses(2012)


def test_policy_lags_and_leads(data: GameData) -> None:
    ym = (2005, 1)
    assert firm_scale_cents(data, ym, "associate_1", PayPolicy.of("lag", 8000)) == 10_000_000
    assert firm_scale_cents(data, ym, "associate_1", PayPolicy.of("lead", 11000)) == 13_750_000
    assert firm_scale_cents(data, ym, "associate_1", PayPolicy.of("match", 5000)) == 12_500_000


def test_bands_by_city(data: GameData, balance: Balance) -> None:
    assert band_cents(data, balance, "counsel", "new_york") == 26_000_000
    assert band_cents(data, balance, "counsel", "chicago") == 22_100_000
    assert band_cents(data, balance, "paralegal", "nowhere") == 6_000_000


def test_starting_staff_on_the_scale(data: GameData, balance: Balance) -> None:
    game = start(data, balance)
    for e in game.state.employments:
        person = game.state.person(e.person_id)
        if person.founding_partner:
            assert e.salary_cents == 0  # equity partners take profit, not salary
        else:
            assert e.salary_cents == market_scale_cents(data, (2005, 1), person.level)


def test_pay_policy_action(data: GameData, balance: Balance) -> None:
    game = start(data, balance)
    with pytest.raises(InvalidActionError):
        game.act(SetPayPolicy(game.founder_id, "lag", 10_500))
    with pytest.raises(InvalidActionError):
        game.act(SetPayPolicy(game.founder_id, "lead", 9_000))
    game.act(SetPayPolicy(game.founder_id, "lead", 11_000))
    assert game.state.player.pay_policy == PayPolicy("lead", 11_000)
    game.advance()  # phase 9 raises associates to the firm's scale
    for e in game.state.staff(1):
        level = game.state.person(e.person_id).level
        if class_index(level) is not None:
            assert e.salary_cents == market_scale_cents(data, (2005, 1), level) * 11 // 10


def test_scale_never_cuts(data: GameData, balance: Balance) -> None:
    game = start(data, balance)
    state = game.state
    high = tuple(
        replace(e, salary_cents=e.salary_cents * 2) if e.salary_cents else e
        for e in state.employments
    )
    state = apply_scale(replace(state, employments=high), data)
    assert [e.salary_cents for e in state.employments] == [e.salary_cents for e in high]


def test_payroll_lines_and_accounts(data: GameData, balance: Balance) -> None:
    """A month's costs: 5000 salaries, 5200 benefits at 25%, 6000 rent per head."""
    game = start(data, balance)
    lines = {c.label: c for c in monthly_cost_lines(game.state, 1, balance, data)}
    salaries = [e.salary_cents for e in game.state.staff(1) if e.salary_cents]
    monthly = sum(monthly_salary_cents(s) for s in salaries)
    assert lines["Associate and counsel salaries"].account == "5000_associate_salaries"
    assert lines["Associate and counsel salaries"].amount == monthly
    assert lines["Benefits"].amount == sum(
        benefits_cents(monthly_salary_cents(s), balance.pay) for s in salaries
    )
    heads = len(game.state.staff(1))
    assert lines["Rent"].account == "6000_rent"
    assert lines["Rent"].amount == heads * balance.pay.rent_per_head_cents
    n = len(game.entries)
    game.advance()
    entry = next(e for e in game.entries[n:] if e.memo.startswith("Monthly costs"))
    assert sum(ln.amount for ln in entry.lines) == 0
    assert entry.lines[-1].account == "1000_cash"
    assert -entry.lines[-1].amount == sum(c.amount for c in lines.values())


def test_solo_scenario_pays_a_paralegal_as_staff(data: GameData, balance: Balance) -> None:
    game = start(data, balance, scenario="solo_founder")
    lines = {c.label: c for c in monthly_cost_lines(game.state, 1, balance, data)}
    assert lines["Staff salaries"].account == "5100_staff_salaries"
    assert lines["Staff salaries"].amount == monthly_salary_cents(6_000_000)
    assert lines["Associate and counsel salaries"].amount == 0


def test_bonuses_post_in_december_only(data: GameData, balance: Balance) -> None:
    """Brief: bonuses post in December, to 5010, by class year (ledger test)."""
    game = start(data, balance, seed=3)
    game.state = replace(
        game.state, employments=tuple(e for e in game.state.employments if e.status == "active")
    )
    staff_before = {e.person_id: game.state.person(e.person_id).level for e in game.state.staff(1)}
    for _ in range(14):
        n = len(game.entries)
        month = turn_to_ym(game.state.turn, game.state.save_meta.start_ym)[1]
        game.advance()
        bonuses = [
            e for e in game.entries[n:] if any(ln.account == "5010_bonuses" for ln in e.lines)
        ]
        if month != 12:
            assert not bonuses
            continue
        assert len(bonuses) == 1
        entry = bonuses[0]
        assert {ln.account for ln in entry.lines} == {"5010_bonuses", "1000_cash"}
        expected = 0
        for pid in staff_before:
            e = next(x for x in game.state.employments if x.person_id == pid)
            if e.status == "active" and e.salary_cents:
                level = game.state.person(pid).level
                expected += market_bonus_cents(data, balance, level, 2005, e.salary_cents)
        assert entry.lines[0].amount == expected
    assert any(i.kind == "bonuses_paid" for i in game.log)


def test_part_year_bonus_is_prorated() -> None:
    assert prorated(1_200_000, 4, 12) == 400_000
    assert prorated(1_200_000, 12, 12) == 1_200_000
    assert prorated(1_000_000, 1, 12) == 83_333
