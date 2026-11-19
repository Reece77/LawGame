"""Recruitment, inbox and payroll endpoints (PT-M1b sub-task 6; ADR-0007, ADR-0014, 0016)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from ptk.api.app import create_app
from tests.integration.test_people_api import FORBIDDEN, _keys, _schema_closure

SCHEMAS = ("RecruitmentOut", "OfferPreviewOut", "InboxItemOut", "PayrollOut")


def _client() -> TestClient:
    client = TestClient(create_app())
    made = client.post("/api/saves", json={"slug": "rec", "firm_name": "Acme LLP", "seed": 3})
    assert made.status_code == 200, made.text
    return client


def _advance_to(client: TestClient, label: str) -> None:
    for _ in range(30):
        if client.get("/api/saves/rec/game").json()["date_label"] == label:
            return
        assert client.post("/api/saves/rec/advance").status_code == 200
    raise AssertionError(f"never reached {label}")


def test_campus_cycle_through_the_api(save_dir: Path) -> None:
    client = _client()
    view = client.get("/api/saves/rec/recruitment").json()
    assert view["campus"]["registration_open"] and view["energy"] == view["energy_per_month"]
    opened = client.post(
        "/api/saves/rec/recruitment/searches",
        json={"role": "corporate_ma", "channel": "campus", "school_tiers": ["t14", "national"]},
    )
    assert opened.status_code == 200, opened.text
    view = opened.json()
    assert view["campus"]["registered_roles"] == ["Corporate and M&A lawyer"]
    assert view["energy"] == view["energy_per_month"] - 5
    dup = client.post(
        "/api/saves/rec/recruitment/searches", json={"role": "corporate_ma", "channel": "campus"}
    )
    assert dup.status_code == 400 and dup.json()["code"] == "invalid_action"
    _advance_to(client, "May 2005")
    view = client.get("/api/saves/rec/recruitment").json()
    cands = view["candidates"]
    assert len(cands) == 7 and view["campus"]["in_summer"]
    cand = cands[0]
    assert cand["offer_blocked_reason"] == "campus_offer_month"
    early = client.post(
        "/api/saves/rec/recruitment/offers",
        json={"candidate_id": cand["id"], "salary_cents": cand["ask_cents"]},
    )
    assert early.status_code == 409 and early.json()["code"] == "interview_required"
    _advance_to(client, "Aug 2005")
    no_interview = client.post(
        "/api/saves/rec/recruitment/offers",
        json={"candidate_id": cand["id"], "salary_cents": cand["ask_cents"]},
    )
    assert no_interview.status_code == 409 and no_interview.json()["code"] == "interview_required"
    view = client.post(f"/api/saves/rec/recruitment/candidates/{cand['id']}/interview").json()
    cand = next(c for c in view["candidates"] if c["id"] == cand["id"])
    assert cand["interviewed"] and cand["offer_allowed"]
    hint = client.get(
        f"/api/saves/rec/recruitment/candidates/{cand['id']}/offer-preview",
        params={"salary_cents": int(cand["ask_cents"] * 1.3)},
    ).json()
    assert hint["hint"] in ("likely", "uncertain") and hint["ask_cents"] == cand["ask_cents"]
    view = client.post(
        "/api/saves/rec/recruitment/offers",
        json={"candidate_id": cand["id"], "salary_cents": int(cand["ask_cents"] * 1.5)},
    ).json()
    assert len(view["offers"]) == 1
    client.post("/api/saves/rec/advance")
    inbox = client.get("/api/saves/rec/inbox").json()
    titles = [i["title"] for i in inbox]
    assert any("summer associates" in t for t in titles)
    assert any("class of 2006" in t or "declined" in t for t in titles)
    view = client.get("/api/saves/rec/recruitment").json()
    if view["campus"]["signed"]:
        assert view["campus"]["signed"][0]["start_label"] == "Sep 2006"
    read = client.post("/api/saves/rec/inbox/read").json()
    assert all(i["read"] for i in read)


def test_pay_policy_and_payroll(save_dir: Path) -> None:
    client = _client()
    payroll = client.get("/api/saves/rec/payroll").json()
    assert payroll["headcount"] == 4
    labels = {line["label"]: line for line in payroll["lines"]}
    assert labels["Rent"]["account"] == "6000_rent" and labels["Rent"]["amount_cents"] == 1_200_000
    assert payroll["total_cents"] == sum(line["amount_cents"] for line in payroll["lines"])
    bad = client.put("/api/saves/rec/recruitment/pay-policy", json={"mode": "lag", "pct_bp": 12000})
    assert bad.status_code == 400
    view = client.put(
        "/api/saves/rec/recruitment/pay-policy", json={"mode": "lead", "pct_bp": 11000}
    ).json()
    assert view["pay_policy"]["mode"] == "lead"
    assert (
        view["scale"][0]["firm_cents"] == 13_750_000
        and view["scale"][0]["market_cents"] == 12_500_000
    )


def test_no_hidden_value_in_recruitment(save_dir: Path) -> None:
    client = _client()
    spec = client.get("/openapi.json").json()
    for name in _schema_closure(spec, SCHEMAS):
        props = set(spec["components"]["schemas"][name].get("properties", {}))
        assert not props & FORBIDDEN, (name, props & FORBIDDEN)
    client.post("/api/saves/rec/recruitment/searches", json={"role": "ip", "channel": "job_post"})
    client.post("/api/saves/rec/advance")
    body = client.get("/api/saves/rec/recruitment").json()
    assert body["candidates"]
    assert not set(_keys(body)) & FORBIDDEN
    people = client.get("/api/saves/rec/people").json()
    assert len(people) == 4  # candidates are not on the People screen
    assert people[2]["morale"] is not None and people[0]["morale"] is None
