"""PT-M15: the Risk screen's API. No hidden value (a claim's merit or size, a claim not yet
surfaced, a case's culpability) in any schema or response; the actions round-trip."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

from ptk.api.app import create_app
from ptk.db import saves
from ptk.db.risk_io import write_risk
from ptk.db.session import make_sessionmaker, shared_engine
from ptk.sim.risk.models import Claim, DisciplinaryCase, with_case, with_claim
from tests.integration.test_people_api import _keys, _schema_closure

FORBIDDEN = {"merit", "size_cents", "culpability", "surfaces_turn", "created_turn"}
ROOTS = ("RiskScreenOut",)


def _client(save_dir: Path) -> TestClient:
    client = TestClient(create_app())
    made = client.post("/api/saves", json={"slug": "rk", "firm_name": "Risky LLP", "seed": 7})
    assert made.status_code == 200, made.text
    path = saves.open_save(save_dir, "rk")
    for _ in range(24):  # until the firm has a named matter
        assert client.post("/api/saves/rk/advance").status_code == 200
        state, _ = saves.read_state(path)
        if any(m.firm_id == state.player.id for m in state.market.matters):
            break
    matter = next(m for m in state.market.matters if m.firm_id == state.player.id)
    base = Claim(
        id=500,
        firm_id=state.player.id,
        matter_id=matter.id,
        client_id=matter.client_id,
        practice=matter.practice,
        source="error",
        created_turn=state.turn,
        surfaces_turn=state.turn + 5,
        merit=0.4321,
        size_cents=123_456_789,
        demand_cents=200_000_000,
    )
    offer = replace(
        base,
        id=501,
        stage="offer",
        noticed_turn=state.turn - 3,
        merit_lo=0.2,
        merit_hi=0.7,
        offer_cents=1_000_000,
        offer_expires=state.turn + 2,
        deductible_cents=10_000_000,
        limit_cents=500_000_000,
    )
    person = next(
        state.person(e.person_id) for e in state.staff(state.player.id)
        if not state.person(e.person_id).is_founder
    )  # fmt: skip
    case = DisciplinaryCase(
        id=502,
        firm_id=state.player.id,
        person_id=person.id,
        cause="neglect",
        jurisdiction="us_ny",
        opened_turn=state.turn,
        culpability=0.777,
    )
    risk = with_case(with_claim(with_claim(state.risk, base), offer), case)
    with make_sessionmaker(shared_engine(path))() as session, session.begin():
        write_risk(session, risk)
    return client


def test_no_hidden_value_in_any_risk_schema_or_response(save_dir: Path) -> None:
    client = _client(save_dir)
    spec = client.get("/openapi.json").json()
    schemas = _schema_closure(spec, ROOTS)
    assert {"MalpracticeClaimOut", "CaseOut", "PolicyOut", "InquiryOut"} <= schemas
    for name in schemas:
        props = set(spec["components"]["schemas"][name].get("properties", {}))
        assert not props & FORBIDDEN, (name, props & FORBIDDEN)
    body = client.get("/api/saves/rk/risk").json()
    assert not set(_keys(body)) & FORBIDDEN
    assert [c["id"] for c in body["claims"]] == [501]  # the latent claim is not shown
    text = str(body)
    assert "0.4321" not in text and "123456789" not in text and "0.777" not in text
    assert body["policy"] is not None and body["policy"]["premium_cents"] > 0


def test_risk_actions_round_trip(save_dir: Path) -> None:
    client = _client(save_dir)
    r = client.post("/api/saves/rk/risk/supervision", json={"supervision": "lax"})
    assert r.status_code == 200 and r.json()["supervision"] == "lax"
    r = client.post("/api/saves/rk/risk/terms", json={"deductible_cents": 25_000_000})
    assert r.status_code == 200 and r.json()["terms"]["deductible_cents"] == 25_000_000
    assert client.post("/api/saves/rk/risk/terms", json={"deductible_cents": 1}).status_code == 409
    r = client.post("/api/saves/rk/risk/claims/501/respond", json={"choice": "settle"})
    assert r.status_code == 200
    claim = next(c for c in r.json()["claims"] if c["id"] == 501)
    assert claim["outcome"] == "settled" and claim["indemnity_cents"] == 1_000_000
    assert claim["deductible_paid_cents"] == 1_000_000 and claim["insurer_paid_cents"] == 0
    r = client.post("/api/saves/rk/risk/cases/502/respond", json={"choice": "contest"})
    assert r.status_code == 200
    assert next(c for c in r.json()["cases"] if c["id"] == 502)["choice"] == "contest"
    again = client.post("/api/saves/rk/risk/cases/502/respond", json={"choice": "cooperate"})
    assert again.status_code == 409
