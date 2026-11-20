"""Event modifiers (TST formulas.md 23.2): a choice's lasting percent change to one stat of a
person, a practice group or the whole firm. A modifier starts in the month it is chosen,
applies every month for its months, then expires. Several on the same stat multiply.

Ported from backend/tst/sim/events/modifiers.py @ 02fba2aa (Tech Startup Tycoon); changed:
targets are people, units and the firm; the stats are Partner Track's (a person's morale
target and how fast their strain builds), read by `person_factor`; ids from EventsState.
"""

from __future__ import annotations

from dataclasses import replace

from ptk.sim.events.data import MODIFIER_STATS, EventsBalance, Severity
from ptk.sim.events.models import Effect, Modifier, with_modifier
from ptk.sim.state import GameState

FIRM, UNIT, PERSON = "firm", "unit", "person"


def kind_id(target: str) -> tuple[str, int | None]:
    kind, _, rest = target.partition(":")
    return kind, int(rest) if rest.isdigit() else None


def running(state: GameState, firm_id: int) -> tuple[Modifier, ...]:
    """The firm's modifiers that apply this month."""
    return tuple(m for m in state.events.modifiers if m.firm_id == firm_id and m.active(state.turn))


def person_factor(state: GameState, person_id: int, stat: str) -> float:
    """A person stat: modifiers on the person, their unit and their firm (1.0 with none)."""
    if not state.events.modifiers:  # the common case: no event has started one
        return 1.0
    firm_id = state.employer_of(person_id)
    if firm_id is None:
        return 1.0
    targets = {(PERSON, person_id), (FIRM, firm_id)}
    unit_id = state.org.unit_of(person_id)
    if unit_id is not None:
        targets.add((UNIT, unit_id))
    out = 1.0
    for m in state.events.modifiers:
        if m.firm_id != firm_id or m.stat != stat or not m.active(state.turn):
            continue
        if kind_id(m.target) in targets:
            out *= m.factor
    return out


def clamp_modifier(
    value_pct: float, months: int, severity: Severity, events: EventsBalance
) -> tuple[float, int]:
    """Value and months held to the severity's caps (23.2)."""
    cap = events.cap("modifier", severity)
    return max(-cap, min(cap, value_pct)), max(1, min(events.max_months(severity), months))


def start(
    state: GameState,
    firm_id: int,
    event_id: int | None,
    effect: Effect,
    severity: Severity,
    events: EventsBalance,
) -> GameState:
    """A chosen modifier effect starts this month, its value and months clamped again (the
    stored choice was validated already; this keeps a hand-edited save inside the caps)."""
    kind, ident = kind_id(effect.target)
    if effect.stat not in MODIFIER_STATS or ident is None:
        return state
    if kind not in {PERSON if w == "other" else w for w in MODIFIER_STATS[effect.stat]}:
        return state
    value, months = clamp_modifier(effect.value, effect.months, severity, events)
    if value == 0:
        return state
    es = state.events
    modifier = Modifier(
        id=es.next_modifier_id,
        firm_id=firm_id,
        event_id=event_id,
        target=effect.target,
        stat=effect.stat,
        value_pct=value,
        start_turn=state.turn,
        end_turn=state.turn + months,
    )
    return replace(state, events=with_modifier(es, modifier))


def expire(state: GameState) -> tuple[GameState, tuple[Modifier, ...]]:
    """At month end: modifiers whose last month was this one leave the state. Returns the
    state and the expired modifiers."""
    done = tuple(m for m in state.events.modifiers if m.end_turn <= state.turn + 1)
    if not done:
        return state, ()
    gone = {m.id for m in done}
    kept = tuple(m for m in state.events.modifiers if m.id not in gone)
    return replace(state, events=replace(state.events, modifiers=kept)), done
