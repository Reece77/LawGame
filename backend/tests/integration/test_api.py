from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from ptk.api.app import create_app


def test_new_game_advance_and_errors(save_dir: Path) -> None:
    client = TestClient(create_app())
    meta = client.get("/api/meta").json()
    assert any(s["id"] == "biglaw_spinout" for s in meta["scenarios"])
    made = client.post("/api/saves", json={"slug": "api", "firm_name": "Acme LLP"})
    assert made.status_code == 200, made.text
    assert made.json()["date_label"] == "Jan 2005"
    assert made.json()["cash_cents"] == 60_000_000
    moved = client.post("/api/saves/api/advance").json()
    assert moved["turn"] == 1 and moved["date_label"] == "Feb 2005"
    assert [s["slug"] for s in client.get("/api/saves").json()] == ["api"]
    again = client.post("/api/saves", json={"slug": "api", "firm_name": "Acme LLP"})
    assert again.status_code == 409 and again.json()["code"] == "save_exists"
    missing = client.get("/api/saves/nope/game")
    assert missing.status_code == 404 and missing.json()["code"] == "save_not_found"
    bad = client.post("/api/saves", json={"slug": "x", "firm_name": "A", "scenario_id": "zzz"})
    assert bad.status_code == 400 and bad.json()["code"] == "unknown_scenario"
