"""PT-M6 invariants under random drafts and random choices:

- whatever the LLM returns, a validated effect is within its severity's cap, aimed only at an
  eligible target, and never resigns a real person (ADR-0005, ADR PT-0013);
- applying any validated choice posts balanced ledger entries of whole cents and keeps morale,
  strain and client relationships in 0-100, skills in 1-20 and colleague relationships in
  -100..100 (CLAUDE.md invariants).
"""

from __future__ import annotations

from dataclasses import replace
from functools import cache
from typing import Any

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from ptk.events.validator import ValidatedEvent, validate_event
from ptk.loader import load_balance, load_game_data
from ptk.sim.events.data import EFFECT_TYPES, VALUELESS
from ptk.sim.events.director import eligible_targets
from ptk.sim.events.effects import apply_choice
from ptk.sim.events.formulas import effect_cap
from ptk.sim.events.models import GameEvent, with_event
from ptk.sim.state import GameState
from tests.conftest import DATA_DIR
from tests.events_support import played

DATA = load_game_data(DATA_DIR)
BALANCE = load_balance(DATA_DIR)
SEVERITIES = ("minor", "major", "critical")


@cache
def _base() -> GameState:
    return played(DATA, BALANCE, seed=7, turns=8)


def _event(state: GameState, template_id: str, severity: str, base: int) -> GameEvent:
    staff = [e.person_id for e in state.staff(state.player.id)]
    matter = state.market.open_matters(state.player.id)[0]
    return GameEvent(
        id=state.events.next_event_id,
        firm_id=state.player.id,
        turn=state.turn,
        template_id=template_id,
        category="client",
        severity=severity,  # type: ignore[arg-type]
        trigger="gc_demand",
        strength=0.5,
        person_ids=tuple(staff[:2]),
        client_id=matter.client_id,
        matter_id=matter.id,
        cash_base_cents=base,
        status="open",
    )


def _effect(targets: list[str]) -> st.SearchStrategy[dict[str, Any]]:
    return st.fixed_dictionaries(
        {
            "type": st.sampled_from([*EFFECT_TYPES, "teleport"]),
            "target": st.sampled_from([*targets, "person:999999", "", "board"]),
            "value": st.one_of(
                st.floats(-1e9, 1e9, allow_nan=False), st.integers(-(10**9), 10**9), st.just("x")
            ),
        },
        optional={
            "stat": st.sampled_from(["morale_target", "strain_gain", "brand"]),
            "months": st.integers(-5, 50),
        },
    )


@settings(max_examples=60, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    data=st.data(),
    template_index=st.integers(0, len(DATA.event_templates) - 1),
    severity=st.sampled_from(SEVERITIES),
    base=st.integers(0, 10**10),
)
def test_validated_drafts_stay_in_bounds(
    data: st.DataObject, template_index: int, severity: str, base: int
) -> None:
    state = _base()
    template = DATA.event_templates[template_index]
    event = _event(state, template.id, severity, base)
    targets = list(eligible_targets(state, event))
    choices = data.draw(
        st.lists(
            st.fixed_dictionaries(
                {
                    "label": st.text(min_size=0, max_size=20),
                    "effects": st.lists(_effect(targets), max_size=5),
                }
            ),
            max_size=4,
        )
    )
    draft = {"title": "T", "body": "B", "choices": choices}
    result = validate_event(
        draft,
        template=template,
        severity=severity,  # type: ignore[arg-type]
        targets=tuple(targets),
        cash_base_cents=base,
        events=BALANCE.events,
    )
    if not isinstance(result, ValidatedEvent):
        return
    for choice in result.choices:
        assert len(choice.effects) <= 3  # tunable-exempt: TST 16.3
        for effect in choice.effects:
            assert effect.target in targets or effect.target == ""
            if effect.type in VALUELESS:
                continue
            cap = effect_cap(effect.type, severity, BALANCE.events, base, gain=effect.value > 0)  # type: ignore[arg-type]
            assert abs(effect.value) <= cap + 1e-6
            if effect.type == "cash_delta":
                assert effect.value == round(effect.value)

    # Applying the first choice keeps every invariant.
    written = replace(event, choices=result.choices, title="T")
    applied = replace(state, events=with_event(state.events, written))
    new, entries, _ = apply_choice(
        applied, written, result.choices[0].key, BALANCE, DATA, auto=False
    )
    for entry in entries:
        assert sum(line.amount for line in entry.lines) == 0
        assert all(isinstance(line.amount, int) for line in entry.lines)
    for ps in new.person_states:
        assert ps.morale is None or 0.0 <= ps.morale <= 100.0
    for p in new.people:
        assert 0.0 <= p.strain <= 100.0
        assert all(1.0 <= v <= 20.0 for _, v in p.skills.items)
    for r in new.market.relationships:
        assert 0.0 <= r.score <= 100.0
    for pair in new.events.colleagues:
        assert -100.0 <= pair.value <= 100.0
