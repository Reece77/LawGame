"""PT-M4: the Partnership endpoints, the save round trip of the partnership, and the rule
that no partner's portability, true vote utility or confidence number reaches the API
(acceptance; CLAUDE.md section 10)."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

from ptk.api.app import create_app
from ptk.config import get_settings
from ptk.db import saves
from ptk.db.core import make_sessionmaker, shared_engine
from ptk.db.partnership_io import write_partnership
from ptk.loader import balance as load_balance
from ptk.loader import game_data
from ptk.sim.partnership.governance import base_utility
from ptk.sim.partnership.models import with_partner
from tests.integration.test_matters_api import FORBIDDEN
from tests.integration.test_people_api import _schema_closure

ROOTS = ("PartnershipOut",)
SLUG = "pt"


def _client(turns: int = 2, scenario: str = "group_lift", seed: int = 4) -> TestClient:
    client = TestClient(create_app())
    made = client.post(
        "/api/saves",
        json={"slug": SLUG, "firm_name": "Partners LLP", "seed": seed, "scenario_id": scenario},
    )
    assert made.status_code == 200, made.text
    for _ in range(turns):
        assert client.post(f"/api/saves/{SLUG}/advance").status_code == 200
    return client


def _path() -> Path:
    return saves.open_save(get_settings().resolved_save_dir(), SLUG)


def test_partnership_screen_data(save_dir: Path) -> None:
    client = _client()
    r = client.get(f"/api/saves/{SLUG}/partnership")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["you_are_mp"] and body["comp_system"] == "modified_lockstep"
    assert len(body["partners"]) == 3
    me = next(p for p in body["partners"] if p["is_you"])
    assert me["is_mp"] and me["confidence_label"] == "managing partner"
    others = [p for p in body["partners"] if not p["is_you"]]
    assert all(p["confidence_label"] in ("supportive", "neutral", "restless") for p in others)
    assert all(p["market_band"]["lo"] < p["market_band"]["hi"] for p in others)
    assert body["capital_cents"] == sum(p["capital_cents"] for p in body["partners"])
    assert {t["term"] for t in body["agreement"]} >= {"comp_system", "draw_share_bp"}
    w = body["whip"]
    assert sum(w[k]["lo"] for k in w) <= 2 <= sum(w[k]["hi"] for k in w)
    assert body["revolver"]["facility_cents"] == 200_000_000


def test_actions_through_the_api(save_dir: Path) -> None:
    client = _client()
    r = client.post(f"/api/saves/{SLUG}/partnership/capital-call", json={"amount_cents": 1_000_000})
    assert r.status_code == 200, r.text
    vote = next(v for v in r.json()["votes"] if v["kind"] == "capital_call")
    assert vote["status"] == "open" and vote["predicted_yes"] is not None
    dup = client.post(f"/api/saves/{SLUG}/partnership/capital-call", json={"amount_cents": 1})
    assert dup.status_code == 409 and dup.json()["code"] == "partnership_rule"
    assert client.post(f"/api/saves/{SLUG}/advance").status_code == 200
    body = client.get(f"/api/saves/{SLUG}/partnership").json()
    assert next(v for v in body["votes"] if v["vote_id"] == vote["vote_id"])["status"] in (
        "passed",
        "failed",
    )
    r = client.post(f"/api/saves/{SLUG}/partnership/draws", json={"suspended": True})
    assert r.status_code == 200 and r.json()["draws_suspended"]
    r = client.post(
        f"/api/saves/{SLUG}/partnership/laterals/search", json={"practice": "corporate_ma"}
    )
    assert r.status_code == 200, r.text
    lat = r.json()["laterals"][0]
    assert lat["book"]["lo"] < lat["book"]["hi"] and lat["clients"] == []
    r = client.post(f"/api/saves/{SLUG}/partnership/laterals/{lat['person_id']}/diligence")
    assert r.status_code == 200, r.text
    lat2 = next(x for x in r.json()["laterals"] if x["person_id"] == lat["person_id"])
    assert lat2["diligence"] and lat2["conflicts"] is not None
    bad = client.post(f"/api/saves/{SLUG}/partnership/terms", json={"term": "x", "value": 1})
    assert bad.status_code == 409


def test_the_partnership_survives_a_save_round_trip(save_dir: Path) -> None:
    # PT-M7: seed 5 (with overhead per lawyer the untouched group lift on seed 4 dissolves in
    # its fourteenth month; this test is about the round trip, so the firm must be alive)
    client = _client(turns=13, seed=5)
    state, _ = saves.read_state(_path())
    assert not state.ended
    fp = state.partnership.of(1)
    assert fp is not None and fp.last_profit_cents is not None and fp.pnl
    assert client.post(f"/api/saves/{SLUG}/advance").status_code == 200
    again, _ = saves.read_state(_path())
    fp2 = again.partnership.of(1)
    assert fp2 is not None and fp2.agreement == fp.agreement
    assert {p.person_id for p in fp2.partners} <= {p.person_id for p in fp.partners}


def test_no_hidden_value_reaches_the_api(save_dir: Path) -> None:
    client = _client()
    # plant distinctive hidden values: confidence, satisfaction, portability
    path = _path()
    state, _ = saves.read_state(path)
    fp = state.partnership.of(1)
    assert fp is not None
    for i, p in enumerate(fp.partners):
        fp = with_partner(fp, replace(p, confidence=37.1234 + i, satisfaction=-0.4321))
    people = tuple(
        replace(p, portability_bp=4321) if p.portability_bp is not None else p for p in state.people
    )
    state = replace(
        state,
        people=people,
        partnership=replace(state.partnership, firms=(fp,)),
    )
    from ptk.db.state_io import write_people

    with make_sessionmaker(shared_engine(path))() as session, session.begin():
        write_partnership(session, state.partnership)
        write_people(session, state)
    client.post(f"/api/saves/{SLUG}/partnership/capital-call", json={"amount_cents": 1_000_000})
    state, _ = saves.read_state(path)
    fp = state.partnership.of(1)
    assert fp is not None
    vote = fp.votes[-1]
    utilities = [
        base_utility(state, fp, vote, p, load_balance(), game_data()) for p in fp.equity_partners
    ]
    text = client.get(f"/api/saves/{SLUG}/partnership").text
    body = json.loads(text)
    assert "37.1234" not in text and "38.1234" not in text and "4321" not in text
    assert "0.4321" not in text
    for u in utilities:
        assert f"{u:.6g}" not in text
    keys = json.dumps(body)
    for word in ('confidence":', "satisfaction", "portability", "utility"):
        assert word not in keys
    # nothing hidden in the schema either
    schema = client.get("/openapi.json").json()
    for name in _schema_closure(schema, ROOTS):
        props = set(schema["components"]["schemas"][name].get("properties", {}))
        assert not props & (FORBIDDEN | {"confidence", "satisfaction", "portability_bp"}), name
