"""Event template data (`data/events/*.yaml`) and the events balance, validated at load.

Ported from backend/tst/sim/events/data.py @ 02fba2aa (Tech Startup Tycoon); changed: Partner
Track's categories (spec 15), triggers, effect types and placeholders replace TST's tech and
industry ones; templates carry a `restricted` flag (ADR PT-0013: never about a real person);
the events balance lives here (TST keeps it in data_models) so the catalog and its caps are
checked together.

Templates are the offline mode and the LLM fallback, so the checks here make sure every drawn
trigger has a minor template, every critical trigger a critical one, every placeholder can be
filled from the trigger's targets, and every effect is in the catalog within its caps.
"""

from __future__ import annotations

import re
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

type Severity = Literal["minor", "major", "critical"]
SEVERITIES: Final = ("minor", "major", "critical")

# Spec 15's categories. Each has at least one template of every severity (the brief).
CATEGORIES: Final = (
    "client",
    "matter",
    "people",
    "partnership",
    "market",
    "regulatory",
    "press",
    "technology",
)

# Triggers the director computes from state each month, in table order (formulas: triggers.py).
TRIGGERS: Final = (
    # people
    "low_morale",
    "high_strain",
    "burnout",
    "star_associate",
    "tag_noticed",
    "anniversary",
    "team_clash",
    "team_bond",
    "associate_error",
    # clients
    "client_cooling",
    "big_instruction",
    "gc_demand",
    "panel_review",
    "fee_dispute",
    # matters
    "deadline_slip",
    "deal_on_brink",
    "settlement_offer",
    "matter_won",
    "matter_lost",
    # partnership
    "credit_dispute",
    "partner_retiring",
    # market
    "scale_move",
    "demand_shift",
    # regulatory
    "conflict_surfaced",
    "annual_audit",
    "bar_complaint",
    # technology
    "tech_pitch",
    "quiet_month",
)
# Drawn per open case matter on the events stream after the crises (matter_draws in
# triggers.py): a document turns up, a judge rules on a motion.
MATTER_DRAWS: Final = ("smoking_gun", "judge_ruling")
# Crises (TST 23.3): checked in phase 12 apart from the drawn triggers; each brings its
# critical template whenever it holds and no critical event came in the critical gap.
CRISIS_TRIGGERS: Final = ("key_exit", "client_walkout", "verdict_due")
# Queued by the engine (a later milestone's system) by template id, never drawn: spec 15's
# critical set whose systems arrive later (partnership votes and covenants PT-M4; trust
# accounts, malpractice, AI eras and the press in v2). `queue_engine_event` queues them.
ENGINE_QUEUED: Final = (
    "partner_group_exit",
    "no_confidence",
    "merger_vote",
    "covenant_breach",
    "trust_shortfall",
    "malpractice_claim",
    "ai_sanction",
    "press_storm",
)
SCHEDULED: Final = ("storyline", "follow_up", *ENGINE_QUEUED)
CRITICAL_TRIGGERS: Final = (*CRISIS_TRIGGERS, *ENGINE_QUEUED, "storyline")
ALL_TRIGGERS: Final = (*TRIGGERS, *MATTER_DRAWS, *CRISIS_TRIGGERS, *SCHEDULED)

