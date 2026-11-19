"""PT-M1b sub-task 1: searches and offers (TST formulas.md 7; spec 5.7)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import (
    CampusSeasonError,
    InsufficientEnergyError,
    InterviewRequiredError,
    InvalidActionError,
    OfferExistsError,
)
from ptk.sim.hiring.actions import (
    CloseSearch,
    Interview,
    MakeOffer,
    OpenSearch,
    ReferenceCheck,
    Scout,
    WithdrawOffer,
)
from ptk.sim.hiring.formulas import acceptance_probability, offer_score, recruiter_fee_cents
from ptk.sim.hiring.phases import resolve_offers
from ptk.sim.hiring.rules import offer_preview
from ptk.sim.rng import RngFactory
from ptk.sim.state import with_person_states
from tests.hiring_helpers import Game, start


def _p(ratio: float, balance: Balance, fit: int = 0, risk: float = 10.0) -> float:
    offer = balance.hiring.offer
    score = offer_score(ratio=ratio, matching_interests=fit, risk_appetite=risk, offer=offer)
    return acceptance_probability(score, offer)


def test_worked_example_neutral_candidate(balance: Balance) -> None:
    """A neutral candidate (no favoured interests, risk appetite 10, recruiting-10 offer
    maker, prestige 0): 0.95x 27.4%, 1.00x 42.6%, 1.10x 74.1%."""
    assert _p(0.95, balance) == pytest.approx(0.2744, abs=1e-3)
    assert _p(1.00, balance) == pytest.approx(0.4256, abs=1e-3)
    assert _p(1.10, balance) == pytest.approx(0.7408, abs=1e-3)


def test_acceptance_criterion_by_formula(balance: Balance) -> None:
    """Brief: 1.10x is accepted at least 30 points more often than 0.95x (the neutral
    candidate); for any candidate the richer offer is likelier."""
    assert _p(1.10, balance) - _p(0.95, balance) >= 0.30
    for fit in (0, 1, 2):
        for risk in (6.0, 10.0, 14.0):
            assert _p(1.10, balance, fit, risk) > _p(0.95, balance, fit, risk)


def _laterals(data: GameData, balance: Balance, seed: int) -> Game:
    game = start(data, balance, seed=seed)
    game.act(OpenSearch(actor_id=game.founder_id, role="corporate_ma", channel="job_post"))
    game.advance()
    return game


def test_acceptance_criterion_measured(data: GameData, balance: Balance) -> None:
    """Re-measured over generated lateral candidates and seeded resolution draws: an offer
    at 1.10x the ask is accepted >= 30 points more often than one at 0.95x."""
    accepted = {0.95: 0, 1.10: 0}
    total = 0
    for seed in range(40):
        game = _laterals(data, balance, seed)
        state = game.state
        for c in [c for c in state.candidates if c.status == "open"]:
            state = replace(
                state,
                candidates=tuple(
                    replace(x, interviewed_turn=state.turn) if x.person_id == c.person_id else x
                    for x in state.candidates
                ),
            )
        cands = [c for c in state.candidates if c.status == "open"]
        total += len(cands)
        for ratio in accepted:
            s = state
            for c in cands:
                offer = MakeOffer(game.founder_id, c.person_id, int(c.ask_cents * ratio))
                from ptk.sim.hiring.actions import make_offer

                s = make_offer(s, offer, balance).state
            s = replace(s, turn=s.turn + 1)
            s, _, _ = resolve_offers(s, RngFactory(seed), balance, data)
            accepted[ratio] += sum(1 for o in s.offers if o.status == "accepted")
    gap = (accepted[1.10] - accepted[0.95]) / total
    assert total > 150
    assert gap >= 0.30, (accepted, total)


def test_offer_needs_an_interview(data: GameData, balance: Balance) -> None:
    game = _laterals(data, balance, 3)
    cand = next(c for c in game.state.candidates if c.status == "open")
    with pytest.raises(InterviewRequiredError):
        game.act(MakeOffer(game.founder_id, cand.person_id, cand.ask_cents))
    game.act(Interview(game.founder_id, cand.person_id))
    game.act(MakeOffer(game.founder_id, cand.person_id, cand.ask_cents))
    with pytest.raises(OfferExistsError):
        game.act(MakeOffer(game.founder_id, cand.person_id, cand.ask_cents))
    offer = game.state.pending_offer_for(cand.person_id)
    assert offer is not None
    game.act(WithdrawOffer(game.founder_id, offer.id))
    assert game.state.pending_offer_for(cand.person_id) is None


def test_interview_narrows_and_costs_energy(data: GameData, balance: Balance) -> None:
    game = _laterals(data, balance, 4)
    cand = next(c for c in game.state.candidates if c.status == "open")
    before = game.state.reveal(1, cand.person_id)
    assert before is not None
    energy = game.state.person_state(game.founder_id).energy
    game.act(Interview(game.founder_id, cand.person_id))
    game.act(ReferenceCheck(game.founder_id, cand.person_id))
    after = game.state.reveal(1, cand.person_id)
    assert after is not None and after.profile_revealed_turn == game.state.turn
    assert after.record("negotiation").hw < before.record("negotiation").hw
    cost = balance.energy.cost
    assert game.state.person_state(game.founder_id).energy == (
        (energy or 0) - cost["interview"] - cost["reference_check"]
    )


def test_energy_runs_out(data: GameData, balance: Balance) -> None:
    game = _laterals(data, balance, 5)
    game.state = with_person_states(
        game.state, [replace(game.state.person_state(game.founder_id), energy=3)]
    )
    cand = next(c for c in game.state.candidates if c.status == "open")
    with pytest.raises(InsufficientEnergyError):
        game.act(Interview(game.founder_id, cand.person_id))
    game.advance()  # energy resets after phase 12
    assert game.state.person_state(game.founder_id).energy == balance.energy.per_month


def test_lateral_hire_joins_next_month_and_pays_recruiter(data: GameData, balance: Balance) -> None:
    game = start(data, balance, seed=8)
    game.act(OpenSearch(game.founder_id, "corporate_ma", "recruiter", level="associate_5"))
    game.advance()
    assert game.state.searches[0].status == "closed"  # a recruiter brings one batch
    cands = [c for c in game.state.candidates if c.status == "open"]
    assert cands and all(game.state.person(c.person_id).level == "associate_5" for c in cands)
    for c in cands:
        game.act(Interview(game.founder_id, c.person_id))
        game.act(MakeOffer(game.founder_id, c.person_id, int(c.ask_cents * 1.2)))
    n = len(game.entries)
    game.advance()
    hired = [o for o in game.state.offers if o.status == "accepted"]
    assert hired
    fees = [e for e in game.entries[n:] if e.memo.startswith("Recruiter fee")]
    assert len(fees) == len(hired)
    for offer, fee in zip(hired, fees, strict=True):
        assert fee.lines[0].account == "6200_recruiting"
        assert fee.lines[0].amount == offer.salary_cents * 2500 // 10_000  # senior: 25%
        e = game.state.employment_of(offer.candidate_id)
        assert e is not None and e.salary_cents == offer.salary_cents


def test_recruiter_fee_is_20_or_25_percent(balance: Balance) -> None:
    assert recruiter_fee_cents(10_000_000, "associate_2", balance.hiring) == 2_000_000
    assert recruiter_fee_cents(10_000_000, "associate_5", balance.hiring) == 2_500_000
    assert recruiter_fee_cents(10_000_000, "counsel", balance.hiring) == 2_500_000


def test_tier_filter_and_lowball(data: GameData, balance: Balance) -> None:
    game = start(data, balance, seed=9)
    game.act(OpenSearch(game.founder_id, "ip", "job_post", school_tiers=("t14",)))
    game.advance()
    cands = [c for c in game.state.candidates if c.status == "open"]
    assert cands and {game.state.person(c.person_id).school_tier for c in cands} == {"t14"}
    c = cands[0]
    game.act(Interview(game.founder_id, c.person_id))
    preview = offer_preview(game.state, c, int(c.ask_cents * 0.8), balance, data)
    assert preview.hint == "unlikely" and preview.floor_cents == -(-c.ask_cents * 85 // 100)
    game.act(MakeOffer(game.founder_id, c.person_id, int(c.ask_cents * 0.8)))
    game.advance()
    assert game.state.offers[0].status == "declined"  # below 0.85x always declines
    assert game.state.searches[0].status == "open"  # a job post keeps producing batches
    game.act(CloseSearch(game.founder_id, game.state.searches[0].id))
    assert game.state.searches[0].status == "closed"


def test_search_rules(data: GameData, balance: Balance) -> None:
    game = start(data, balance)
    fid = game.founder_id
    with pytest.raises(InvalidActionError):
        game.act(OpenSearch(fid, "paralegal", "job_post", school_tiers=("t14",)))
    with pytest.raises(InvalidActionError):
        game.act(OpenSearch(fid, "corporate_ma", "recruiter", level="equity_partner"))
    with pytest.raises(InvalidActionError):
        game.act(OpenSearch(fid, "corporate_ma", "campus", level="associate_3"))
    game.advance_to(5)
    with pytest.raises(CampusSeasonError):  # registration closes after April
        game.act(OpenSearch(fid, "corporate_ma", "campus"))


def test_scout_narrows_every_open_candidate(data: GameData, balance: Balance) -> None:
    game = _laterals(data, balance, 6)
    search = game.state.searches[0]
    before = {
        c.person_id: game.state.reveal(1, c.person_id).record("writing").hw  # type: ignore[union-attr]
        for c in game.state.candidates
    }
    game.act(Scout(game.founder_id, search.id))
    for pid, hw in before.items():
        rv = game.state.reveal(1, pid)
        assert rv is not None and rv.record("writing").hw < hw


def test_resolution_is_seeded(data: GameData, balance: Balance) -> None:
    def run() -> list[str]:
        game = _laterals(data, balance, 12)
        for c in [c for c in game.state.candidates if c.status == "open"]:
            game.act(Interview(game.founder_id, c.person_id))
            game.act(MakeOffer(game.founder_id, c.person_id, c.ask_cents))
        game.advance()
        return [o.status for o in game.state.offers]

    assert run() == run()
