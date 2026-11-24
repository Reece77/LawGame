"""PT-M14: the Technology endpoints, the save round trip of the firm's technology, the matter
page's AI fields, and no hidden value in their schemas (CLAUDE.md section 10: partners'
adaptability and technology, the CKO's effect, the seeded targets)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from ptk.api.app import create_app
from ptk.config import get_settings
from ptk.db import saves
from tests.integration.test_matters_api import FORBIDDEN
from tests.integration.test_people_api import _schema_closure

ROOTS = ("TechOut",)  # MatterOut and PracticeScreenOut gain only ai_* fields (checked below)
SLUG = "tech"
HIDDEN = FORBIDDEN | {"adaptability", "buyin", "buy_in", "target", "seed", "effect", "score"}


def _client() -> TestClient:
    client = TestClient(create_app())
    body = {"slug": SLUG, "firm_name": "Founders LLP", "seed": 4, "scenario_id": "biglaw_spinout"}
    made = client.post("/api/saves", json=body)
    assert made.status_code == 200, made.text
    return client


def test_no_tech_schema_names_a_hidden_value(save_dir: Path) -> None:
    spec = create_app().openapi()
    for name in _schema_closure(spec, ROOTS):
        props = spec["components"]["schemas"][name].get("properties", {})
        for field in props:
            assert not any(word in field.lower() for word in HIDDEN), (name, field)
    for name in ("MatterOut", "PracticeScreenOut"):
        props = spec["components"]["schemas"][name]["properties"]
        for field in (f for f in props if f.startswith("ai_")):
            assert not any(word in field.lower() for word in HIDDEN), (name, field)


def test_technology_view_and_actions(save_dir: Path) -> None:
    client = _client()
    view = client.get(f"/api/saves/{SLUG}/tech").json()
    keys = [e["key"] for e in view["eras"]]
    assert keys == ["ediscovery", "offshore", "tar", "contract_analysis", "genai", "agentic"]
    assert [e["available"] for e in view["eras"]] == [True, False, False, False, False, False]
    assert all(t["efficiency_pct"] == 100 for t in view["tasks"])
    assert not view["clients"]["pressure"] and not view["can_launch"]
    # generative AI does not exist in 2005; products open at stage 3
    refused = client.post(
        f"/api/saves/{SLUG}/tech/invest", json={"era": "genai", "subscription_bp": 10000}
    )
    assert refused.status_code == 409 and refused.json()["code"] == "tech_action"
    refused = client.post(
        f"/api/saves/{SLUG}/tech/products",
        json={"practice": "corporate_ma", "kind_key": "private_ma", "price_bp": 10000},
    )
    assert refused.status_code == 409
    ok = client.post(
        f"/api/saves/{SLUG}/tech/invest", json={"era": "ediscovery", "subscription_bp": 10000}
    )
    assert ok.status_code == 200, ok.text
    era = ok.json()["eras"][0]
    assert era["platform"] and era["subscription_bp"] == 10000 and era["monthly_cents"] > 0
    ok = client.post(f"/api/saves/{SLUG}/tech/training", json={"hours": 40})
    assert ok.json()["training"]["hours"] == 40
    assert client.post(f"/api/saves/{SLUG}/advance").status_code == 200
    # round trip: what the save holds is what the view shows
    path = saves.open_save(get_settings().resolved_save_dir(), SLUG)
    state = saves.read_state(path)[0]
    firm = state.tech.firm(state.player.id)
    assert firm is not None and firm.training_hours == 40
    assert firm.era("ediscovery") is not None and firm.era("ediscovery").adoption > 0  # type: ignore[union-attr]
    view = client.get(f"/api/saves/{SLUG}/tech").json()
    assert view["eras"][0]["adoption_pct"] == round(100 * firm.era("ediscovery").adoption)  # type: ignore[union-attr]
    practices = client.get(f"/api/saves/{SLUG}/screens/practices")
    if practices.status_code == 200:
        assert all("ai_cut_bp" in p for p in practices.json())