EFFECT_TYPES: Final = (
    "morale_delta",  # morale points
    "relationship_delta",  # client relationship score points (0-100, spec 7.2)
    "pair_delta",  # colleague relationship points (TST 16.7)
    "cash_delta",  # cents; capped in bp of the cash base
    "reputation_delta",  # reputation points: a placeholder until PT-M5's rankings (no-op hook)
    "hours_pct",  # percent change to the hours a matter still needs
    "strain_delta",  # strain points (spec 5.6)
    "wip_writedown",  # percent of a matter's WIP written down (PT-M3b's billing interface)
    "merits_shift",  # logit points on a case's hidden merits (never shown as a number)
    "confidence_delta",  # partners' confidence in the MP: a placeholder until PT-M4 (no-op hook)
    "growth_boost",  # skill points, once
    "reveal_tag",  # a hidden tag is revealed to the firm
    "salary_change",  # percent raise, never a cut
    "resign",  # the person gives notice
    "retain",  # a counter-offer withdraws someone's notice (TST 23.3)
    "follow_up",  # a critical event's follow-up next month (TST 16.3)
    "modifier",  # a lasting percent change to one stat for some months (TST 23.2)
)
VALUELESS: Final = ("reveal_tag", "resign", "retain", "follow_up")  # no size: happen or not
NON_NEGATIVE: Final = ("growth_boost", "salary_change", "wip_writedown")  # never negative
# ADR PT-0013: effects never applied to a person flagged real (a real career ends by retirement;
# no tags are revealed about a real person). The validator rejects drafts that try.
REAL_RESTRICTED_EFFECTS: Final = ("resign", "reveal_tag")

# Template target words and the effects that may use each.
EFFECT_TARGETS: Final[dict[str, tuple[str, ...]]] = {
    "morale_delta": ("person", "other", "unit", "firm"),
    "relationship_delta": ("client",),
    "pair_delta": ("pair",),
    "cash_delta": ("firm",),
    "reputation_delta": ("firm",),
    "hours_pct": ("matter",),
    "strain_delta": ("person", "other", "unit", "firm"),
    "wip_writedown": ("matter",),
    "merits_shift": ("matter",),
    "confidence_delta": ("partnership",),
    "growth_boost": ("person", "other"),
    "reveal_tag": ("person", "other"),
    "salary_change": ("person", "other"),
    "resign": ("person", "other"),
    "retain": ("person",),
    "follow_up": ("",),
    "modifier": ("person", "other", "unit", "firm"),
}

# What a modifier can change (TST 23.2), and the target words each stat accepts. A firm
# target reaches everyone on the firm's books.
MODIFIER_STATS: Final[dict[str, tuple[str, ...]]] = {
    "morale_target": ("person", "other", "unit", "firm"),
    "strain_gain": ("person", "other", "unit", "firm"),
}
STAT_LABELS: Final[dict[str, str]] = {
    "morale_target": "morale target",
    "strain_gain": "strain build-up",
}

