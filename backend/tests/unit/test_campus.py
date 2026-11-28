"""PT-M1b sub-task 2: the campus cycle (spec 5.7; ADR PT-0002 section 3)."""

from __future__ import annotations

import pytest
from simcore.kernel.calendar import turn_to_ym

from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import CampusSeasonError
from ptk.sim.hiring.actions import Interview, MakeOffer, OpenSearch
from ptk.sim.hiring.pay import firm_scale_cents
from tests.hiring_helpers import Game, start


def _summer(data: GameData, balance: Balance, seed: int = 21, tiers: tuple[str, ...] = ()) -> Game:
    game = start(data, balance, seed=seed)
    game.act(OpenSearch(game.founder_id, "corporate_ma", "campus", school_tiers=tiers))
    game.advance_to(5)  # May: the summer associates have arrived
    return game


def _ym(game: Game) -> tuple[int, int]:
    return turn_to_ym(game.state.turn, game.state.save_meta.start_ym)


def test_summer_associates_arrive_in_may_by_tier(data: GameData, balance: Balance) -> None:
    game = _summer(data, balance)
    summers = [c for c in game.state.candidates if c.channel == "campus"]
    assert len(summers) == sum(balance.campus.per_tier.values())
    tiers = [game.state.person(c.person_id).school_tier for c in summers]
    for tier, n in balance.campus.per_tier.items():
        assert tiers.count(tier) == n
    assert all(game.state.person(c.person_id).level == "associate_1" for c in summers)
    assert game.state.searches[0].status == "closed"
    assert any(i.kind == "summer_programme" for i in game.log)


def test_tier_filter_visits_only_those_schools(data: GameData, balance: Balance) -> None:
    game = _summer(data, balance, tiers=("t14",))
    tiers = {game.state.person(c.person_id).school_tier for c in game.state.candidates}
    assert tiers == {"t14"}


def test_summer_months_scout_and_cost(data: GameData, balance: Balance) -> None:
    game = _summer(data, balance)
    pid = game.state.candidates[0].person_id
    hw_may = game.state.reveal(1, pid).record("writing").hw  # type: ignore[union-attr]
    n = len(game.entries)
    game.advance()  # May is played: a scouting month, and summer pay
    assert game.state.reveal(1, pid).record("writing").hw < hw_may  # type: ignore[union-attr]
    costs = [e for e in game.entries[n:] if e.memo.startswith("Monthly costs")]
    assert "Summer programme" in costs[0].memo


def test_offers_only_in_august(data: GameData, balance: Balance) -> None:
    game = _summer(data, balance)
    c = game.state.candidates[0]
    game.act(Interview(game.founder_id, c.person_id))
    with pytest.raises(CampusSeasonError):
        game.act(MakeOffer(game.founder_id, c.person_id, c.ask_cents))
    game.advance_to(8)
    game.act(MakeOffer(game.founder_id, c.person_id, c.ask_cents))


def test_a_september_class_starts_on_the_scale_for_its_year(
    data: GameData, balance: Balance
) -> None:
    """Brief: offers in August 2005 sign the class of 2006, which starts in September 2006
    on the 2006 scale (not the 2005 scale the offers were made at)."""
    game = _summer(data, balance, seed=22)
    game.advance_to(8)
    summers = [c for c in game.state.candidates if c.status == "open"][:7]  # energy for 7
    for c in summers:
        game.act(Interview(game.founder_id, c.person_id))
        game.act(MakeOffer(game.founder_id, c.person_id, int(c.ask_cents * 1.1)))
    game.advance()  # August is played: the offers resolve in its phase 1
    signed = [c for c in game.state.candidates if c.status == "signed"]
    assert signed
    assert all(game.state.employment_of(c.person_id) is None for c in signed)
    offers = {o.candidate_id: o for o in game.state.offers}
    start_turn = offers[signed[0].person_id].start_turn
    assert turn_to_ym(start_turn, game.state.save_meta.start_ym) == (2006, 9)
    expired = {c.person_id for c in game.state.candidates if c.status == "expired"}
    offered = {c.person_id for c in summers}
    assert expired == {c.person_id for c in game.state.candidates} - offered
    game.advance()
    game.advance_to(9)  # the next turn is September 2006
    assert _ym(game) == (2006, 9)
    game.advance()
    scale_2006 = data.salary_scale.market_salaries((2006, 9))[0]
    policy = game.state.player.pay_policy
    assert firm_scale_cents(data, (2006, 9), "associate_1", policy) == scale_2006
    for c in signed:
        e = game.state.employment_of(c.person_id)
        assert e is not None and e.start_turn == start_turn
        person = game.state.person(c.person_id)
        assert person.level == "associate_1"  # no class-year step on the first day
        assert e.salary_cents == max(offers[c.person_id].salary_cents, scale_2006)
        assert scale_2006 == 14_500_000 and e.salary_cents >= 14_500_000
    assert sum(1 for i in game.log if i.kind == "class_started") == len(signed)


def test_unoffered_summer_associates_leave_after_august(data: GameData, balance: Balance) -> None:
    game = _summer(data, balance)
    game.advance_to(9)
    assert all(c.status == "expired" for c in game.state.candidates)


def test_campus_pools_are_seeded(data: GameData, balance: Balance) -> None:
    a = _summer(data, balance, seed=30)
    b = _summer(data, balance, seed=30)
    assert a.state.people == b.state.people
    assert [c.ask_cents for c in a.state.candidates] == [c.ask_cents for c in b.state.candidates]
