"""PT-M7a sub-task 6: Holiday and "continue until" (spec 4.2). Each stop reason stops it, a
critical event refuses it, and every month played is its own committed turn."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

from ptk.api.app import create_app
from ptk.db import saves
from ptk.db.core import make_sessionmaker, shared_engine
from ptk.db.state_io import load_state, write_turn
from ptk.holiday import run_holiday, stop_reason
from ptk.sim.data_models import Balance, GameData
from ptk.sim.events.director import queue_engine_event
from ptk.sim.matters.intake import with_matter
from ptk.sim.matters.models import SettlementOffer
from ptk.sim.partnership.models import (
    Approach,
    Vote,
    with_approach,
    with_firm_partnership,
    with_vote,
)
from ptk.sim.snapshot import TurnSnapshot
from tests.hiring_helpers import start

SLUG = "hol"


def _client(save_dir: Path) -> TestClient:
    client = TestClient(create_app())
    made = client.post("/api/saves", json={"slug": SLUG, "firm_name": "Away LLP", "seed": 4})
    assert made.status_code == 200, made.text
    return client


def test_each_stop_reason(data: GameData, balance: Balance) -> None:
    g = start(data, balance, seed=4)
    g.advance(2)  # March 2005
    while not g.state.market.open_matters(g.state.player.id):
        g.advance()
    state = g.state
    start_turn = state.turn - 1
    assert stop_reason(state, start_turn, 1, 6, None, balance) is None
    assert stop_reason(state, start_turn, 6, 6, None, balance) == "months"
    assert stop_reason(state, start_turn, 1, 6, state.turn, balance) == "date"
    fp = state.partnership.of(state.player.id)
    assert fp is not None
    partner = next(p.person_id for p in fp.partners)
    approached = replace(
        state,
        partnership=with_firm_partnership(
            state.partnership,
            with_approach(
                fp,
                Approach(
                    id=1,
                    firm_id=state.player.id,
                    person_id=partner,
                    suitor_key="x",
                    suitor_name="X LLP",
                    suitor_firm_id=None,
                    offer_comp_cents=1,
                    guarantee_years=0,
                    made_turn=state.turn - 1,
                    respond_by_turn=state.turn + 1,
                ),
            ),
        ),
    )
    assert stop_reason(approached, start_turn, 1, 6, None, balance) == "approach"
    assert stop_reason(approached, state.turn, 1, 6, None, balance) is None  # before it began
    voting = replace(
        state,
        partnership=with_firm_partnership(
            state.partnership,
            with_vote(
                fp,
                Vote(
                    id=1,
                    firm_id=state.player.id,
                    kind="terms",
                    subject_id=None,
                    params=(),
                    opened_turn=state.turn,
                    threshold_bp=5000,
                ),
            ),
        ),
    )
    assert stop_reason(voting, start_turn, 1, 6, None, balance) == "vote"
    matter = state.market.open_matters(state.player.id)[0]
    offered = replace(
        state,
        market=with_matter(
            state.market,
            replace(matter, settlement=SettlementOffer(5000, state.turn - 1, state.turn)),
        ),
    )
    assert stop_reason(offered, start_turn, 1, 6, None, balance) == "settlement_offer"
    ended = replace(state, save_meta=replace(state.save_meta, game_state="dissolved"))
    assert stop_reason(ended, start_turn, 1, 6, None, balance) == "game_over"


def test_december_with_an_eligible_associate_stops_for_the_vote(
    data: GameData, balance: Balance
) -> None:
    g = start(data, balance, seed=4)  # biglaw_spinout: the fourth-year is eligible in 2008
    while g.state.turn < 47:  # December 2008 is the next month to play
        g.advance()
    corp = next(p for p in g.state.people if p.role == "corporate_ma" and p.level == "associate_8")
    assert corp is not None
    assert stop_reason(g.state, 40, 1, 24, None, balance) == "vote"


def test_a_holiday_commits_each_month(save_dir: Path, data: GameData, balance: Balance) -> None:
    client = _client(save_dir)
    out = client.post(f"/api/saves/{SLUG}/holiday", json={"months": 3})
    assert out.status_code == 200, out.text
    body = out.json()
    assert body["months_played"] >= 1 and body["reason"] in {
        "months",
        "settlement_offer",
        "approach",
        "vote",
        "critical_event",
    }
    path = saves.open_save(save_dir, SLUG)
    played = body["months_played"]
    assert saves.read_state(path)[0].turn == played
    assert len(saves.snapshots(path, 1)) == played  # one committed turn a month
    until = client.post(
        f"/api/saves/{SLUG}/holiday", json={"until_year": 2005, "until_month": 12}
    ).json()
    assert until["reason"] in {"date", "settlement_offer", "approach", "vote", "critical_event"}
    if until["reason"] == "date":
        assert until["to_label"].endswith("2005") and saves.read_state(path)[0].turn == 11
    bad = client.post(f"/api/saves/{SLUG}/holiday", json={"months": 0})
    assert bad.status_code == 400 and bad.json()["code"] == "invalid_holiday"


def test_a_critical_event_stops_and_refuses_a_holiday(
    save_dir: Path, data: GameData, balance: Balance
) -> None:
    _client(save_dir)
    path = saves.open_save(save_dir, SLUG)
    sessions = make_sessionmaker(shared_engine(path))
    with sessions() as session, session.begin():
        state = load_state(session)
        state = queue_engine_event(state, "covenant_breach", state.turn + 1)
        write_turn(session, state, (), (), TurnSnapshot(turn=-1, firms=()))
    result = run_holiday(path, balance, data, months=12)
    assert result.reason == "critical_event" and result.months_played <= 2
    client = TestClient(create_app())
    refused = client.post(f"/api/saves/{SLUG}/holiday", json={"months": 2})
    assert refused.status_code == 409 and refused.json()["code"] == "critical_event_open"
