"""PT-M9: the Automation API on the practice save pt-2008 (Reece's manual check: automate
billing, campus hiring and one group's staffing, set limits, play on and read the digests), its
schemas (no hidden value), and area decisions logged as recomputed (ADR-0015)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select

from ptk.api.app import create_app
from ptk.db import saves
from ptk.db.models import DecisionLogRow
from ptk.db.session import make_sessionmaker, shared_engine
from ptk.loader import load_balance, load_game_data
from ptk.sim.decisions import Decisions
from ptk.sim.rng import RngFactory
from ptk.sim.turn import advance_turn
from tests.conftest import DATA_DIR

# Words no Automation schema field may carry (CLAUDE.md 10; TST 40.11)
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
    "overload",
    "draw",
    "best",
    "right",
)
AUTOMATION_SCHEMAS = (
    "AutomationOut",
    "AreaRowOut",
    "AreaPersonOut",
    "GuardrailValueOut",
    "AreaLineOut",
    "KpiOut",
    "ProposalOut",
    "OwnerRecordOut",
    "DigestOut",
    "DigestAreaOut",
    "RunByOut",
    "GiveIn",
    "TakeOverIn",
    "SettingsIn",
    "InboxItemOut",
)
BASE = "/api/saves/pt-2008/automation"


def _fields(spec: dict[str, Any], name: str) -> set[str]:
    return set(spec["components"]["schemas"][name]["properties"])


def test_no_automation_schema_names_a_hidden_value(save_dir: Path) -> None:
    spec = create_app().openapi()
    for name in AUTOMATION_SCHEMAS:
        for field in _fields(spec, name):
            assert not any(word in field.lower() for word in FORBIDDEN), (name, field)


def _appoint(client: TestClient, seat: str) -> int:
    lead = "/api/saves/pt-2008/leadership"
    view = client.get(lead).json()
    slot = next(s for s in view["seats"] if s["key"] == seat)["slots"][0]
    pick = int(slot["candidates"][0]["person_id"])
    assert client.post(f"{lead}/appoint", json={"seat": seat, "person_id": pick}).status_code == 200
    return pick


def _group(client: TestClient) -> None:
    """A practice group led by an equity partner, as the player would make one."""
    from ptk.config import get_settings
    from ptk.db.org_io import run_org_action
    from ptk.sim.org.actions import CreateUnit, MovePerson, SetLeader

    data, balance = load_game_data(DATA_DIR), load_balance(DATA_DIR)
    path = saves.open_save(get_settings().resolved_save_dir(), "pt-2008")
    state = saves.read_state(path)[0]
    founder = state.founder_of(state.player.id)
    assert founder is not None
    lead = next(
        p for p in state.people
        if p.level == "equity_partner" and not p.is_founder
        and state.employer_of(p.id) == state.player.id
    )  # fmt: skip
    practice = data.role(lead.role).practice
    unit = run_org_action(
        path, CreateUnit(founder, "practice_group", practice=practice), balance, data
    ).unit_id
    assert unit is not None
    for e in state.staff(state.player.id):
        p = state.person(e.person_id)
        if p.role == lead.role and not p.is_founder:
            run_org_action(path, MovePerson(founder, p.id, unit), balance, data)
    run_org_action(path, SetLeader(founder, unit, lead.id), balance, data)


def _setup(client: TestClient) -> dict[str, Any]:
    assert client.post("/api/practice/pt-2008").status_code == 200
    view = client.get(BASE).json()
    rows = {(r["area"], r["slot"]): r for r in view["areas"]}
    assert rows[("billing", 0)]["status"] == "unavailable"  # no CFO yet
    assert "seat" in rows[("billing", 0)]["reason"]
    assert rows[("knowledge", 0)]["status"] == "unavailable"
    cfo = _appoint(client, "cfo")
    chro = _appoint(client, "chro")
    view = client.post(
        f"{BASE}/give", json={"area": "billing", "person_id": cfo, "limit_cents": 5_000_000}
    ).json()
    view = client.post(f"{BASE}/give", json={"area": "hiring", "person_id": chro}).json()
    assert next(r for r in view["areas"] if r["area"] == "staffing")["status"] == "unavailable"
    _group(client)
    view = client.get(BASE).json()
    staffing = next(r for r in view["areas"] if r["area"] == "staffing" and r["status"] == "manual")
    leader = staffing["eligible"][0]["person_id"]
    view = client.post(
        f"{BASE}/give", json={"area": "staffing", "slot": staffing["slot"], "person_id": leader}
    ).json()
    view = client.post(
        f"{BASE}/settings",
        json={"area": "billing", "guardrails": [{"key": "writedown_bp", "value": 500}]},
    ).json()
    # June 2008 runs at under 60% utilisation: hire from 50% so the CHRO has work to do
    view = client.post(
        f"{BASE}/settings",
        json={"area": "hiring", "guardrails": [{"key": "busy_bp", "value": 5000}]},
    ).json()
    return view


def test_the_manual_check_automates_three_areas_and_reads_digests(save_dir: Path) -> None:
    client = TestClient(create_app())
    view = _setup(client)
    automated = [r for r in view["areas"] if r["status"] == "automated"]
    assert {r["area"] for r in automated} == {"billing", "hiring", "staffing"}
    billing = next(r for r in automated if r["area"] == "billing")
    assert billing["limit_cents"] == 5_000_000 and billing["monthly_cents"] == 15_000_000
    assert {g["key"]: g["value"] for g in billing["guardrails"]}["writedown_bp"] == 500
    assert billing["owner"]["fit"] in ("weak", "fair", "good", "strong", "unknown")
    run_by = client.get(f"{BASE}/run-by/billing").json()
    assert run_by["owner"]["person_id"] == billing["owner"]["person_id"]
    for _ in range(3):
        assert client.post("/api/saves/pt-2008/advance").status_code == 200
    inbox = client.get("/api/saves/pt-2008/inbox").json()
    digests = [i for i in inbox if i["template"] == "automation_digest"]
    assert len(digests) == 3 and digests[0]["title"].startswith("Your month:")
    assert digests[0]["link_kind"] == "automation"
    everything = client.get("/api/saves/pt-2008/inbox", params={"everything": True}).json()
    assert len(everything) >= len(inbox)
    assert not any(i["in_digest"] for i in inbox)
    digest = client.get(f"{BASE}/digest/{digests[0]['link_id']}").json()
    assert {a["area"] for a in digest["areas"]} == {"billing", "hiring", "staffing"}
    view = client.get(BASE).json()
    assert view["owners"] and all(o["capacity"] == 100 for o in view["owners"])
    view = client.post(f"{BASE}/take-over", json={"area": "billing"}).json()
    assert next(r for r in view["areas"] if r["area"] == "billing")["status"] == "manual"
    assert client.get(f"{BASE}/run-by/billing").json()["owner"] is None


def test_area_decisions_are_logged_as_recomputed(save_dir: Path) -> None:
    client = TestClient(create_app())
    _setup(client)
    data, balance = load_game_data(DATA_DIR), load_balance(DATA_DIR)
    path = saves.open_save(save_dir, "pt-2008")
    seen = 0
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
        ).area_decisions
        saves.run_turn(path, balance, data, answer_critical=True)
        with make_sessionmaker(shared_engine(path))() as session:
            rows = session.scalars(
                select(DecisionLogRow).where(
                    DecisionLogRow.turn == state.turn, DecisionLogRow.source == "area"
                )
            ).all()
        got = [json.loads(r.payload_json) for r in rows]
        from dataclasses import asdict

        assert got == [json.loads(json.dumps(asdict(d), sort_keys=True)) for d in expected]
        seen += len(got)
    assert seen, "no area decided anything in three months"
