"""PT-M3b: the Finance endpoints (KPIs, statements, balance sheet, ageing, bills, matter
money), the write-down and dispute actions, the save round trip of billing, and the rule
that no hidden value leaves the engine (CLAUDE.md section 10)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from ptk.api.app import create_app
from ptk.config import get_settings
from ptk.db import saves
from ptk.db.billing_io import client_book_balances
from ptk.db.core import make_sessionmaker, shared_engine
from ptk.sim.ledger import CLIENT_BANK, OWED_TO_CLIENTS
from tests.integration.test_matters_api import FORBIDDEN
from tests.integration.test_people_api import _schema_closure

ROOTS = ("FinanceOut", "BillOut", "MatterMoneyOut")


def _client(turns: int = 6) -> TestClient:
    client = TestClient(create_app())
    made = client.post("/api/saves", json={"slug": "fin", "firm_name": "Acme LLP", "seed": 9})
    assert made.status_code == 200, made.text
    for _ in range(turns):
        assert client.post("/api/saves/fin/advance").status_code == 200
    return client


def test_finance_screen_data(save_dir: Path) -> None:
    client = _client()
    fin = client.get("/api/saves/fin/finance")
    assert fin.status_code == 200, fin.text
    body = fin.json()
    k = body["kpis"]
    assert k["wip_cents"] >= 0 and k["receivables_cents"] >= 0
    assert k["realisation_bp"] is not None and 5000 < k["realisation_bp"] < 15000
    assert len(body["months"]) == 6
    views = {(s["label"], s["basis"]) for s in body["statements"]}
    assert any(b == "accrual" for _, b in views) and any(b == "cash" for _, b in views)
    for s in body["statements"]:
        assert s["profit_cents"] == s["revenue_cents"] - s["costs_cents"]
    cash = next(s for s in body["statements"] if s["basis"] == "cash")
    assert cash["revenue_cents"] == sum(m["collections_cents"] for m in body["months"])
    assets = sum(x["amount_cents"] for x in body["balance_sheet"] if x["kind"] == "asset")
    claims = sum(x["amount_cents"] for x in body["balance_sheet"] if x["kind"] != "asset")
    accrual = next(s for s in body["statements"] if s["basis"] == "accrual")
    assert assets == claims + accrual["profit_cents"]  # the year's profit is not yet closed out
    assert sum(b["amount_cents"] for b in body["receivables_ageing"]) == k["receivables_cents"]
    assert sum(b["amount_cents"] for b in body["wip_ageing"]) == k["wip_cents"]
    bills = client.get("/api/saves/fin/finance/bills").json()
    assert sum(b["outstanding_cents"] for b in bills) == k["receivables_cents"]
    money = client.get("/api/saves/fin/finance/matters").json()
    assert money and all(m["billed_cents"] >= 0 for m in money)


def test_write_down_and_dispute_actions(save_dir: Path) -> None:
    client = _client()
    money = client.get("/api/saves/fin/finance/matters").json()
    target = next(
        (
            m
            for m in money
            if not m["closed"] and m["model"] in ("hourly", "blended", "success", "capped")
        ),
        None,
    )
    if target is not None:
        r = client.post(
            "/api/saves/fin/finance/write-down", json={"matter_id": target["matter_id"], "bp": 1500}
        )
        assert r.status_code == 200, r.text
        row = next(m for m in r.json() if m["matter_id"] == target["matter_id"])
        assert row["writedown_bp"] == 1500
    bad = client.post("/api/saves/fin/finance/write-down", json={"matter_id": 999_999, "bp": 100})
    assert bad.status_code == 404
    missing = client.post("/api/saves/fin/finance/bills/999999/dispute", json={"choice": "concede"})
    assert missing.status_code == 404
    disputed = client.get("/api/saves/fin/finance/bills", params={"status": "disputed"}).json()
    if disputed:
        bid = disputed[0]["id"]
        r = client.post(f"/api/saves/fin/finance/bills/{bid}/dispute", json={"choice": "negotiate"})
        assert r.status_code == 200, r.text
        assert all(b["id"] != bid or b["dispute"] is None for b in r.json())


def test_client_book_balances_in_the_save(save_dir: Path) -> None:
    _client(turns=10)
    path = saves.open_save(get_settings().resolved_save_dir(), "fin")
    with make_sessionmaker(shared_engine(path))() as session:
        book = client_book_balances(session)
    bank = sum(v for (_, a, _), v in book.items() if a == CLIENT_BANK)
    owed = sum(v for (_, a, _), v in book.items() if a == OWED_TO_CLIENTS)
    assert bank == -owed
    state, _ = saves.read_state(path)
    assert sum(f.owed_cents for f in state.billing.funds) == bank


def test_finance_schemas_carry_no_hidden_value(save_dir: Path) -> None:
    schema = TestClient(create_app()).get("/openapi.json").json()
    names = _schema_closure(schema, ROOTS)
    for name in names:
        props = schema["components"]["schemas"][name].get("properties", {})
        assert not FORBIDDEN & set(props), (name, FORBIDDEN & set(props))
