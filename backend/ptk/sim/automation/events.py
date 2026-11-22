"""Routine events answered by an area's owner (spec 9.4; TST formulas.md 40.5).

Ported from backend/tst/sim/automation/events.py @ 80a38079 (Tech Startup Tycoon); changed:
Partner Track's event categories and effects. At the start of phase 1, before unanswered
events take their first choice (PT-M6), each open, written, non-critical event of the player's
firm whose category maps to an automated area with "Let them answer routine events" on is
answered by that area's owner; otherwise by the routine-events area's owner (the COO) if that
area is automated. The right rule picks the choice with the best listed effect as the player
sees it (cash per $10,000, morale, relationship, reputation, confidence and strain points, a
modifier per 5%), ties to a do-nothing or the smaller choice; the mistake picks the second
best. The quality draw is stream `auto_events` (id 61) keyed (event id,). Critical events always
go to the player. Hidden effects (a case's merits, a hidden tag) never count.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Final

from ptk.sim.automation import owners
from ptk.sim.automation.models import AreaDecision, AreaOwner
from ptk.sim.automation.run import owner_quality, remember
from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import SimError
from ptk.sim.events.models import EventChoice, GameEvent
from ptk.sim.ledger import LedgerEntry
from ptk.sim.log import LogItem
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState

STREAM: Final = "auto_events"
EVENTS_AREA: Final = "events"
# Event categories (data/events) and the area that answers them.
CATEGORY_AREA: Final[dict[str, str]] = {
    "client": "bd",
    "market": "bd",
    "press": "bd",
    "matter": "staffing",
    "people": "development",
    "partnership": "laterals",
    "regulatory": "intake",
    "technology": "offices",
}
# Points per unit of each listed effect, as the player reads a choice (TST 40.12).
WEIGHTS: Final[dict[str, float]] = {
    "cash_delta": 1 / 1_000_000,  # tunable-exempt: a point per $10,000 (cents)
    "morale_delta": 1.0,
    "relationship_delta": 1.0,
    "pair_delta": 0.5,
    "reputation_delta": 1.0,
    "confidence_delta": 1.0,
    "strain_delta": -1.0,
    "hours_pct": -0.2,
    "wip_writedown": -0.5,
    "modifier": 0.2,  # a point per 5%
}


def choice_value(choice: EventChoice) -> float:
    total = 0.0
    for e in choice.effects:
        w = WEIGHTS.get(e.type)
        if w is None:
            continue  # hidden or unvalued effects never count
        total += w * e.value
    return total


def ranked(event: GameEvent) -> list[EventChoice]:
    """Best first; ties to a do-nothing, then the smaller choice (fewer effects), then key."""
    return sorted(
        event.choices,
        key=lambda c: (-choice_value(c), not c.do_nothing, len(c.effects), c.key),
    )


def answerer(state: GameState, event: GameEvent, b: Balance) -> AreaOwner | None:
    auto = state.automation
    area = CATEGORY_AREA.get(event.category)
    if area is not None:
        slot = 0
        if owners.area_def(b, area).seat == "practice_group_leader":
            slot = event.unit_id or _group_of(state, event) or -1
        o = auto.owner(event.firm_id, area, slot)
        if o is not None and o.answer_events:
            return o
    o = auto.owner(event.firm_id, EVENTS_AREA, 0)
    return o if o is not None and o.answer_events else None


def _group_of(state: GameState, event: GameEvent) -> int | None:
    if event.practice is None:
        return None
    for u in state.org.firm_units(event.firm_id):
        if u.kind == "practice_group" and u.practice == event.practice:
            return u.id
    return None


def answer_routine_events(
    state: GameState, rng: RngFactory, b: Balance, data: GameData
) -> tuple[GameState, tuple[LedgerEntry, ...], tuple[LogItem, ...]]:
    """Phase 1, before PT-M6's auto-resolve."""
    from ptk.sim.events.effects import choose

    if state.ended or not state.automation.owners:
        return state, (), ()
    entries: list[LedgerEntry] = []
    logs: list[LogItem] = []
    lines: list[AreaDecision] = []
    firm = state.player.id
    start = sum(1 for d in state.automation.decisions if d.turn == state.turn)
    for event in state.events.open_events(firm):
        if event.severity == "critical" or event.status != "open" or not event.choices:
            continue
        o = answerer(state, event, b)
        if o is None:
            continue
        options = ranked(event)
        u = float(rng.stream(state.turn, "auto_events", event.id).random())
        right = u < owner_quality(state, o, b, data)
        pick = options[0] if right or len(options) == 1 else options[1]
        try:
            state, posted, logged = choose(state, event.id, pick.key, b, data)
        except SimError:
            continue
        entries += posted
        logs += [replace(i, in_digest=True) for i in logged]
        lines.append(
            AreaDecision(
                firm, state.turn, start + len(lines), o.area, o.slot, o.person_id,
                "event" if right or pick is options[0] else "mistake", "choose_event",
                f"answered \"{event.title}\": {pick.label}", 0, "event", event.id,
            )
        )  # fmt: skip
    if lines:
        state = remember(state, lines, b)
    return state, tuple(entries), tuple(logs)
