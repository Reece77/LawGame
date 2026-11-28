"""Load and write the events state (schema v7, PT-M6), and the event service against a save.

Events, storylines, queued events, modifiers, colleague pairs and the id counters are current
state, rewritten in place. `write_pending` runs after a turn commits (and before the next turn,
in case it did not): in one transaction it gives every pending event its words and choices and
every pending text its words, logs each adapter call, adds an inbox item for each, then adds
the spend to the monthly meter (TST tst/db/events.py's pattern).
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

from simcore_llm.base import LLMAdapter
from simcore_llm.settings import active_adapter, add_spend, load_settings, month_spend
from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from ptk.config import get_settings
from ptk.db.core import make_sessionmaker, shared_engine
from ptk.db.models import (
    ColleaguePairRow,
    EventCountersRow,
    EventModifierRow,
    GameEventRow,
    InboxItemRow,
    LLMCallLogRow,
    LLMTextRow,
    QueuedEventRow,
    StorylineRow,
)
from ptk.events.service import TEXT_TITLES, Writer, kpis_of, write_event, write_text
from ptk.sim.data_models import Balance, GameData
from ptk.sim.events.models import (
    ColleaguePair,
    Effect,
    EventChoice,
    EventsState,
    GameEvent,
    Modifier,
    QueuedEvent,
    Storyline,
    TextRequest,
)
from ptk.sim.ledger import CASH

COUNTERS_ID: Final = 1
EVENT_KINDS: Final = {"critical": "critical_event"}  # inbox template by severity; else "event"
TEASER_WORDS: Final = 30  # tunable-exempt: inbox preview length
TEXT_INBOX: Final = "llm_text"  # the inbox template of a written read-only text
# What a written text's inbox item links to (PT-M8: a seat report opens its holder's page).
TEXT_LINKS: Final[dict[str, Any]] = {"matter_brief": "matter", "seat_report": "person"}


def text_title(state: Any, kind: str, turn: int, ref_id: int | None, data: GameData) -> str:
    """A written text's inbox title; a seat report names its seat and holder (PT-M8)."""
    if kind == "seat_report" and ref_id is not None:
        from ptk.loader import balance as load_balance
        from ptk.sim.org.reports import report_facts

        return report_facts(state, turn, state.player.id, ref_id, data, load_balance())[0]
    return TEXT_TITLES.get(kind, kind)


NOT_IN_INBOX: Final = ("headlines",)  # shown on the Overview, not as inbox items


# --- (De)serialising ----------------------------------------------------------------------------


def _choice(raw: dict[str, Any]) -> EventChoice:
    return EventChoice(
        key=raw["key"],
        label=raw["label"],
        effects=tuple(Effect(**e) for e in raw["effects"]),
        do_nothing=raw.get("do_nothing", False),
    )


def _event_data(e: GameEvent) -> str:
    data = asdict(e)
    for key in ("id", "firm_id", "turn", "template_id", "category", "severity", "status", "title"):
        data.pop(key)
    return json.dumps(data, sort_keys=True)


def _event(row: GameEventRow) -> GameEvent:
    data = json.loads(row.data_json)
    data["person_ids"] = tuple(data["person_ids"])
    data["choices"] = tuple(_choice(c) for c in data["choices"])
    return GameEvent(
        id=row.id,
        firm_id=row.firm_id,
        turn=row.turn,
        template_id=row.template_id,
        category=row.category,
        severity=row.severity,  # type: ignore[arg-type]
        status=row.status,  # type: ignore[arg-type]
        title=row.title,
        **data,
    )


def _rest(obj: object, *keys: str) -> str:
    data = asdict(obj)  # type: ignore[call-overload]
    for key in keys:
        data.pop(key)
    return json.dumps(data, sort_keys=True)


