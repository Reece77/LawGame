"""Reads and validates backend/data YAML (ADR-0008). Outside the sim; invalid data fails."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from ptk.config import get_settings
from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import InvalidDataError


def _read(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        loaded = yaml.safe_load(fh)
    if not isinstance(loaded, dict):
        raise InvalidDataError(f"{path.name} must hold a mapping")
    return loaded


def load_game_data(data_dir: Path) -> GameData:
    scenarios = _read(data_dir / "scenarios.yaml")
    try:
        return GameData(
            accounts=tuple(_read(data_dir / "accounts.yaml")["accounts"]),
            scenarios=tuple(scenarios["scenarios"]),
            difficulties=tuple(scenarios["difficulties"]),
        )
    except (ValidationError, KeyError) as exc:
        raise InvalidDataError(f"invalid seed data: {exc}") from exc


def load_balance(data_dir: Path) -> Balance:
    try:
        return Balance.model_validate(_read(data_dir / "balance.yaml"))
    except ValidationError as exc:
        raise InvalidDataError(f"invalid balance.yaml: {exc}") from exc


@lru_cache(maxsize=1)
def game_data() -> GameData:
    return load_game_data(get_settings().data_dir)


@lru_cache(maxsize=1)
def balance() -> Balance:
    return load_balance(get_settings().data_dir)
