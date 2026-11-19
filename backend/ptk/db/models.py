"""SQLAlchemy tables for one save file (ADR-0004). Data dictionary: docs/data-dictionary.md.

History tables (ledger, snapshots, turn log, decision log) are append-only; current-state
tables (save_meta, firm) are updated in place.
"""

from __future__ import annotations

from sqlalchemy import BigInteger, Float, ForeignKey, Integer, String, Text
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
    pay_policy_mode: Mapped[str] = mapped_column(String(10))  # PT-M1b: match, lag, lead
    pay_policy_bp: Mapped[int] = mapped_column(Integer)  # bp of the market scale


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


# --- People (schema v2, PT-M1a). Current state, updated in place each turn. --------------
# Attribute sets are JSON lists of [key, value] pairs in data-file order; floats round-trip
# exactly through JSON (repr), so a reloaded save draws and grows identically.


class PersonRow(Base):
    __tablename__ = "person"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(40))
    last_name: Mapped[str] = mapped_column(String(40))
    birth_turn: Mapped[int] = mapped_column(Integer)
    role: Mapped[str] = mapped_column(String(40))
    level: Mapped[str] = mapped_column(String(40))
    skills_json: Mapped[str] = mapped_column(Text)
    personality_json: Mapped[str] = mapped_column(Text)
    hidden_json: Mapped[str] = mapped_column(Text)  # hidden traits: never in the API
    potential_ability: Mapped[float] = mapped_column(Float)  # hidden: never in the API
    familiarity_json: Mapped[str] = mapped_column(Text)
    familiarity_peak_json: Mapped[str] = mapped_column(Text)
    interests_json: Mapped[str] = mapped_column(Text)
    work_style: Mapped[str] = mapped_column(String(40))
    tags_json: Mapped[str] = mapped_column(Text)  # true tags; shown only once revealed
    school_tier: Mapped[str | None] = mapped_column(String(40), nullable=True)
    bar_admissions_json: Mapped[str] = mapped_column(Text)
    city: Mapped[str] = mapped_column(String(40))
    strain: Mapped[float] = mapped_column(Float)
    burnout_since: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_burnout_turn: Mapped[int | None] = mapped_column(Integer, nullable=True)
    book_cents: Mapped[int] = mapped_column(BigInteger)
    portability_bp: Mapped[int | None] = mapped_column(Integer, nullable=True)  # hidden
    is_founder: Mapped[bool]
    founding_partner: Mapped[bool]
    background: Mapped[str | None] = mapped_column(String(40), nullable=True)
    real: Mapped[bool]


class EmploymentRow(Base):
    __tablename__ = "employment"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("person.id"), index=True)
    firm_id: Mapped[int] = mapped_column(ForeignKey("firm.id"), index=True)
    start_turn: Mapped[int] = mapped_column(Integer)
    end_turn: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20))
    end_reason: Mapped[str | None] = mapped_column(String(20), nullable=True)
    salary_cents: Mapped[int] = mapped_column(BigInteger)  # PT-M1b: a year


class RevealRow(Base):
    __tablename__ = "reveal_state"
    observer_firm_id: Mapped[int] = mapped_column(ForeignKey("firm.id"), primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("person.id"), primary_key=True)
    attributes_json: Mapped[str] = mapped_column(Text)  # [[key, hw, offset, turn], ...]
    profile_revealed_turn: Mapped[int | None] = mapped_column(Integer, nullable=True)
    revealed_tags_json: Mapped[str] = mapped_column(Text)  # [[tag, turn], ...]


# --- Hiring, pay and the inbox (schema v3, PT-M1b) ------------------------------------------


class SearchRow(Base):
    __tablename__ = "search"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    firm_id: Mapped[int] = mapped_column(ForeignKey("firm.id"), index=True)
    role: Mapped[str] = mapped_column(String(40))
    channel: Mapped[str] = mapped_column(String(20))
    actor_id: Mapped[int] = mapped_column(Integer)
    opened_turn: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20))
    closed_turn: Mapped[int | None] = mapped_column(Integer, nullable=True)
    level: Mapped[str | None] = mapped_column(String(40), nullable=True)
    school_tiers_json: Mapped[str] = mapped_column(Text)
    plan_id: Mapped[int | None] = mapped_column(Integer, nullable=True)


class CandidateRow(Base):
    __tablename__ = "candidate"
    person_id: Mapped[int] = mapped_column(ForeignKey("person.id"), primary_key=True)
    firm_id: Mapped[int] = mapped_column(ForeignKey("firm.id"), index=True)
    search_id: Mapped[int] = mapped_column(ForeignKey("search.id"), index=True)
    channel: Mapped[str] = mapped_column(String(20))
    ask_cents: Mapped[int] = mapped_column(BigInteger)
    created_turn: Mapped[int] = mapped_column(Integer)
    expires_turn: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20))
    resolved_turn: Mapped[int | None] = mapped_column(Integer, nullable=True)
    interviewed_turn: Mapped[int | None] = mapped_column(Integer, nullable=True)


class OfferRow(Base):
    __tablename__ = "offer"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    firm_id: Mapped[int] = mapped_column(ForeignKey("firm.id"), index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("person.id"), index=True)
    actor_id: Mapped[int] = mapped_column(Integer)
    salary_cents: Mapped[int] = mapped_column(BigInteger)
    made_turn: Mapped[int] = mapped_column(Integer)
    start_turn: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20))
    resolved_turn: Mapped[int | None] = mapped_column(Integer, nullable=True)
    plan_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unit_id: Mapped[int | None] = mapped_column(Integer, nullable=True)


class PersonStateRow(Base):
    __tablename__ = "person_state"
    person_id: Mapped[int] = mapped_column(ForeignKey("person.id"), primary_key=True)
    energy: Mapped[int | None] = mapped_column(Integer, nullable=True)
    morale: Mapped[float | None] = mapped_column(Float, nullable=True)


class InboxItemRow(Base):
    """Rendered inbox entries for the player's firm (append-only, except `read`)."""

    __tablename__ = "inbox_item"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    turn: Mapped[int] = mapped_column(Integer, index=True)
    firm_id: Mapped[int] = mapped_column(Integer, index=True)
    template: Mapped[str] = mapped_column(String(60))
    title: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)
    link_kind: Mapped[str | None] = mapped_column(String(20), nullable=True)
    link_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    read: Mapped[bool]
