"""PT-M16 sub-tasks 4-5: the spring tables, quarterly league tables, October's directory bands
with the March submission, and Best places to work (spec 12.3)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import InvalidActionError
from ptk.sim.rankings import effects, lists
from ptk.sim.rankings import phase as rank_phase
from ptk.sim.rankings.actions import MakeSubmission, make_submission
from ptk.sim.rankings.models import Submission
from ptk.sim.state import GameState
from tests.matters_support import game, play


@pytest.fixture(scope="module")
def year_in(data: GameData, balance: Balance) -> GameState:
    """A firm through April 2006 (turns 0-15)."""
    state, _ = play(game(data, balance), data, balance, 16)
    return state


def test_the_spring_tables_rank_the_prior_year(
    year_in: GameState, data: GameData, balance: Balance
) -> None:
    rk = year_in.standing.rankings
    assert rk.published_turn("tables") == 15  # April 2006, for fiscal 2005
    revenue = [r for r in rk.tables if r.kind == "revenue"]
    assert revenue and all(r.year == 2005 for r in revenue)
    assert [r.place for r in revenue] == list(range(1, len(revenue) + 1))
    values = [r.value_cents for r in revenue]
    assert values == sorted(values, reverse=True)
    assert all(v >= balance.rankings.tables.min_revenue_cents for v in values)
    assert len(revenue) <= balance.rankings.tables.revenue_places
    # a new firm is too small to enter in its first year
    pid = year_in.player.id
    mine = next(y for y in rk.years if y[0] == 2005)
    assert (pid in {r.firm_id for r in revenue}) == (
        mine[1] >= balance.rankings.tables.min_revenue_cents
    )


def test_a_large_enough_player_enters_the_tables(
    year_in: GameState, data: GameData, balance: Balance
) -> None:
    rk = year_in.standing.rankings
    big = replace(rk, years=((2005, 100_000_000_000, 400, 300_000_000),))
    state = replace(year_in, standing=replace(year_in.standing, rankings=big))
    rows = lists.tables(state, 2005, lists.rivals_now(state, data), balance)
    assert any(r.firm_id == state.player.id and r.kind == "revenue" for r in rows)


def test_league_tables_each_quarter(year_in: GameState, data: GameData, balance: Balance) -> None:
    rk = year_in.standing.rankings
    assert rk.published_turn("league") == 14  # March 2006
    practices = lists.league_practices(data, balance)
    assert "corporate_ma" in practices and "commercial_litigation" not in practices
    for practice, rows in lists.by_practice(rk.league).items():
        assert practice in practices
        top = [r for r in rows if r.place <= balance.rankings.league.places]
        assert [r.place for r in top] == list(range(1, len(top) + 1))
        assert [r.value_cents for r in top] == sorted((r.value_cents for r in top), reverse=True)


def test_october_bands_and_the_submission(data: GameData, balance: Balance) -> None:
    state, _ = play(game(data, balance), data, balance, 22)  # through October 2006
    rk = state.standing.rankings
    assert rk.published_turn("bands") == 21
    assert {b.band for b in rk.bands} <= set(range(1, 7))
    assert any(p.firm_id != state.player.id for p in rk.people)  # rivals' named individuals
    # a submission raises the firm's score; none costs it
    pid = state.player.id
    without = lists.submission_points(state, 2006, balance)
    assert without == -balance.rankings.directory.no_submission
    sub = Submission(2006, 14, (1,), (), 0.5)
    withsub = replace(state, standing=replace(state.standing, rankings=replace(rk, submission=sub)))
    assert lists.submission_points(withsub, 2006, balance) == pytest.approx(
        balance.rankings.directory.submission_points * 0.5
    )
    a = {
        b.practice: b.score
        for b in lists.bands(state, 2006, lists.rivals_now(state, data), data, balance)
        if b.firm_id == pid
    }
    b = {
        b.practice: b.score
        for b in lists.bands(withsub, 2006, lists.rivals_now(state, data), data, balance)
        if b.firm_id == pid
    }
    for practice, score in b.items():
        if practice in a:
            assert score > a[practice]


def test_the_submission_action(data: GameData, balance: Balance) -> None:
    state, _ = play(game(data, balance), data, balance, 14)  # March 2006
    pid = state.player.id
    actor = state.founder_of(pid)
    assert actor is not None
    matters = [m for m in state.market.matters if m.firm_id == pid and not m.pro_bono][:2]
    rels = [r for r in state.market.relationships if r.firm_id == pid][:2]
    assert matters and rels
    action = MakeSubmission(actor, tuple(m.id for m in matters), tuple(r.client_id for r in rels))
    out = make_submission(state, action, balance)
    sub = out.state.standing.rankings.submission
    assert sub is not None and sub.year == 2006 and 0 < sub.strength <= 1
    for r in rels:  # each referee spends a little of the relationship
        after = out.state.market.relationship(r.client_id, pid)
        assert after is not None and after.score == pytest.approx(
            max(0.0, r.score - balance.rankings.directory.referee_cost)
        )
    with pytest.raises(InvalidActionError):  # one a year
        make_submission(out.state, action, balance)
    with pytest.raises(InvalidActionError):  # outside March-April
        make_submission(replace(state, turn=state.turn + 3), action, balance)
    with pytest.raises(InvalidActionError):  # too many matters
        make_submission(state, replace(action, matter_ids=tuple(range(1, 8))), balance)


def test_best_places_to_work_and_its_campus_bonus(data: GameData, balance: Balance) -> None:
    state, _ = play(game(data, balance), data, balance, 19)  # through July 2006
    rk = state.standing.rankings
    assert rk.published_turn("places") == 18
    places = [r.place for r in rk.places]
    assert places == sorted(places)
    pid = state.player.id
    first = rk.places[0]
    top = replace(rk, places=(replace(first, firm_id=pid),))
    placed = replace(state, standing=replace(state.standing, rankings=top))
    assert effects.recruiting_term(placed, pid, None, True, balance) == pytest.approx(
        balance.rankings.places.campus_bonus
    )
    assert effects.recruiting_term(placed, pid, None, False, balance) == 0.0


def test_publications_are_inbox_items(data: GameData, balance: Balance) -> None:
    state, _ = play(game(data, balance), data, balance, 15)  # April 2006 is next
    _, logs, _press = rank_phase.month(state, data, balance)
    kinds = {i.template for i in logs}
    assert "tables_published" in kinds
    assert all(i.link_kind == "rankings" for i in logs)
