"""Helpers for PT-M6 tests: a played firm with matters and events, and hand-made events."""

from __future__ import annotations

from dataclasses import replace

from ptk.sim.data_models import Balance, GameData
from ptk.sim.events.models import Effect, EventChoice, GameEvent, with_event
from ptk.sim.state import GameState
from tests.matters_support import game, play


def played(data: GameData, balance: Balance, seed: int = 3, turns: int = 8) -> GameState:
    """A biglaw-spinout firm after `turns` months, its events written by the mock adapter."""
    state, _ = play(game(data, balance, seed), data, balance, turns, seed, write_events=True)
    return state


def open_event(
    state: GameState,
    *effects: Effect,
    severity: str = "major",
    person_ids: tuple[int, ...] = (),
    client_id: int | None = None,
    matter_id: int | None = None,
    cash_base_cents: int = 100_000_000,
    template_id: str = "gc_demand_ask",
) -> tuple[GameState, GameEvent]:
    """The state with one open, written event whose choice A carries `effects`."""
    es = state.events
    event = GameEvent(
        id=es.next_event_id,
        firm_id=state.player.id,
        turn=state.turn,
        template_id=template_id,
        category="client",
        severity=severity,  # type: ignore[arg-type]
        trigger="gc_demand",
        strength=0.5,
        person_ids=person_ids,
        client_id=client_id,
        matter_id=matter_id,
        cash_base_cents=cash_base_cents,
        status="open",
        title="A test event",
        body="Body.",
        choices=(EventChoice("A", "Do it", effects), EventChoice("B", "No", (), True)),
        source="template",
    )
    return replace(state, events=with_event(es, event)), event


def employees(state: GameState) -> list[int]:
    founder = state.founder_of(state.player.id)
    return [
        e.person_id
        for e in state.staff(state.player.id)
        if e.person_id != founder and e.status == "active"
    ]
