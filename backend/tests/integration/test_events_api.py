"""PT-M6 endpoints: events in the inbox and the API, answering one, a critical event blocking
Continue (409) until answered, read-only texts, the LLM settings (offline mode) and the meter;
no hidden value in any events schema or response. All writing uses MockLLMAdapter."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from ptk.api.app import create_app
from ptk.db import saves
from ptk.db.core import make_sessionmaker, shared_engine
from ptk.db.state_io import load_state, write_turn
from ptk.sim.events.director import queue_engine_event
from ptk.sim.snapshot import TurnSnapshot
from tests.integration.test_matters_api import FORBIDDEN
from tests.integration.test_people_api import _keys, _schema_closure

SLUG = "ev"
ROOTS = ("EventOut", "TextOut", "LLMSettingsOut", "MeterOut", "GameOut")
FORBIDDEN_HERE = FORBIDDEN | {"strength", "trigger", "cash_base_cents", "value", "potential"}


def _client(save_dir: Path, turns: int = 3) -> TestClient:
    client = TestClient(create_app())
    made = client.post("/api/saves", json={"slug": SLUG, "firm_name": "Event LLP", "seed": 4})
    assert made.status_code == 200, made.text
    for _ in range(turns):
        response = client.post(f"/api/saves/{SLUG}/advance")
        assert response.status_code == 200, response.text
    return client


def test_events_listed_answered_and_in_the_inbox(save_dir: Path) -> None:
    client = _client(save_dir)
    events = client.get(f"/api/saves/{SLUG}/events").json()
    assert events, "the director queued events"
    open_ = [e for e in events if e["status"] == "open"]
    assert open_ and all(e["choices"] for e in open_)
    assert all(e["source"] == "mock" for e in events)
    inbox = client.get(f"/api/saves/{SLUG}/inbox").json()
    linked = {i["link_id"] for i in inbox if i["link_kind"] == "event"}
    assert {e["id"] for e in events} <= linked
    first = open_[0]
    answer = client.post(
        f"/api/saves/{SLUG}/events/{first['id']}/choose",
        json={"choice": first["choices"][-1]["key"]},
    )
    assert answer.status_code == 200, answer.text
    assert (
        answer.json()["status"] == "answered"
        and answer.json()["chosen"] == first["choices"][-1]["key"]
    )
    again = client.post(f"/api/saves/{SLUG}/events/{first['id']}/choose", json={"choice": "A"})
    assert again.status_code == 409
    assert client.get(f"/api/saves/{SLUG}/events/999999").status_code == 404
    # earlier months' events were answered by Continue with their first choice
    auto = [e for e in events if e["status"] == "auto"]
    assert auto and all(e["chosen"] == "A" for e in auto if e["choices"])


def test_critical_event_blocks_continue(save_dir: Path) -> None:
    client = _client(save_dir, turns=1)
    path = saves.open_save(save_dir, SLUG)
    sessions = make_sessionmaker(shared_engine(path))
    with sessions() as session, session.begin():  # a later milestone's engine queues one
        state = load_state(session)
        state = queue_engine_event(state, "covenant_breach", state.turn + 1)
        write_turn(session, state, (), (), TurnSnapshot(turn=-1, firms=()))
    assert client.post(f"/api/saves/{SLUG}/advance").status_code == 200
    game = client.get(f"/api/saves/{SLUG}/game").json()
    blocking = game["blocking_event_id"]
    assert blocking is not None
    event = client.get(f"/api/saves/{SLUG}/events/{blocking}").json()
    assert event["severity"] == "critical" and event["title"]
    refused = client.post(f"/api/saves/{SLUG}/advance")
    assert refused.status_code == 409 and refused.json()["code"] == "critical_event_open"
    assert (
        client.post(f"/api/saves/{SLUG}/events/{blocking}/choose", json={"choice": "A"}).status_code
        == 200
    )
    assert client.get(f"/api/saves/{SLUG}/game").json()["blocking_event_id"] is None
    assert client.post(f"/api/saves/{SLUG}/advance").status_code == 200


def test_texts_settings_and_meter(save_dir: Path) -> None:
    client = _client(save_dir, turns=2)
    texts = client.get(f"/api/saves/{SLUG}/texts?kind=headlines").json()
    assert texts and all(t["kind"] == "headlines" and t["text"] for t in texts)
    settings = client.get("/api/llm/settings").json()
    assert settings["monthly_budget_cents"] == 1000 and settings["in_use"] == "mock"
    assert settings["key_present"] is False
    changed = client.put(
        "/api/llm/settings", json={"adapter": "templates", "monthly_budget_cents": 500}
    ).json()
    assert changed["adapter"] == "templates" and changed["monthly_budget_cents"] == 500
    meter = client.get("/api/llm/meter").json()
    assert meter["budget_cents"] == 500 and meter["calls"] > 0
    assert meter["spent_cents"] == 0  # the mock is free
    assert (save_dir / "llm_settings.json").is_file()


def test_no_hidden_value_in_any_events_schema_or_response(save_dir: Path) -> None:
    client = _client(save_dir, turns=6)
    spec = client.get("/openapi.json").json()
    schemas = _schema_closure(spec, ROOTS)
    assert {"EventOut", "EventChoiceOut", "EventRefOut"} <= schemas
    for name in schemas:
        props = set(spec["components"]["schemas"][name].get("properties", {}))
        assert not props & FORBIDDEN_HERE, (name, props & FORBIDDEN_HERE)
    bodies: list[Any] = [client.get(f"/api/saves/{SLUG}/events").json()]
    bodies.append(client.get(f"/api/saves/{SLUG}/texts").json())
    for body in bodies:
        assert not set(_keys(body)) & FORBIDDEN_HERE
    # a merits shift is shown in words, never as a number
    for event in bodies[0]:
        for choice in event["choices"]:
            for text in choice["effects"]:
                assert "logit" not in text and "merits" not in text.lower()
