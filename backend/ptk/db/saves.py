"""Save files: create, list, open, and play a turn in one transaction (ADR-0004)."""

from __future__ import annotations

import json
import re
import secrets
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select

from ptk.db import backup, migrate
from ptk.db.models import FirmRow, SaveMetaRow, TurnSnapshotRow
from ptk.db.org_io import write_delegate_actions
from ptk.db.session import make_sessionmaker, shared_engine
from ptk.db.state_io import META_ID, insert_new, ledger_balances, load_state, write_turn
from ptk.sim.calendar import format_turn
from ptk.sim.data_models import Balance, GameData
from ptk.sim.decisions import Decisions
from ptk.sim.errors import InvalidSaveNameError, SaveExistsError, SaveNotFoundError
from ptk.sim.people.founder import FounderSpec
from ptk.sim.rng import MAX_SEED, RngFactory
from ptk.sim.setup import new_game
from ptk.sim.state import GameState
from ptk.sim.turn import TurnResult, advance_turn

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")


@dataclass(frozen=True, slots=True)
class SaveSummary:
    slug: str
    name: str
    firm_name: str
    turn: int
    date_label: str
    game_state: str


def save_path(save_dir: Path, slug: str) -> Path:
    if not _SLUG_RE.match(slug):
        raise InvalidSaveNameError(
            f"save names use lower-case letters, digits and hyphens, got {slug!r}"
        )
    return save_dir / f"{slug}{backup.SAVE_SUFFIX}"


def create_save(
    save_dir: Path,
    slug: str,
    *,
    firm_name: str,
    scenario_id: str,
    difficulty: str,
    data: GameData,
    balance: Balance,
    seed: int | None = None,
    founder: FounderSpec | None = None,
) -> GameState:
    path = save_path(save_dir, slug)
    if path.exists():
        raise SaveExistsError(f"a save named {slug!r} already exists")
    master_seed = secrets.randbelow(MAX_SEED + 1) if seed is None else seed
    game = new_game(
        name=slug,
        firm_name=firm_name,
        master_seed=master_seed,
        scenario_id=scenario_id,
        difficulty=difficulty,
        data=data,
        balance=balance,
        founder=founder,
    )
    save_dir.mkdir(parents=True, exist_ok=True)
    migrate.upgrade_new(path)
    sessions = make_sessionmaker(shared_engine(path))
    with sessions() as session, session.begin():
        insert_new(session, game.state, game.ledger_entries)
    return game.state


def open_save(save_dir: Path, slug: str) -> Path:
    path = save_path(save_dir, slug)
    if not path.is_file():
        raise SaveNotFoundError(f"no save named {slug!r}")
    backup.wait(path)
    migrate.ensure_current(path)
    return path


def read_state(path: Path) -> tuple[GameState, dict[tuple[int, str], int]]:
    sessions = make_sessionmaker(shared_engine(path))
    with sessions() as session:
        return load_state(session), ledger_balances(session)


def run_turn(path: Path, balance: Balance, data: GameData) -> TurnResult:
    """Play one month: load, advance, write everything in one transaction (ADR-0004 4)."""
    sessions = make_sessionmaker(shared_engine(path))
    with sessions() as session, session.begin():
        state = load_state(session)
        result = advance_turn(
            state,
            Decisions(),
            RngFactory(state.save_meta.master_seed),
            balance,
            data,
            ledger_balances(session),
        )
        write_turn(
            session, result.new_state, result.ledger_entries, result.log_items, result.snapshot
        )
        write_delegate_actions(session, state.turn, result.delegate_actions)
    if result.new_state.turn % balance.backups.every_turns == 0:
        backup.periodic_backup_in_background(
            path, result.new_state.turn, balance.backups.keep_periodic
        )
    return result


def list_saves(save_dir: Path) -> list[SaveSummary]:
    out: list[SaveSummary] = []
    if not save_dir.is_dir():
        return out
    for path in sorted(save_dir.glob(f"*{backup.SAVE_SUFFIX}")):
        sessions = make_sessionmaker(shared_engine(path))
        with sessions() as session:
            meta = session.get(SaveMetaRow, META_ID)
            firm = session.scalars(select(FirmRow).where(FirmRow.is_player)).first()
            if meta is None or firm is None:
                continue
            start = (meta.start_year, meta.start_month)
            out.append(
                SaveSummary(
                    slug=backup.slug_of(path),
                    name=meta.name,
                    firm_name=firm.name,
                    turn=meta.current_turn,
                    date_label=format_turn(meta.current_turn, start),
                    game_state=meta.game_state,
                )
            )
    return out


def snapshots(path: Path, firm_id: int) -> list[tuple[int, dict[str, object]]]:
    sessions = make_sessionmaker(shared_engine(path))
    with sessions() as session:
        rows = session.scalars(
            select(TurnSnapshotRow)
            .where(TurnSnapshotRow.firm_id == firm_id)
            .order_by(TurnSnapshotRow.turn)
        )
        return [(r.turn, json.loads(r.kpis_json)) for r in rows]
