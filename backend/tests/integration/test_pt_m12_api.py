"""PT-M12 sub-task 9: the Practices screen shows the twenty with their driver, cycle, the
firm's position and main billing model; Enter practice; the matter's contingency and funding
fields (none names a hidden value)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from ptk.api.app import create_app
from tests.integration.test_matters_api import FORBIDDEN

SLUG = "twenty"
FUNDING_FIELDS = (
    "billing_model",
    "contingency_share_bp",
    "contingency_wip_cents",
    "funded",
    "funded_bp",
    "funder_return_bp",
    "funder_advances_cents",
    "funding_offer_bp",
    "funding_offer_return_bp",
)


def _client() -> TestClient:
    client = TestClient(create_app())
    body = {"slug": SLUG, "firm_name": "Twenty LLP", "seed": 1, "scenario_id": "biglaw_spinout"}
    made = client.post("/api/saves", json=body)
    assert made.status_code == 200, made.text
    return client


def test_the_practices_screen_shows_twenty_with_cycle_and_position(save_dir: Path) -> None:
    client = _client()
    rows = client.get(f"/api/saves/{SLUG}/practices/screen").json()
    assert len(rows) == 20
    by = {r["key"]: r for r in rows}
    assert by["restructuring"]["cycle"] == "counter_cyclical"
    assert by["financial_regulation"]["cycle"] == "policy"
    assert by["mass_torts"]["billing_model"] == "contingency"
    assert by["private_client"]["billing_model"] == "retainer"
    assert by["corporate_ma"]["practised"] and not by["tax"]["practised"]
    assert all(r["driver"] for r in rows)


def test_enter_a_practice_by_a_lateral_partner_search(save_dir: Path) -> None:
    client = _client()
    out = client.post(
        f"/api/saves/{SLUG}/practices/international_arbitration/enter",
        json={"route": "lateral", "person_id": None},
    )
    assert out.status_code == 200, out.text
    partnership = client.get(f"/api/saves/{SLUG}/partnership").json()
    assert any(c["practice"] == "international_arbitration" for c in partnership["laterals"])
    again = client.post(
        f"/api/saves/{SLUG}/practices/corporate_ma/enter",
        json={"route": "team", "person_id": None},
    )
    assert again.status_code >= 400  # already practised: the engine's refusal


def test_funding_is_refused_on_a_matter_that_is_not_contingency(save_dir: Path) -> None:
    client = _client()
    client.post(f"/api/saves/{SLUG}/advance")
    matters = client.get(f"/api/saves/{SLUG}/matters").json()
    if not matters:
        return
    m = client.get(f"/api/saves/{SLUG}/matters/{matters[0]['id']}").json()
    for field in FUNDING_FIELDS:
        assert field in m
    if m["billing_model"] != "contingency":
        refused = client.post(f"/api/saves/{SLUG}/matters/{m['id']}/funding")
        assert refused.status_code >= 400


def test_no_funding_field_names_a_hidden_value(save_dir: Path) -> None:
    props = create_app().openapi()["components"]["schemas"]["MatterOut"]["properties"]
    for field in FUNDING_FIELDS:
        assert field in props
        assert not any(word in field.lower() for word in FORBIDDEN), field