def load_events(session: Session) -> EventsState:
    events = tuple(
        _event(r) for r in session.scalars(select(GameEventRow).order_by(GameEventRow.id))
    )
    storylines = []
    for r in session.scalars(select(StorylineRow).order_by(StorylineRow.id)):
        data = json.loads(r.data_json)
        data["person_ids"] = tuple(data["person_ids"])
        storylines.append(
            Storyline(id=r.id, firm_id=r.firm_id, key=r.key, status=r.status, **data)  # type: ignore[arg-type]
        )
    queued = []
    for q in session.scalars(select(QueuedEventRow).order_by(QueuedEventRow.id)):
        data = json.loads(q.data_json)
        data["person_ids"] = tuple(data["person_ids"])
        queued.append(
            QueuedEvent(
                id=q.id,
                firm_id=q.firm_id,
                template_id=q.template_id,
                due_turn=q.due_turn,
                done=q.done,
                **data,
            )
        )
    modifiers = tuple(
        Modifier(
            id=r.id,
            firm_id=r.firm_id,
            event_id=r.event_id,
            target=r.target,
            stat=r.stat,
            value_pct=r.value_pct,
            start_turn=r.start_turn,
            end_turn=r.end_turn,
        )
        for r in session.scalars(select(EventModifierRow).order_by(EventModifierRow.id))
    )
    pairs = tuple(
        ColleaguePair(a=r.a, b=r.b, value=r.value, start=r.start, since_turn=r.since_turn)
        for r in session.scalars(
            select(ColleaguePairRow).order_by(ColleaguePairRow.a, ColleaguePairRow.b)
        )
    )
    counters = session.get(EventCountersRow, COUNTERS_ID)
    return EventsState(
        events=events,
        storylines=tuple(storylines),
        queued=tuple(queued),
        modifiers=modifiers,
        colleagues=pairs,
        next_event_id=counters.next_event_id if counters else 1,
        next_storyline_id=counters.next_storyline_id if counters else 1,
        next_queued_id=counters.next_queued_id if counters else 1,
        next_modifier_id=counters.next_modifier_id if counters else 1,
    )


def write_events(session: Session, es: EventsState) -> None:
    """Rewrite the events tables from the state."""
    for table in (
        GameEventRow,
        StorylineRow,
        QueuedEventRow,
        EventModifierRow,
        ColleaguePairRow,
        EventCountersRow,
    ):
        session.execute(delete(table))
    if es.events:
        session.execute(
            insert(GameEventRow),
            [
                {
                    "id": e.id,
                    "firm_id": e.firm_id,
                    "turn": e.turn,
                    "template_id": e.template_id,
                    "category": e.category,
                    "severity": e.severity,
                    "status": e.status,
                    "title": e.title,
                    "data_json": _event_data(e),
                }
                for e in es.events
            ],
        )
    if es.storylines:
        session.execute(
            insert(StorylineRow),
            [
                {
                    "id": s.id,
                    "firm_id": s.firm_id,
                    "key": s.key,
                    "status": s.status,
                    "data_json": _rest(s, "id", "firm_id", "key", "status"),
                }
                for s in es.storylines
            ],
        )
    if es.queued:
        session.execute(
            insert(QueuedEventRow),
            [
                {
                    "id": q.id,
                    "firm_id": q.firm_id,
                    "template_id": q.template_id,
                    "due_turn": q.due_turn,
                    "done": q.done,
                    "data_json": _rest(q, "id", "firm_id", "template_id", "due_turn", "done"),
                }
                for q in es.queued
            ],
        )
    if es.modifiers:
        session.execute(insert(EventModifierRow), [asdict(m) for m in es.modifiers])
    if es.colleagues:
        session.execute(insert(ColleaguePairRow), [asdict(p) for p in es.colleagues])
    session.add(
        EventCountersRow(
            id=COUNTERS_ID,
            next_event_id=es.next_event_id,
            next_storyline_id=es.next_storyline_id,
            next_queued_id=es.next_queued_id,
            next_modifier_id=es.next_modifier_id,
        )
    )


def add_text_requests(session: Session, requests: tuple[TextRequest, ...]) -> None:
    session.add_all(
        LLMTextRow(
            turn=r.turn,
            firm_id=r.firm_id,
            kind=r.kind,
            ref_id=r.ref_id,
            status="pending",
            text="",
            source="",
        )
        for r in requests
    )


# --- The service against a save -----------------------------------------------------------------


