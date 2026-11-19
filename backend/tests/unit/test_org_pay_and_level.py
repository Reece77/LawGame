"""Raises and promotions (TST formulas.md 13.8) with ADR PT-0006's levels."""

from __future__ import annotations

from dataclasses import replace

import pytest

from ptk.sim import interfaces
from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import OrgActionError, OrgRuleError
from ptk.sim.org.actions import GiveRaise, Promote, raise_morale_change
from ptk.sim.state import GameState
from tests.org_support import act, founder, game, staff


@pytest.fixture
def payroll(monkeypatch: pytest.MonkeyPatch) -> dict[int, int]:
    """A stand-in for PT-M1b's payroll behind the pay seam: $100,000 for everyone."""
    salaries: dict[int, int] = {}

    def get(state: GameState, person_id: int) -> int | None:
        return salaries.get(person_id, 10_000_000)

    def put(state: GameState, person_id: int, salary: int) -> GameState:
        salaries[person_id] = salary
        return replace(state)

    monkeypatch.setattr(interfaces, "salary_cents", get)
    monkeypatch.setattr(interfaces, "set_salary", put)
    return salaries


def test_raise_morale_rules(balance: Balance) -> None:
    assert raise_morale_change(10_000_000, 10_500_000, None, 5, balance) == 3  # exactly 5%
    assert raise_morale_change(10_000_000, 10_499_999, None, 5, balance) == 0
    assert raise_morale_change(10_000_000, 9_999_999, None, 5, balance) == -10
    assert raise_morale_change(10_000_000, 11_000_000, 0, 11, balance) == 0  # cooling down
    assert raise_morale_change(10_000_000, 11_000_000, 0, 12, balance) == 3


def test_give_raise(data: GameData, balance: Balance, payroll: dict[int, int]) -> None:
    state = game(data, balance)
    fid, pid = founder(state), staff(state)[0].id
    state = act(state, GiveRaise(fid, pid, 11_000_000), data, balance)
    assert payroll[pid] == 11_000_000
    assert state.org.person(pid).last_raise_turn == 0
    assert [(n.points, n.reason) for n in state.org.nudges] == [(3, "raise")]
    state = act(state, GiveRaise(fid, pid, 12_000_000), data, balance)  # within 12 turns
    assert len(state.org.nudges) == 1
    state = act(state, GiveRaise(fid, pid, 9_000_000), data, balance)
    assert [(n.points, n.reason) for n in state.org.nudges][-1] == (-10, "pay cut")
    with pytest.raises(OrgActionError):
        act(state, GiveRaise(fid, pid, 9_000_000), data, balance)
    with pytest.raises(OrgActionError):
        act(state, GiveRaise(fid, pid, 0), data, balance)
    with pytest.raises(OrgRuleError):
        act(state, GiveRaise(fid, fid, 50_000_000), data, balance)


def test_raise_waits_for_payroll(data: GameData, balance: Balance) -> None:
    state = game(data, balance)
    with pytest.raises(OrgRuleError, match="payroll"):
        act(state, GiveRaise(founder(state), staff(state)[0].id, 11_000_000), data, balance)


def _person(state: GameState, level: str) -> int:
    return next(p.id for p in staff(state) if p.level == level)


def test_promotion_ladder(data: GameData, balance: Balance) -> None:
    state = game(data, balance)
    fid = founder(state)
    a3 = _person(state, "associate_3")
    state = act(state, Promote(fid, a3), data, balance)
    assert state.person(a3).level == "associate_4"
    record = state.org.person(a3)
    assert (record.accelerated_years, record.last_promoted_turn) == (1, 0)
    assert [(n.person_id, n.points, n.reason) for n in state.org.nudges] == [(a3, 5, "promoted")]
    for _ in range(4):  # 4 -> 8, each a class year ahead of September
        state = act(state, Promote(fid, a3), data, balance)
    assert state.person(a3).level == "associate_8"
    assert state.org.person(a3).accelerated_years == 5
    state = act(state, Promote(fid, a3), data, balance)
    assert state.person(a3).level == "counsel"  # not a class year: not accelerated
    assert state.org.person(a3).accelerated_years == 5
    with pytest.raises(OrgRuleError, match="partnership vote"):
        act(state, Promote(fid, a3), data, balance)


def test_who_cannot_be_promoted(data: GameData, balance: Balance) -> None:
    state = game(data, balance)
    fid = founder(state)
    partner = next(p.id for p in staff(state) if p.founding_partner)
    paralegal = _person(state, "paralegal")
    with pytest.raises(OrgRuleError, match="as far as a promotion goes"):
        act(state, Promote(fid, partner), data, balance)
    with pytest.raises(OrgRuleError, match="as far as a promotion goes"):
        act(state, Promote(fid, paralegal), data, balance)
    with pytest.raises(OrgRuleError, match="managing founding partner"):
        act(state, Promote(fid, fid), data, balance)


def test_promote_to_never_reaches_partnership(balance: Balance) -> None:
    assert not {"income_partner", "equity_partner"} & set(balance.org.promote_to.values())
    assert balance.org.promote_to["staff"] == "manager"
    assert "director" not in balance.org.promote_to  # chief is not reachable (TST: no exec)
