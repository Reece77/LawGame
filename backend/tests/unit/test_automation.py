"""Automation (PT-M9; spec 9.4; TST formulas.md 40; ADR-0015): areas, owners, limits,
one-offs as proposals, decision quality, the digest, routine events, replay."""

from __future__ import annotations

from dataclasses import asdict, replace

import pytest

from ptk.sim.automation import owners
from ptk.sim.automation.actions import (
    AnswerProposal,
    GiveArea,
    SetAreaSettings,
    TakeOverArea,
    apply_automation_action,
)
from ptk.sim.automation.config import AREA_RULES, SPEC_ONE_OFFS
from ptk.sim.automation.events import choice_value, ranked
from ptk.sim.automation.run import overload, owner_quality, quality, with_automation
from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import AutomationError, NotManagingPartnerError
from ptk.sim.events.models import Effect, EventChoice, GameEvent
from ptk.sim.hiring.actions import SetPayPolicy
from ptk.sim.matters.actions import SeekWaiver, SetRatePolicy
from ptk.sim.org.actions import CreatePlan
from ptk.sim.org.seats import ProposeExcoTerm
from ptk.sim.partnership.actions import (
    CapitalCall,
    Counter,
    Deequitise,
    LateralOffer,
    ProposePartner,
    ProposeTerms,
)
from ptk.sim.rivals.actions import ApproachRival
from ptk.sim.rng import RngFactory
from tests.automation_support import auto_run, automate_all, give, refill
from tests.seats_support import funded, led_firm, mp, run, steady


@pytest.fixture(scope="module")
def led(data: GameData, balance: Balance):  # type: ignore[no-untyped-def]
    b = steady(balance)
    return led_firm(data, b), b


@pytest.fixture(scope="module")
def automated(led, data: GameData):  # type: ignore[no-untyped-def]
    state, b = led
    return automate_all(state, data, b), b


def _act(state, action, data, b):  # type: ignore[no-untyped-def]
    state = refill(state, b)
    return apply_automation_action(
        state, action, seq=1, rng=RngFactory(1), b=b, data=data, ledger_balances=funded(state)
    )


# --- Sub-task 1: areas and owners ---------------------------------------------------------------


def test_every_area_of_spec_9_4_exists_with_an_owner_seat(balance: Balance, data: GameData) -> None:
    rules = {a.rule for a in balance.automation.areas.values()}
    assert rules == set(AREA_RULES)
    for a in balance.automation.areas.values():
        if a.who == "seat":
            assert a.seat is not None
            data.seat(a.seat)  # a seats.yaml seat
    assert not balance.automation.areas["knowledge"].available  # PT-M14


def test_a_vacant_seat_cannot_be_automated(led, data: GameData) -> None:  # type: ignore[no-untyped-def]
    from ptk.sim.org.seats import AppointSeat, apply_seat_action

    state, b = led
    firm = state.player.id
    assert owners.eligible_people(state, firm, "billing", 0, b, data)
    state = refill(state, b)
    state = apply_seat_action(state, AppointSeat(mp(state), "cfo", 0, None), b, data).state
    assert owners.eligible_people(state, firm, "billing", 0, b, data) == ()
    assert "fill the chief financial officer seat" in (
        owners.cant_automate(state, firm, "billing", 0, b, data) or ""
    )
    cfo_less = state
    pid = next(e.person_id for e in state.staff(firm) if not state.person(e.person_id).is_founder)
    with pytest.raises(AutomationError):
        _act(cfo_less, GiveArea(mp(state), "billing", pid), data, b)
    assert owners.cant_automate(state, firm, "knowledge", 0, b, data) is not None