# What each trigger can name. Firm, founder, partnership and amount can always be asked for.
ALWAYS: Final = frozenset({"firm", "founder", "partnership", "amount"})
_PERSON = frozenset({"person", "pair", "unit"})
_MATTER = frozenset({"matter", "client", "gc", "practice"})
TRIGGER_SUPPLIES: Final[dict[str, frozenset[str]]] = {
    "low_morale": _PERSON,
    "high_strain": _PERSON,
    "burnout": _PERSON,
    "star_associate": _PERSON,
    "tag_noticed": _PERSON,
    "anniversary": _PERSON,
    "team_clash": _PERSON | {"other"} | _MATTER,
    "team_bond": _PERSON | {"other"} | _MATTER,
    "associate_error": _PERSON | _MATTER,
    "client_cooling": _PERSON | frozenset({"client", "gc"}),
    "big_instruction": _PERSON | _MATTER,
    "gc_demand": _PERSON | frozenset({"client", "gc"}),
    "panel_review": _PERSON | frozenset({"client", "gc", "months"}),
    "fee_dispute": _PERSON | _MATTER,
    "deadline_slip": _PERSON | _MATTER,
    "deal_on_brink": _PERSON | _MATTER,
    "settlement_offer": _PERSON | _MATTER,
    "matter_won": _PERSON | _MATTER,
    "matter_lost": _PERSON | _MATTER,
    "credit_dispute": _PERSON | {"other"} | _MATTER,
    "partner_retiring": _PERSON,
    "scale_move": frozenset(),
    "demand_shift": frozenset({"practice"}),
    "conflict_surfaced": _PERSON | _MATTER,
    "annual_audit": frozenset(),
    "bar_complaint": _PERSON | _MATTER,
    "tech_pitch": frozenset(),
    "quiet_month": frozenset(),
    "smoking_gun": _PERSON | _MATTER,
    "judge_ruling": _PERSON | _MATTER | {"court"},
    "key_exit": _PERSON,
    "client_walkout": _PERSON | frozenset({"client", "gc"}),
    "verdict_due": _PERSON | _MATTER | {"court"},
    # Engine-queued (later milestones say what they supply; the firm and founder until then).
    **{trigger: frozenset() for trigger in ENGINE_QUEUED},
}
PLACEHOLDER_RE: Final = re.compile(r"\{([a-z_]+)\}")
PLACEHOLDERS: Final = (
    "person",
    "other",
    "unit",
    "firm",
    "founder",
    "client",
    "gc",  # the client's general counsel (generated, spec 7.3)
    "matter",
    "practice",
    "court",
    "amount",
    "months",
    "partnership",
)


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class EffectSpec(_Frozen):
    """One effect of a template choice. `share` is the fraction of the severity's cap
    (negative: a loss or a cost; a cash gain is a share of the smaller gain cap)."""

    type: str
    target: str = ""
    share: float = Field(default=0.0, ge=-1.0, le=1.0)
    stat: str | None = None  # modifier only
    months: int | None = Field(default=None, ge=1)  # modifier only, held to the severity's

    @model_validator(mode="after")
    def _check(self) -> EffectSpec:
        if self.type not in EFFECT_TYPES:
            raise ValueError(f"unknown effect {self.type!r}")
        if self.type == "modifier":
            if self.stat not in MODIFIER_STATS or self.months is None:
                raise ValueError(f"a modifier needs a stat in {list(MODIFIER_STATS)} and months")
            if self.target not in MODIFIER_STATS[self.stat]:
                raise ValueError(
                    f"a {self.stat} modifier may target {list(MODIFIER_STATS[self.stat])}"
                )
        elif self.stat is not None or self.months is not None:
            raise ValueError("only a modifier has a stat and months")
        if self.target not in EFFECT_TARGETS[self.type]:
            raise ValueError(
                f"{self.type} may target {list(EFFECT_TARGETS[self.type])}, not {self.target!r}"
            )
        if self.type in VALUELESS and self.share:
            raise ValueError(f"{self.type} takes no share")
        if self.type not in VALUELESS and not self.share:
            raise ValueError(f"{self.type} needs a non-zero share")
        if self.type in NON_NEGATIVE and self.share < 0:
            raise ValueError(f"{self.type} cannot be negative")
        return self


class ChoiceSpec(_Frozen):
    key: str = Field(pattern=r"^[ABC]$")
    label: str = Field(min_length=1, max_length=80)  # tunable-exempt: button text length
    effects: tuple[EffectSpec, ...] = Field(default=(), max_length=3)  # tunable-exempt: TST 16.3
    do_nothing: bool = False  # TST 23.2: the one kind of choice allowed no effect

    @model_validator(mode="after")
    def _check(self) -> ChoiceSpec:
        if not self.effects and not self.do_nothing:
            raise ValueError(f"choice {self.key}: give it an effect or mark it do_nothing")
        if self.effects and self.do_nothing:
            raise ValueError(f"choice {self.key}: a do_nothing choice has no effects")
        return self


class StorylineSpec(_Frozen):
    """A storyline step (TST 16.6). Step 1 opens it (and names it); later steps are scheduled."""

    key: str = Field(min_length=1)
    step: int = Field(ge=1)
    title: str | None = None  # step 1 only
    next_after_turns: int | None = Field(default=None, ge=1)
    next_template: str | None = None
    summary: str = Field(min_length=1)


