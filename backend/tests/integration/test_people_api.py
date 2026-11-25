"""People endpoints (sub-task 6) and the hidden-value rule (ADR-0007; ADR PT-0006 5)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from ptk.api.app import create_app

# Hidden values: never a field name anywhere in a people response or schema.
FORBIDDEN = {
    "potential_ability",
    "pa",
    "hidden",
    "consistency",
    "burnout_risk",
    "big_moments",
    "poachability",
    "portability",
    "portability_bp",
    "integrity_true",
    "true_value",
    "offset",
    "hw",
    "familiarity_peak",
}
PEOPLE_SCHEMAS = ("PersonRowOut", "PersonOut")


def _keys(value: Any) -> Iterator[str]:
    if isinstance(value, dict):
        for key, inner in value.items():
            yield key
            yield from _keys(inner)
    elif isinstance(value, list):
        for inner in value:
            yield from _keys(inner)


def _schema_closure(spec: dict[str, Any], roots: tuple[str, ...]) -> set[str]:
    """Every component schema reachable from the people schemas."""
    components = spec["components"]["schemas"]
    seen: set[str] = set()
    todo = list(roots)
    while todo:
        name = todo.pop()
        if name in seen:
            continue
        seen.add(name)
        for text in _refs(components[name]):
            todo.append(text.rsplit("/", 1)[-1])
    return seen


def _refs(value: Any) -> Iterator[str]:
    if isinstance(value, dict):
        for key, inner in value.items():
            if key == "$ref" and isinstance(inner, str):
                yield inner
            else:
                yield from _refs(inner)
    elif isinstance(value, list):
        for inner in value:
            yield from _refs(inner)


def _client(save_dir: Path) -> TestClient:
    client = TestClient(create_app())
    made = client.post(
        "/api/saves",
        json={"slug": "ppl", "firm_name": "Acme LLP", "seed": 5, "background": "trial_lawyer"},
    )
    assert made.status_code == 200, made.text
    return client


def test_meta_lists_backgrounds(save_dir: Path) -> None:
    meta = TestClient(create_app()).get("/api/meta").json()
    assert [b["key"] for b in meta["backgrounds"]][:2] == ["biglaw_ma_partner", "trial_lawyer"]


def test_people_list_and_profile(save_dir: Path) -> None:
    client = _client(save_dir)
    rows = client.get("/api/saves/ppl/people").json()
    assert [r["id"] for r in rows] == [1, 2, 3, 4]
    founder = rows[0]
    assert founder["is_founder"] and founder["role"] == "commercial_litigation"
    assert founder["strain"] == 20.0 and founder["burnt_out"] is False
    assert len(founder["familiarity"]) == 20  # PT-M12: twenty practices
    lit = next(f for f in founder["familiarity"] if f["practice"] == "commercial_litigation")
    assert lit["lo"] == lit["hi"] >= 15  # the firm knows its founder exactly
    assert founder["potential"]  # a phrase, never a number
    profile = client.get("/api/saves/ppl/people/1").json()
    assert profile["background"] == "Trial lawyer"
    assert profile["bar_admissions"] == ["New York"]
    assert len(profile["skills"]) == 30 and profile["interests"] is not None
    assert profile["book_cents"] >= 100_000_000
    associate = client.get("/api/saves/ppl/people/3").json()
    advocacy = next(s for s in associate["skills"] if s["key"] == "advocacy")
    assert advocacy["lo"] < advocacy["hi"]  # a range, not the true value
    assert associate["book_cents"] is None
    missing = client.get("/api/saves/ppl/people/99")
    assert missing.status_code == 404 and missing.json()["code"] == "not_found"
    bad = client.post(
        "/api/saves", json={"slug": "bad", "firm_name": "B", "background": "astronaut"}
    )
    assert bad.status_code == 400 and bad.json()["code"] == "invalid_founder"


def test_no_hidden_value_in_any_people_schema(save_dir: Path) -> None:
    client = _client(save_dir)
    spec = client.get("/openapi.json").json()
    schemas = _schema_closure(spec, PEOPLE_SCHEMAS)
    assert {"PersonRowOut", "PersonOut", "RangeOut", "FamiliarityOut", "AttributeOut"} <= schemas
    for name in schemas:
        props = set(spec["components"]["schemas"][name].get("properties", {}))
        assert not props & FORBIDDEN, (name, props & FORBIDDEN)
    for _ in range(3):
        client.post("/api/saves/ppl/advance")
    responses = [client.get("/api/saves/ppl/people").json()]
    responses += [client.get(f"/api/saves/ppl/people/{i}").json() for i in range(1, 5)]
    for body in responses:
        assert not set(_keys(body)) & FORBIDDEN
    # and no true attribute or trait leaks as a value: every shown skill is a range that the
    # save's true value lies inside, and potential appears only as a phrase
    from ptk.config import get_settings
    from ptk.db import saves

    state, _ = saves.read_state(saves.open_save(get_settings().resolved_save_dir(), "ppl"))
    for body in responses[1:]:
        person = state.person(body["id"])
        for skill in body["skills"]:
            assert skill["lo"] <= person.skills[skill["key"]] <= skill["hi"]
        assert str(round(person.potential_ability)) not in str(body["potential"])
