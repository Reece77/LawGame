"""PT-M6 validator and service: untrusted drafts are clamped and filtered; a draft that fails
validation is retried once, then the template is used (the brief's criterion); the budget and
offline mode fall back to templates; drafts may not resign a real person (ADR PT-0013). Every
test uses MockLLMAdapter (CLAUDE.md section 10)."""

from __future__ import annotations

import copy
from dataclasses import replace
from typing import Any

import pytest

from ptk.events.drafts import template_draft
from ptk.events.service import Writer, kpis_of, write_event, write_text
from ptk.events.validator import Rejection, ValidatedEvent, validate_event
from ptk.llm.offline import MockLLMAdapter, TemplateAdapter
from ptk.llm.settings import LLMSettings
from ptk.sim.data_models import Balance, GameData
from ptk.sim.events.director import eligible_targets
from ptk.sim.events.models import GameEvent, with_event
from ptk.sim.state import GameState, with_people
from tests.events_support import played

BAD = {"title": "x", "body": "y", "choices": [{"label": "only one", "effects": []}]}


@pytest.fixture(scope="module")
def base(data: GameData, balance: Balance) -> GameState:
    return played(data, balance, seed=3, turns=8)


def _pending(
    state: GameState, data: GameData, template_id: str = "gc_demand_ask"
) -> tuple[GameState, GameEvent]:
    """A pending event of `template_id` about the firm's first client, partner and matter."""
    rel = state.market.relationships[0]
    matter = state.market.open_matters(state.player.id)[0]
    if matter.court is None:  # templates that name {court} need a case before a court
        from ptk.sim.matters.intake import with_matter

        matter = replace(matter, court=data.courts.courts[0].key)
        state = replace(state, market=with_matter(state.market, matter))
    staff = [e.person_id for e in state.staff(state.player.id)]
    pid = next(p for p in staff if not state.person(p).is_founder)
    other = next(p for p in staff if p != pid)
    template = data.event_template(template_id)
    event = GameEvent(
        id=state.events.next_event_id,
        firm_id=state.player.id,
        turn=state.turn,
        template_id=template_id,
        category=template.category,
        severity="major" if "major" in template.severities else template.severities[0],
        trigger=template.trigger,
        strength=0.6,
        person_ids=(pid, other) if "other" in template.needs() else (pid,),
        client_id=rel.client_id,
        matter_id=matter.id,
        practice=matter.practice,
        months=24,
        amount_cents=16_000_000,
        cash_base_cents=50_000_000,
    )
    return replace(state, events=with_event(state.events, event)), event


def _writer(adapter: Any, budget: float = 1_000_000.0) -> Writer:
    return Writer(adapter, LLMSettings(), lambda: budget)


def _kpis(state: GameState, data: GameData) -> Any:
    return kpis_of(state, 0, data)


def test_mock_draft_is_used(base: GameState, data: GameData, balance: Balance) -> None:
    state, event = _pending(base, data)
    writer = _writer(MockLLMAdapter())
    new = write_event(state, event, _kpis(state, data), writer, balance, data)
    written = new.events.event(event.id)
    assert written is not None and written.status == "open" and written.source == "mock"
    assert written.title.startswith("[mock] ") and len(writer.records) == 1


def test_rejected_twice_falls_back_to_template(
    base: GameState, data: GameData, balance: Balance
) -> None:
    """The brief: LLM drafts that fail validation fall back after one retry."""
    state, event = _pending(base, data)
    adapter = MockLLMAdapter(script=[BAD, BAD, BAD])
    writer = _writer(adapter)
    new = write_event(state, event, _kpis(state, data), writer, balance, data)
    written = new.events.event(event.id)
    assert written is not None and written.source == "template"
    assert len(adapter.calls) == 2  # the draft and one retry, no third
    assert adapter.calls[1].retry_note is not None  # type: ignore[union-attr]
    assert writer.rejected == 1 and [r.outcome for r in writer.records] == ["rejected"] * 2
    template = template_draft(state, event, data.event_template(event.template_id), balance, data)
    assert written.title == template["title"]


def test_retry_that_validates_is_kept(base: GameState, data: GameData, balance: Balance) -> None:
    state, event = _pending(base, data)
    good = template_draft(state, event, data.event_template(event.template_id), balance, data)
    good = copy.deepcopy(good) | {"title": "Written on the second try"}
    adapter = MockLLMAdapter(script=[BAD, good])
    new = write_event(state, event, _kpis(state, data), _writer(adapter), balance, data)
    written = new.events.event(event.id)
    assert written is not None and written.source == "mock" and written.title == good["title"]


def test_budget_spent_and_offline_use_templates(
    base: GameState, data: GameData, balance: Balance
) -> None:
    state, event = _pending(base, data)
    adapter = MockLLMAdapter()
    writer = _writer(adapter, budget=0.0)
    new = write_event(state, event, _kpis(state, data), writer, balance, data)
    assert new.events.event(event.id).source == "template" and not adapter.calls  # type: ignore[union-attr]
    assert [r.outcome for r in writer.records] == ["budget"]
    offline = _writer(TemplateAdapter())
    new = write_event(state, event, _kpis(state, data), offline, balance, data)
    assert new.events.event(event.id).source == "template" and not offline.records  # type: ignore[union-attr]


