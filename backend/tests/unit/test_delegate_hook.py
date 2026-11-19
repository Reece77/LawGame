"""The delegate hiring hook PT-M2 builds on (ptk.sim.interfaces; TST 13.10, ADR-0015)."""

from __future__ import annotations

import pytest

from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import InsufficientEnergyError, InterviewRequiredError
from ptk.sim.interfaces import (
    InterviewRequest,
    OfferRequest,
    OpenSearchRequest,
    ScoutRequest,
    delegate_hiring,
    manager_morale_term,
)
from ptk.sim.ledger import apply_entries
from tests.hiring_helpers import start


def test_a_delegate_hires_through_the_hook(data: GameData, balance: Balance) -> None:
    game = start(data, balance, seed=17)
    hook = delegate_hiring()
    delegate = next(
        e.person_id
        for e in game.state.staff(1)
        if not game.state.person(e.person_id).founding_partner
    )
    rng = game.rng
    n = 0

    def draws():  # type: ignore[no-untyped-def]
        return rng.stream(game.state.turn, "misc", delegate, n)

    state = hook.set_energy(game.state, delegate, 100)
    req = OpenSearchRequest(role="corporate_ma", channel="job_post", plan_id=7)
    assert hook.energy_cost(req, balance) == balance.energy.cost["job_post"]
    result = hook.apply(
        state,
        req,
        actor_id=delegate,
        draws=draws,
        balance=balance,
        data=data,
        balances=game.balances,
    )
    assert hook.energy_left(result.state, delegate) == 100 - balance.energy.cost["job_post"]
    assert [s.plan_id for s in hook.searches(result.state, 1)] == [7]
    game.state = result.state
    founder_energy = game.state.person_state(game.founder_id).energy
    game.advance()  # the job post's batch arrives; delegates' energy is PT-M2's to reset
    state = hook.set_energy(game.state, delegate, 100)
    cands = hook.candidates(state, 1, role="corporate_ma")
    assert cands and all(c.plan_id == 7 and not c.interviewed for c in cands)
    cand = cands[0]
    with pytest.raises(InterviewRequiredError):
        hook.apply(
            state,
            OfferRequest(cand.candidate_id, cand.ask_cents),
            actor_id=delegate,
            draws=draws,
            balance=balance,
            data=data,
            balances=game.balances,
        )
    for req2 in (ScoutRequest(cands[0].search_id), InterviewRequest(cand.candidate_id)):
        state = hook.apply(
            state,
            req2,
            actor_id=delegate,
            draws=draws,
            balance=balance,
            data=data,
            balances=game.balances,
        ).state
    state = hook.apply(
        state,
        OfferRequest(cand.candidate_id, int(cand.ask_cents * 1.3), plan_id=7, unit_id=3),
        actor_id=delegate,
        draws=draws,
        balance=balance,
        data=data,
        balances=game.balances,
    ).state
    # The delegate's energy is their own: the founder's is untouched.
    assert state.person_state(game.founder_id).energy == founder_energy
    with pytest.raises(InsufficientEnergyError):
        hook.apply(
            hook.set_energy(state, delegate, 0),
            InterviewRequest(cands[1].candidate_id),
            actor_id=delegate,
            draws=draws,
            balance=balance,
            data=data,
            balances=game.balances,
        )
    game.state = state
    turn = game.state.turn
    game.advance()
    hires = hook.hires(game.state, 1, turn)
    offer = next(o for o in game.state.offers if o.candidate_id == cand.candidate_id)
    if offer.status == "accepted":
        assert [(h.person_id, h.plan_id, h.unit_id) for h in hires] == [(cand.candidate_id, 7, 3)]
    else:
        assert hires == ()
    assert apply_entries({}, game.entries)  # entries still post


def test_manager_term_is_zero_until_pt_m2(data: GameData, balance: Balance) -> None:
    game = start(data, balance)
    assert manager_morale_term(game.state, 3, balance, data) == 0.0
