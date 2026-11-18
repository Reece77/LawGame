from __future__ import annotations

from pathlib import Path

import pytest

from ptk.loader import load_game_data
from ptk.sim.data_models import GameData
from ptk.sim.errors import InvalidDataError
from ptk.sim.ledger import ENGINE_ACCOUNTS


def test_engine_accounts_exist(data: GameData) -> None:
    codes = {a.code for a in data.accounts}
    assert set(ENGINE_ACCOUNTS) <= codes


def test_client_book_is_separate(data: GameData) -> None:
    client = [a for a in data.accounts if a.book == "client"]
    assert client and all(a.code.startswith("C") for a in client)


def test_default_scenario_starts_in_2005(data: GameData) -> None:
    scenario = data.scenario("biglaw_spinout")
    assert scenario is not None and scenario.start_ym == (2005, 1)


def test_invalid_data_fails_at_load(tmp_path: Path) -> None:
    (tmp_path / "accounts.yaml").write_text(
        "accounts:\n  - { code: C1000_x, name: x, type: asset }\n"  # client code, firm book
    )
    (tmp_path / "scenarios.yaml").write_text("scenarios: []\ndifficulties: []\n")
    with pytest.raises(InvalidDataError):
        load_game_data(tmp_path)
