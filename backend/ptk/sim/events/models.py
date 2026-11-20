"""Frozen event models (TST formulas.md 16; ADR-0005, ADR-0012).

Ported from backend/tst/sim/events/models.py @ 02fba2aa (Tech Startup Tycoon); changed:
firms instead of companies; an event names a matter, a client and a practice instead of a
product, segment, rival or loan; colleague relationships (TST's `Relationship`, 16.7) live
here as `ColleaguePair`; every events table is one `EventsState` on the game state.

Phase 12 of turn T queues next month's events as `GameEvent`s with status "pending" and
returns an `EventRequest` for each. After the turn commits, the event service writes the
words and the validated choices (status "open"); the player answers during month T + 1, or
Continue answers minor and major ones with their first choice. A written critical event
blocks Continue until it is answered.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

from ptk.sim.events.data import Severity

PCT = 100  # tunable-exempt: percent

type EventStatus = Literal["pending", "open", "answered", "auto"]
type StorylineStatus = Literal["active", "ended"]
type Tone = Literal["grounded", "light"]
type TextKind = Literal[
    "headlines", "matter_brief", "pitch_letter", "partner_memo", "year_end_letter"
]


@dataclass(frozen=True, slots=True)
class Effect:
    """One validated effect. `target` is "person:<id>", "pair:<a>-<b>", "unit:<id>",
    "firm:<id>", "client:<id>", "matter:<id>", "partnership" or "" (follow_up). A `modifier`
    also names its `stat` and how many `months` it runs; its value is percent."""

    type: str
    target: str
    value: float = 0.0
    stat: str = ""
    months: int = 0


@dataclass(frozen=True, slots=True)
class Modifier:
    """A running effect of an event choice (TST 23.2): `stat` of `target` x (1 + value_pct /
    100) every month from `start_turn` until `end_turn` (exclusive), then it expires."""

    id: int
    firm_id: int
    event_id: int | None
    target: str  # "person:<id>", "unit:<id>", "firm:<id>"
    stat: str
    value_pct: float
    start_turn: int
    end_turn: int

    def active(self, turn: int) -> bool:
        return self.start_turn <= turn < self.end_turn

    @property
    def factor(self) -> float:
        return 1 + self.value_pct / PCT


@dataclass(frozen=True, slots=True)
class EventChoice:
    key: str
    label: str
    effects: tuple[Effect, ...] = ()
    do_nothing: bool = False  # an explicit "Do nothing" choice (TST 23.2)


@dataclass(frozen=True, slots=True)
class GameEvent:
    id: int
    firm_id: int
    turn: int  # the month it is shown in (queued in phase 12 of turn - 1)
    template_id: str
    category: str
    severity: Severity
    trigger: str
    strength: float
    person_ids: tuple[int, ...] = ()  # the trigger's people (a pair: two)
    unit_id: int | None = None
    client_id: int | None = None
    matter_id: int | None = None
    practice: str | None = None
    months: int | None = None
    amount_cents: int | None = None  # a sum the trigger names (a new scale's first-year pay)
    cash_base_cents: int = 0  # max(cash, 3 x monthly fees) when queued
    tone: Tone = "grounded"
    storyline_id: int | None = None
    status: EventStatus = "pending"
    title: str = ""
    body: str = ""
    choices: tuple[EventChoice, ...] = ()
    chosen: str | None = None
    resolved_turn: int | None = None
    source: str = ""  # who wrote the words: claude, template or mock

    @property
    def is_open(self) -> bool:
        return self.status in ("pending", "open")

    def choice(self, key: str) -> EventChoice | None:
        return next((c for c in self.choices if c.key == key), None)


@dataclass(frozen=True, slots=True)
class Storyline:
    """A multi-month thread of template steps (TST 16.6)."""

    id: int
    firm_id: int
    key: str  # the template storyline key
    title: str
    step: int  # the last step queued
    started_turn: int
    summary: str
    person_ids: tuple[int, ...] = ()
    unit_id: int | None = None
    client_id: int | None = None
    matter_id: int | None = None
    practice: str | None = None
    next_turn: int | None = None  # the month the next step is shown in
    next_template: str | None = None
    status: StorylineStatus = "active"
    ended_turn: int | None = None


@dataclass(frozen=True, slots=True)
class QueuedEvent:
    """A follow-up of a critical event (TST 16.3), or an event a later milestone's engine
    queues by template id (`queue_engine_event`)."""

    id: int
    firm_id: int
    template_id: str
    due_turn: int  # the month it is shown in
    source_event_id: int | None  # None: queued by the engine
    person_ids: tuple[int, ...] = ()
    unit_id: int | None = None
    client_id: int | None = None
    matter_id: int | None = None
    practice: str | None = None
    done: bool = False


@dataclass(frozen=True, slots=True)
class ColleaguePair:
    """Two colleagues who work together, `a < b` (TST 16.7's relationship). `value` is the true
    relationship (-100 to 100); the player sees only a label."""

    a: int
    b: int
    value: float
    start: float
    since_turn: int

    @property
    def key(self) -> tuple[int, int]:
        return (self.a, self.b)


@dataclass(frozen=True, slots=True)
class TextRequest:
    """Read-only LLM text (TST 16.8; spec 15's kinds). `ref_id` is the matter of a briefing
    or the client of a pitch letter."""

    kind: TextKind
    firm_id: int
    turn: int
    ref_id: int | None = None


@dataclass(frozen=True, slots=True)
class EventRequest:
    """What phase 12 asks the event service to write (ADR-0012). The service reads the stored
    event and the state for everything else; `targets` is the eligible list."""

    event_id: int
    firm_id: int
    turn: int
    template_id: str
    severity: Severity
    tone: Tone
    targets: tuple[str, ...]
    storyline_id: int | None = None


@dataclass(frozen=True, slots=True)
class EventsState:
    """Every events table (sorted by id; colleague pairs by (a, b)). Records are never dropped
    except expired modifiers and colleague pairs whose people left."""

    events: tuple[GameEvent, ...] = ()
    storylines: tuple[Storyline, ...] = ()
    queued: tuple[QueuedEvent, ...] = ()
    modifiers: tuple[Modifier, ...] = ()
    colleagues: tuple[ColleaguePair, ...] = ()
    next_event_id: int = 1
    next_storyline_id: int = 1
    next_queued_id: int = 1
    next_modifier_id: int = 1

    def event(self, event_id: int) -> GameEvent | None:
        return next((e for e in self.events if e.id == event_id), None)

    def storyline(self, storyline_id: int) -> Storyline | None:
        return next((s for s in self.storylines if s.id == storyline_id), None)

    def open_events(self, firm_id: int) -> tuple[GameEvent, ...]:
        return tuple(e for e in self.events if e.firm_id == firm_id and e.is_open)

    def pair(self, a: int, b: int) -> ColleaguePair | None:
        x, y = (a, b) if a < b else (b, a)
        return next((p for p in self.colleagues if p.a == x and p.b == y), None)


EMPTY_EVENTS = EventsState()


# --- Upserts (return new EventsState; tuples stay sorted) -------------------------------------


def with_event(es: EventsState, event: GameEvent) -> EventsState:
    rest = [e for e in es.events if e.id != event.id]
    return replace(
        es,
        events=tuple(sorted([*rest, event], key=lambda e: e.id)),
        next_event_id=max(es.next_event_id, event.id + 1),
    )


def with_storyline(es: EventsState, story: Storyline) -> EventsState:
    rest = [s for s in es.storylines if s.id != story.id]
    return replace(
        es,
        storylines=tuple(sorted([*rest, story], key=lambda s: s.id)),
        next_storyline_id=max(es.next_storyline_id, story.id + 1),
    )


def with_queued(es: EventsState, queued: QueuedEvent) -> EventsState:
    rest = [q for q in es.queued if q.id != queued.id]
    return replace(
        es,
        queued=tuple(sorted([*rest, queued], key=lambda q: q.id)),
        next_queued_id=max(es.next_queued_id, queued.id + 1),
    )


def with_modifier(es: EventsState, modifier: Modifier) -> EventsState:
    rest = [m for m in es.modifiers if m.id != modifier.id]
    return replace(
        es,
        modifiers=tuple(sorted([*rest, modifier], key=lambda m: m.id)),
        next_modifier_id=max(es.next_modifier_id, modifier.id + 1),
    )


def with_pairs(es: EventsState, pairs: tuple[ColleaguePair, ...]) -> EventsState:
    return replace(es, colleagues=tuple(sorted(pairs, key=lambda p: p.key)))
