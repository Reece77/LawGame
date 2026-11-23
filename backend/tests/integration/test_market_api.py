"""Market endpoints (PT-M5 sub-task 8), the hidden-value rule, the save round trip of the
rivals, and ADR-0015's replay rule for their decisions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select

from ptk.api.app import create_app
from ptk.db import saves
from ptk.db.models import DecisionLogRow
from ptk.db.rivals_io import _CACHE
from ptk.db.session import make_sessionmaker, shared_engine
from ptk.sim.data_models import Balance, GameData
from ptk.sim.decisions import Decisions
from ptk.sim.rng import RngFactory
from ptk.sim.turn import advance_turn
from tests.integration.test_people_api import _keys, _schema_closure

# Hidden values (CLAUDE.md section 10) of rivals: demand, shocks, the player's effects on
# them, utilities and needs, a key person's book and portability, cost and capacity.
FORBIDDEN = {
    "demand_cents",
    "shock",
    "offset_cents",
    "utility",
    "need",
    "book_cents",
    "portability_bp",
    "rpl_cap_cents",
    "cost_per_lawyer_cents",
    "utilisation",
    "rate_index",
    "hidden",
    "personality_traits",
    "skills",
    "potential_ability",
    "probability",
    "opposing_quality",
}
ROOTS = ("MarketOut", "RivalOut", "MatterOut")


def _client(save_dir: Path, turns: int = 3) -> TestClient:
    client = TestClient(create_app())
    made = client.post("/api/saves", json={"slug": "mkt", "firm_name": "Acme LLP", "seed": 11})
    assert made.status_code == 200, made.text
    for _ in range(turns):
        assert client.post("/api/saves/mkt/advance").status_code == 200
    return client


def test_market_rival_and_actions(save_dir: Path) -> None:
    client = _client(save_dir)
    market = client.get("/api/saves/mkt/market").json()
    names = [r["name"] for r in market["rivals"]]
    assert "Skadden, Arps, Slate, Meagher & Flom" in names
    assert market["rivals"][0]["revenue_cents"] >= market["rivals"][-1]["revenue_cents"]
    claims = ["references", "track_record", "continuity", "ai_efficiency"]  # PT-M14
    assert market["claims"] == claims
    skadden = next(r for r in market["rivals"] if r["short"] == "Skadden")
    rival = client.get(f"/api/saves/mkt/rivals/{skadden['id']}").json()
    assert rival["people"] and any(p["real"] for p in rival["people"])
    assert rival["personality"] == "Performance machine"
    assert client.get("/api/saves/mkt/rivals/999999").status_code == 404
    after = client.post(f"/api/saves/mkt/rivals/{skadden['id']}/approach", json={})
    assert after.status_code == 200, after.text
    rival = client.get(f"/api/saves/mkt/rivals/{skadden['id']}").json()
    assert any(p["met"] for p in rival["people"])
    bad = client.post("/api/saves/mkt/rfps/999/pitch", json={"team": [1], "claims": []})
    assert bad.status_code == 400
    assert client.post("/api/saves/mkt/approaches/999/counter").status_code == 400


def test_no_hidden_value_in_any_market_schema_or_response(save_dir: Path) -> None:
    client = _client(save_dir, turns=2)
    spec = client.get("/openapi.json").json()
    schemas = _schema_closure(spec, ROOTS)
    assert {"RivalRowOut", "KeyPersonOut", "RfpOut", "RivalApproachOut", "NewsOut"} <= schemas
    for name in schemas:
        props = set(spec["components"]["schemas"][name].get("properties", {}))
        assert not props & FORBIDDEN, (name, props & FORBIDDEN)
    market = client.get("/api/saves/mkt/market").json()
    bodies: list[Any] = [market]
    bodies += [client.get(f"/api/saves/mkt/rivals/{r['id']}").json() for r in market["rivals"][:5]]
    for body in bodies:
        assert not set(_keys(body)) & FORBIDDEN


def test_rivals_round_trip_and_replay(save_dir: Path, data: GameData, balance: Balance) -> None:
    saves.create_save(
        save_dir, "rr", firm_name="F", scenario_id="biglaw_spinout", difficulty="standard",
        data=data, balance=balance, seed=12,
    )  # fmt: skip
    path = saves.open_save(save_dir, "rr")
    before, balances = saves.read_state(path)
    expected = advance_turn(before, Decisions(), RngFactory(12), balance, data, balances)
    for _ in range(3):
        saves.run_turn(path, balance, data)
    _CACHE.clear()  # read the rivals back from the database itself
    loaded, _ = saves.read_state(path)
    played = before
    bal = balances
    from ptk.sim.ledger import apply_entries

    for _ in range(3):
        result = advance_turn(played, Decisions(), RngFactory(12), balance, data, bal)
        bal = dict(apply_entries(bal, result.ledger_entries))
        played = result.new_state
    assert loaded.rivals == played.rivals
    assert loaded.market.judges == played.market.judges
    assert expected.rival_moves  # the rivals decide every month
    # The decision log holds every rival move, and replay recomputes them exactly.
    with make_sessionmaker(shared_engine(path))() as session:
        rows = session.scalars(
            select(DecisionLogRow)
            .where(DecisionLogRow.source == "rival")
            .order_by(DecisionLogRow.id)
        ).all()
    first = [json.loads(r.payload_json) for r in rows if r.turn == 0]
    assert [m["action"] for m in first] == [m.action for m in expected.rival_moves]
    assert [m["detail"] for m in first] == [m.detail for m in expected.rival_moves]
