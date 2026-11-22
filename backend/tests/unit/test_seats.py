"""Seats (PT-M8; spec 9.1; TST formulas.md 18.3): scores, effects, eligibility and the
player's seat actions."""

from __future__ import annotations

from dataclasses import replace

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import NotManagingPartnerError, SeatRuleError
from ptk.sim.interfaces import seat_effect
from ptk.sim.org.seat_models import EXCO, PGL
from ptk.sim.org.seats import (
    AppointSeat,
    ProposeExcoTerm,
    apply_seat_action,
    effect_of_score,
    exco_elected,
    holder_of,
    ineligible_reason,
    true_score,
)
from ptk.sim.state import with_firm
from tests.seats_support import (
    add_bs,
    appoint,
    appointed_committee,
    group,
    mp,
    staged,
    with_score,
)


def test_worked_examples_in_pt_units(balance: Balance) -> None:
    # TST 18.10: s = 14 gives e = 0.5; the clamp holds e in [-0.5, 1].
    assert effect_of_score(14, balance) == pytest.approx(0.5)
    assert effect_of_score(10, balance) == 0.0
    assert effect_of_score(6, balance) == -0.5
    assert effect_of_score(2, balance) == -0.5
    assert effect_of_score(18, balance) == pytest.approx(1.0)
    assert effect_of_score(20, balance) == pytest.approx(1.0)


def test_cfo_vacant_at_stage_two_is_minus_half(data: GameData, balance: Balance) -> None:
    state = staged(data, balance, stage=2)
    assert seat_effect(state, state.player.id, "cfo", balance, data) == -0.5
    # before its stage a seat has no effect, filled or not
    early = with_firm(state, replace(state.player, stage=1))
    assert seat_effect(early, early.player.id, "cfo", balance, data) == 0.0
    # pricing opens at stage 3: nothing at stage 2
    assert seat_effect(state, state.player.id, "pricing_director", balance, data) == 0.0


def test_a_cfo_at_score_14_gives_half(data: GameData, balance: Balance) -> None:
    state = staged(data, balance, stage=2)
    state, cfo = add_bs(state, data, balance, "finance")
    state = with_score(state, data, cfo, "cfo", 14.0)
    assert true_score(state.person(cfo), data.seat("cfo")) == pytest.approx(14.0)
    state = appoint(state, data, balance, "cfo", cfo)
    assert holder_of(state, state.player.id, "cfo") == cfo
    assert seat_effect(state, state.player.id, "cfo", balance, data) == pytest.approx(0.5)
    # a holder who leaves the books leaves the seat vacant
    gone = replace(
        state,
        employments=tuple(
            replace(e, status="ended", end_turn=state.turn) if e.person_id == cfo else e
            for e in state.employments
        ),
    )
    assert seat_effect(gone, gone.player.id, "cfo", balance, data) == -0.5


def test_eligibility(data: GameData, balance: Balance) -> None:
    state = staged(data, balance)
    firm = state.player.id
    state, staff = add_bs(state, data, balance, "finance", level="staff")
    state, manager = add_bs(state, data, balance, "finance", level="manager", n=1)
    assoc = next(p.id for p in state.people if p.level.startswith("associate"))
    income = next(p.id for p in state.people if p.level == "income_partner")
    equity = next(p.id for p in state.people if p.level == "equity_partner" and not p.is_founder)
    cfo, pgl, gc = data.seat("cfo"), data.seat(PGL), data.seat("general_counsel")
    assert ineligible_reason(state, firm, staff, cfo, balance)
    assert ineligible_reason(state, firm, manager, cfo, balance) is None
    assert ineligible_reason(state, firm, assoc, cfo, balance)
    assert ineligible_reason(state, firm, income, cfo, balance) is None  # a partner may
    assert ineligible_reason(state, firm, income, pgl, balance)  # an equity partner only
    assert ineligible_reason(state, firm, equity, pgl, balance) is None
    assert ineligible_reason(state, firm, income, gc, balance) is None  # partner or counsel
    assert ineligible_reason(state, firm, mp(state), cfo, balance)  # the MP has their own


def test_appoint_spends_energy_and_moves_confidence(data: GameData, balance: Balance) -> None:
    state = staged(data, balance)
    firm = state.player.id
    equity = next(p.id for p in state.people if p.level == "equity_partner" and not p.is_founder)
    person = state.person(equity)
    state = with_people_ambition(state, equity, 16.0)
    fp = state.partnership.of(firm)
    assert fp is not None
    before = fp.partner(equity)
    assert before is not None
    state = appoint(state, data, balance, "general_counsel", equity)
    after = state.partnership.of(firm)
    assert after is not None
    p = after.partner(equity)
    assert p is not None
    assert p.nudge - before.nudge == pytest.approx(
        balance.seats.appoint_confidence_per_ambition * 6
    )
    energy = state.person_state(mp(state)).energy
    assert energy == balance.energy.per_month - balance.energy.cost["appoint_seat"]
    # removing them takes it back
    state = appoint(state, data, balance, "general_counsel", None)
    again = state.partnership.of(firm)
    assert again is not None and (q := again.partner(equity)) is not None
    assert q.nudge == pytest.approx(before.nudge)
    del person


