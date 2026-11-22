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
    conflict_checks: Mapped[bool]  # PT-M3a (ADR PT-0009 5)
    # PT-M7a: pro bono (spec 7.8) and the yearly rate rise
    pro_bono_credit_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pro_bono_avg_tenths: Mapped[float] = mapped_column(Float, default=0.0)
    rate_rise_bp: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rate_index: Mapped[float] = mapped_column(Float, default=1.0)
    # PT-M7b: the card by practice ({practice: bp}, JSON) and the firm's hours policy
    rate_card: Mapped[str] = mapped_column(Text, default="{}")
    billable_target_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)


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
    pro_bono_ytd_tenths: Mapped[int] = mapped_column(Integer, default=0)  # PT-M7a


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


# --- Org (schema v4, PT-M2). Current state, rewritten each turn and after each org action. ---


class OrgUnitRow(Base):
    __tablename__ = "org_unit"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    firm_id: Mapped[int] = mapped_column(ForeignKey("firm.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20))  # practice_group, team
    name: Mapped[str] = mapped_column(String(64))
    parent_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # None: firm root
    leader_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    practice: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_turn: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20))  # active, dissolved
    dissolved_turn: Mapped[int | None] = mapped_column(Integer, nullable=True)


class OrgMemberRow(Base):
    __tablename__ = "org_member"
    person_id: Mapped[int] = mapped_column(ForeignKey("person.id"), primary_key=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("org_unit.id"), index=True)


class HiringPlanRow(Base):
    __tablename__ = "hiring_plan"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    firm_id: Mapped[int] = mapped_column(ForeignKey("firm.id"), index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("person.id"))
    unit_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    role: Mapped[str] = mapped_column(String(40))
    target: Mapped[int] = mapped_column(Integer)
    channel: Mapped[str] = mapped_column(String(20))
    ratio_bp: Mapped[int] = mapped_column(Integer)
    created_turn: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20))
    hired: Mapped[int] = mapped_column(Integer)
    closed_turn: Mapped[int | None] = mapped_column(Integer, nullable=True)
    focus: Mapped[str] = mapped_column(String(20))
    level: Mapped[str | None] = mapped_column(String(40), nullable=True)
    hires_json: Mapped[str] = mapped_column(Text)  # [person_id, ...]
    activity_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # last activity


class OrgPersonRow(Base):
    __tablename__ = "org_person"
    person_id: Mapped[int] = mapped_column(ForeignKey("person.id"), primary_key=True)
    last_raise_turn: Mapped[int | None] = mapped_column(Integer, nullable=True)
    accelerated_years: Mapped[int] = mapped_column(Integer)
    last_promoted_turn: Mapped[int | None] = mapped_column(Integer, nullable=True)


class OrgMoraleNudgeRow(Base):
    __tablename__ = "org_morale_nudge"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # recording order
    person_id: Mapped[int] = mapped_column(ForeignKey("person.id"))
    turn: Mapped[int] = mapped_column(Integer)
    points: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(String(40))


# --- Clients and matters (schema v5, PT-M3a). Current state, rewritten each turn and after each
# action, except client and judge (written once at game creation) and hours_log (append-only).


class ClientRow(Base):
    __tablename__ = "client"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    sector: Mapped[str] = mapped_column(String(40))
    real: Mapped[bool]
    data_json: Mapped[str] = mapped_column(Text)  # the rest of the Client, GC included


class JudgeRow(Base):
    __tablename__ = "judge"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    court: Mapped[str] = mapped_column(String(40))
    first_name: Mapped[str] = mapped_column(String(40))
    last_name: Mapped[str] = mapped_column(String(40))
    traits_json: Mapped[str] = mapped_column(Text)  # hidden procedural traits
    real: Mapped[bool]
    from_turn: Mapped[int] = mapped_column(Integer, default=0)  # PT-M5: on the bench from
    until_turn: Mapped[int | None] = mapped_column(Integer, nullable=True)  # PT-M5: off it from


class RelationshipRow(Base):
    __tablename__ = "relationship"
    client_id: Mapped[int] = mapped_column(ForeignKey("client.id"), primary_key=True)
    firm_id: Mapped[int] = mapped_column(ForeignKey("firm.id"), primary_key=True)
    score: Mapped[float] = mapped_column(Float)
    partner_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    data_json: Mapped[str] = mapped_column(Text)  # the rest of the Relationship


class MatterRow(Base):
    __tablename__ = "matter"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    firm_id: Mapped[int] = mapped_column(ForeignKey("firm.id"), index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("client.id"), index=True)
    practice: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20), index=True)
    opened_turn: Mapped[int] = mapped_column(Integer)
    closed_turn: Mapped[int | None] = mapped_column(Integer, nullable=True)
    data_json: Mapped[str] = mapped_column(Text)  # the rest of the Matter, hidden values included


class AppearanceRow(Base):
    __tablename__ = "appearance"
    person_id: Mapped[int] = mapped_column(ForeignKey("person.id"), primary_key=True)
    judge_id: Mapped[int] = mapped_column(ForeignKey("judge.id"), primary_key=True)
    tenths: Mapped[int] = mapped_column(Integer)


