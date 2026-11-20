"""PT-M6 template data: at least 40 templates; every category has every severity (the brief);
every drawn trigger a minor template and every critical trigger a critical one; bad templates
fail at load."""

from __future__ import annotations

from collections import Counter

import pytest
from pydantic import ValidationError

from ptk.sim.data_models import GameData
from ptk.sim.events.data import (
    CATEGORIES,
    CRISIS_TRIGGERS,
    ENGINE_QUEUED,
    MATTER_DRAWS,
    SEVERITIES,
    TRIGGERS,
    EventTemplate,
    template_problems,
)


def test_at_least_forty_templates(data: GameData) -> None:
    assert len(data.event_templates) >= 40  # tunable-exempt: the brief
    assert template_problems(data.event_templates) == []


@pytest.mark.parametrize("category", CATEGORIES)
@pytest.mark.parametrize("severity", SEVERITIES)
def test_every_category_has_every_severity(data: GameData, category: str, severity: str) -> None:
    assert any(t.category == category and severity in t.severities for t in data.event_templates), (
        f"no {severity} {category} template"
    )


def test_triggers_are_covered(data: GameData) -> None:
    for trigger in (*TRIGGERS, *MATTER_DRAWS):
        assert any(
            t.trigger == trigger and "minor" in t.severities for t in data.event_templates
        ), trigger
    for trigger in (*CRISIS_TRIGGERS, *ENGINE_QUEUED):
        assert any(t.trigger == trigger and t.is_critical for t in data.event_templates), trigger


def test_spec_critical_set_present(data: GameData) -> None:
    """Spec 15's critical events each have a template (a trial verdict on a key matter, a
    partner group's letter, a covenant breach, a trust-account shortfall, a malpractice claim
    above the limit, an MP no-confidence petition, a merger vote)."""
    critical = {t.trigger for t in data.event_templates if t.is_critical}
    assert {
        "verdict_due",
        "partner_group_exit",
        "covenant_breach",
        "trust_shortfall",
        "malpractice_claim",
        "no_confidence",
        "merger_vote",
    } <= critical


def test_restricted_templates_are_the_misconduct_and_health_ones(data: GameData) -> None:
    restricted = {t.trigger for t in data.event_templates if t.restricted}
    assert {"burnout", "associate_error", "bar_complaint"} <= restricted


def test_categories_are_balanced(data: GameData) -> None:
    counts = Counter(t.category for t in data.event_templates)
    assert set(counts) == set(CATEGORIES)


BASE = {
    "id": "x",
    "category": "people",
    "trigger": "low_morale",
    "severities": ["minor"],
    "weight": 1.0,
    "title": "{person}",
    "body": "b",
    "choices": [
        {
            "key": "A",
            "label": "a",
            "effects": [{"type": "morale_delta", "target": "person", "share": 0.5}],
        },
        {"key": "B", "label": "b", "do_nothing": True},
    ],
}


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"category": "space"}, "unknown category"),
        ({"trigger": "rocket"}, "unknown trigger"),
        ({"title": "{rocket}"}, "unknown placeholders"),
        (
            {
                "choices": [{"key": "A", "label": "a", "effects": [{"type": "warp", "share": 1}]}]
                * 2
            },
            "unknown effect",
        ),
        (
            {
                "choices": [
                    {"key": "A", "label": "a", "effects": [{"type": "resign", "target": "person"}]},
                    {"key": "B", "label": "b", "do_nothing": True},
                ]
            },
            "resign is for major",
        ),
        (
            {
                "choices": [
                    {
                        "key": "A",
                        "label": "a",
                        "effects": [{"type": "salary_change", "target": "person", "share": -0.5}],
                    },
                    {"key": "B", "label": "b", "do_nothing": True},
                ]
            },
            "cannot be negative",
        ),
    ],
)
def test_bad_templates_fail(change: dict[str, object], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        EventTemplate.model_validate(BASE | change)


def test_critical_only_for_critical_triggers() -> None:
    template = EventTemplate.model_validate(BASE | {"severities": ["critical"]})
    assert any("may be critical" in p for p in template_problems((template,)))
