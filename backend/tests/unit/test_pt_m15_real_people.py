"""PT-M15 (ADR PT-0013): a person flagged real is never the subject of a claim's blame, a
disciplinary case or a client-money misuse, over 3-year runs (the suite) and 30-year runs
(nightly), with every risk chance raised so the systems fire often and half the firm's people
flagged real."""

from __future__ import annotations

from dataclasses import replace

import pytest

from ptk.sim.data_models import Balance
from ptk.sim.decisions import Decisions
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState
from ptk.sim.turn import advance_turn
from tests.matters_support import game, solvent
from tests.risk_support import loaded


def _hot(balance: Balance) -> Balance:
    r = balance.risk
    causes = r.discipline.causes.model_copy(
        update={"court": 400, "neglect": 200, "padding_bp": 10_000, "supervision_bp": 10_000}
    )
    return solvent(balance).model_copy(
        update={
            "risk": r.model_copy(
                update={
                    "claims": r.claims.model_copy(update={"from_error_bp": 10_000}),
                    "discipline": r.discipline.model_copy(update={"causes": causes}),
                    "trust": r.trust.model_copy(update={"misuse_bp": 500, "error_bp": 0}),
                }
            )
        }
    )


def _flag_half(state: GameState) -> GameState:
    """Every other person (by id) apart from the founders is flagged real."""
    people = tuple(
        replace(p, real=True) if p.id % 2 == 0 and not p.founding_partner else p
        for p in state.people
    )
    return replace(state, people=people)


def _check(turns: int, seed: int) -> None:
    data, balance = loaded()
    hot = _hot(balance)
    state = game(data, balance, seed)
    for _ in range(turns):
        if state.ended:
            break
        state = _flag_half(state)
        state = advance_turn(state, Decisions(), RngFactory(seed), hot, data, {}).new_state
    state = _flag_half(state)
    real = {p.id for p in state.people if p.real}
    risk = state.risk
    assert risk.claims, "the run made claims"
    assert all(c.blamed_id not in real for c in risk.claims)
    assert all(c.person_id not in real for c in risk.cases)
    assert all(r.person_id not in real for r in risk.reconciliations if r.person_id is not None)
    assert risk.cases, "the run opened disciplinary cases"


@pytest.mark.parametrize("seed", [1, 2])
def test_real_people_are_never_subjects_over_three_years(seed: int) -> None:
    _check(36, seed)


@pytest.mark.nightly
@pytest.mark.parametrize("seed", [1, 2, 3])
def test_real_people_are_never_subjects_over_thirty_years(seed: int) -> None:
    _check(360, seed)
