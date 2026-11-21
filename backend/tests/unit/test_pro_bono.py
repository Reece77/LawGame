"""PT-M7a sub-task 3: pro bono (spec 7.8). Flow and named matters with no fees, the credit
policy, morale, learning and recruiting appeal; billing never sees pro bono."""

from __future__ import annotations

from dataclasses import replace

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from ptk.loader import load_balance, load_game_data
from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import MatterActionError
from ptk.sim.hiring.formulas import acceptance_probability, offer_score
from ptk.sim.hiring.phases import hours_ratio
from ptk.sim.hiring.rules import prestige
from ptk.sim.matters import formulas as fx
from ptk.sim.matters.actions import SetProBonoCredit
from ptk.sim.matters.models import PRO_BONO_CLIENT_ID
from ptk.sim.matters.pro_bono import morale_term, recruiting_appeal
from ptk.sim.matters.staffing import credit_hours, pro_bono_pool_tenths
from ptk.sim.people.models import WorkMonth
from ptk.sim.state import with_firm
from tests.conftest import DATA_DIR
from tests.hiring_helpers import start
from tests.matters_support import game, grown_firm, play

DATA = load_game_data(DATA_DIR)
BALANCE = load_balance(DATA_DIR)


def test_the_pool_grows_with_the_credit_policy(balance: Balance) -> None:
    none = pro_bono_pool_tenths(50, 0, balance)
    default = pro_bono_pool_tenths(50, balance.pro_bono.credit_hours, balance)
    assert 0 < none < default
    # (12 + 1.0 x 50) / 12 hours a lawyer a month x 50 lawyers
    assert default == round(50 * (12 + 50) / 12 * fx.TENTHS)


def test_pro_bono_is_worked_never_billed(data: GameData, balance: Balance) -> None:
    state = grown_firm(data, balance, 30, seed=2)
    pro_bono_seen = named_seen = False
    for _ in range(18):
        state, results = play(state, data, balance, 1, seed=2)
        result = results[-1]
        pb = [r for r in state.market.hours if r.client_id == PRO_BONO_CLIENT_ID]
        pro_bono_seen = pro_bono_seen or bool(pb)
        assert all(r.value_cents == 0 and r.substantive_tenths == r.tenths for r in pb)
        # billing: no engagement, flow account or bill for the pro bono client
        b = state.billing
        assert all(e.client_id != PRO_BONO_CLIENT_ID for e in b.engagements)
        assert all(f.client_id != PRO_BONO_CLIENT_ID for f in b.flows)
        assert all(x.client_id != PRO_BONO_CLIENT_ID for x in b.bills)
        snap = result.snapshot.firms[0]
        billable = sum(r.tenths for r in state.market.hours if r.client_id != PRO_BONO_CLIENT_ID)
        month = next(m for m in b.months if m.turn == result.snapshot.turn)
        assert month.billable_tenths == billable and snap.utilisation_bp is not None
        for m in state.market.matters:
            if m.pro_bono:
                named_seen = True
                assert m.expected_fees_cents == 0 and m.wip_cents == 0
                assert state.market.relationship(m.client_id, state.player.id) is None
    assert pro_bono_seen and named_seen


@settings(max_examples=5, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(seed=st.integers(1, 10_000), credit=st.integers(0, 120))
def test_credit_never_exceeds_the_policy_in_a_year(seed: int, credit: int) -> None:
    state = game(DATA, BALANCE, seed=seed, scenario="group_lift")
    state = with_firm(state, replace(state.player, pro_bono_credit_hours=credit))
    credited: dict[int, int] = {}
    worked: dict[int, int] = {}
    import ptk.sim.matters.phase as phase

    seen: list[dict[int, WorkMonth]] = []
    original = phase.month_hours

    def spy(*args, **kwargs):  # type: ignore[no-untyped-def]
        out = original(*args, **kwargs)
        seen.append(out.work)
        return out

    phase.month_hours = spy
    try:
        play(state, DATA, BALANCE, 12, seed)  # January to December 2005
    finally:
        phase.month_hours = original
    for work in seen:
        for pid, w in work.items():
            assert 0 <= w.credited_tenths <= w.pro_bono_tenths
            credited[pid] = credited.get(pid, 0) + w.credited_tenths
            worked[pid] = worked.get(pid, 0) + w.pro_bono_tenths
    assert all(c <= credit * fx.TENTHS for c in credited.values())
    assert all(credited[p] == min(worked[p], credit * fx.TENTHS) for p in credited)


def test_credited_hours_count_toward_the_target(data: GameData, balance: Balance) -> None:
    state = game(data, balance)
    person = next(p for p in state.people if p.level.startswith("associate"))
    base = WorkMonth(person.id, (("corporate_ma", 1200),), pro_bono_tenths=100)
    credited = replace(base, credited_tenths=100)
    low, high = hours_ratio(person, base, balance), hours_ratio(person, credited, balance)
    assert low is not None and high is not None and high > low


def test_pro_bono_raises_associates_morale_only(balance: Balance) -> None:
    full = balance.pro_bono.morale_full_hours * fx.TENTHS
    assert morale_term("associate_3", 0, balance) == 0.0
    assert morale_term("associate_3", round(full / 2), balance) == pytest.approx(
        balance.pro_bono.morale_max / 2
    )
    assert morale_term("associate_3", round(full * 3), balance) == balance.pro_bono.morale_max
    assert morale_term("equity_partner", round(full), balance) == 0.0


def test_pro_bono_raises_recruiting_appeal(data: GameData, balance: Balance) -> None:
    state = game(data, balance)
    plain = prestige(state, state.player.id, balance)
    busy = with_firm(state, replace(state.player, pro_bono_avg_tenths=50.0))  # 60 h a year
    assert prestige(busy, busy.player.id, balance) == pytest.approx(
        plain + recruiting_appeal(50.0, balance)
    )
    cfg = balance.hiring.offer
    p0 = acceptance_probability(
        offer_score(ratio=1.0, matching_interests=1, risk_appetite=10, offer=cfg, prestige=plain),
        cfg,
    )
    p1 = acceptance_probability(
        offer_score(
            ratio=1.0,
            matching_interests=1,
            risk_appetite=10,
            offer=cfg,
            prestige=prestige(busy, busy.player.id, balance),
        ),
        cfg,
    )
    assert p1 > p0
    assert recruiting_appeal(10_000.0, balance) == balance.pro_bono.appeal_max


def test_the_credit_policy_is_an_action(data: GameData, balance: Balance) -> None:
    g = start(data, balance)
    assert credit_hours(g.state, g.state.player.id, balance) == balance.pro_bono.credit_hours
    g.act(SetProBonoCredit(g.founder_id, 120))
    assert credit_hours(g.state, g.state.player.id, balance) == 120
    with pytest.raises(MatterActionError):
        g.act(SetProBonoCredit(g.founder_id, balance.pro_bono.credit_max_hours + 1))


def test_named_kinds_exist(data: GameData, balance: Balance) -> None:
    for k in balance.pro_bono.named_kinds:
        assert data.practice(k.practice).kind(k.kind)
