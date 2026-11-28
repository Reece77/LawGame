"""PT-M6 director: seeded and repeatable, cooldowns, the critical gap, storylines, engine
events, Continue blocked by a written critical event, and ADR PT-0013's real-person rule."""

from __future__ import annotations

from collections import Counter
from dataclasses import replace
from itertools import pairwise

import pytest

from ptk.sim.data_models import Balance, GameData
from ptk.sim.decisions import Decisions
from ptk.sim.errors import CriticalEventOpenError
from ptk.sim.events.data import REAL_RESTRICTED_EFFECTS, TRIGGERS
from ptk.sim.events.director import queue_engine_event
from ptk.sim.events.effects import choose, critical_open
from ptk.sim.state import GameState, with_people
from ptk.sim.streams import RngFactory
from ptk.sim.turn import advance_turn
from tests.events_support import played
from tests.hiring_helpers import mock_events
from tests.matters_support import game, grown_firm, play


def _signature(state: GameState) -> list[tuple[object, ...]]:
    return [
        (e.id, e.turn, e.template_id, e.severity, e.person_ids, e.matter_id, e.client_id, e.tone)
        for e in state.events.events
    ]


def test_same_seed_same_events(data: GameData, balance: Balance) -> None:
    a = played(data, balance, seed=5, turns=12)
    b = played(data, balance, seed=5, turns=12)
    assert _signature(a) == _signature(b)
    assert a.events == b.events
    c = played(data, balance, seed=6, turns=12)
    assert _signature(a) != _signature(c)


def test_unwritten_events_have_no_effect(data: GameData, balance: Balance) -> None:
    """In-memory turns without the event service queue events but never write them: they
    close at Continue with nothing applied (only the service gives them choices)."""
    state, _ = play(game(data, balance, 4), data, balance, 6, 4)
    assert state.events.events  # the director ran
    assert all(e.status in ("pending", "auto") and not e.choices for e in state.events.events)


def test_cooldowns_and_critical_gap(data: GameData, balance: Balance) -> None:
    ev = balance.events
    state, _ = play(grown_firm(data, balance, 30, seed=2), data, balance, 36, 2, write_events=True)
    events = state.events.events
    by_template: dict[str, list[int]] = {}
    for e in events:
        by_template.setdefault(e.template_id, []).append(e.turn)
    for template_id, turns in by_template.items():
        template = data.event_template(template_id)
        if template.trigger not in TRIGGERS:  # crises, storylines and follow-ups are exempt
            continue
        gaps = [later - first for first, later in pairwise(turns)]
        assert all(g >= ev.template_cooldown_turns for g in gaps), (template_id, turns)
    critical = sorted(e.turn for e in events if e.severity == "critical")
    pairs = pairwise(critical)
    assert all(later - first >= ev.critical_gap_turns for first, later in pairs)


@pytest.mark.nightly  # PT-M11: over 60 s; check's runtime (product manager, 2026-11-23)
def test_storyline_runs_its_steps(data: GameData, balance: Balance) -> None:
    seen = Counter()
    for seed in range(1, 9):
        state = played(data, balance, seed=seed, turns=24)
        for story in state.events.storylines:
            steps = [e for e in state.events.events if e.storyline_id == story.id]
            assert [e.turn for e in steps] == sorted(e.turn for e in steps)
            seen[story.key] += 1
            if story.status == "ended" and story.key == "star_flight" and len(steps) == 3:
                assert [e.template_id for e in steps] == [
                    "star_headhunter",
                    "star_offer",
                    "star_decision",
                ]
    assert seen  # storylines happen


def test_engine_event_arrives_critical_and_blocks_continue(
    data: GameData, balance: Balance
) -> None:
    state = played(data, balance, seed=3, turns=2)
    state = queue_engine_event(state, "partner_group_exit", state.turn + 1)
    rng = RngFactory(3)
    result = advance_turn(state, Decisions(), rng, balance, data, {}, answer_critical=True)
    state = mock_events(result.new_state, balance, data)
    waiting = critical_open(state)
    assert [e.template_id for e in waiting] == ["partner_group_exit"]
    assert waiting[0].severity == "critical"
    with pytest.raises(CriticalEventOpenError):
        advance_turn(state, Decisions(), rng, balance, data, {})
    state, _entries, _ = choose(state, waiting[0].id, "A", balance, data)
    assert not critical_open(state)
    assert state.events.event(waiting[0].id).status == "answered"  # type: ignore[union-attr]
    advance_turn(state, Decisions(), rng, balance, data, {})  # Continue works again


def test_continue_answers_minor_and_major_with_first_choice(
    data: GameData, balance: Balance
) -> None:
    state = played(data, balance, seed=3, turns=6)
    for e in state.events.events:
        if e.turn < state.turn and e.severity != "critical":
            assert e.status == "auto"
            assert e.chosen == "A"


# --- ADR PT-0013: no restricted event, tag or effect ever selects a person flagged real -----


def _all_real(state: GameState) -> GameState:
    return with_people(state, [replace(p, real=True, tags=()) for p in state.people])


@pytest.mark.parametrize("seed", (1, 2, 3, 4))
def test_no_restricted_event_selects_a_real_person(
    seed: int, data: GameData, balance: Balance
) -> None:
    """Everyone flagged real: over three years of a 30-lawyer firm with every event written
    and answered with its first choice, no restricted template (misconduct, blame, burnout)
    names a real person, no event effect resigns one or reveals a tag about one, and no real
    person gains a tag or leaves through an event."""
    state = _all_real(grown_firm(data, balance, 30, seed))
    rng = RngFactory(seed)
    known_before = {(r.person_id, t) for r in state.reveals for t in r.revealed_tags}
    for _ in range(36):
        result = advance_turn(state, Decisions(), rng, balance, data, {}, answer_critical=True)
        state = mock_events(result.new_state, balance, data)
        # newcomers (hires) are made real too, so every person is real throughout
        state = _all_real(state)
    real = {p.id for p in state.people if p.real}
    for event in state.events.events:
        template = data.event_template(event.template_id)
        if template.restricted:
            assert not set(event.person_ids) & real, event
        for choice in event.choices:
            for effect in choice.effects:
                if effect.type in REAL_RESTRICTED_EFFECTS:
                    kind, _, rest = effect.target.partition(":")
                    assert not (kind == "person" and int(rest) in real), (event, effect)
    for reveal in state.reveals:  # no tag was revealed about anyone after the start
        assert {(reveal.person_id, t) for t in reveal.revealed_tags} <= known_before


def test_restricted_template_skipped_for_a_real_person(data: GameData, balance: Balance) -> None:
    """A burnout hit on a real person never becomes the restricted burnout event."""
    from ptk.sim.events.director import candidates
    from ptk.sim.events.triggers import TriggerHit

    state = played(data, balance, seed=3, turns=2)
    pid = next(p.id for p in state.people if not p.is_founder)
    hit = TriggerHit("burnout", 0.7, (pid,))
    assert any(c.template.restricted for c in candidates(state, [hit], balance, data))
    state = with_people(state, [replace(state.person(pid), real=True)])
    assert not any(c.template.restricted for c in candidates(state, [hit], balance, data))
