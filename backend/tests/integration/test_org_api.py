"""Org endpoints (PT-M2 sub-task 5): read the org, reorganise, plans; and the hidden-value
rule for every org schema (no true skill, quality, span limit or potential)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from ptk.api.app import create_app
from tests.integration.test_people_api import FORBIDDEN, _keys, _schema_closure

ORG_SCHEMAS = ("OrgOut", "PersonOrgOut")
ORG_FORBIDDEN = FORBIDDEN | {"quality", "span", "span_limit", "leadership", "mentoring", "morale"}


def _client(save_dir: Path, scenario: str = "group_lift") -> TestClient:
    client = TestClient(create_app())
    body = {"slug": "org", "firm_name": "Org LLP", "scenario_id": scenario, "seed": 5}
    assert client.post("/api/saves", json=body).status_code == 200
    return client


def test_reorganise_through_the_api(save_dir: Path) -> None:
    client = _client(save_dir)
    org = client.get("/api/saves/org/org").json()
    assert org["practice_groups_unlocked"] and org["lawyers"] == 10 and org["unlock_at"] == 10
    assert org["units"] == [] and len(org["root_members"]) == 10
    assert org["supervisors"][0]["person"]["id"] == org["founder"]["id"]
    assert org["supervisors"][0]["reports"] == 10 and org["supervisors"][0]["over_span"]
    lit = next(m for m in org["root_members"] if m["level"] == "associate_6")

    org = client.post(
        "/api/saves/org/org/units",
        json={"kind": "practice_group", "practice": "commercial_litigation"},
    ).json()
    unit = org["units"][0]
    assert unit["name"] == "Commercial litigation" and unit["leader"] is None
    assert "commercial_litigation" not in {p["key"] for p in org["open_practices"]}
    org = client.put(
        f"/api/saves/org/org/people/{lit['id']}/unit", json={"unit_id": unit["id"]}
    ).json()
    org = client.put(
        f"/api/saves/org/org/units/{unit['id']}/leader", json={"person_id": lit["id"]}
    ).json()
    assert org["units"][0]["leader"]["id"] == lit["id"]
    org = client.post(
        "/api/saves/org/org/plans",
        json={
            "owner_id": lit["id"],
            "role": "commercial_litigation",
            "target": 2,
            "channel": "campus",
            "unit_id": unit["id"],
        },
    ).json()
    plan = org["plans"][0]
    assert plan["campus"] and plan["level"] == "associate_1" and plan["status"] == "active"
    assert org["units"][0]["campus_target"] == 2

    me = client.get(f"/api/saves/org/org/people/{lit['id']}").json()
    assert me["leads"]["id"] == unit["id"] and me["unit_name"] == "Commercial litigation"
    assert me["supervisor"]["id"] == org["founder"]["id"] and me["plans_owned"] == 1
    assert me["promote_to"] == "associate_7" and me["promotion_accelerated"]

    # Errors map to 400 and 404 with a code; nothing changes.
    bad = client.put(f"/api/saves/org/org/units/{unit['id']}/leader", json={"person_id": 999})
    assert bad.status_code == 404
    bad = client.post("/api/saves/org/org/units", json={"kind": "team", "name": "   "})
    assert bad.status_code == 400 and bad.json()["code"] == "org_rule"
    assert client.delete("/api/saves/org/org/plans/77").status_code == 404
    assert (
        client.post(
            f"/api/saves/org/org/people/{lit['id']}/raise", json={"salary_cents": 1}
        ).status_code
        == 400
    )

    org = client.post(f"/api/saves/org/org/people/{lit['id']}/promote").json()
    org = client.delete(f"/api/saves/org/org/plans/{plan['id']}").json()
    assert org["plans"] == []
    assert client.post("/api/saves/org/advance").status_code == 200
    org = client.delete(f"/api/saves/org/org/units/{unit['id']}").json()
    assert org["units"] == [] and len(org["root_members"]) == 10


def test_practice_groups_locked_in_a_small_firm(save_dir: Path) -> None:
    client = _client(save_dir, "biglaw_spinout")
    org = client.get("/api/saves/org/org").json()
    assert not org["practice_groups_unlocked"] and org["lawyers"] == 4
    bad = client.post("/api/saves/org/org/units", json={"kind": "practice_group", "practice": "ip"})
    assert bad.status_code == 400
    assert (
        client.post("/api/saves/org/org/units", json={"kind": "team", "name": "Deals"}).status_code
        == 200
    )


def test_no_hidden_value_in_any_org_schema(save_dir: Path) -> None:
    client = _client(save_dir)
    spec = client.get("/openapi.json").json()
    schemas = _schema_closure(spec, ORG_SCHEMAS)
    assert {
        "OrgOut",
        "OrgUnitOut",
        "OrgMemberOut",
        "SupervisorOut",
        "PlanOut",
        "PersonOrgOut",
    } <= schemas
    for name in schemas:
        props = set(spec["components"]["schemas"][name].get("properties", {}))
        assert not props & ORG_FORBIDDEN, (name, props & ORG_FORBIDDEN)
    body: Any = client.get("/api/saves/org/org").json()
    first = body["root_members"][0]["id"]
    person = client.get(f"/api/saves/org/org/people/{first}").json()
    assert not set(_keys(body)) & ORG_FORBIDDEN
    assert not set(_keys(person)) & ORG_FORBIDDEN