class EventTemplate(_Frozen):
    id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    category: str
    trigger: str
    severities: tuple[Severity, ...] = Field(min_length=1)
    weight: float = Field(gt=0)
    title: str = Field(min_length=1)
    body: str = Field(min_length=1)
    choices: tuple[ChoiceSpec, ...] = Field(min_length=2, max_length=3)  # tunable-exempt: 16.3
    storyline: StorylineSpec | None = None
    follow_up: str | None = None
    # ADR PT-0013: misconduct, blame, health and burnout events; never about a real person.
    restricted: bool = False

    @property
    def is_critical(self) -> bool:
        return "critical" in self.severities

    def texts(self) -> tuple[str, ...]:
        story = (self.storyline.summary, self.storyline.title or "") if self.storyline else ()
        return (self.title, self.body, *(c.label for c in self.choices), *story)

    def modifier_stats(self) -> frozenset[str]:
        """The stats the LLM may attach modifiers for: those the template's own use."""
        return frozenset(
            e.stat for c in self.choices for e in c.effects if e.type == "modifier" and e.stat
        )

    def needs(self) -> frozenset[str]:
        """Everything the template names: placeholders and effect targets."""
        names = {m for t in self.texts() for m in PLACEHOLDER_RE.findall(t)}
        for choice in self.choices:
            for effect in choice.effects:
                if effect.target == "pair":
                    names |= {"pair", "person"}
                elif effect.target:
                    names.add(effect.target)
        return frozenset(names)

    @model_validator(mode="after")
    def _check(self) -> EventTemplate:
        if self.category not in CATEGORIES:
            raise ValueError(f"unknown category {self.category!r}")
        if self.trigger not in ALL_TRIGGERS:
            raise ValueError(f"unknown trigger {self.trigger!r}")
        keys = [c.key for c in self.choices]
        if keys != ["A", "B", "C"][: len(keys)]:
            raise ValueError(f"choices must be keyed A, B[, C] in order, got {keys}")
        unknown = sorted(
            {m for t in self.texts() for m in PLACEHOLDER_RE.findall(t)} - set(PLACEHOLDERS)
        )
        if unknown:
            raise ValueError(f"unknown placeholders {unknown}")
        types = {e.type for c in self.choices for e in c.effects}
        if "resign" in types and self.severities == ("minor",):
            raise ValueError("resign is for major and critical events only (TST 16.3)")
        if "retain" in types and not self.is_critical:
            raise ValueError("retain is for critical events only (TST 23.3)")
        if "follow_up" in types and (not self.is_critical or not self.follow_up):
            raise ValueError("follow_up needs a critical template that names its follow_up")
        if self.follow_up and not self.is_critical:
            raise ValueError("only a critical template names a follow_up")
        if self.trigger == "storyline" and self.storyline is None:
            raise ValueError("a storyline-triggered template needs a storyline step")
        return self


class EventTemplatesFile(_Frozen):
    templates: tuple[EventTemplate, ...]


