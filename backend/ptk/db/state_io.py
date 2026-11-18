"""Load the game state from a save and write a turn's results (ADR-0004)."""

from __future__ import annotations

import json
from dataclasses import replace

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ptk.db.models import (
    FirmRow,
    LedgerEntryRow,
    LedgerLineRow,
    SaveMetaRow,
    TurnLogRow,
    TurnSnapshotRow,
)
from ptk.sim.ledger import LedgerEntry
from ptk.sim.log import LogItem
from ptk.sim.money import Cents
from ptk.sim.snapshot import TurnSnapshot
from ptk.sim.state import FirmState, GameState, SaveMeta

META_ID = 1
_SIGN = 2**63  # SQLite integers are signed 64-bit; seeds are 0..2**64-1


def seed_to_db(seed: int) -> int:
    return seed - _SIGN


def seed_from_db(value: int) -> int:
    return value + _SIGN


def insert_new(session: Session, state: GameState, entries: tuple[LedgerEntry, ...]) -> None:
    meta = state.save_meta
    session.add(
        SaveMetaRow(
            id=META_ID,
            name=meta.name,
            master_seed=seed_to_db(meta.master_seed),
            scenario_id=meta.scenario_id,
            difficulty=meta.difficulty,
            start_year=meta.start_ym[0],
            start_month=meta.start_ym[1],
            current_turn=state.turn,
            game_state=meta.game_state,
            ended_turn=meta.ended_turn,
        )
    )
    for firm in state.firms:
        session.add(
            FirmRow(
                id=firm.id,
                name=firm.name,
                is_player=firm.is_player,
                stage=firm.stage,
                founded_turn=firm.founded_turn,
                home_city=firm.home_city,
            )
        )
    session.flush()
    write_entries(session, entries)


def load_state(session: Session) -> GameState:
    row = session.get(SaveMetaRow, META_ID)
    if row is None:
        raise LookupError("save has no save_meta row")
    meta = SaveMeta(
        name=row.name,
        master_seed=seed_from_db(row.master_seed),
        scenario_id=row.scenario_id,
        difficulty=row.difficulty,
        start_ym=(row.start_year, row.start_month),
        game_state=row.game_state,  # type: ignore[arg-type]
        ended_turn=row.ended_turn,
    )
    firms = tuple(
        FirmState(
            id=f.id,
            name=f.name,
            is_player=f.is_player,
            stage=f.stage,
            founded_turn=f.founded_turn,
            home_city=f.home_city,
        )
        for f in session.scalars(select(FirmRow).order_by(FirmRow.id))
    )
    return GameState(save_meta=meta, turn=row.current_turn, firms=firms)


def ledger_balances(session: Session) -> dict[tuple[int, str], Cents]:
    stmt = (
        select(LedgerEntryRow.firm_id, LedgerLineRow.account, func.sum(LedgerLineRow.amount_cents))
        .join(LedgerEntryRow, LedgerLineRow.entry_id == LedgerEntryRow.id)
        .group_by(LedgerEntryRow.firm_id, LedgerLineRow.account)
    )
    return {(int(f), str(a)): int(total) for f, a, total in session.execute(stmt)}


def write_entries(session: Session, entries: tuple[LedgerEntry, ...]) -> None:
    for entry in entries:
        row = LedgerEntryRow(turn=entry.turn, firm_id=entry.firm_id, memo=entry.memo)
        session.add(row)
        session.flush()
        session.add_all(
            LedgerLineRow(
                entry_id=row.id,
                account=line.account,
                amount_cents=line.amount,
                practice=line.practice,
                office_id=line.office_id,
            )
            for line in entry.lines
        )


def write_turn(
    session: Session,
    new_state: GameState,
    entries: tuple[LedgerEntry, ...],
    log_items: tuple[LogItem, ...],
    snapshot: TurnSnapshot,
) -> None:
    write_entries(session, entries)
    session.add_all(
        TurnLogRow(turn=i.turn, firm_id=i.firm_id, kind=i.kind, message=i.message)
        for i in log_items
    )
    session.add_all(
        TurnSnapshotRow(turn=snapshot.turn, firm_id=f.firm_id, kpis_json=json.dumps(f.kpis()))
        for f in snapshot.firms
    )
    meta = session.get(SaveMetaRow, META_ID)
    assert meta is not None
    meta.current_turn = new_state.turn
    meta.game_state = new_state.save_meta.game_state
    meta.ended_turn = new_state.save_meta.ended_turn
    for firm in new_state.firms:
        row = session.get(FirmRow, firm.id)
        assert row is not None
        row.name, row.stage = firm.name, firm.stage


def with_turn(state: GameState, turn: int) -> GameState:
    return replace(state, turn=turn)