class OriginationRow(Base):
    __tablename__ = "origination"
    person_id: Mapped[int] = mapped_column(ForeignKey("person.id"), primary_key=True)
    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    cents: Mapped[int] = mapped_column(BigInteger)


class HoursLogRow(Base):
    """Every month's hours by person and matter or client flow (append-only)."""

    __tablename__ = "hours_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    turn: Mapped[int] = mapped_column(Integer, index=True)
    person_id: Mapped[int] = mapped_column(Integer, index=True)
    client_id: Mapped[int] = mapped_column(Integer)
    practice: Mapped[str] = mapped_column(String(40))
    matter_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    tenths: Mapped[int] = mapped_column(Integer)
    substantive_tenths: Mapped[int] = mapped_column(Integer)
    value_cents: Mapped[int] = mapped_column(BigInteger)


class MarketDemandRow(Base):
    __tablename__ = "market_demand"
    practice: Mapped[str] = mapped_column(String(40), primary_key=True)
    demand_cents: Mapped[int] = mapped_column(BigInteger)  # the last month played


# --- Events and the LLM (schema v7, PT-M6) ---------------------------------------------------
# Events, storylines, queued events, modifiers and colleague pairs are current state, rewritten
# each turn and after each answer; the LLM's texts and call log are append-only (a text's words
# are filled in once, after its turn commits).


class GameEventRow(Base):
    __tablename__ = "game_event"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    firm_id: Mapped[int] = mapped_column(ForeignKey("firm.id"), index=True)
    turn: Mapped[int] = mapped_column(Integer, index=True)
    template_id: Mapped[str] = mapped_column(String(60))
    category: Mapped[str] = mapped_column(String(20))
    severity: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(10), index=True)
    title: Mapped[str] = mapped_column(Text)
    data_json: Mapped[str] = mapped_column(Text)  # the rest of the GameEvent, choices included


class StorylineRow(Base):
    __tablename__ = "storyline"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    firm_id: Mapped[int] = mapped_column(ForeignKey("firm.id"), index=True)
    key: Mapped[str] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(10))
    data_json: Mapped[str] = mapped_column(Text)


class QueuedEventRow(Base):
    __tablename__ = "queued_event"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    firm_id: Mapped[int] = mapped_column(ForeignKey("firm.id"), index=True)
    template_id: Mapped[str] = mapped_column(String(60))
    due_turn: Mapped[int] = mapped_column(Integer)
    done: Mapped[bool]
    data_json: Mapped[str] = mapped_column(Text)


class EventModifierRow(Base):
    __tablename__ = "event_modifier"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    firm_id: Mapped[int] = mapped_column(ForeignKey("firm.id"), index=True)
    event_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target: Mapped[str] = mapped_column(String(40))
    stat: Mapped[str] = mapped_column(String(40))
    value_pct: Mapped[float] = mapped_column(Float)
    start_turn: Mapped[int] = mapped_column(Integer)
    end_turn: Mapped[int] = mapped_column(Integer)


class ColleaguePairRow(Base):
    __tablename__ = "colleague_pair"
    a: Mapped[int] = mapped_column(ForeignKey("person.id"), primary_key=True)
    b: Mapped[int] = mapped_column(ForeignKey("person.id"), primary_key=True)
    value: Mapped[float] = mapped_column(Float)  # hidden: the player sees a label
    start: Mapped[float] = mapped_column(Float)
    since_turn: Mapped[int] = mapped_column(Integer)


class EventCountersRow(Base):
    """The next ids of the events tables (records are dropped, so max + 1 is not enough)."""

    __tablename__ = "event_counters"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # always 1
    next_event_id: Mapped[int] = mapped_column(Integer)
    next_storyline_id: Mapped[int] = mapped_column(Integer)
    next_queued_id: Mapped[int] = mapped_column(Integer)
    next_modifier_id: Mapped[int] = mapped_column(Integer)


class LLMTextRow(Base):
    """A read-only text (TST 16.8): pending when its turn commits, written after."""

    __tablename__ = "llm_text"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    turn: Mapped[int] = mapped_column(Integer, index=True)
    firm_id: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(30))
    ref_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(10), index=True)  # pending, written
    text: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(20))


class LLMCallLogRow(Base):
    """Every adapter call (ADR-0005 section 6): append-only, for the meter and debugging."""

    __tablename__ = "llm_call_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    turn: Mapped[int] = mapped_column(Integer, index=True)
    purpose: Mapped[str] = mapped_column(String(30))
    model: Mapped[str] = mapped_column(String(60))
    prompt_hash: Mapped[str] = mapped_column(String(16))
    input_tokens: Mapped[int] = mapped_column(Integer)
    output_tokens: Mapped[int] = mapped_column(Integer)
    cost_cents: Mapped[float] = mapped_column(Float)  # tenths of a cent matter; money-exact: meter
    latency_ms: Mapped[int] = mapped_column(Integer)
    outcome: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[str] = mapped_column(String(32))  # wall clock: the meter only
    prompt: Mapped[str | None] = mapped_column(Text, nullable=True)  # PTK_LLM_DEBUG=1 only
    response: Mapped[str | None] = mapped_column(Text, nullable=True)


