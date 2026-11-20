"""Applying an event's choice (TST formulas.md 16.3; ADR-0005, ADR-0014): the engine disposes.
Every effect was validated and clamped when the event was written; here it is clamped again
against the stored severity and cash base, and anything whose target is gone (someone left, a
pair ended, a matter closed) is skipped. A restricted effect never touches a person flagged
real (ADR PT-0013).

Ported from backend/tst/sim/events/effects.py @ 02fba2aa (Tech Startup Tycoon); changed: law
effects (client relationships, colleague pairs, strain, a matter's hours and merits, WIP
write-downs, reputation and confidence through interfaces' hooks) replace product, board,
loan and industry steps; Continue is blocked by critical events only (spec 15).
"""

from __future__ import annotations

from dataclasses import replace

from ptk.sim import interfaces
from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import CriticalEventOpenError, EventActionError, UnknownEventError
from ptk.sim.events.colleagues import clamp_relationship, pair_key, with_pair_value
from ptk.sim.events.data import REAL_RESTRICTED_EFFECTS
from ptk.sim.events.formulas import clamp_effect
from ptk.sim.events.models import (
    EventChoice,
    GameEvent,
    QueuedEvent,
    with_event,
    with_queued,
    with_storyline,
)
from ptk.sim.events.modifiers import start as start_modifier
from ptk.sim.hiring.models import PersonState
from ptk.sim.ledger import CASH, FEES, GENERAL_ADMIN, LedgerEntry
from ptk.sim.log import LogItem, inbox_item
from ptk.sim.matters.intake import bump, with_matter
from ptk.sim.money import exact
from ptk.sim.people.formulas import clamp_strain
from ptk.sim.state import (
    GameState,
    with_employment,
    with_person,
    with_person_states,
    with_reveals,
)

MORALE_MAX = 100.0  # tunable-exempt: morale scale 0-100
PERCENT = 100  # tunable-exempt: percent, as an integer for exact money
PAIR = 2  # tunable-exempt: two people


def parse_target(target: str) -> tuple[str, tuple[int, ...]]:
    """Split a target: "person:12" is ("person", (12,)), "pair:3-9" is ("pair", (3, 9)),
    "partnership" is ("partnership", ())."""
    kind, _, rest = target.partition(":")
    if not rest:
        return kind, ()
    try:
        return kind, tuple(int(x) for x in rest.split("-"))
    except ValueError:
        return kind, ()


def _employees(state: GameState, firm_id: int) -> list[int]:
    founder = state.founder_of(firm_id)
    return [p for p in state.staff_ids(firm_id) if p != founder]


def _unit_members(state: GameState, firm_id: int, unit_id: int) -> list[int]:
    staff = set(_employees(state, firm_id))
    return sorted(
        m.person_id for m in state.org.members if m.unit_id == unit_id and m.person_id in staff
    )


def _people_of(state: GameState, firm_id: int, kind: str, ids: tuple[int, ...]) -> list[int]:
    staff = set(state.staff_ids(firm_id))
    if kind == "person" and ids and ids[0] in staff:
        return [ids[0]]
    if kind == "unit" and ids:
        return _unit_members(state, firm_id, ids[0])
    if kind == "firm":
        return _employees(state, firm_id)
    return []


def _morale(state: GameState, person_ids: list[int], value: float) -> GameState:
    moved: list[PersonState] = []
    for pid in person_ids:
        ps = state.person_state(pid)
        if ps.morale is not None:
            moved.append(replace(ps, morale=max(0.0, min(MORALE_MAX, ps.morale + value))))
    return with_person_states(state, moved)


def _strain(state: GameState, person_ids: list[int], value: float) -> GameState:
    for pid in person_ids:
        person = state.person(pid)
        state = with_person(state, replace(person, strain=clamp_strain(person.strain + value)))
    return state


def _retain(state: GameState, person_id: int) -> tuple[GameState, list[LogItem]]:
    """Someone serving notice after resigning stays (TST 23.3): the notice is withdrawn."""
    employment = state.employment_of(person_id)
    if employment is None or employment.status != "notice" or employment.end_reason != "resigned":
        return state, []
    state = with_employment(
        state, replace(employment, status="active", end_turn=None, end_reason=None)
    )
    person = state.person(person_id)
    log = inbox_item(
        state.turn,
        employment.firm_id,
        "retained",
        link_kind="person",
        link_id=person_id,
        name=f"{person.first_name} {person.last_name}",
    )
    return state, [log]


