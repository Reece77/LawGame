"""Delegated hiring (TST formulas.md 13.10, ADR-0015) through PT-M1b's delegate hook, driven
here by a deterministic stand-in for hiring (tests/org_fake_hiring.py)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import OrgRuleError
from ptk.sim.interfaces import InterviewRequest, OfferRequest, OpenSearchRequest, ScoutRequest
from ptk.sim.org.actions import ClosePlan, CreatePlan, CreateUnit, MovePerson, SetLeader
from ptk.sim.org.delegates import activity_text, available_hook, plan_offer_salary, run_delegates
from ptk.sim.org.models import PlanActivity
from ptk.sim.state import GameState
from ptk.sim.streams import RngFactory
from tests.org_fake_hiring import FakeHiring
from tests.org_support import FIRM, act, founder, game, staff


def _group_with_leader(data: GameData, balance: Balance) -> tuple[GameState, int, int]:
    state = game(data, balance)
    fid = founder(state)
    state = act(state, CreateUnit(fid, "practice_group", practice="corporate_ma"), data, balance)
    gid = state.org.firm_units(FIRM)[0].id
    leader = next(p.id for p in staff(state) if p.level == "associate_5")
    state = act(state, MovePerson(fid, leader, gid), data, balance)
    state = act(state, SetLeader(fid, gid, leader), data, balance)
    return state, gid, leader


def _plan(state: GameState, data: GameData, balance: Balance, **kw: object) -> GameState:
    state_, gid, leader = (
        state,
        state.org.firm_units(FIRM)[0].id,
        state.org.firm_units(FIRM)[0].leader_id,
    )
    assert leader is not None
    fields: dict[str, object] = dict(
        owner_id=leader,
        role="corporate_ma",
        target=2,
        channel="job_post",
        ratio_bp=10500,
        unit_id=gid,
    )
    fields.update(kw)
    return act(state_, CreatePlan(founder(state), **fields), data, balance)  # type: ignore[arg-type]


def _run(state: GameState, data: GameData, balance: Balance, fake: FakeHiring) -> GameState:
    rng = RngFactory(state.save_meta.master_seed)
    return run_delegates(state, rng, balance, data, {}, fake)[0]


def test_delegate_acts_with_own_energy_and_stream(data: GameData, balance: Balance) -> None:
    state, _, leader = _group_with_leader(data, balance)
    state = _plan(state, data, balance)
    fake = FakeHiring(seed=state.save_meta.master_seed)
    rng = RngFactory(state.save_meta.master_seed)
    state, _, logs, taken = run_delegates(state, rng, balance, data, {}, fake)
    # Every request was the delegate's; the founding partner's energy was never touched.
    assert {a.actor_id for a in taken} == {leader}
    assert founder(state) not in fake.energy
    kinds = [type(a.request).__name__ for a in taken]
    # 100 energy: search 10, interviews of 6 while more than the 20 reserve stays, a scout
    # pass of 20, then offers (free) to the best two interviewed.
    assert kinds == [
        "OpenSearchRequest",
        "InterviewRequest",
        "InterviewRequest",
        "InterviewRequest",
        "InterviewRequest",
        "ScoutRequest",
        "OfferRequest",
        "OfferRequest",
    ]
    assert fake.energy[leader] == 100 - 10 - 4 * 6 - 20
    # Each draw came from stream `delegate` keyed (delegate, n): n counts their requests.
    assert fake.draw_log
    for turn, actor, n, value in fake.draw_log:
        expected = float(
            RngFactory(state.save_meta.master_seed).stream(turn, "delegate", actor, n).random()
        )
        assert value == expected
    assert [d[2] for d in fake.draw_log] == list(range(len(fake.draw_log)))
    plan = state.org.firm_plans(FIRM)[0]
    assert plan.last_activity == PlanActivity(turn=0, searches=1, interviews=4, scouted=4, offers=2)
    assert len(logs) == 1 and logs[0].kind == "plan_activity"
    assert "interviewed 4" in logs[0].message and "made 2 offers" in logs[0].message
    offers = [a.request for a in taken if isinstance(a.request, OfferRequest)]
    assert all(o.plan_id == plan.id and o.unit_id == plan.unit_id for o in offers)


def test_offers_go_to_the_best_known_and_at_the_plan_ratio(
    data: GameData, balance: Balance
) -> None:
    state, _, _ = _group_with_leader(data, balance)
    state = _plan(state, data, balance, target=1, ratio_bp=11000)
    fake = FakeHiring(seed=1)
    rng = RngFactory(1)
    state, _, _, taken = run_delegates(state, rng, balance, data, {}, fake)
    from ptk.sim.org.delegates import known_score

    pool = fake.candidates(state, FIRM, "corporate_ma")
    best = max(
        pool, key=lambda c: (known_score(state, FIRM, c.candidate_id, data), -c.candidate_id)
    )
    offer = next(a.request for a in taken if isinstance(a.request, OfferRequest))
    assert offer.candidate_id == best.candidate_id
    assert offer.salary_cents == plan_offer_salary(best.ask_cents, 11000)


def test_hires_join_the_unit_and_fill_the_plan(data: GameData, balance: Balance) -> None:
    """Phase 2 month by month (no other phases, so nobody resigns): offers made one month are
    answered the next; an accepted hire joins the plan's unit and fills it."""
    state, gid, _ = _group_with_leader(data, balance)
    state = _plan(state, data, balance, target=1)
    fake = FakeHiring(seed=state.save_meta.master_seed)
    rng = RngFactory(state.save_meta.master_seed)
    for _ in range(6):
        state = run_delegates(state, rng, balance, data, {}, fake)[0]
        if state.org.firm_plans(FIRM)[0].status == "filled":
            break
        state = replace(state, turn=state.turn + 1)
    plan = state.org.firm_plans(FIRM)[0]
    assert plan.status == "filled" and plan.hired == 1 and len(plan.hires) == 1
    assert state.org.unit_of(plan.hires[0]) == gid
    # The filled plan's delegate closes its search the next month.
    state = run_delegates(replace(state, turn=state.turn + 1), rng, balance, data, {}, fake)[0]
    assert fake.searches(state, FIRM) == ()


