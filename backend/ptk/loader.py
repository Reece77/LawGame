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


def _event_templates(folder: Path) -> tuple[dict[str, Any], ...]:
    """Every events/*.yaml file's templates, files in name order (PT-M6)."""
    out: list[dict[str, Any]] = []
    for path in sorted(folder.glob("*.yaml")):
        out += _read(path)["templates"]
    return tuple(out)


def load_game_data(data_dir: Path) -> GameData:
    try:
        scenarios = _read(data_dir / "scenarios.yaml")
        personality = _read(data_dir / "personality.yaml")
        backgrounds = _read(data_dir / "backgrounds.yaml")
        practices = _read(data_dir / "practices.yaml")
        market = {k: v for k, v in practices.items() if k != "practices"}
        return GameData(
            accounts=tuple(_read(data_dir / "accounts.yaml")["accounts"]),
            scenarios=tuple(scenarios["scenarios"]),
            difficulties=tuple(scenarios["difficulties"]),
            jurisdictions=tuple(scenarios["jurisdictions"]),
            skills=tuple(_read(data_dir / "skills.yaml")["skills"]),
            personality=tuple(personality["personality"]),
            hidden=tuple(personality["hidden"]),
            work_styles=tuple(personality["work_styles"]),
            interests=tuple(_read(data_dir / "interests.yaml")["interests"]),
            practices=tuple(practices["practices"]),
            school_tiers=tuple(_read(data_dir / "schools.yaml")["school_tiers"]),
            roles=tuple(_read(data_dir / "roles.yaml")["roles"]),
            tags=tuple(_read(data_dir / "tags.yaml")["tags"]),
            backgrounds=tuple(backgrounds["backgrounds"]),
            personality_presets=tuple(backgrounds["personality_presets"]),
            names=_read(data_dir / "names.yaml")["names"],
            salary_scale=_read(data_dir / "salary_scale.yaml"),
            inbox_templates=_read(data_dir / "inbox_templates.yaml")["templates"],
            market=market,
            clients=_read(data_dir / "clients.yaml"),
            courts=_read(data_dir / "courts.yaml"),
            rivals={  # PT-M5
                "firms": _read(data_dir / "firms.yaml"),
                "people": {
                    **_read(data_dir / "notables.yaml"),
                    **_read(data_dir / "judges.yaml"),
                },
            },
            event_templates=_event_templates(data_dir / "events"),
            macro=_read(data_dir / "macro_history.yaml"),  # PT-M7
            seats=_read(data_dir / "seats.yaml"),  # PT-M8
            geo={**_read(data_dir / "cities.yaml"), **_read(data_dir / "bar_rules.yaml")},  # PT-M11
        )
    except (ValidationError, KeyError, FileNotFoundError) as exc:
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
