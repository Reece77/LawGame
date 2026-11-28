"""PT-M8: the Leadership API on the practice save pt-2008 (a 60-lawyer firm at stage 2), its
schemas (no hidden value), and seat decisions logged as recomputed (ADR-0015)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from ptk.api.app import create_app
from ptk.db import saves
from ptk.db.core import make_sessionmaker, shared_engine
from ptk.db.models import DecisionLogRow
from ptk.loader import load_balance, load_game_data
from ptk.sim.decisions import Decisions
from ptk.sim.streams import RngFactory
from ptk.sim.turn import advance_turn
from tests.conftest import DATA_DIR

# Words no Leadership schema field may carry (CLAUDE.md 8; TST 18.8, 24.4, 27.6)
FORBIDDEN = (
    "score",
    "true",
    "quality",
    "mistake",
    "chance",
    "probability",
    "ambition",
    "hidden",
    "potential",
    "integrity_value",
    "right",
)
LEADERSHIP_SCHEMAS = (
    "LeadershipOut",
    "SeatOut",
    "SeatSlotOut",
    "SeatHolderOut",
    "SeatCandidateOut",
    "SeatGuardrailOut",
    "SeatDecisionOut",
    "SeatPitchOut",
    "SkillRangeOut",
)


def _fields(spec: dict[str, Any], name: str) -> set[str]:
    return set(spec["components"]["schemas"][name]["properties"])


def test_no_leadership_schema_names_a_hidden_value(save_dir: Path) -> None:
    spec = create_app().openapi()
    for name in LEADERSHIP_SCHEMAS:
        for field in _fields(spec, name):
            assert not any(word in field.lower() for word in FORBIDDEN), (name, field)


def test_appoint_a_cfo_authority_pitch_and_report(
    save_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PTK_DEBUG_ROUTES", "1")
    client = TestClient(create_app())
    assert client.post("/api/practice/pt-2008").status_code == 200
    base = "/api/saves/pt-2008/leadership"
    view = client.get(base).json()
    assert view["stage"] == 2
    seats = {s["key"]: s for s in view["seats"]}
    assert seats["cfo"]["open"] and not seats["pricing_director"]["open"]
    cfo_slot = seats["cfo"]["slots"][0]
    assert cfo_slot["holder"] is None and cfo_slot["candidates"]
    pick = cfo_slot["candidates"][0]["person_id"]
    view = client.post(f"{base}/appoint", json={"seat": "cfo", "person_id": pick}).json()
    cfo = next(s for s in view["seats"] if s["key"] == "cfo")["slots"][0]
    assert cfo["holder"]["person_id"] == pick and cfo["holder"]["fit"] in (
        "weak",
        "fair",
        "good",
        "strong",
    )
    bad = client.post(f"{base}/appoint", json={"seat": "pricing_director", "person_id": pick})
    assert bad.status_code == 409
    rails = [{"key": "writedown_bp", "value": 500}]
    view = client.post(
        f"{base}/authority", json={"seat": "cfo", "enabled": True, "guardrails": rails}
    ).json()
    cfo = next(s for s in view["seats"] if s["key"] == "cfo")["slots"][0]
    assert cfo["authority_enabled"]
    assert {g["key"]: g["value"] for g in cfo["guardrails"]}["writedown_bp"] == 500
    # the e2e suite's forced draw: the CFO pitches its cost programme now
    view = client.post("/api/saves/pt-2008/debug/pitch").json()
    pending = [p for p in view["pitches"] if p["status"] == "pending"]
    assert pending and pending[0]["holder_id"] == pick
    inbox = client.get("/api/saves/pt-2008/inbox").json()
    assert any(i["link_kind"] == "pitch" for i in inbox)
    pitch_id = pending[0]["id"]
    view = client.post(f"{base}/pitches/{pitch_id}/answer", json={"answer": "approve"}).json()
    assert next(p for p in view["pitches"] if p["id"] == pitch_id)["status"] == "approved"
    again = client.post(f"{base}/pitches/{pitch_id}/answer", json={"answer": "decline"})
    assert again.status_code == 409
    # June 2008 is a quarter's end: the CFO's report arrives with the month (a blocking critical
    # event takes its first choice first, as the e2e do: PT-M16's reputation moved which events
    # the practice save meets)
    game = client.get("/api/saves/pt-2008/game").json()
    if game["blocking_event_id"] is not None:
        choose = f"/api/saves/pt-2008/events/{game['blocking_event_id']}/choose"
        assert client.post(choose, json={"choice": "A"}).status_code == 200
    assert client.post("/api/saves/pt-2008/advance").status_code == 200
    inbox = client.get("/api/saves/pt-2008/inbox").json()
    reports = [i for i in inbox if "quarterly report" in i["title"]]
    assert reports and reports[0]["link_kind"] == "person" and reports[0]["link_id"] == pick


def test_seat_decisions_are_logged_as_recomputed(
    save_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = TestClient(create_app())
    assert client.post("/api/practice/pt-2008").status_code == 200
    base = "/api/saves/pt-2008/leadership"
    view = client.get(base).json()
    cmo = next(s for s in view["seats"] if s["key"] == "cmo")["slots"][0]
    pick = cmo["candidates"][0]["person_id"]
    client.post(f"{base}/appoint", json={"seat": "cmo", "person_id": pick})
    client.post(f"{base}/authority", json={"seat": "cmo", "enabled": True})
    data, balance = load_game_data(DATA_DIR), load_balance(DATA_DIR)
    path = saves.open_save(save_dir, "pt-2008")
    for _ in range(3):
        state, balances = saves.read_state(path)
        expected = advance_turn(
            state,
            Decisions(),
            RngFactory(state.save_meta.master_seed),
            balance,
            data,
            balances,
            answer_critical=True,
        ).seat_decisions
        saves.run_turn(path, balance, data, answer_critical=True)
        with make_sessionmaker(shared_engine(path))() as session:
            rows = session.scalars(
                select(DecisionLogRow).where(
                    DecisionLogRow.turn == state.turn, DecisionLogRow.source == "seat"
                )
            ).all()
        assert [json.loads(r.payload_json)["text"] for r in rows] == [d.text for d in expected]
