"""PT-M6 context builder (ADR-0005 section 4; CLAUDE.md section 10): an LLM prompt carries
revealed ranges as words, revealed tags and public matter facts, and never a hidden true
value: a case's merits or opposing counsel's quality, a partner's portability, potential, a
person's hidden traits or unrevealed tags, a general counsel's personality or a judge's
traits. Planted marker values must not appear anywhere in any prompt."""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from ptk.events.context import build_prompt, person_context
from ptk.events.service import kpis_of
from ptk.sim.data_models import Balance, GameData
from ptk.sim.events.director import eligible_targets
from ptk.sim.events.models import GameEvent
from ptk.sim.matters.intake import with_matter
from ptk.sim.matters.models import MeritsAssessment
from ptk.sim.state import GameState, with_people
from tests.events_support import played

MERITS = 1.23456789
OPPOSING = 17.6543
PORTABILITY = 7321
POTENTIAL = 187.6543
HIDDEN = 19.4321
RANGE_LO, RANGE_HI = 0.7345678, 1.7345678  # PT-M7a: an early case assessment's range
STRAY = "toxic_high_performer"  # a tag the firm has not noticed


def _plant(state: GameState, data: GameData) -> GameState:
    """Distinctive hidden values everywhere, so a leak shows up in the prompt text."""
    people = []
    for p in state.people:
        hidden = p.hidden.updated({k: HIDDEN for k, _ in p.hidden.items})
        people.append(
            replace(
                p,
                hidden=hidden,
                potential_ability=POTENTIAL,
                portability_bp=PORTABILITY,
                tags=(*p.tags, STRAY) if STRAY not in p.tags else p.tags,
            )
        )
    state = with_people(state, people)
    market = state.market
    for m in market.matters:
        market = with_matter(
            market,
            replace(
                m,
                merits=MERITS,
                opposing_quality=OPPOSING,
                assessment=MeritsAssessment(turn=0, lo=RANGE_LO, hi=RANGE_HI),
            ),
        )
    return replace(state, market=market)


@pytest.fixture(scope="module")
def planted(data: GameData, balance: Balance) -> GameState:
    return _plant(played(data, balance, seed=3, turns=10), data)


def _events_for_every_template(state: GameState, data: GameData) -> list[GameEvent]:
    staff = [e.person_id for e in state.staff(state.player.id)]
    matter = state.market.open_matters(state.player.id)[0]
    out = []
    for i, template in enumerate(data.event_templates):
        out.append(
            GameEvent(
                id=10_000 + i,
                firm_id=state.player.id,
                turn=state.turn,
                template_id=template.id,
                category=template.category,
                severity=template.severities[-1],
                trigger=template.trigger,
                strength=0.6,
                person_ids=tuple(staff[:2]),
                client_id=matter.client_id,
                matter_id=matter.id,
                practice=matter.practice,
                months=24,
                amount_cents=16_000_000,
                cash_base_cents=50_000_000,
                tone="light" if i % 2 else "grounded",
            )
        )
    return out


def test_prompts_never_carry_hidden_values(
    planted: GameState, data: GameData, balance: Balance
) -> None:
    kpis = kpis_of(planted, 123_400_00, data)
    stray_label = next(t.label for t in data.tags if t.key == STRAY)
    hidden_keys = {h.key for h in data.hidden}
    gc_traits = {t.key for t in data.personality}
    judge_traits = {t.key for t in data.courts.judge_traits}
    for event in _events_for_every_template(planted, data):
        template = data.event_template(event.template_id)
        system, user = build_prompt(
            planted, event, template, eligible_targets(planted, event), kpis, balance, data
        )
        text = system + user
        for marker in (MERITS, OPPOSING, PORTABILITY, POTENTIAL, HIDDEN, RANGE_LO, RANGE_HI):
            assert str(marker) not in text, (event.template_id, marker)
        assert stray_label not in text and STRAY not in text
        context = json.loads(user)
        keys = _keys(context)
        assert not keys & {"merits", "opposing_quality", "portability_bp", "potential_ability"}
        assert not keys & hidden_keys
        assert not keys & judge_traits
        gc = (context.get("client") or {}).get("general_counsel")
        assert gc is None or isinstance(gc, str)  # a name only: never the GC's personality
        assert not keys & (gc_traits - {"name"})


def _keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {k for v in value.values() for k in _keys(v)}
    if isinstance(value, list):
        return {k for v in value for k in _keys(v)}
    return set()


def test_person_context_uses_revealed_words_only(planted: GameState, data: GameData) -> None:
    fid = planted.player.id
    for pid in planted.staff_ids(fid):
        out = person_context(planted, fid, pid, data)
        assert set(out) <= {
            "name",
            "practice",
            "level",
            "real",
            "tenure_months",
            "morale",
            "strain",
            "strong_at",
            "weak_at",
            "noticed",
            "interests",
        }
        reveal = planted.reveal(fid, pid)
        noticed = {t for t, _ in reveal.revealed_tags} if reveal else set()
        labels = {t.key: t.label for t in data.tags}
        assert set(out.get("noticed", [])) == {labels[t] for t in noticed}


def test_real_people_bring_the_business_only_rule(
    planted: GameState, data: GameData, balance: Balance
) -> None:
    pid = next(p for p in planted.staff_ids(planted.player.id))
    state = with_people(planted, [replace(planted.person(pid), real=True)])
    event = replace(_events_for_every_template(state, data)[0], person_ids=(pid,))
    template = data.event_template(event.template_id)
    system, user = build_prompt(
        state,
        event,
        template,
        eligible_targets(state, event),
        kpis_of(state, 0, data),
        balance,
        data,
    )
    assert "business and procedural matters only" in system
    assert json.loads(user)["people"][0]["real"] is True