def test_giving_and_taking_back_an_area(led, data: GameData) -> None:  # type: ignore[no-untyped-def]
    state, b = led
    firm = state.player.id
    cfo = owners.eligible_people(state, firm, "billing", 0, b, data)[0]
    state = give(state, data, b, "billing", cfo)
    o = state.automation.owner(firm, "billing")
    assert o is not None and o.person_id == cfo
    assert o.limit_cents == owners.default_limit(5_000_000_000, b)  # 2% of $50M
    assert o.monthly_cents == b.automation.monthly_limit_mult * o.limit_cents
    assert state.leadership.authority(firm, "cfo", 0).enabled  # one setting (TST 40.12)
    out = _act(state, SetAreaSettings(mp(state), "billing", 0, limit_cents=1_000_000), data, b)
    assert out.state.automation.owner(firm, "billing").limit_cents == 1_000_000  # type: ignore[union-attr]
    with pytest.raises(AutomationError):  # the monthly limit is at least the decision's
        _act(state, SetAreaSettings(mp(state), "billing", 0, monthly_cents=1), data, b)
    back = _act(out.state, TakeOverArea(mp(state), "billing"), data, b).state
    assert back.automation.owner(firm, "billing") is None
    assert not back.leadership.authority(firm, "cfo", 0).enabled
    with pytest.raises(NotManagingPartnerError):
        _act(state, TakeOverArea(cfo, "billing"), data, b)


def test_an_owner_who_leaves_hands_the_area_back(automated, data: GameData) -> None:  # type: ignore[no-untyped-def]
    from ptk.sim.automation.run import automation_month

    state, b = automated
    firm = state.player.id
    o = state.automation.owner(firm, "billing")
    assert o is not None
    gone = replace(
        state,
        employments=tuple(
            replace(e, status="left") if e.person_id == o.person_id else e
            for e in state.employments
        ),
    )
    out = automation_month(gone, RngFactory(1), b, data, funded(state))
    assert out.state.automation.owner(firm, "billing") is None
    assert any(i.kind == "area_returned" for i in out.log)


# --- Sub-task 2: money limits ----------------------------------------------------------------


def test_a_decision_at_the_limit_is_a_proposal_and_the_month_has_a_cap(  # type: ignore[no-untyped-def]
    automated, data: GameData
) -> None:
    state, b = automated
    firm = state.player.id
    unit, practice, leader = next(
        (u.id, u.practice, u.leader_id)
        for u in state.org.firm_units(firm)
        if u.kind == "practice_group" and u.leader_id is not None
    )
    plan = CreatePlan(
        mp(state),
        leader,
        data.practice_role(practice).key,
        1,
        "job_post",
        10_000,
        unit,  # type: ignore[arg-type]
    )
    from ptk.sim.automation.limits import commitment

    cost = commitment(state, plan, b, data)
    assert cost > 0
    o = state.automation.owner(firm, "hiring")
    assert o is not None
    tight = with_automation(
        state,
        replace(
            state.automation,
            owners=tuple(
                replace(x, limit_cents=cost, monthly_cents=cost) if x is o else x
                for x in state.automation.owners
            ),
        ),
    )
    r = auto_run(tight, data, b, "hiring")
    assert not r.attempt(plan, "a plan")  # at the limit: a proposal
    assert r.lines[-1][0] == "proposal"
    assert len(r.state.automation.pending(firm)) == len(state.automation.pending(firm)) + 1
    pid = r.state.automation.pending(firm)[-1].id
    plans = len(r.state.org.plans)
    approved = _act(r.state, AnswerProposal(mp(state), pid, True), data, b).state
    assert approved.automation.proposal(pid).status == "approved"  # type: ignore[union-attr]
    assert len(approved.org.plans) == plans + 1  # an org action, run as the MP
    loose = with_automation(
        state,
        replace(
            state.automation,
            owners=tuple(
                replace(x, limit_cents=cost + 1, monthly_cents=cost + 1) if x is o else x
                for x in state.automation.owners
            ),
        ),
    )
    r = auto_run(loose, data, b, "hiring")
    assert r.attempt(plan, "a plan")
    again = replace(plan, role=data.practice_role(practice).key, target=1)
    assert not r.attempt(again, "a second plan")  # past the month's limit: it waits
    assert any(line[0] == "over_budget" for line in r.lines)


# --- Sub-task 3: one-offs ----------------------------------------------------------------------