def template_problems(templates: tuple[EventTemplate, ...]) -> list[str]:
    """Cross-template checks: ids unique; every drawn trigger has a minor template and every
    critical trigger a critical one; every category has every severity; placeholders and
    targets resolvable from the trigger; storyline steps and follow-ups point at scheduled
    templates."""
    problems: list[str] = []
    by_id: dict[str, EventTemplate] = {}
    for t in templates:
        if t.id in by_id:
            problems.append(f"duplicate event template id {t.id!r}")
        by_id[t.id] = t
    for trigger in (*TRIGGERS, *MATTER_DRAWS):
        drawn = [t for t in templates if t.trigger == trigger]
        if not any("minor" in t.severities for t in drawn):
            problems.append(f"trigger {trigger!r} has no minor template")
    for trigger in (*CRISIS_TRIGGERS, *ENGINE_QUEUED):
        if not any(t.trigger == trigger and t.is_critical for t in templates):
            problems.append(f"trigger {trigger!r} has no critical template")
    for t in templates:
        if t.is_critical and t.trigger not in CRITICAL_TRIGGERS:
            problems.append(f"{t.id}: only {list(CRITICAL_TRIGGERS)} may be critical")
    for category in CATEGORIES:
        for severity in SEVERITIES:
            if not any(t.category == category and severity in t.severities for t in templates):
                problems.append(f"category {category!r} has no {severity} template")
    # Scheduled templates inherit their origin's targets: walk each chain from its start.
    origin: dict[str, str] = {}
    for t in templates:
        if t.trigger in SCHEDULED:
            continue
        nxt = t.storyline.next_template if t.storyline else None
        chain = [nxt] if nxt else []
        if t.follow_up:
            chain.append(t.follow_up)
        for first in chain:
            seen: set[str] = set()
            current: str | None = first
            while current and current not in seen:
                seen.add(current)
                origin.setdefault(current, t.trigger)
                step = by_id.get(current)
                current = step.storyline.next_template if step and step.storyline else None
    for t in templates:
        if t.trigger in ENGINE_QUEUED or t.trigger in CRISIS_TRIGGERS:
            missing = sorted(t.needs() - ALWAYS - TRIGGER_SUPPLIES[t.trigger])
            if missing:
                problems.append(f"{t.id}: trigger {t.trigger!r} cannot supply {missing}")
            if t.trigger in ENGINE_QUEUED:
                continue
        if t.trigger in SCHEDULED and t.id not in origin:
            problems.append(f"{t.id}: scheduled template that nothing schedules")
            continue
        trigger = origin.get(t.id, t.trigger) if t.trigger in SCHEDULED else t.trigger
        missing = sorted(t.needs() - ALWAYS - TRIGGER_SUPPLIES.get(trigger, frozenset()))
        if missing:
            problems.append(f"{t.id}: trigger {trigger!r} cannot supply {missing}")
        if t.follow_up:
            follow = by_id.get(t.follow_up)
            if follow is None or follow.trigger != "follow_up":
                problems.append(f"{t.id}: follow_up {t.follow_up!r} is not a follow_up template")
        story = t.storyline
        if story is None:
            continue
        if (story.step == 1) != (t.trigger != "storyline"):
            problems.append(f"{t.id}: only step 1 of a storyline is drawn by a trigger")
        if story.step == 1 and not story.title:
            problems.append(f"{t.id}: step 1 of a storyline needs a title")
        if (story.next_template is None) != (story.next_after_turns is None):
            problems.append(f"{t.id}: next_template and next_after_turns go together")
        if story.next_template:
            following = by_id.get(story.next_template)
            if (
                following is None
                or following.storyline is None
                or following.storyline.key != story.key
                or following.storyline.step != story.step + 1
            ):
                problems.append(
                    f"{t.id}: next_template must be step {story.step + 1} of {story.key!r}"
                )
    return problems


# --- Balance (balance.yaml `events:` and `colleagues:`) ---------------------------------------


class _Span(_Frozen):
    lo: float
    hi: float

    @model_validator(mode="before")
    @classmethod
    def _from_list(cls, value: object) -> object:
        if isinstance(value, list | tuple):
            if len(value) != 2:  # tunable-exempt: a pair
                raise ValueError("expected [min, max]")
            return {"lo": value[0], "hi": value[-1]}
        return value


class TriggerBalance(_Frozen):
    """One trigger's thresholds; unused fields stay None."""

    below: float | None = None
    span: float | None = Field(default=None, gt=0)
    at_most: float | None = None
    at_least: float | None = None
    strength: float | None = None
    top_fraction: float | None = Field(default=None, gt=0, le=1)
    tenure_months: int | None = Field(default=None, ge=0)
    months: int | None = Field(default=None, ge=1)
    chance: float | None = Field(default=None, ge=0, le=1)
    ratio: float | None = Field(default=None, gt=0)
    age: int | None = Field(default=None, ge=0)
    min_cents: int | None = Field(default=None, ge=0)


