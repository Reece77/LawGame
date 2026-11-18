from __future__ import annotations

import os
from pathlib import Path

import pytest

from ptk.loader import load_balance, load_game_data
from ptk.sim.data_models import Balance, GameData

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"

# Never call the Anthropic API in tests (CLAUDE.md section 8).
os.environ["PTK_LLM_ADAPTER"] = "mock"
os.environ.pop("ANTHROPIC_API_KEY", None)
os.environ.setdefault("PTK_SQLITE_SYNC", "OFF")


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--update-golden",
        action="store_true",
        default=False,
        help="Regenerate tests/golden/snapshots/*.json (record the reason in CHANGELOG.md)",
    )


@pytest.fixture(scope="session")
def data() -> GameData:
    return load_game_data(DATA_DIR)


@pytest.fixture(scope="session")
def balance() -> Balance:
    return load_balance(DATA_DIR)


@pytest.fixture
def save_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "saves"
    monkeypatch.setenv("PTK_SAVE_DIR", str(path))
    from ptk.config import get_settings

    get_settings.cache_clear()
    return path