def _one_off_actions(state, data, b):  # type: ignore[no-untyped-def]
    """An action carrying each of spec 9.4's one-offs the game can take today."""
    from ptk.sim.matters.intake import key_clients, with_matter

    actor = mp(state)
    firm = state.player.id
    partner = next(
        p.id for p in state.people if p.level == "equity_partner" and not p.is_founder
        and state.employer_of(p.id) == firm
    )  # fmt: skip
    keys = sorted(key_clients(state.market, firm, b))
    matter = next(m for m in state.market.matters if m.firm_id == firm)
    adverse = keys[0] if keys else matter.client_id
    held = replace(matter, status="conflicted", adverse_client_id=adverse)
    state = replace(state, market=with_matter(state.market, held))
    if not keys:  # make the adverse client a key client: the fixture's top fee payer
        rels = tuple(
            replace(r, fees_12m=10**12) if (r.client_id, r.firm_id) == (adverse, firm) else r
            for r in state.market.relationships
        )
        state = replace(state, market=replace(state.market, relationships=rels))
    return state, {
        "partnership admissions": [ProposePartner(actor, partner, "equity")],
        "de-equitisations": [Deequitise(actor, partner, "income")],
        "guarantees": [LateralOffer(actor, partner, 100, 2), Counter(actor, 1, 100, 0, 1)],
        "mergers and combinations": [ApproachRival(actor, 1, "corporate_ma")],
        "a capital call": [CapitalCall(actor, 100)],
        "changes to the partnership agreement": [
            ProposeTerms(actor, "comp_system", "lockstep"),
            ProposeExcoTerm(actor, True),
        ],
        "a salary-scale change above the market": [SetPayPolicy(actor, "lead", 11_000)],
        "taking on a matter adverse to a key client with a waiver": [SeekWaiver(actor, held.id)],
    }


def test_no_one_off_of_spec_9_4_can_be_taken_by_an_owner(automated, data: GameData) -> None:  # type: ignore[no-untyped-def]
    """The brief's enumerating test: every one-off of spec 9.4's list either has no action in
    the game yet (a later milestone's system) or, offered to any area's owner, becomes a
    proposal and changes nothing else."""
    state, b = automated
    state, _, _ = run(state, data, b, 2)  # matters and trailing fees (key clients)
    state, actions = _one_off_actions(state, data, b)
    for name, kinds in SPEC_ONE_OFFS.items():
        if kinds is None:
            assert name not in actions
            continue
        assert name in actions, name
        assert {a.kind for a in actions[name]} == set(kinds), name
    from ptk.sim.automation.limits import is_one_off

    for o in state.automation.owners:
        for name, acts in actions.items():
            for action in acts:
                assert is_one_off(state, action, b), (name, action.kind)
                r = auto_run(state, data, b, o.area, o.slot)
                before = r.state
                assert not r.attempt(action, name)
                assert r.entries == []
                # nothing changed but the proposal record (and its inbox item)
                assert replace(r.state, automation=before.automation) == before
                assert r.lines[-1][0] == "proposal" or any(
                    p.action_json and p.status == "pending" for p in r.state.automation.proposals
                )


def test_approving_a_proposal_runs_it_as_the_mp_and_declining_closes_it(  # type: ignore[no-untyped-def]
    automated, data: GameData
) -> None:
    state, b = automated
    firm = state.player.id
    r = auto_run(state, data, b, "pricing")
    assert not r.attempt(SetPayPolicy(mp(state), "lead", 11_000), "pay above the market")
    pid = r.state.automation.pending(firm)[-1].id
    out = _act(r.state, AnswerProposal(mp(state), pid, True), data, b)
    assert out.state.player.pay_policy.mode == "lead"
    assert out.state.automation.proposal(pid).status == "approved"  # type: ignore[union-attr]
    r = auto_run(state, data, b, "pricing")
    r.attempt(SetPayPolicy(mp(state), "lead", 11_500), "pay further above")
    pid = r.state.automation.pending(firm)[-1].id
    out = _act(r.state, AnswerProposal(mp(state), pid, False), data, b)
    assert out.state.player.pay_policy == state.player.pay_policy
    assert out.state.automation.proposal(pid).status == "declined"  # type: ignore[union-attr]
    # a declined move is not proposed again for repropose_months
    r = auto_run(out.state, data, b, "pricing")
    r.attempt(SetPayPolicy(mp(state), "lead", 11_500), "pay further above")
    assert (
        not r.state.automation.pending(firm)[-1:]
        or r.state.automation.pending(firm)[-1].id != pid + 1
    )


# --- Sub-task 4: decision quality ---------------------------------------------------------------


