"""PT-M16: the Rankings and Press endpoints, the save round trip of reputation, the press and
the rankings (the history table included), and no hidden value in their schemas (CLAUDE.md
section 10; TST 29.6)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from ptk.api.app import create_app
from ptk.config import get_settings
from ptk.db import saves
from ptk.db.core import make_sessionmaker, shared_engine
from ptk.db.models import RankingEntryRow
from tests.integration.test_matters_api import FORBIDDEN
from tests.integration.test_people_api import _schema_closure

ROOTS = ("RankingsOut", "PressOut", "PracticeScreenOut", "PracticeHeadcountOut")
SLUG = "st"
HIDDEN = FORBIDDEN | {
    "potential",
    "portability",
    "book",
    "baseline",
    "shock",
    "weight",
}


def _client() -> TestClient:
    client = TestClient(create_app())
    body = {"slug": SLUG, "firm_name": "Founders LLP", "seed": 4, "scenario_id": "biglaw_spinout"}
    made = client.post("/api/saves", json=body)
    assert made.status_code == 200, made.text
    return client


def advance(client: TestClient) -> None:
    game = client.get(f"/api/saves/{SLUG}/game").json()
    if game["blocking_event_id"] is not None:
        r = client.post(
            f"/api/saves/{SLUG}/events/{game['blocking_event_id']}/choose", json={"choice": "A"}
        )
        assert r.status_code == 200, r.text
    r = client.post(f"/api/saves/{SLUG}/advance")
    assert r.status_code == 200, r.text


def test_no_standing_schema_names_a_hidden_value(save_dir: Path) -> None:
    spec = create_app().openapi()
    for name in _schema_closure(spec, ROOTS):
        props = spec["components"]["schemas"][name].get("properties", {})
        for field in props:
            assert not any(word in field.lower() for word in HIDDEN), (name, field)


def test_rankings_and_press_through_a_year(save_dir: Path) -> None:
    client = _client()
    for _ in range(14):  # to March 2006: the submission window
        advance(client)
    view = client.get(f"/api/saves/{SLUG}/rankings").json()
    sub = view["submission"]
    assert sub["window_open"] and not sub["made"] and sub["matters"]
    assert view["bands_year"] == 2005 and view["bands"]
    body = {
        "matter_ids": [m["matter_id"] for m in sub["matters"][:3]],
        "referee_ids": [r["client_id"] for r in sub["referees"][:2]],
    }
    made = client.post(f"/api/saves/{SLUG}/rankings/submission", json=body)
    assert made.status_code == 200, made.text
    assert made.json()["submission"]["made"] and made.json()["submission"]["strength_pct"] >= 0
    again = client.post(f"/api/saves/{SLUG}/rankings/submission", json=body)
    assert again.status_code in (400, 409, 422)
    # the press: answer any open moment with a measured word
    press = client.get(f"/api/saves/{SLUG}/press").json()
    assert 0 <= press["credibility"] <= 100
    opened = [m for m in press["moments"] if m["open"]]
    if opened:
        r = client.post(
            f"/api/saves/{SLUG}/press/{opened[0]['id']}/answer", json={"tone": "measured"}
        )
        assert r.status_code == 200, r.text
        answered = next(m for m in r.json()["moments"] if m["id"] == opened[0]["id"])
        assert answered["tone"] == "measured" and not answered["by_office"]
    for _ in range(8):  # to November 2006: April's tables and October's bands publish
        advance(client)
    view = client.get(f"/api/saves/{SLUG}/rankings").json()
    assert view["tables_year"] == 2005 and view["revenue"]
    assert view["bands_year"] == 2006
    assert view["league"] and view["places_year"] == 2006
    practices = client.get(f"/api/saves/{SLUG}/practices/screen").json()
    assert all(0 <= row["reputation"] <= 100 for row in practices)
    assert any(row["reputation_causes"] for row in practices)
    # every October's bands are in the save's history table
    path = saves.open_save(get_settings().resolved_save_dir(), SLUG)
    with make_sessionmaker(shared_engine(path))() as session:
        years = session.scalars(
            select(func.count(func.distinct(RankingEntryRow.year))).where(
                RankingEntryRow.kind == "bands"
            )
        ).one()
    assert years == 2
    # the state round-trips
    state = saves.read_state(path)[0]
    assert state.standing.reputation.entries
    assert state.standing.rankings.submission is not None
