"""A template's own draft for one event (TST formulas.md 16.4), in the JSON shape the LLM
returns (spec 12): the offline mode, the fallback, and what MockLLMAdapter starts from. Effect
values are in the effect's units, cash in dollars, as the LLM is asked to write them.

Ported from backend/tst/events/drafts.py @ 02fba2aa (Tech Startup Tycoon); changed: Partner
Track's target words; no press, public, loan or industry names; an effect the real-person rule
forbids (ADR PT-0013) is left out of the draft, and a choice left without effects says so.
"""

from __future__ import annotations

from typing import Any

from ptk.sim.data_models import Balance, GameData
from ptk.sim.events.data import REAL_RESTRICTED_EFFECTS, EventTemplate
from ptk.sim.events.formulas import share_value
from ptk.sim.events.models import GameEvent
from ptk.sim.events.render import placeholder_names, render
from ptk.sim.state import GameState

CENTS_PER_DOLLAR = 100  # tunable-exempt: unit conversion
PAIR = 2  # tunable-exempt: two people


def target_string(state: GameState, event: GameEvent, word: str) -> str | None:
    """A template target word as an eligible-list entry for this event; None if it cannot be
    named (the effect is then left out)."""
    fid = event.firm_id
    founder = state.founder_of(fid)
    people = event.person_ids
    if word == "person":
        return f"person:{people[0]}" if people else None
    if word == "other":
        return f"person:{people[1]}" if len(people) > 1 else None
    if word == "pair":
        if len(people) >= PAIR:
            a, b = sorted(people[:PAIR])
        elif people and founder is not None and people[0] != founder:
            a, b = sorted((founder, people[0]))
        else:
            return None
        return f"pair:{a}-{b}"
    if word == "unit":
        return f"unit:{event.unit_id}" if event.unit_id is not None else f"firm:{fid}"
    if word == "firm":
        return f"firm:{fid}"
    if word == "client":
        return f"client:{event.client_id}" if event.client_id is not None else None
    if word == "matter":
        return f"matter:{event.matter_id}" if event.matter_id is not None else None
    if word == "partnership":
        return "partnership"
    return ""  # follow_up


def real_targets(state: GameState, event: GameEvent) -> frozenset[str]:
    """The event's people flagged real, as "person:<id>" targets (ADR PT-0013)."""
    real = {p.id for p in state.people if p.real}
    return frozenset(f"person:{p}" for p in event.person_ids if p in real)


def event_names(state: GameState, event: GameEvent, data: GameData) -> dict[str, str]:
    return placeholder_names(
        state,
        data,
        event.firm_id,
        person_ids=event.person_ids,
        unit_id=event.unit_id,
        client_id=event.client_id,
        matter_id=event.matter_id,
        practice=event.practice,
        months=event.months,
        amount_cents=event.amount_cents,
    )


def template_draft(
    state: GameState, event: GameEvent, template: EventTemplate, balance: Balance, data: GameData
) -> dict[str, Any]:
    names = event_names(state, event, data)
    first_cost = next(
        (
            share_value(
                "cash_delta", e.share, event.severity, balance.events, event.cash_base_cents
            )
            for c in template.choices
            for e in c.effects
            if e.type == "cash_delta"
        ),
        None,
    )
    if first_cost is not None and "amount" not in names:
        names["amount"] = f"${abs(first_cost) / CENTS_PER_DOLLAR:,.0f}"
    real = real_targets(state, event)
    choices = []
    for choice in template.choices:
        effects = []
        for spec in choice.effects:
            target = target_string(state, event, spec.target)
            if target is None:
                continue
            if spec.type in REAL_RESTRICTED_EFFECTS and target in real:
                continue  # ADR PT-0013
            value = share_value(
                spec.type, spec.share, event.severity, balance.events, event.cash_base_cents
            )
            if spec.type == "cash_delta":
                value = value / CENTS_PER_DOLLAR
            effect: dict[str, Any] = {"type": spec.type, "target": target, "value": value}
            if spec.type == "modifier":
                effect |= {"stat": spec.stat, "months": spec.months}
            effects.append(effect)
        choices.append(
            {
                "key": choice.key,
                "label": render(choice.label, names),
                "effects": effects,
                **({"do_nothing": True} if choice.do_nothing or not effects else {}),
            }
        )
    summary = render(template.storyline.summary, names) if template.storyline else ""
    return {
        "title": render(template.title, names),
        "body": render(template.body, names),
        "choices": choices,
        "storyline_summary": summary,
    }