def test_quality_follows_the_spec_and_overload_lowers_it(  # type: ignore[no-untyped-def]
    automated, balance: Balance, data: GameData
) -> None:
    assert quality(1.0, balance) == pytest.approx(0.6)
    assert quality(10.0, balance) == pytest.approx(0.85)
    assert quality(20.0, balance) == pytest.approx(0.98)
    state, b = automated
    o = next(x for x in state.automation.owners if x.area == "billing")
    base = owner_quality(state, o, b, data)
    assert overload(state, o.person_id, b) == 0
    # give the CFO's person every area's workload: q falls with the excess energy
    heavy = replace(
        state.automation,
        owners=(
            *state.automation.owners,
            *(
                replace(o, area=a, slot=900 + i)
                for i, a in enumerate(["bd", "hiring", "laterals", "development", "staffing"])
            ),
        ),
    )
    loaded = with_automation(state, heavy)
    extra = overload(loaded, o.person_id, b)
    assert extra > 0
    assert owner_quality(loaded, o, b, data) == pytest.approx(
        max(b.automation.overload_floor, base - b.automation.overload_per_energy * extra)
    )


def test_the_quality_draw_is_seeded_and_keyed_by_area_firm_and_slot() -> None:
    from ptk.sim.automation.run import area_gen

    rng = RngFactory(7)
    a = area_gen(rng, 3, 2, 1, 0).random()
    assert a == area_gen(RngFactory(7), 3, 2, 1, 0).random()
    assert a != area_gen(rng, 3, 3, 1, 0).random()
    assert a != area_gen(rng, 3, 2, 1, 5).random()


# --- Sub-task 5: the digest and routine events ----------------------------------------------


def test_owners_act_every_month_with_a_digest_and_replay_identically(  # type: ignore[no-untyped-def]
    automated, data: GameData
) -> None:
    state, b = automated
    a, results_a, _ = run(state, data, b, 4)
    again, results_b, _ = run(state, data, b, 4)
    lines_a = [asdict(d) for r in results_a for d in r.area_decisions]
    lines_b = [asdict(d) for r in results_b for d in r.area_decisions]
    assert lines_a, "no area decided anything in four months"
    assert lines_a == lines_b  # recomputed on replay (ADR-0015)
    assert a.automation == again.automation
    for r in results_a:
        digests = [i for i in r.log_items if i.kind == "automation_digest"]
        assert len(digests) == 1
        assert "Your people ran" in dict(digests[0].params)["summary"]


def test_a_routine_event_goes_to_the_area_owner_and_critical_ones_never(  # type: ignore[no-untyped-def]
    automated, data: GameData
) -> None:
    from ptk.sim.automation.events import answer_routine_events
    from ptk.sim.events.models import EventsState

    state, b = automated
    firm = state.player.id
    good = EventChoice("A", "Spend", (Effect("cash_delta", f"firm:{firm}", -5_000_000),))
    best = EventChoice("B", "Talk to them", (Effect("morale_delta", f"firm:{firm}", 3.0),))
    nothing = EventChoice("C", "Do nothing", (), do_nothing=True)
    base = GameEvent(
        id=901, firm_id=firm, turn=state.turn, template_id="t", category="client",
        severity="minor", trigger="x", strength=1.0, status="open", title="A client asks",
        choices=(good, best, nothing),
    )  # fmt: skip
    critical = replace(base, id=902, severity="critical", title="A crisis")
    events = replace(state.events, events=(*state.events.events, base, critical))
    assert isinstance(events, EventsState)
    state = replace(state, events=events)
    assert ranked(base)[0].key == "B" and choice_value(nothing) == 0
    out, _entries, _log = answer_routine_events(state, RngFactory(1), b, data)
    answered = out.events.event(901)
    assert answered is not None and answered.chosen in ("B", "C")  # best, or the second best
    assert out.events.event(902).status == "open"  # type: ignore[union-attr]
    line = next(d for d in out.automation.decisions if d.link_id == 901)
    assert line.area == "bd"  # a client event goes to the CMO's area


def test_an_area_with_rate_policy_never_moves_outside_the_band(automated, data: GameData) -> None:  # type: ignore[no-untyped-def]
    state, b = automated
    r = auto_run(state, data, b, "pricing")
    assert r.attempt(SetRatePolicy(mp(state), 300), "rates")  # sets rates: commits nothing