def test_plans_pause_when_the_owner_stops_leading(data: GameData, balance: Balance) -> None:
    state, gid, _ = _group_with_leader(data, balance)
    state = _plan(state, data, balance)
    other = next(p.id for p in staff(state) if p.level == "associate_3")
    fid = founder(state)
    state = act(state, MovePerson(fid, other, gid), data, balance)
    state = act(state, SetLeader(fid, gid, other), data, balance)
    assert state.org.firm_plans(FIRM)[0].status == "paused"
    fake = FakeHiring(seed=1)
    assert run_delegates(state, RngFactory(1), balance, data, {}, fake)[3] == ()


def test_plans_pause_when_the_owner_leaves(data: GameData, balance: Balance) -> None:
    state, _, leader = _group_with_leader(data, balance)
    state = _plan(state, data, balance)
    gone = tuple(
        replace(e, status="ended", end_turn=0, end_reason="resigned")
        if e.person_id == leader
        else e
        for e in state.employments
    )
    state = replace(state, employments=gone)
    out = run_delegates(state, RngFactory(1), balance, data, {}, FakeHiring(seed=1))
    assert out[0].org.plans[0].status == "paused" and out[3] == ()


def test_who_may_own_a_plan(data: GameData, balance: Balance) -> None:
    state, _, leader = _group_with_leader(data, balance)
    fid = founder(state)
    not_leader = next(p.id for p in staff(state) if p.level == "associate_3")
    with pytest.raises(OrgRuleError, match="leads a unit or is a recruiting manager"):
        act(state, CreatePlan(fid, not_leader, "corporate_ma", 1, "job_post", 10000), data, balance)
    with pytest.raises(OrgRuleError, match="managing founding partner"):
        act(state, CreatePlan(fid, fid, "corporate_ma", 1, "job_post", 10000), data, balance)
    assert act(state, CreatePlan(fid, leader, "ip", 1, "any", 12000), data, balance).org.plans


def test_campus_target_per_group(data: GameData, balance: Balance) -> None:
    state, gid, leader = _group_with_leader(data, balance)
    fid = founder(state)
    campus = CreatePlan(fid, leader, "corporate_ma", 3, "campus", 10000, unit_id=gid)
    state = act(state, campus, data, balance)
    plan = state.org.firm_plans(FIRM)[0]
    assert plan.campus and plan.level == "associate_1"
    with pytest.raises(OrgRuleError, match="already has a campus target"):
        act(state, campus, data, balance)
    with pytest.raises(OrgRuleError, match="group's own practice"):
        act(state, CreatePlan(fid, leader, "ip", 3, "campus", 10000, unit_id=gid), data, balance)
    with pytest.raises(OrgRuleError, match="belongs to a practice group"):
        act(state, CreatePlan(fid, leader, "corporate_ma", 3, "campus", 10000), data, balance)
    # In January the delegate opens a campus search and interviews, but offers wait for August.
    fake = FakeHiring(seed=3)
    state, _, _, taken = run_delegates(state, RngFactory(3), balance, data, {}, fake)
    kinds = {type(a.request) for a in taken}
    assert OpenSearchRequest in kinds and InterviewRequest in kinds and OfferRequest not in kinds
    assert fake.searches(state, FIRM)[0].channel == "campus"
    # A closed plan's search closes the next month.
    state = act(state, ClosePlan(fid, plan.id), data, balance)
    run_delegates(state, RngFactory(3), balance, data, {}, fake)
    assert fake.searches(state, FIRM) == ()


def test_focus_potential_considers_juniors(data: GameData, balance: Balance) -> None:
    state, _, _ = _group_with_leader(data, balance)
    state = _plan(state, data, balance, focus="potential", level="associate_5")
    fake = FakeHiring(seed=5)
    taken = run_delegates(state, RngFactory(5), balance, data, {}, fake)[3]
    # Senior candidates only: a potential plan interviews and offers to nobody (13.10), though
    # the delegate still scouts the role's search with the energy left (step 4).
    assert [type(a.request) for a in taken] == [OpenSearchRequest, ScoutRequest]


def test_no_hiring_system_means_no_delegate_actions(data: GameData, balance: Balance) -> None:
    state, _, _ = _group_with_leader(data, balance)
    state = _plan(state, data, balance)
    out = run_delegates(state, RngFactory(1), balance, data, {}, None)
    assert out[1:] == ((), (), ())

    def missing() -> FakeHiring:
        raise ImportError("no hiring yet")

    class Placeholder:
        def __getattr__(self, name: str) -> object:
            raise NotImplementedError(name)

    assert available_hook(missing) is None
    assert available_hook(lambda: Placeholder()) is None  # type: ignore[arg-type,return-value]
    assert available_hook(lambda: FakeHiring(seed=1)) is not None


def test_activity_text() -> None:
    a = PlanActivity(turn=0, searches=1, interviews=4, offers=2)
    assert (
        activity_text(a, "lawyer") == "opened a new search, interviewed 4 lawyers and made 2 offers"
    )
    assert activity_text(PlanActivity(turn=0, scouted=1), "x", "potential") == (
        "scouted 1 candidate, favouring potential"
    )
    assert ScoutRequest(1).search_id == 1