def default_adapter(save_dir: Path) -> LLMAdapter:
    """The adapter the settings choose (PTK_LLM_ADAPTER wins; tests set "mock")."""
    settings = get_settings()
    return active_adapter(load_settings(save_dir), settings.anthropic_api_key, settings.llm_adapter)


def event_inbox_row(event: GameEvent) -> InboxItemRow:
    """An inbox item for a written event, opening its card."""
    words = event.body.split()
    teaser = " ".join(words[:TEASER_WORDS]) + ("…" if len(words) > TEASER_WORDS else "")
    return InboxItemRow(
        turn=event.turn,
        firm_id=event.firm_id,
        template=EVENT_KINDS.get(event.severity, "event"),
        title=event.title,
        body=teaser,
        link_kind="event",
        link_id=event.id,
        read=False,
    )


def has_pending(session: Session) -> bool:
    return (
        session.scalar(select(GameEventRow.id).where(GameEventRow.status == "pending").limit(1))
        is not None
        or session.scalar(select(LLMTextRow.id).where(LLMTextRow.status == "pending").limit(1))
        is not None
    )


def write_pending(
    path: Path,
    balance: Balance,
    data: GameData,
    *,
    adapter: LLMAdapter | None = None,
) -> int:
    """Write every pending event and text of the save; returns how many events were written."""
    from ptk.db.state_io import ledger_balances, load_state

    save_dir = path.parent
    sessions = make_sessionmaker(shared_engine(path))
    with sessions() as session, session.begin():
        if not has_pending(session):
            return 0
        state = load_state(session)
        settings = load_settings(save_dir)
        spent = month_spend(save_dir).cents
        writer = Writer(
            adapter=adapter or default_adapter(save_dir),
            settings=settings,
            budget_left=lambda: settings.monthly_budget_cents - spent,
            debug=os.environ.get("PTK_LLM_DEBUG") == "1",
        )
        cash = ledger_balances(session).get((state.player.id, CASH), 0)
        kpis = kpis_of(state, cash, data)
        pending = [e for e in state.events.events if e.status == "pending"]
        for event in pending:
            state = write_event(state, event, kpis, writer, balance, data)
        texts = list(
            session.scalars(
                select(LLMTextRow).where(LLMTextRow.status == "pending").order_by(LLMTextRow.id)
            )
        )
        for text in texts:
            text.text, text.source = write_text(
                state, text.kind, text.turn, text.ref_id, writer, kpis, data
            )
            text.status = "written"
            if text.text and text.kind not in NOT_IN_INBOX:
                session.add(
                    InboxItemRow(
                        turn=text.turn,
                        firm_id=text.firm_id,
                        template=TEXT_INBOX,
                        title=text_title(state, text.kind, text.turn, text.ref_id, data),
                        body=text.text,
                        link_kind=TEXT_LINKS.get(text.kind),
                        link_id=text.ref_id if text.kind in TEXT_LINKS else None,
                        read=False,
                    )
                )
        now = datetime.now(UTC).isoformat(timespec="seconds")
        session.add_all(
            LLMCallLogRow(
                turn=state.turn,
                purpose=r.purpose,
                model=r.model,
                prompt_hash=r.prompt_hash,
                input_tokens=r.input_tokens,
                output_tokens=r.output_tokens,
                cost_cents=r.cost_cents,
                latency_ms=r.latency_ms,
                outcome=r.outcome,
                created_at=now,
                prompt=r.prompt,
                response=r.response,
            )
            for r in writer.records
        )
        written = {e.id for e in pending}
        opened = [e for e in state.events.events if e.id in written and e.status == "open"]
        session.add_all(event_inbox_row(e) for e in opened)
        write_events(session, state.events)
    if writer.records or writer.spent_cents:
        add_spend(
            save_dir,
            writer.spent_cents,
            calls=sum(1 for r in writer.records if r.outcome != "budget"),
            claude_events=writer.claude_events if writer.adapter.name == "claude" else 0,
            rejected=writer.rejected,
            event_cents=writer.event_cents,
        )
    return len(opened)