class CrisisBalance(_Frozen):
    """Critical events from crises (TST 23.3, with Partner Track's crises)."""

    key_exit_top_fraction: float = Field(gt=0, le=1)  # staff by current ability whose exit counts
    walkout_share: float = Field(gt=0, le=1)  # a client this share of 12-month fees is key
    walkout_below: float = Field(ge=0, le=100)  # relationship score below which it walks
    verdict_months: int = Field(ge=1)  # months a key matter's verdict event is not repeated


class EventsBalance(_Frozen):
    """Event director, effect caps and storylines (TST formulas.md 16)."""

    count_weights: tuple[float, ...]
    category_repeat_factor: float = Field(ge=0)
    template_cooldown_turns: int = Field(ge=0)
    person_cooldown_turns: int = Field(ge=0)
    matter_cooldown_turns: int = Field(ge=0)
    client_cooldown_turns: int = Field(ge=0)
    critical_gap_turns: int = Field(ge=0)
    major_from: float = Field(ge=0, le=1)
    light_tone_chance_bp: int = Field(ge=0, le=10_000)  # tunable-exempt: basis-point scale
    max_storylines: int = Field(ge=0)
    summary_words: int = Field(gt=0)
    body_words: int = Field(gt=0)
    recent_summaries: int = Field(ge=0)
    trigger: dict[str, TriggerBalance]
    caps: dict[str, tuple[float, float, float]]
    modifier_months: tuple[int, int, int]
    cash_revenue_months: float = Field(ge=0)
    cash_gain_share: float = Field(ge=0, le=1)
    effect_size_bounds: _Span
    crisis: CrisisBalance
    texts: TextsBalance

    @model_validator(mode="after")
    def _check(self) -> EventsBalance:
        tolerance = 1e-9  # tunable-exempt: float tolerance
        if not self.count_weights or abs(sum(self.count_weights) - 1) > tolerance:
            raise ValueError("events.count_weights: probabilities of 0, 1, 2 ... events, sum 1")
        wanted = sorted((*TRIGGERS, *MATTER_DRAWS))
        if sorted(self.trigger) != wanted:
            raise ValueError(f"events.trigger must cover exactly {wanted}")
        sized = sorted(set(EFFECT_TYPES) - set(VALUELESS))
        if sorted(self.caps) != sized:
            raise ValueError(f"events.caps must cover exactly {sized}")
        for effect, caps in self.caps.items():
            if any(c <= 0 for c in caps) or list(caps) != sorted(caps):
                raise ValueError(f"events.caps.{effect}: three rising positive caps")
        months = self.modifier_months
        if any(m < 1 for m in months) or list(months) != sorted(months):
            raise ValueError("events.modifier_months: three rising positive month counts")
        return self

    def cap(self, effect: str, severity: str) -> float:
        return self.caps[effect][SEVERITIES.index(severity)]

    def max_months(self, severity: str) -> int:
        """The longest a modifier of this severity runs (TST 23.2)."""
        return self.modifier_months[SEVERITIES.index(severity)]

    def fixed(self, trigger: str) -> float:
        """A trigger's fixed strength (0 when it has none)."""
        return float(self.trigger[trigger].strength or 0.0)


class TextsBalance(_Frozen):
    """Read-only LLM texts (TST 16.8; spec 15's text kinds)."""

    brief_min_cents: int = Field(ge=0)  # expected fees from which a new matter gets a briefing
    briefs_per_month: int = Field(ge=0)
    pitch_letters_per_month: int = Field(ge=0)
    memo_months: tuple[int, ...]  # calendar months of the partners' memo (comp letters)
    year_end_month: int = Field(ge=1, le=12)  # tunable-exempt: calendar


class ColleaguesBalance(_Frozen):
    """Relationships between colleagues on the same matter team (TST 16.7)."""

    start_base: float
    start_per_temperament: float = Field(ge=0)
    start_clamp: _Span
    drift: float = Field(ge=0, le=1)
    tag_push: dict[str, float]
    label_bounds: tuple[float, float, float, float]
    range: _Span


EventsBalance.model_rebuild()
