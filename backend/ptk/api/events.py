"""Events, read-only texts and the LLM settings and meter (PT-M6; ADR-0005, ADR-0009).

What the player sees of an event: its words, its choices and each choice's effects in words
and numbers (ptk.sim.events.describe), never a trigger's strength, a cap or a hidden value (a
case's merits shift is shown in words). Answering is one action in its own transaction
(`saves.run_action`, ADR-0014). The settings and the meter live beside the saves, not in one
(ADR-0005 sections 6 and 7); the API key is never stored or returned.
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field
from simcore.kernel.calendar import format_turn
from simcore_llm.settings import load_settings, month_key, month_spend, reset_date, save_settings
from sqlalchemy import select

from ptk import loader
from ptk.config import get_settings
from ptk.db import saves
from ptk.db.core import make_sessionmaker, shared_engine
from ptk.db.models import LLMTextRow
from ptk.sim.errors import UnknownEventError
from ptk.sim.events.actions import ChooseEvent
from ptk.sim.events.describe import choice_texts
from ptk.sim.events.effects import critical_open
from ptk.sim.events.models import GameEvent
from ptk.sim.events.render import full_name
from ptk.sim.state import GameState

RECENT = 60  # tunable-exempt: events listed (open ones always)
TEXTS = 12  # tunable-exempt: texts listed

type SeverityOut = Literal["minor", "major", "critical"]
type EventStatusOut = Literal["pending", "open", "answered", "auto"]
type TextKindOut = Literal[
    "headlines", "matter_brief", "pitch_letter", "partner_memo", "year_end_letter", "seat_report"
]


class EventRefOut(BaseModel):
    id: int
    name: str


class EventChoiceOut(BaseModel):
    key: str
    label: str
    effects: list[str]  # each effect in words and numbers; "Do nothing: no effect"


class EventOut(BaseModel):
    id: int
    turn: int
    date_label: str
    category: str
    severity: SeverityOut
    status: EventStatusOut
    title: str
    body: str
    choices: list[EventChoiceOut]
    chosen: str | None
    source: str  # who wrote the words: claude, template or mock
    storyline: str | None  # the storyline's title
    people: list[EventRefOut]
    client: EventRefOut | None
    matter: EventRefOut | None


class ChooseIn(BaseModel):
    choice: str = Field(pattern=r"^[ABC]$")


class TextOut(BaseModel):
    turn: int
    date_label: str
    kind: TextKindOut
    text: str
    source: str


class LLMSettingsOut(BaseModel):
    adapter: Literal["claude", "templates"]  # offline mode: templates
    monthly_budget_cents: int
    key_present: bool  # an ANTHROPIC_API_KEY is set (never returned)
    in_use: str  # the adapter that writes: claude, template or mock


class LLMSettingsIn(BaseModel):
    adapter: Literal["claude", "templates"]
    monthly_budget_cents: int = Field(ge=0, le=100_000)  # tunable-exempt: $1,000 a month at most


class MeterOut(BaseModel):
    month: str  # YYYY-MM, real calendar month
    spent_cents: int  # rounded
    budget_cents: int
    calls: int
    events_claude: int
    events_rejected: int
    avg_event_cents: float
    reset_date: str


def event_view(state: GameState, event: GameEvent) -> EventOut:
    balance = loader.balance()
    known = {p.id: p for p in state.people}
    story = state.events.storyline(event.storyline_id) if event.storyline_id else None
    client = None
    if event.client_id is not None:
        client = EventRefOut(id=event.client_id, name=state.market.client(event.client_id).name)
    matter_row = state.market.matter(event.matter_id) if event.matter_id is not None else None
    return EventOut(
        id=event.id,
        turn=event.turn,
        date_label=format_turn(event.turn, state.save_meta.start_ym),
        category=event.category,
        severity=event.severity,
        status=event.status,
        title=event.title or "(being written)",
        body=event.body,
        choices=[
            EventChoiceOut(key=c.key, label=c.label, effects=choice_texts(state, event, c, balance))
            for c in event.choices
        ],
        chosen=event.chosen,
        source=event.source,
        storyline=story.title if story else None,
        people=[
            EventRefOut(id=p, name=full_name(known[p])) for p in event.person_ids if p in known
        ],
        client=client,
        matter=EventRefOut(id=matter_row.id, name=matter_row.name) if matter_row else None,
    )


def blocking_event_id(state: GameState) -> int | None:
    """The written critical event that blocks Continue, if any (spec 15)."""
    waiting = critical_open(state)
    return waiting[0].id if waiting else None


def _state(slug: str) -> GameState:
    return saves.read_state(saves.open_save(get_settings().resolved_save_dir(), slug))[0]


def _settings_out() -> LLMSettingsOut:
    from ptk.db.events_io import default_adapter

    save_dir = get_settings().resolved_save_dir()
    settings = load_settings(save_dir)
    return LLMSettingsOut(
        adapter="templates" if settings.adapter == "templates" else "claude",
        monthly_budget_cents=settings.monthly_budget_cents,
        key_present=bool(get_settings().anthropic_api_key),
        in_use=default_adapter(save_dir).name,
    )


def make_events_router(errors: dict[int | str, dict[str, Any]]) -> APIRouter:
    router = APIRouter()
    base = "/api/saves/{slug}"

    @router.get(
        f"{base}/events", response_model=list[EventOut], responses=errors, operation_id="listEvents"
    )
    def list_events(slug: str) -> list[EventOut]:
        state = _state(slug)
        mine = [e for e in state.events.events if e.firm_id == state.player.id]
        closed = [e for e in reversed(mine) if not e.is_open][:RECENT]
        return [event_view(state, e) for e in [e for e in mine if e.is_open] + closed]

    @router.get(
        f"{base}/events/{{event_id}}",
        response_model=EventOut,
        responses=errors,
        operation_id="getEvent",
    )
    def get_event(slug: str, event_id: int) -> EventOut:
        state = _state(slug)
        event = state.events.event(event_id)
        if event is None or event.firm_id != state.player.id:
            raise UnknownEventError(f"no event {event_id}")
        return event_view(state, event)

    @router.post(
        f"{base}/events/{{event_id}}/choose",
        response_model=EventOut,
        responses=errors,
        operation_id="chooseEvent",
    )
    def choose_event(slug: str, event_id: int, body: ChooseIn) -> EventOut:
        path = saves.open_save(get_settings().resolved_save_dir(), slug)
        outcome = saves.run_action(
            path, ChooseEvent(event_id, body.choice), loader.balance(), loader.game_data()
        )
        event = outcome.state.events.event(event_id)
        assert event is not None
        return event_view(outcome.state, event)

    @router.get(
        f"{base}/texts", response_model=list[TextOut], responses=errors, operation_id="listTexts"
    )
    def list_texts(slug: str, kind: TextKindOut | None = None) -> list[TextOut]:
        path = saves.open_save(get_settings().resolved_save_dir(), slug)
        state = saves.read_state(path)[0]
        stmt = select(LLMTextRow).where(LLMTextRow.status == "written", LLMTextRow.text != "")
        if kind is not None:
            stmt = stmt.where(LLMTextRow.kind == kind)
        with make_sessionmaker(shared_engine(path))() as session:
            rows = session.scalars(stmt.order_by(LLMTextRow.id.desc()).limit(TEXTS)).all()
            return [
                TextOut(
                    turn=r.turn,
                    date_label=format_turn(r.turn, state.save_meta.start_ym),
                    kind=r.kind,
                    text=r.text,
                    source=r.source,
                )
                for r in rows
            ]

    @router.get("/api/llm/settings", response_model=LLMSettingsOut, operation_id="getLlmSettings")
    def get_llm_settings() -> LLMSettingsOut:
        return _settings_out()

    @router.put("/api/llm/settings", response_model=LLMSettingsOut, operation_id="setLlmSettings")
    def set_llm_settings(body: LLMSettingsIn) -> LLMSettingsOut:
        save_dir = get_settings().resolved_save_dir()
        settings = load_settings(save_dir).model_copy(
            update={"adapter": body.adapter, "monthly_budget_cents": body.monthly_budget_cents}
        )
        save_settings(save_dir, settings)
        return _settings_out()

    @router.get("/api/llm/meter", response_model=MeterOut, operation_id="getLlmMeter")
    def get_llm_meter() -> MeterOut:
        save_dir = get_settings().resolved_save_dir()
        spend = month_spend(save_dir)
        events = spend.events_claude
        return MeterOut(
            month=month_key(),
            spent_cents=round(spend.cents),
            budget_cents=load_settings(save_dir).monthly_budget_cents,
            calls=spend.calls,
            events_claude=events,
            events_rejected=spend.events_rejected,
            avg_event_cents=round(spend.event_cents / events, 2) if events else 0.0,
            reset_date=reset_date(),
        )

    return router
