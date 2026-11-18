"""SQLAlchemy tables for one save file (ADR-0004). Data dictionary: docs/data-dictionary.md.

History tables (ledger, snapshots, turn log, decision log) are append-only; current-state
tables (save_meta, firm) are updated in place.
"""

from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SaveMetaRow(Base):
    __tablename__ = "save_meta"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # always 1
    name: Mapped[str] = mapped_column(String(80))
    master_seed: Mapped[int] = mapped_column(BigInteger)  # stored as signed; see state_io
    scenario_id: Mapped[str] = mapped_column(String(40))
    difficulty: Mapped[str] = mapped_column(String(20))
    start_year: Mapped[int] = mapped_column(Integer)
    start_month: Mapped[int] = mapped_column(Integer)
    current_turn: Mapped[int] = mapped_column(Integer)
    game_state: Mapped[str] = mapped_column(String(20))
    ended_turn: Mapped[int | None] = mapped_column(Integer, nullable=True)


class FirmRow(Base):
    __tablename__ = "firm"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    is_player: Mapped[bool]
    stage: Mapped[int] = mapped_column(Integer)
    founded_turn: Mapped[int] = mapped_column(Integer)
    home_city: Mapped[str] = mapped_column(String(40))


class LedgerEntryRow(Base):
    __tablename__ = "ledger_entry"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    turn: Mapped[int] = mapped_column(Integer, index=True)
    firm_id: Mapped[int] = mapped_column(ForeignKey("firm.id"), index=True)
    memo: Mapped[str] = mapped_column(Text)


class LedgerLineRow(Base):
    __tablename__ = "ledger_line"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("ledger_entry.id"), index=True)
    account: Mapped[str] = mapped_column(String(40), index=True)
    amount_cents: Mapped[int] = mapped_column(BigInteger)
    practice: Mapped[str | None] = mapped_column(String(40), nullable=True)
    office_id: Mapped[int | None] = mapped_column(Integer, nullable=True)


class TurnSnapshotRow(Base):
    __tablename__ = "turn_snapshot"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    turn: Mapped[int] = mapped_column(Integer, index=True)
    firm_id: Mapped[int] = mapped_column(ForeignKey("firm.id"), index=True)
    kpis_json: Mapped[str] = mapped_column(Text)


class TurnLogRow(Base):
    __tablename__ = "turn_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    turn: Mapped[int] = mapped_column(Integer, index=True)
    firm_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    kind: Mapped[str] = mapped_column(String(60))
    message: Mapped[str] = mapped_column(Text)


class DecisionLogRow(Base):
    __tablename__ = "decision_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    turn: Mapped[int] = mapped_column(Integer, index=True)
    seq: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(20))  # player, delegate, rival
    payload_json: Mapped[str] = mapped_column(Text)