def with_people_ambition(state, pid, value):  # type: ignore[no-untyped-def]
    from ptk.sim.state import with_people

    p = state.person(pid)
    return with_people(state, [replace(p, personality=p.personality.updated({"ambition": value}))])


def test_one_seat_each_and_only_the_mp_appoints(data: GameData, balance: Balance) -> None:
    state = appointed_committee(staged(data, balance))
    equity = [p.id for p in state.people if p.level == "equity_partner" and not p.is_founder]
    state = appoint(state, data, balance, "general_counsel", equity[0])
    with pytest.raises(SeatRuleError):
        appoint(state, data, balance, "cfo", equity[0])
    # the committee is allowed beside another seat
    state = appoint(state, data, balance, EXCO, equity[0], slot=1)
    with pytest.raises(NotManagingPartnerError):
        apply_seat_action(state, AppointSeat(equity[1], "cfo", 0, equity[2]), balance, data)


def test_practice_group_leader_is_the_unit_leader(data: GameData, balance: Balance) -> None:
    state = staged(data, balance)
    state, unit = group(state, data, balance, "corporate_ma")
    firm = state.player.id
    # vacant from stage 3
    assert seat_effect(state, firm, PGL, balance, data, unit_id=unit) == -0.5
    leader = next(
        p.id
        for p in state.people
        if p.level == "equity_partner" and not p.is_founder and p.role != "corporate_ma"
    )
    state = with_score(state, data, leader, PGL, 16.0)
    state = appoint(state, data, balance, PGL, leader, slot=unit)
    assert state.org.unit(unit).leader_id == leader  # type: ignore[union-attr]
    assert state.org.unit_of(leader) == unit  # moved into the group first
    assert seat_effect(state, firm, PGL, balance, data, unit_id=unit) == pytest.approx(0.75)


def test_committee_effect_counts_missing_members(data: GameData, balance: Balance) -> None:
    state = appointed_committee(staged(data, balance))
    firm = state.player.id
    assert seat_effect(state, firm, EXCO, balance, data) == -0.5
    equity = [p.id for p in state.people if p.level == "equity_partner" and not p.is_founder]
    state = with_score(state, data, equity[0], EXCO, 18.0)
    state = appoint(state, data, balance, EXCO, equity[0], slot=1)
    # (1 + -0.5 + -0.5) / 3
    assert seat_effect(state, firm, EXCO, balance, data) == pytest.approx(0.0)


def test_exco_term_default_and_proposal(data: GameData, balance: Balance) -> None:
    state = staged(data, balance, lawyers=60)
    firm = state.player.id
    assert not exco_elected(state, firm, balance, data)  # appointed below 100 lawyers
    big = staged(data, balance, lawyers=110)
    assert exco_elected(big, big.player.id, balance, data)
    state = apply_seat_action(state, ProposeExcoTerm(mp(state), True), balance, data).state
    assert state.leadership.firm(firm).exco_proposed is True


@settings(max_examples=60, deadline=None)
@given(st.lists(st.floats(1.0, 20.0), min_size=4, max_size=4))
def test_effect_is_always_in_range(values: list[float]) -> None:
    from ptk.loader import balance as load_balance
    from ptk.loader import game_data

    b, d = load_balance(), game_data()
    seat = d.seat("cfo")
    score = sum(w * v for (_, w), v in zip(seat.weights.items(), values, strict=True))
    assert 1.0 <= score <= 20.0
    assert -0.5 <= effect_of_score(score, b) <= 1.0


def test_cfo_pricing_and_coo_effects(data: GameData, balance: Balance) -> None:
    """PT-M8 after PT-M7b: the CFO's days to pay, the pricing director's discounts and the
    COO's rent, each x e (spec 9.1); vacant from their stages counts -0.5."""
    from ptk.sim.billing.phase import _Run
    from ptk.sim.hiring.formulas import rent_cents
    from ptk.sim.hiring.phases import _office_rent
    from ptk.sim.rng import RngFactory

    state = staged(data, balance, stage=3)
    firm = state.player.id
    fx = balance.seats.effects
    run = _Run(state, firm, RngFactory(1), data, balance)
    assert run.pay_factor == pytest.approx(1 + 0.5 * fx.cfo_collection)  # vacant CFO
    assert run.discount_cut_bp == round(-10_000 * 0.5 * fx.pricing_realisation)
    for role, seat in (("finance", "cfo"), ("finance", "pricing_director"), ("operations", "coo")):
        state, pid = add_bs(state, data, balance, role, n=len(seat))
        state = with_score(state, data, pid, seat, 18.0)  # e = 1
        state = appoint(state, data, balance, seat, pid)
    run = _Run(state, firm, RngFactory(1), data, balance)
    assert run.pay_factor == pytest.approx(1 - fx.cfo_collection)
    assert run.discount_cut_bp == round(10_000 * fx.pricing_realisation)
    heads = len(state.staff(firm))
    rent = rent_cents(heads, state.player.home_city, balance.pay)
    assert _office_rent(state, firm, heads, balance, data) == round(rent * (1 - fx.coo_office))
    early = with_firm(state, replace(state.player, stage=1))
    assert _office_rent(early, firm, heads, balance, data) == rent
