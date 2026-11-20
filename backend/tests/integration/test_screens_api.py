"""PT-M3c read views: the staffing board, the Practices screen, Explain, matter risk and a
client's share and panel status; and the hidden-value rule for every new schema."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from ptk.api.app import create_app
from ptk.api.matters import _risk
from ptk.api.screens import OUTLOOK_BANDS, explain, outlook_band, practices_screen
from ptk.sim.data_models import Balance, GameData
from ptk.sim.matters.intake import with_matter
from ptk.sim.matters.models import Matter, TeamMember
from ptk.sim.state import GameState
from tests.integration.test_matters_api import FORBIDDEN
from tests.integration.test_people_api import _keys, _schema_closure
from tests.matters_support import game, play

ROOTS = ("StaffingBoardOut", "PracticeScreenOut", "ExplainOut", "ClientRowOut", "MatterRowOut")
BANDS = {label for _top, label in OUTLOOK_BANDS}


def _client(save_dir: Path, turns: int = 3) -> TestClient:
    client = TestClient(create_app())
    made = client.post(
        "/api/saves",
        json={"slug": "scr", "firm_name": "Screens LLP", "seed": 3, "scenario_id": "group_lift"},
    )
    assert made.status_code == 200, made.text
    for _ in range(turns):
        assert client.post("/api/saves/scr/advance").status_code == 200
    return client


def _first_open(client: TestClient) -> dict[str, Any]:
    matters: list[dict[str, Any]] = client.get("/api/saves/scr/matters").json()
    assert matters, "group lift, seed 3, has an open matter by March"
    return matters[0]


def test_board_free_hours_are_exactly_what_the_engine_accepts(save_dir: Path) -> None:
    client = _client(save_dir)
    matter = _first_open(client)
    board = client.get(f"/api/saves/scr/matters/{matter['id']}/board").json()
    people = board["people"]
    assert people and board["practice"] == matter["practice"]
    on_team = [p["on_team"] for p in people]
    assert on_team == sorted(on_team, reverse=True), "the team comes first"
    assert board["events"] and board["events"][0]["title"]
    person = next(p for p in people if not p["on_team"] and p["free_hours"] > 1)
    url = f"/api/saves/scr/matters/{matter['id']}/team"
    over = client.post(
        url, json={"person_id": person["person"]["id"], "hours": int(person["free_hours"]) + 1}
    )
    assert over.status_code == 409 and over.json()["code"] == "over_capacity"
    assert "at most" in over.json()["message"]
    ok = client.post(
        url, json={"person_id": person["person"]["id"], "hours": int(person["free_hours"])}
    )
    assert ok.status_code == 200, ok.text
    after = client.get(f"/api/saves/scr/matters/{matter['id']}/board").json()
    mine = next(p for p in after["people"] if p["person"]["id"] == person["person"]["id"])
    assert mine["on_team"] and mine["free_hours"] == 0
    assert mine["warnings"], "planning to the limit is overtime"
    assert client.get("/api/saves/scr/matters/9999/board").status_code == 404


def test_practices_screen_agrees_with_the_market_view(save_dir: Path) -> None:
    client = _client(save_dir)
    rows = client.get("/api/saves/scr/practices/screen").json()
    market = {p["key"]: p for p in client.get("/api/saves/scr/practices").json()}
    assert len(rows) == 10
    for row in rows:
        m = market[row["key"]]
        assert len(row["demand_trend"]) == 3
        assert row["demand_trend"][-1]["cents"] == row["demand_cents"] == m["demand_cents"]
        assert row["revenue_cents"] == m["value_last_month_cents"]
        assert row["lawyers"] <= m["people"]
        assert [r["card_cents"] for r in row["rates"]] == [r["cents"] for r in m["rates"]]
    used = [r for r in rows if r["capacity_hours"] > 0]
    assert used and all(0 <= (r["utilisation_bp"] or 0) <= 20000 for r in used)


def test_explain_metrics(save_dir: Path) -> None:
    client = _client(save_dir)
    matter = _first_open(client)
    firm = client.get("/api/saves/scr/explain/utilisation").json()
    assert firm["subject"] == "the firm" and firm["value"] > 0 and len(firm["items"]) == 3
    named, flow, capacity = (i["amount"] for i in firm["items"])
    assert round(100 * (named + flow) / capacity, 1) == firm["value"]
    person = client.get("/api/saves/scr/people").json()[0]
    one = client.get(f"/api/saves/scr/explain/utilisation?entity={person['id']}").json()
    assert one["subject"] == person["name"]
    practice = client.get(
        f"/api/saves/scr/explain/utilisation?entity=practice:{matter['practice']}"
    ).json()
    assert practice["subject"]
    outlook = client.get(f"/api/saves/scr/explain/outlook?entity={matter['id']}").json()
    assert outlook["value"] is None and outlook["band"] in BANDS
    margin = client.get(f"/api/saves/scr/explain/matter_margin?entity={matter['id']}").json()
    assert (
        margin["items"][0]["amount"] + margin["items"][1]["amount"] == margin["items"][2]["amount"]
    )
    real = client.get(f"/api/saves/scr/explain/realisation?entity={matter['id']}").json()
    assert real["items"][0]["amount"] == matter["wip_cents"]
    assert client.get("/api/saves/scr/explain/outlook").status_code == 404
    assert client.get("/api/saves/scr/explain/outlook?entity=x").status_code == 404
    assert client.get("/api/saves/scr/explain/utilisation?entity=999").status_code == 404
    assert client.get("/api/saves/scr/explain/p_win?entity=1").status_code == 422


def test_no_hidden_value_in_any_screens_schema_or_response(save_dir: Path) -> None:
    client = _client(save_dir)
    spec = client.get("/openapi.json").json()
    schemas = _schema_closure(spec, ROOTS)
    assert {"BoardPersonOut", "ExplainItemOut", "TrendPointOut"} <= schemas
    for name in schemas:
        props = set(spec["components"]["schemas"][name].get("properties", {}))
        assert not props & FORBIDDEN, (name, props & FORBIDDEN)
    matter = _first_open(client)
    bodies: list[Any] = [
        client.get(f"/api/saves/scr/matters/{matter['id']}/board").json(),
        client.get("/api/saves/scr/practices/screen").json(),
        client.get("/api/saves/scr/clients").json(),
    ]
    for metric in ("utilisation", "realisation", "matter_margin", "outlook"):
        bodies.append(client.get(f"/api/saves/scr/explain/{metric}?entity={matter['id']}").json())
    for body in bodies:
        assert not set(_keys(body)) & FORBIDDEN


@pytest.fixture(scope="module")
def played(data: GameData, balance: Balance) -> GameState:
    return play(game(data, balance, 3, "group_lift"), data, balance, 3, seed=3)[0]


def test_outlook_ignores_hidden_values(played: GameState, data: GameData, balance: Balance) -> None:
    """The band comes from revealed ranges only: merits and opposing counsel never move it."""
    m = next(m for m in played.market.open_matters(played.player.id))
    base = explain(played, "outlook", str(m.id), data, balance)
    for merits, opposing in ((-3.0, 19.0), (3.0, 1.0)):
        hidden = replace(m, merits=merits, opposing_quality=opposing)
        state = replace(played, market=with_matter(played.market, hidden))
        assert explain(state, "outlook", str(m.id), data, balance) == base


def test_outlook_bands_cover_every_chance() -> None:
    assert outlook_band(0.0) == "Uphill"
    assert outlook_band(0.5) == "Even"
    assert outlook_band(1.0) == "Strong"
    assert [outlook_band(t - 1e-9) for t, _ in OUTLOOK_BANDS] == [b for _, b in OUTLOOK_BANDS]


def test_demand_trend_replays_the_turns_draws(
    played: GameState, data: GameData, balance: Balance
) -> None:
    rows = practices_screen(played, data, balance)
    assert [r.demand_cents for r in rows] == list(played.market.demand_cents)


def test_risk_levels() -> None:
    m = Matter(
        id=1,
        firm_id=1,
        client_id=1,
        practice="corporate_ma",
        kind_key="private_ma",
        kind="deal",
        name="x",
        opened_turn=0,
        planned_months=6,
        expected_fees_cents=1,
        hours_needed_tenths=100,
    )
    assert _risk(m, False) == ("high", ["Nobody staffed"])
    staffed = replace(m, team=(TeamMember(person_id=1, role="lead", planned_tenths=100),))
    assert _risk(staffed, False) == ("low", [])
    assert _risk(replace(staffed, under_months=1), False)[0] == "medium"
    assert _risk(replace(staffed, missed_deadlines=2), False) == ("high", ["2 missed deadlines"])
    assert _risk(staffed, True)[0] == "high"
    assert _risk(replace(staffed, status="closed", missed_deadlines=3), False) == ("low", [])


def test_client_share_and_panel_status(save_dir: Path) -> None:
    client = _client(save_dir)
    rows = client.get("/api/saves/scr/clients").json()
    assert rows
    for c in rows:
        assert c["panel_status"] in {"key", "active", "dormant"}
        share, wallet = c["share_estimate"], c["wallet_estimate"]
        assert share["lo"] <= share["hi"]
        if wallet["hi"]:
            assert share["lo"] == 10000 * c["fees_12m_cents"] // wallet["hi"]
    assert any(c["panel_status"] == "key" for c in rows)
