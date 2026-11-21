"""Practices, clients and matters endpoints (PT-M3a sub-task 8), the hidden-value rule, the
save round trip and the CLI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from ptk.api.app import create_app
from ptk.cli import app as cli
from ptk.config import get_settings
from ptk.db import saves
from ptk.sim.data_models import Balance, GameData
from ptk.sim.ledger import apply_entries
from tests.integration.test_people_api import _keys, _schema_closure
from tests.matters_support import play

# Hidden values (CLAUDE.md section 10): a matter's merits and win chance, opposing counsel's
# quality, judges' traits, a GC's personality, escaped errors, the true wallet.
FORBIDDEN = {
    "merits",
    "p_win",
    "win_chance",
    "opposing_quality",
    "traits",
    "personality",
    "hidden",
    "errors_escaped",
    "hidden_conflict",
    "wallet_cents",
    "craft_hours",
    "craft_weight",
    "quality",
    "docket_speed",
    "settlement_pressure",
    "fraction_bp",
    "stakes_cents",
}
ROOTS = ("PracticeMarketOut", "ClientRowOut", "ClientOut", "MatterRowOut", "MatterOut")


def _client(save_dir: Path, turns: int = 4) -> TestClient:
    client = TestClient(create_app())
    made = client.post("/api/saves", json={"slug": "mat", "firm_name": "Acme LLP", "seed": 9})
    assert made.status_code == 200, made.text
    for _ in range(turns):
        assert client.post("/api/saves/mat/advance").status_code == 200
    return client


def test_practices_clients_and_matters(save_dir: Path) -> None:
    client = _client(save_dir)
    practices = client.get("/api/saves/mat/practices").json()
    assert practices[0]["key"] == "corporate_ma" and len(practices) == 10
    assert abs(sum(p["demand_base_cents"] for p in practices) * 12 - 1_235_000_000_000) < 100
    assert all(r["cents"] > 0 for p in practices for r in p["rates"])
    clients = client.get("/api/saves/mat/clients").json()
    assert clients and all(0 <= c["relationship"] <= 100 for c in clients)
    assert all(c["wallet_estimate"]["lo"] <= c["wallet_estimate"]["hi"] for c in clients)
    detail = client.get(f"/api/saves/mat/clients/{clients[0]['id']}").json()
    assert detail["general_counsel"]["name"] and detail["panel"]
    assert {x["practice"] for x in detail["cross_sell"]}.isdisjoint(detail["practices"])
    assert client.get("/api/saves/mat/clients/99999").status_code == 404
    matters = client.get("/api/saves/mat/matters?status=all").json()
    assert matters, "four months bring named matters"
    open_m = client.get("/api/saves/mat/matters").json()
    assert all(m["status"] == "open" for m in open_m)
    m = client.get(f"/api/saves/mat/matters/{matters[0]['id']}").json()
    assert m["phases"] and m["team"] is not None
    assert client.get("/api/saves/mat/matters/99999").status_code == 404


def test_staffing_through_the_api_refuses_over_capacity(save_dir: Path) -> None:
    client = _client(save_dir)
    matter = next(m for m in client.get("/api/saves/mat/matters").json())
    detail = client.get(f"/api/saves/mat/matters/{matter['id']}").json()
    on_team = {t["person"]["id"] for t in detail["team"]}
    person = next(
        p["id"] for p in client.get("/api/saves/mat/people").json() if p["id"] not in on_team
    )
    over = client.post(
        f"/api/saves/mat/matters/{matter['id']}/team", json={"person_id": person, "hours": 390}
    )
    assert over.status_code == 409 and over.json()["code"] == "over_capacity"
    ok = client.post(
        f"/api/saves/mat/matters/{matter['id']}/team", json={"person_id": person, "hours": 10}
    )
    assert ok.status_code == 200, ok.text
    assert person in {t["person"]["id"] for t in ok.json()["team"]}
    hours = client.put(f"/api/saves/mat/matters/{matter['id']}/team/{person}", json={"hours": 12})
    assert (
        next(t for t in hours.json()["team"] if t["person"]["id"] == person)["planned_hours"] == 12
    )
    gone = client.delete(f"/api/saves/mat/matters/{matter['id']}/team/{person}")
    assert person not in {t["person"]["id"] for t in gone.json()["team"]}
    lead = gone.json()["lead"]["id"]
    refused = client.delete(f"/api/saves/mat/matters/{matter['id']}/team/{lead}")
    assert refused.status_code == 400 and refused.json()["code"] == "staffing"
    again = client.post(f"/api/saves/mat/matters/{matter['id']}/default-staffing")
    assert again.status_code == 200 and again.json()["lead"] is not None
    checks = client.put("/api/saves/mat/conflict-checks", json={"enabled": False})
    assert checks.json() == {"enabled": False}
    assert client.get("/api/saves/mat/conflict-checks").json() == {"enabled": False}
    no_offer = client.post(
        f"/api/saves/mat/matters/{matter['id']}/settlement", json={"accept": True}
    )
    assert no_offer.status_code == 409


def test_no_hidden_value_in_any_matters_schema_or_response(save_dir: Path) -> None:
    client = _client(save_dir, turns=8)
    spec = client.get("/openapi.json").json()
    schemas = _schema_closure(spec, ROOTS)
    assert {"MatterOut", "TeamMemberOut", "GeneralCounselOut", "SettlementOut"} <= schemas
    for name in schemas:
        props = set(spec["components"]["schemas"][name].get("properties", {}))
        assert not props & FORBIDDEN, (name, props & FORBIDDEN)
    bodies: list[Any] = [client.get("/api/saves/mat/practices").json()]
    clients = client.get("/api/saves/mat/clients").json()
    bodies += [clients] + [client.get(f"/api/saves/mat/clients/{c['id']}").json() for c in clients]
    matters = client.get("/api/saves/mat/matters?status=all").json()
    bodies += [matters] + [client.get(f"/api/saves/mat/matters/{m['id']}").json() for m in matters]
    for body in bodies:
        assert not set(_keys(body)) & FORBIDDEN


def test_save_round_trip_keeps_the_market(save_dir: Path, data: GameData, balance: Balance) -> None:
    saves.create_save(
        save_dir,
        "rt",
        firm_name="F",
        scenario_id="group_lift",
        difficulty="standard",
        data=data,
        balance=balance,
        seed=21,
    )
    path = saves.open_save(save_dir, "rt")
    for _ in range(9):
        saves.run_turn(path, balance, data, answer_critical=True)
    loaded, _ = saves.read_state(path)
    # the same months played in memory give the same market
    from ptk.sim.setup import new_game

    fresh = new_game(
        name="rt",
        firm_name="F",
        master_seed=21,
        scenario_id="group_lift",
        difficulty="standard",
        data=data,
        balance=balance,
    )
    played, _ = play(
        fresh.state,
        data,
        balance,
        9,
        seed=21,
        write_events=True,
        ledger=apply_entries({}, fresh.ledger_entries),
    )
    assert loaded.market == played.market
    assert loaded.firms == played.firms


def test_cli_matters_and_staff(save_dir: Path) -> None:
    runner = CliRunner()
    assert runner.invoke(cli, ["new-game", "--name", "cli", "--seed", "40"]).exit_code == 0
    assert runner.invoke(cli, ["advance", "--save", "cli", "--turns", "4"]).exit_code == 0
    out = runner.invoke(cli, ["matters", "--save", "cli", "--status", "all"])
    assert out.exit_code == 0 and "matter 1" in out.output
    shown = runner.invoke(cli, ["staff", "show", "--save", "cli", "--matter", "1"])
    assert shown.exit_code == 0
    bad = runner.invoke(
        cli,
        ["staff", "assign", "--save", "cli", "--matter", "1", "--person", "4", "--hours", "999"],
    )
    assert bad.exit_code == 1
    assert get_settings().resolved_save_dir() == save_dir