def _is_real(state: GameState, person_id: int) -> bool:
    return any(p.real for p in state.people if p.id == person_id)


def apply_choice(
    state: GameState,
    event: GameEvent,
    key: str,
    balance: Balance,
    data: GameData,
    *,
    auto: bool,
) -> tuple[GameState, tuple[LedgerEntry, ...], tuple[LogItem, ...]]:
    """Apply one choice of an open event and close it. An event whose words were never
    written (no choices) closes with nothing applied."""
    choice: EventChoice | None = event.choice(key)
    entries: list[LedgerEntry] = []
    logs: list[LogItem] = []
    fid = event.firm_id
    staff = set(state.staff_ids(fid))
    memo = f"Event: {event.title or event.template_id}"
    for effect in choice.effects if choice else ():
        kind, ids = parse_target(effect.target)
        value = clamp_effect(
            effect.type, effect.value, event.severity, balance.events, event.cash_base_cents
        )
        t = effect.type
        if t in REAL_RESTRICTED_EFFECTS and kind == "person" and ids and _is_real(state, ids[0]):
            continue  # ADR PT-0013: the validator refuses these; a hand-edited save cannot
        if t == "morale_delta":
            state = _morale(state, _people_of(state, fid, kind, ids), value)
        elif t == "strain_delta":
            state = _strain(state, _people_of(state, fid, kind, ids), value)
        elif t == "relationship_delta" and kind == "client" and ids:
            state = replace(state, market=bump(state.market, ids[0], fid, value))
        elif t == "pair_delta" and kind == "pair" and len(ids) == PAIR:
            pair = state.events.pair(*pair_key(ids[0], ids[1]))
            if pair is not None:
                moved = clamp_relationship(pair.value + value, balance.colleagues)
                state = with_pair_value(state, pair.a, pair.b, moved)
        elif t == "cash_delta" and kind == "firm" and round(value):
            cents = round(value)
            entries.append(
                LedgerEntry.transfer(
                    turn=state.turn,
                    firm_id=fid,
                    memo=memo,
                    debit=GENERAL_ADMIN if cents < 0 else CASH,
                    credit=CASH if cents < 0 else FEES,
                    amount=abs(cents),
                )
            )
        elif t == "reputation_delta" and kind == "firm":
            state = interfaces.reputation_change(state, fid, value)
        elif t == "confidence_delta" and kind == "partnership":
            state = interfaces.confidence_change(state, fid, value)
        elif t in ("hours_pct", "merits_shift", "wip_writedown") and kind == "matter" and ids:
            matter = state.market.matter(ids[0])
            if matter is None or not matter.is_open or matter.firm_id != fid:
                continue
            if t == "hours_pct":
                # Exactly, rounded half-to-even once; never below the hours already worked.
                needed = round(matter.hours_needed_tenths * (1 + exact(value) / PERCENT))
                matter = replace(matter, hours_needed_tenths=max(matter.worked_tenths + 1, needed))
                state = replace(state, market=with_matter(state.market, matter))
            elif t == "merits_shift":
                matter = replace(matter, merits=matter.merits + value)
                state = replace(state, market=with_matter(state.market, matter))
            else:
                state, posted = interfaces.write_down_wip(state, matter.id, value, memo)
                entries += posted
        elif t == "growth_boost" and kind == "person" and ids and ids[0] in staff:
            person = state.person(ids[0])
            skill = data.role(person.role).primary[0]
            skills = person.skills.updated({skill: person.skills[skill] + value})
            state = with_person(state, replace(person, skills=skills))
        elif t == "reveal_tag" and kind == "person" and ids and ids[0] in staff:
            person = state.person(ids[0])
            reveal = state.reveal(fid, person.id)
            known = {tag for tag, _ in reveal.revealed_tags} if reveal else set()
            hidden = [tag for tag in person.tags if tag not in known]
            if reveal is not None and hidden:
                tag = hidden[0]
                state = with_reveals(
                    state,
                    [replace(reveal, revealed_tags=(*reveal.revealed_tags, (tag, state.turn)))],
                )
                logs.append(
                    inbox_item(
                        state.turn,
                        fid,
                        "tag_revealed",
                        link_kind="person",
                        link_id=person.id,
                        name=f"{person.first_name} {person.last_name}",
                        reveal_text=next(x.reveal_text for x in data.tags if x.key == tag),
                    )
                )
        elif t == "salary_change" and kind == "person" and ids and ids[0] in staff:
            salary = interfaces.salary_cents(state, ids[0])
            if salary is not None and salary > 0 and value > 0:
                # Exactly, rounded half-to-even once (ADR-0003).
                state = interfaces.set_salary(
                    state, ids[0], round(salary * (1 + exact(value) / PERCENT))
                )
        elif t == "resign" and kind == "person" and ids and ids[0] in staff:
            employment = state.employment_of(ids[0])
            person = state.person(ids[0])
            if employment is not None and employment.status == "active" and not person.is_founder:
                state = with_employment(
                    state,
                    replace(
                        employment, status="notice", end_turn=state.turn + 1, end_reason="resigned"
                    ),
                )
                logs.append(
                    inbox_item(
                        state.turn,
                        fid,
                        "resigned",
                        link_kind="person",
                        link_id=person.id,
                        name=f"{person.first_name} {person.last_name}",
                    )
                )
        elif t == "retain" and kind == "person" and ids:
            state, kept = _retain(state, ids[0])
            logs += kept
        elif t == "follow_up":
            template = data.event_template(event.template_id)
            if template.follow_up:
                es = state.events
                queued = QueuedEvent(
                    id=es.next_queued_id,
                    firm_id=fid,
                    template_id=template.follow_up,
                    due_turn=state.turn + 1,
                    source_event_id=event.id,
                    person_ids=event.person_ids,
                    unit_id=event.unit_id,
                    client_id=event.client_id,
                    matter_id=event.matter_id,
                    practice=event.practice,
                )
                state = replace(state, events=with_queued(es, queued))
        elif t == "modifier":
            state = start_modifier(state, fid, event.id, effect, event.severity, balance.events)
    es = with_event(
        state.events,
        replace(
            event,
            status="auto" if auto else "answered",
            chosen=key if choice else None,
            resolved_turn=state.turn,
        ),
    )
    if event.storyline_id is not None:
        story = es.storyline(event.storyline_id)
        if story is not None and story.status == "active" and story.next_template is None:
            es = with_storyline(es, replace(story, status="ended", ended_turn=state.turn))
    return replace(state, events=es), tuple(entries), tuple(logs)