# --- Billing (schema v6, PT-M3b). Engagements and bills keep every row (closed ones stay for
# history; the state loads the open ones); flow accounts and padders are current state;
# billing_month holds each month's totals; the client book is append-only.


class EngagementRow(Base):
    __tablename__ = "engagement"
    matter_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    firm_id: Mapped[int] = mapped_column(ForeignKey("firm.id"), index=True)
    client_id: Mapped[int] = mapped_column(Integer, index=True)
    model: Mapped[str] = mapped_column(String(20))
    closed: Mapped[bool]
    closed_turn: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    data_json: Mapped[str] = mapped_column(Text)  # the rest of the Engagement


class FlowAccountRow(Base):
    __tablename__ = "flow_account"
    firm_id: Mapped[int] = mapped_column(ForeignKey("firm.id"), primary_key=True)
    client_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    practice: Mapped[str] = mapped_column(String(40), primary_key=True)
    data_json: Mapped[str] = mapped_column(Text)


class BillRow(Base):
    __tablename__ = "bill"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    firm_id: Mapped[int] = mapped_column(ForeignKey("firm.id"), index=True)
    client_id: Mapped[int] = mapped_column(Integer, index=True)
    matter_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    practice: Mapped[str] = mapped_column(String(40))
    model: Mapped[str] = mapped_column(String(20))
    kind: Mapped[str] = mapped_column(String(20))
    issued_turn: Mapped[int] = mapped_column(Integer, index=True)
    status: Mapped[str] = mapped_column(String(20), index=True)
    closed_turn: Mapped[int | None] = mapped_column(Integer, nullable=True)
    billed_cents: Mapped[int] = mapped_column(BigInteger)
    data_json: Mapped[str] = mapped_column(Text)  # the whole Bill, dispute included


class BillingMonthRow(Base):
    __tablename__ = "billing_month"
    firm_id: Mapped[int] = mapped_column(ForeignKey("firm.id"), primary_key=True)
    turn: Mapped[int] = mapped_column(Integer, primary_key=True)
    data_json: Mapped[str] = mapped_column(Text)  # MonthTotals


class BillingPadderRow(Base):
    __tablename__ = "billing_padder"
    person_id: Mapped[int] = mapped_column(Integer, primary_key=True)


class ClientBookEntryRow(Base):
    __tablename__ = "client_book_entry"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    turn: Mapped[int] = mapped_column(Integer, index=True)
    firm_id: Mapped[int] = mapped_column(ForeignKey("firm.id"), index=True)
    memo: Mapped[str] = mapped_column(Text)


class ClientBookLineRow(Base):
    __tablename__ = "client_book_line"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("client_book_entry.id"), index=True)
    account: Mapped[str] = mapped_column(String(40))  # C1000_client_bank, C2000_owed_to_clients
    client_id: Mapped[int] = mapped_column(Integer, index=True)
    amount_cents: Mapped[int] = mapped_column(BigInteger)


# --- Rival firms (schema v9, PT-M5). Current state, rewritten each turn. --------------------
# The rivals' state is one JSON document (firms, key-people membership, moves, approaches,
# RFPs, free agents, history). Key people are generated from it on demand, never stored.


class RivalStateRow(Base):
    __tablename__ = "rival_state"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # always 1
    real_people: Mapped[bool]
    data_json: Mapped[str] = mapped_column(Text)


# --- PT-M4: the partnership (schema v8) -----------------------------------------------------


class PartnershipRow(Base):
    __tablename__ = "partnership"
    firm_id: Mapped[int] = mapped_column(Integer, primary_key=True)  # 0: the id counters
    data_json: Mapped[str] = mapped_column(Text)  # FirmPartnership (or the counters)


# --- PT-M8: seats, authority, pitches (schema v13) ------------------------------------------
# One JSON document (ptk.sim.org.seat_models.LeadershipState). A practice group leader's seat
# is the unit's leader (org_unit.leader_id), so PT-M2's leaders are the holders already.


class LeadershipRow(Base):
    __tablename__ = "leadership"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # always 1
    data_json: Mapped[str] = mapped_column(Text)


# --- PT-M17: the founder's life, family and personal books (schema v13) -----------------------
# The founder-life and family states are JSON documents (one row each); the players' personal
# books are their own double entry (like the client-money book), never mixed with a firm's.


class FounderLifeRow(Base):
    __tablename__ = "founder_life"
    key: Mapped[str] = mapped_column(String(20), primary_key=True)  # "founder_life", "family"
    data_json: Mapped[str] = mapped_column(Text)


class PersonalEntryRow(Base):
    __tablename__ = "personal_entry"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    turn: Mapped[int] = mapped_column(Integer, index=True)
    person_id: Mapped[int] = mapped_column(Integer, index=True)
    memo: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(20))


class PersonalLineRow(Base):
    __tablename__ = "personal_line"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("personal_entry.id"), index=True)
    account: Mapped[str] = mapped_column(String(40))  # 9xxx personal accounts only
    amount_cents: Mapped[int] = mapped_column(BigInteger)
