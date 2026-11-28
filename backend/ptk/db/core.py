"""Partner Track's bindings of sim-core's persistence helpers (`simcore_db`; ADR PT-0019).

The engine factory, backups and Alembic runner are sim-core's (TST's newest, ADR-0004); this
module only fixes PT's own parameters: the save suffix (`.ptk.sqlite`), the fsync switch
(`PTK_SQLITE_SYNC=OFF` for throwaway saves) and PT's migrations folder. PT's tables, mappers,
Alembic chain and inbox queries stay PT's (`ptk.db.*`).
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Final

from simcore_db import backup as _backup
from simcore_db import session as _session
from simcore_db.migrate import Migrator
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from ptk.config import BACKEND_DIR

SAVE_SUFFIX: Final = ".ptk.sqlite"
SYNC_ENV: Final = "PTK_SQLITE_SYNC"
MIGRATIONS_DIR: Final = BACKEND_DIR / "migrations"

MIGRATOR: Final = Migrator(
    MIGRATIONS_DIR,
    suffix=SAVE_SUFFIX,
    turn_sql="SELECT current_turn FROM save_meta",
    sync_env=SYNC_ENV,
)


# --- Engines (TST ADR-0004) -------------------------------------------------------------


def make_engine(path: Path) -> Engine:
    return _session.make_engine(path, SYNC_ENV)


def shared_engine(path: Path) -> Engine:
    return _session.shared_engine(path, SYNC_ENV)


def make_sessionmaker(engine: Engine) -> sessionmaker[Session]:
    return _session.make_sessionmaker(engine)


# --- Backups (TST ADR-0004 section 5) -----------------------------------------------------


def slug_of(save_path: Path) -> str:
    return _backup.slug_of(save_path, SAVE_SUFFIX)


def wait(save_path: Path) -> None:
    _backup.wait(save_path)


def periodic_backups(save_path: Path) -> list[Path]:
    return _backup.periodic_backups(save_path, suffix=SAVE_SUFFIX)


def periodic_backup_in_background(save_path: Path, turn: int, keep: int) -> threading.Thread:
    return _backup.periodic_backup_in_background(save_path, turn, keep, suffix=SAVE_SUFFIX)


# --- Migrations (TST ADR-0004 section 3) --------------------------------------------------


def upgrade_new(save_path: Path) -> None:
    MIGRATOR.upgrade_new(save_path)


def ensure_current(save_path: Path) -> Path | None:
    return MIGRATOR.ensure_current(save_path)