def critical_open(state: GameState) -> tuple[GameEvent, ...]:
    """The player's written critical events still to answer: Continue is refused until they
    are answered (spec 15; TST ADR-0006)."""
    return tuple(
        e
        for e in state.events.open_events(state.player.id)
        if e.severity == "critical" and e.status == "open"
    )


def check_continue(state: GameState) -> None:
    """Refuse Continue while a written critical event waits (spec 15)."""
    waiting = critical_open(state)
    if waiting:
        first = waiting[0]
        raise CriticalEventOpenError(
            f"answer {first.title or first.template_id!r} before you continue", first.id
        )


def auto_resolve(
    state: GameState, balance: Balance, data: GameData, *, critical: bool = False
) -> tuple[GameState, tuple[LedgerEntry, ...], tuple[LogItem, ...]]:
    """Phase 1: the player's unanswered minor and major events resolve to their first choice
    at Continue (TST 16.3). A written critical event never reaches here (advance_turn refuses)
    unless `critical` (scripts and the golden seeds answer it with its first choice too); an
    event whose words were never written closes with nothing applied (only in-memory runs play
    turns without the event service)."""
    entries: list[LedgerEntry] = []
    logs: list[LogItem] = []
    for event in state.events.open_events(state.player.id):
        if event.severity == "critical" and event.status == "open" and not critical:
            continue
        first = event.choices[0].key if event.choices else "A"
        state, posted, logged = apply_choice(state, event, first, balance, data, auto=True)
        entries += posted
        logs += logged
    return state, tuple(entries), tuple(logs)


def choose(
    state: GameState, event_id: int, key: str, balance: Balance, data: GameData
) -> tuple[GameState, tuple[LedgerEntry, ...], tuple[LogItem, ...]]:
    """The player answers an open, written event (an immediate action, ADR-0014)."""
    event = state.events.event(event_id)
    if event is None or event.firm_id != state.player.id:
        raise UnknownEventError(f"no event {event_id}")
    if event.status != "open":
        raise EventActionError(f"event {event_id} is not waiting for an answer")
    if event.choice(key) is None:
        raise EventActionError(f"event {event_id} has no choice {key!r}")
    return apply_choice(state, event, key, balance, data, auto=False)