def _check(
    state: GameState, event: GameEvent, data: GameData, balance: Balance, draft: Any
) -> ValidatedEvent | Rejection:
    from ptk.events.drafts import real_targets

    return validate_event(
        draft,
        template=data.event_template(event.template_id),
        severity=event.severity,
        targets=eligible_targets(state, event),
        cash_base_cents=event.cash_base_cents,
        events=balance.events,
        real_targets=real_targets(state, event),
    )


def test_validator_filters_and_clamps(base: GameState, data: GameData, balance: Balance) -> None:
    state, event = _pending(base, data)
    client = f"client:{event.client_id}"
    draft = {
        "title": "t" * 500,
        "body": " ".join(["word"] * 1000),
        "choices": [
            {
                "label": "A",
                "effects": [
                    {"type": "relationship_delta", "target": client, "value": 999},
                    {"type": "warp_drive", "target": client, "value": 1},
                    {"type": "morale_delta", "target": "person:424242", "value": 1},
                    {"type": "cash_delta", "target": f"firm:{event.firm_id}", "value": -(10**9)},
                ],
            },
            {"label": "B", "effects": [], "do_nothing": True},
            {
                "label": "C",
                "effects": [{"type": "resign", "target": f"person:{event.person_ids[0]}"}],
            },
            {"label": "D", "effects": []},
        ],
    }
    result = _check(state, event, data, balance, draft)
    assert isinstance(result, ValidatedEvent)
    assert len(result.title) <= 120 and len(result.body.split()) <= balance.events.body_words + 1
    assert [c.key for c in result.choices] == ["A", "B", "C"]
    a = result.choices[0]
    assert [e.type for e in a.effects] == ["relationship_delta", "cash_delta"]
    assert a.effects[0].value == balance.events.cap("relationship_delta", event.severity)
    cap = 50_000_000 * balance.events.cap("cash_delta", event.severity) / 10_000
    assert a.effects[1].value == -cap
    assert result.choices[1].do_nothing
    assert result.choices[2].effects == ()  # resign is not this template's effect: dropped
    assert result.dropped >= 4


@pytest.mark.parametrize(
    "draft", [None, "text", [], {"title": "t"}, {"title": "t", "body": "b"}, BAD]
)
def test_validator_rejects_broken_drafts(
    base: GameState, data: GameData, balance: Balance, draft: Any
) -> None:
    state, event = _pending(base, data)
    assert isinstance(_check(state, event, data, balance, draft), Rejection)


def test_draft_resigning_a_real_person_is_rejected(
    base: GameState, data: GameData, balance: Balance
) -> None:
    """ADR PT-0013: the validator rejects drafts whose effects target a real person outside
    the allowed effect types; the template's own draft leaves such effects out."""
    state, event = _pending(base, data, "star_decision")
    pid = event.person_ids[0]
    state = with_people(state, [replace(state.person(pid), real=True)])
    draft = template_draft(state, event, data.event_template("star_decision"), balance, data)
    assert all(e["type"] != "resign" for c in draft["choices"] for e in c["effects"])
    assert isinstance(_check(state, event, data, balance, draft), ValidatedEvent)
    bad = copy.deepcopy(draft)
    bad["choices"][1]["effects"] = [{"type": "resign", "target": f"person:{pid}", "value": 0}]
    assert isinstance(_check(state, event, data, balance, bad), Rejection)
    adapter = MockLLMAdapter(script=[bad, bad])
    new = write_event(state, event, _kpis(state, data), _writer(adapter), balance, data)
    written = new.events.event(event.id)
    assert written is not None and written.source == "template"
    assert all(e.type != "resign" for c in written.choices for e in c.effects)


def test_every_template_validates_for_its_own_draft(
    base: GameState, data: GameData, balance: Balance
) -> None:
    for template in data.event_templates:
        state, event = _pending(base, data, template.id)
        for severity in template.severities:
            ev = replace(event, severity=severity)
            draft = template_draft(state, ev, template, balance, data)
            assert isinstance(_check(state, ev, data, balance, draft), ValidatedEvent), template.id
            assert "{" not in draft["title"] + draft["body"], (template.id, draft["title"])


@pytest.mark.parametrize(
    "kind", ["headlines", "matter_brief", "pitch_letter", "partner_memo", "year_end_letter"]
)
def test_text_kinds(base: GameState, data: GameData, kind: str) -> None:
    ref = None
    if kind == "matter_brief":
        ref = base.market.open_matters(base.player.id)[0].id
    if kind == "pitch_letter":
        ref = base.market.relationships[0].client_id
    adapter = MockLLMAdapter()
    text, source = write_text(
        base, kind, base.turn - 1, ref, _writer(adapter), _kpis(base, data), data
    )
    assert text and source == "mock" and len(adapter.calls) == 1
    text, source = write_text(
        base, kind, base.turn - 1, ref, _writer(TemplateAdapter()), _kpis(base, data), data
    )
    assert text and source == "template"
