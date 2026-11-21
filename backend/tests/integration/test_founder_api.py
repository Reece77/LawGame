"""PT-M17: the Founder and Family endpoints, the save round trip of the founder's life, and
the rule that no hidden value reaches the API: no partner's confidence or vote utility, no
family member's potential or hidden traits (acceptance; CLAUDE.md section 10)."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from ptk.api.app import create_app
from ptk.config import get_settings
from ptk.db import saves
from tests.integration.test_matters_api import FORBIDDEN
from tests.integration.test_people_api import _schema_closure

ROOTS = ("FounderOut", "FamilyOut")
SLUG = "fl"
HIDDEN = FORBIDDEN | {"confidence", "satisfaction", "potential_ability", "utility", "pa"}


def _client(turns: int = 2, **extra: object) -> TestClient:
    client = TestClient(create_app())
    body = {"slug": SLUG, "firm_name": "Founders LLP", "seed": 5, "scenario_id": "group_lift"}
    made = client.post("/api/saves", json={**body, **extra})
    assert made.status_code == 200, made.text
    for _ in range(turns):
        advance(client)
    return client


def advance(client: TestClient) -> None:
    """A month, answering a blocking critical event with its first choice (as the e2e do)."""
    game = client.get(f"/api/saves/{SLUG}/game").json()
    if game["blocking_event_id"] is not None:
        r = client.post(
            f"/api/saves/{SLUG}/events/{game['blocking_event_id']}/choose", json={"choice": "A"}
        )
        assert r.status_code == 200, r.text
    r = client.post(f"/api/saves/{SLUG}/advance")
    assert r.status_code == 200, r.text


def test_founder_screen_data(save_dir: Path) -> None:
    client = _client(turns=14)
    f = client.get(f"/api/saves/{SLUG}/founder").json()
    assert f["status"] == "managing_partner" and f["is_mp"]
    assert [t["key"] for t in f["persona_traits"]] == [
        "visionary",
        "ruthless",
        "beloved",
        "reckless",
    ]
    p = f["personal"]
    assert p["lifetime"]["draws_cents"] > 0
    assert p["lifetime"]["after_tax_cents"] == (
        p["lifetime"]["draws_cents"] + p["lifetime"]["true_up_cents"] - p["lifetime"]["tax_cents"]
    )
    assert p["firm_capital_cents"] > 0 and p["loan_cents"] > 0 and p["recent"]
    assert f["retirement_age"] == 65
    assert f["candidates"], "a co-founder may succeed"
    c = f["candidates"][0]
    assert c["predicted_yes"]["lo"] <= c["predicted_yes"]["hi"] <= c["total_weight"]
    assert (
        f["legacy"]["total"]
        == sum(
            f["legacy"][k] for k in ("firm", "name_on_door", "giving", "persona", "family", "bar")
        )
        or abs(
            f["legacy"]["total"]
            - sum(
                f["legacy"][k]
                for k in ("firm", "name_on_door", "giving", "persona", "family", "bar")
            )
        )
        <= 3
    )  # each part rounded on its own
    # actions
    r = client.post(f"/api/saves/{SLUG}/founder/invest", json={"amount_cents": 100_000})
    assert r.status_code == 200, r.text
    assert r.json()["personal"]["investments_cents"] == 100_000
    r = client.post(f"/api/saves/{SLUG}/founder/bar/committee", json={"on": True})
    assert r.json()["influence"]["committee"] is True
    r = client.post(f"/api/saves/{SLUG}/founder/foundation", json={"cause": "access_to_justice"})
    assert r.status_code == 409  # $1M of personal cash needed
    pid = c["person_id"]
    r = client.post(f"/api/saves/{SLUG}/founder/succession/plan", json={"person_id": pid})
    assert r.json()["plan_id"] == pid


def test_succession_through_the_api(save_dir: Path) -> None:
    client = _client(turns=3)
    f = client.get(f"/api/saves/{SLUG}/founder").json()
    heir = f["candidates"][0]["person_id"]
    old = f["person_id"]
    r = client.post(f"/api/saves/{SLUG}/founder/succession/name", json={"person_id": heir})
    assert r.status_code == 200 and r.json()["open_succession"]
    advance(client)
    f = client.get(f"/api/saves/{SLUG}/founder").json()
    assert f["person_id"] == heir and f["is_mp"]
    played = {x["person_id"]: x["status"] for x in f["played"]}
    assert played[old] == "senior_partner" and played[heir] == "managing_partner"
    advance(client)  # play on


def test_family_screen_and_nothing_hidden(save_dir: Path) -> None:
    client = _client(turns=2, family="children", child_ages=[13, 19], founder_age=50)
    fam = client.get(f"/api/saves/{SLUG}/family").json()
    assert fam["setting"] == "children" and fam["active"]
    kids = [m for m in fam["members"] if m["relation"] == "child"]
    assert len(kids) == 2 and all(isinstance(m["potential"], str) for m in kids)
    young = min(kids, key=lambda m: m["age"])
    r = client.post(
        f"/api/saves/{SLUG}/family/education",
        json={"child_id": young["person_id"], "stage": "school", "tier": "elite"},
    )
    assert r.status_code == 200, r.text
    assert (
        next(m for m in r.json()["members"] if m["person_id"] == young["person_id"])["school"]
        == "elite"
    )
    assert fam["estate"]["rate_bp"] == 4700  # 2005's 47%
    f = client.get(f"/api/saves/{SLUG}/founder").json()
    assert f["age"] in (50, 51)  # a birthday may fall in the first months
    # nothing hidden in the bodies or the schema
    for body in (fam, f, client.get(f"/api/saves/{SLUG}/family").json()):
        text = json.dumps(body)
        for word in ("potential_ability", "confidence", "satisfaction", "hidden"):
            assert f'"{word}"' not in text
    schema = client.get("/openapi.json").json()
    for name in _schema_closure(schema, ROOTS):
        props = set(schema["components"]["schemas"][name].get("properties", {}))
        assert not props & HIDDEN, (name, props & HIDDEN)


def test_founder_life_round_trips_through_the_save(save_dir: Path) -> None:
    client = _client(turns=4, family="partner")
    path = saves.open_save(get_settings().resolved_save_dir(), SLUG)
    state, _ = saves.read_state(path)
    assert state.founder_life.books and state.family.family is not None
    from ptk.db.founder_io import personal_balances
    from ptk.db.session import make_sessionmaker, shared_engine

    with make_sessionmaker(shared_engine(path))() as session:
        sums = personal_balances(session)
    for book in state.founder_life.books:
        assert {a: v for (p, a), v in sums.items() if p == book.person_id} == dict(book.balances)
    del client
