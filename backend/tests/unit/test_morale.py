"""PT-M1b sub-task 5: morale and resignations (TST formulas.md 9-10; spec 5.3)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from ptk.sim.data_models import Balance, GameData
from ptk.sim.hiring.formulas import (
    bonus_fairness_shock,
    hours_term,
    morale_step,
    pay_term,
    prospects_term,
    resignation_bp,
)
from ptk.sim.hiring.phases import month_multiplier, morale_and_departures
from ptk.sim.people.models import WorkMonth
from ptk.sim.rng import RngFactory
from tests.hiring_helpers import Game, start


def test_tst_resignation_table(balance: Balance) -> None:
    """TST 10's table, with its original base 50 bp and floor 40."""
    tst = balance.resign.model_copy(update={"base_bp": 50, "morale_floor": 40})
    assert resignation_bp(70, 12, tst) == pytest.approx(45)
    assert resignation_bp(25, 6, tst) == pytest.approx(131.25)
    assert resignation_bp(25, 6, tst, job_hopper=True) == pytest.approx(262.5)


def test_resignation_terms(balance: Balance) -> None:
    r = balance.resign
    base = resignation_bp(60, 10, r)
    assert resignation_bp(60, 10, r, burnout=True) == pytest.approx(2 * base)
    assert resignation_bp(60, 10, r, lifer=True) == pytest.approx(base * 7 / 11)
    assert resignation_bp(0, 1, r, job_hopper=True, burnout=True, month_mult=2) == r.cap_bp


def test_bonus_timing(balance: Balance) -> None:
    """Associates leave after bonuses (January), wait for them (Oct-Dec); income partners
    leave after the April true-up (spec 5.3)."""
    assert month_multiplier("associate_3", 1, balance) > 1
    assert month_multiplier("associate_3", 11, balance) < 1
    assert month_multiplier("associate_3", 6, balance) == 1
    assert month_multiplier("income_partner", 4, balance) > 1
    assert month_multiplier("income_partner", 1, balance) < 1


def test_hours_term(balance: Balance) -> None:
    """W_hours = -10 x max(0, h/target - 1.1); -5 below 0.6; none without hours recorded."""
    m = balance.morale
    assert hours_term(None, m) == 0
    assert hours_term(1.0, m) == 0
    assert hours_term(1.3, m) == pytest.approx(-2.0)
    assert hours_term(0.5, m) == -5


def test_pay_prospects_and_bonus_terms(balance: Balance) -> None:
    m = balance.morale
    assert pay_term(12_500_000, 12_500_000, m) == 0
    assert pay_term(7_500_000, 12_500_000, m) == m.pay_min  # a regional firm at 60%: -20
    assert pay_term(13_750_000, 12_500_000, m) == pytest.approx(6.0)
    assert pay_term(0, 0, m) == 0  # equity partners have no market salary
    assert prospects_term("associate_7", False, m) == m.prospects_no_sponsor
    assert prospects_term("associate_7", True, m) == m.prospects_sponsor
    assert prospects_term("associate_3", False, m) == 0
    assert bonus_fairness_shock(1_000_000, 2_000_000, m) == m.bonus_min
    assert bonus_fairness_shock(2_000_000, 2_000_000, m) == 0
    assert morale_step(65, 51.67, 0, m) == pytest.approx(65 + 0.3 * (51.67 - 65))


def test_tst_worked_example(balance: Balance) -> None:
    """TST 9: target 51.67 from 65 reaches 53.2 after six months (noise off)."""
    m = balance.morale
    morale = 65.0
    for _ in range(6):
        morale = morale_step(morale, 51.67, 0.0, m)
    assert morale == pytest.approx(53.2, abs=0.05)


def test_morale_follows_pay_and_hours(data: GameData, balance: Balance) -> None:
    game = start(data, balance, seed=4)
    state = game.state
    pid = next(e.person_id for e in state.staff(1) if e.salary_cents)
    underpaid = tuple(
        replace(e, salary_cents=e.salary_cents // 2) if e.person_id == pid else e
        for e in state.employments
    )
    rng = RngFactory(4)
    fair, _ = morale_and_departures(state, rng, balance, data, {})
    low, _ = morale_and_departures(replace(state, employments=underpaid), rng, balance, data, {})
    assert low.person_state(pid).morale < fair.person_state(pid).morale  # type: ignore[operator]
    grind = {pid: WorkMonth(pid, practice_tenths=(("corporate_ma", 2600),))}  # 3,120 h a year
    tired, _ = morale_and_departures(state, rng, balance, data, grind)
    assert tired.person_state(pid).morale < fair.person_state(pid).morale  # type: ignore[operator]


@pytest.mark.nightly  # PT-M11: over 60 s; check's runtime (product manager, 2026-11-23)
def test_resignations_are_seeded_and_give_notice(data: GameData, balance: Balance) -> None:
    def played(seed: int) -> Game:
        """60 unmanaged months, or until the firm dissolves (PT-M12: an unmanaged firm may not
        last five years: T1's do-nothing; seed 0 dissolves in month 55)."""
        game = start(data, balance, seed=seed)
        for _ in range(60):
            if game.state.ended:
                break
            game.advance(1)
        return game

    def leavers(seed: int) -> list[tuple[int, int]]:
        game = played(seed)
        return [
            (e.person_id, e.end_turn or 0) for e in game.state.employments if e.status != "active"
        ]

    assert leavers(5) == leavers(5)
    found = False
    for seed in range(6):
        game = played(seed)
        for e in game.state.employments:
            if e.end_reason == "resigned":
                found = True
                assert e.status == "ended"
                # PT-M7a: biglaw_spinout's fourth-year now meets up or out in December 2008
                # and moves on (recorded as resigned, with PT-M4's notices)
                assert any(
                    i.kind in ("resigned", "moved_on") and i.link_id == e.person_id
                    for i in game.log
                )
                assert any(i.kind == "employee_left" for i in game.log)
    assert found


def test_founding_partners_never_resign(data: GameData, balance: Balance) -> None:
    game = start(data, balance, seed=1)
    game.advance(120)
    for e in game.state.employments:
        if game.state.person(e.person_id).founding_partner:
            assert e.status == "active"
            assert game.state.person_state(e.person_id).morale is None
