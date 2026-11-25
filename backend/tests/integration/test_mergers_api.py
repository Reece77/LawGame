"""PT-M13: the Mergers endpoints, the save round trip of the mergers state, and no hidden value
in their schemas (CLAUDE.md section 10; ADR PT-0016 4)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from ptk.api.app import create_app
from ptk.config import get_settings
from ptk.db import saves
from tests.integration.test_matters_api import FORBIDDEN
from tests.integration.test_people_api import _schema_closure

ROOTS = ("MergersOut",)
SLUG = "mergers"
HIDDEN = FORBIDDEN | {"annuity_share", "lease_years", "adverse", "noise", "bias", "reservation"}


def _client() -> TestClient:
    client = TestClient(create_app())
    body = {"slug": SLUG, "firm_name": "Founders LLP", "seed": 3, "scenario_id": "biglaw_spinout"}
    made = client.post("/api/saves", json=body)
    assert made.status_code == 200, made.text
    return client


def test_no_mergers_schema_names_a_hidden_value(save_dir: Path) -> None:
    spec = create_app().openapi()
    names = _schema_closure(spec, ROOTS)
    assert "MergerRevealOut" in names and "VereinOut" in names
    for name in names:
        props = spec["components"]["schemas"][name].get("properties", {})
        for field in props:
            assert not any(word in field.lower() for word in HIDDEN), (name, field)


def test_approach_diligence_terms_and_the_round_trip(save_dir: Path) -> None:
    client = _client()
    for _ in range(3):  # a few months of run-rates for the rivals
        assert client.post(f"/api/saves/{SLUG}/advance").status_code == 200
    view = client.get(f"/api/saves/{SLUG}/mergers").json()
    assert view["is_mp"] and view["targets"] and not view["deals"]
    elite = next(t for t in view["targets"] if t["merger_blocked"] == "it does not merge")
    refused = client.post(
        f"/api/saves/{SLUG}/mergers/approach", json={"rival_key": elite["key"], "form": "merger"}
    )
    assert refused.status_code == 400  # InvalidActionError
    open_ = [t for t in view["targets"] if t["integrable"] and not t["merger_blocked"]]
    talks = None
    for t in open_[:6]:
        out = client.post(
            f"/api/saves/{SLUG}/mergers/approach", json={"rival_key": t["key"], "form": "merger"}
        ).json()
        deal = out["deals"][0]
        if deal["stage"] == "talks":
            talks = deal
            break
        assert deal["stage"] == "ended" and deal["ended_reason"] == "declined to talk"
        client.post(f"/api/saves/{SLUG}/advance")  # next month's energy
    assert talks is not None, "no firm talked"
    assert talks["reveal"]["level"] == 0 and talks["reveal"]["wip_cents"] is None
    out = client.post(f"/api/saves/{SLUG}/mergers/{talks['id']}/diligence").json()
    deal = next(d for d in out["deals"] if d["id"] == talks["id"])
    assert deal["diligence_running"] and deal["diligence_fees_cents"] > 0
    refused = client.post(
        f"/api/saves/{SLUG}/mergers/{talks['id']}/terms", json={"our_share_bp": 5000}
    )
    assert refused.status_code == 400  # not while diligence runs
    for _ in range(2):
        client.post(f"/api/saves/{SLUG}/advance")
    out = client.get(f"/api/saves/{SLUG}/mergers").json()
    deal = next(d for d in out["deals"] if d["id"] == talks["id"])
    assert deal["reveal"]["level"] == 1 and deal["reveal"]["wip_cents"] is not None
    lo, hi = deal["reveal"]["annuities_cents"]["lo"], deal["reveal"]["annuities_cents"]["hi"]
    assert lo <= hi
    out = client.post(
        f"/api/saves/{SLUG}/mergers/{talks['id']}/terms",
        json={"our_share_bp": 6000, "name": "combined", "rates": "blend"},
    ).json()
    deal = next(d for d in out["deals"] if d["id"] == talks["id"])
    assert deal["stage"] == "terms" and deal["terms"]["our_share_pct"] == 60
    assert deal["prediction"] is not None
    # the mergers state survives the save
    path = saves.open_save(get_settings().resolved_save_dir(), SLUG)
    state = saves.read_state(path)[0]
    assert state.mergers.deal(talks["id"]) is not None
    assert state.mergers.deal(talks["id"]).terms.our_share_bp == 6000  # type: ignore[union-attr]
    out = client.post(f"/api/saves/{SLUG}/mergers/{talks['id']}/walk-away")
    assert out.status_code in (200, 400)  # refused once the partnerships have voted
