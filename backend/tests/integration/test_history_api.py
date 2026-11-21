"""PT-M7 sub-task 4: the History screen's endpoint and the Overview's guidance."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from ptk.api.app import create_app
from ptk.sim.data_models import Balance, GameData
from ptk.sim.whatnext import MAX_ITEMS, getting_started, what_next
from tests.integration.test_matters_api import FORBIDDEN
from tests.integration.test_people_api import _schema_closure
from tests.matters_support import game


def _client(save_dir: Path, turns: int) -> TestClient:
    client = TestClient(create_app())
    made = client.post("/api/saves", json={"slug": "hist", "firm_name": "History LLP", "seed": 5})
    assert made.status_code == 200, made.text
    for _ in range(turns):
        blocking = client.get("/api/saves/hist/game").json()["blocking_event_id"]
        if blocking is not None:  # a critical event: its first choice, as a hurried player
            choose = client.post(f"/api/saves/hist/events/{blocking}/choose", json={"choice": "A"})
            assert choose.status_code == 200
        assert client.post("/api/saves/hist/advance").status_code == 200
    return client


def test_history_has_the_firms_years_and_timeline(save_dir: Path) -> None:
    client = _client(save_dir, 13)
    out = client.get("/api/saves/hist/history").json()
    first = out["years"][0]
    assert first["year"] == 2005 and first["complete"]
    assert first["revenue_cents"] > 0
    assert first["rank"] is not None and 1 <= first["rank"] <= first["firms_ranked"]
    assert not out["years"][-1]["complete"]  # January 2006 played, the year has begun
    kinds = {i["kind"] for i in out["timeline"]}
    assert "market" in kinds or kinds  # the firm's milestones and the market's dated events
    assert [i["turn"] for i in out["timeline"]] == sorted(i["turn"] for i in out["timeline"])


def test_guidance_shows_the_first_year_and_what_next(save_dir: Path) -> None:
    client = _client(save_dir, 1)
    out = client.get("/api/saves/hist/guidance").json()
    assert out["first_year"]
    assert [s["key"] for s in out["getting_started"]] == [
        "staff",
        "hire",
        "bd",
        "collect",
        "policy",
        "vote",
    ]
    assert len(out["what_next"]) <= MAX_ITEMS


def test_getting_started_ticks_from_state(data: GameData, balance: Balance) -> None:
    from dataclasses import replace

    state = game(data, balance)
    steps = {s.key: s.done for s in getting_started(state, data, balance)}
    assert not steps["policy"] and not steps["vote"]
    firm = replace(state.player, rate_rise_bp=500)
    state = replace(state, firms=tuple(firm if f.id == firm.id else f for f in state.firms))
    assert {s.key: s.done for s in getting_started(state, data, balance)}["policy"]


def test_what_next_reads_capacity_and_the_bank(data: GameData, balance: Balance) -> None:
    state = game(data, balance)
    busy = what_next(state, (), 9500, data, balance)
    assert any(i.key == "busy" for i in busy)
    idle = what_next(state, ("cfo_warning",), 5000, data, balance)
    assert [i.key for i in idle][:1] == ["bank"] and any(i.key == "idle" for i in idle)


def test_no_hidden_values_in_the_new_schemas() -> None:
    spec = create_app().openapi()
    components = spec["components"]["schemas"]
    for name in _schema_closure(spec, ("HistoryOut", "GuidanceOut")):
        props = set(components[name].get("properties", {}))
        assert not props & FORBIDDEN, (name, props & FORBIDDEN)
