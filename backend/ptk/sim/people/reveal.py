"""Per-observer knowledge of people (ADR-0007, formulas.md section 4; ADR PT-0006 2, 5).

Ported from backend/tst/sim/people/reveal.py @ 02fba2aa (Tech Startup Tycoon); changed:
the observer is a firm; practice familiarity has reveal records with a narrow initial
half-width (it shows on a CV), offsets drawn after PA's, narrowed by every action that
narrows skills; the knowledge actions are TST's first six (rival actions arrive with
PT-M5).
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Final

from simcore.kernel.scale import ABILITY_MAX, ABILITY_MIN, ATTR_MAX, ATTR_MIN

from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import UnknownKnowledgeActionError
from ptk.sim.fastcopy import replace
from ptk.sim.people.formulas import displayed_range, narrow, narrow_pa
from ptk.sim.people.models import (
    FAM_PREFIX,
    PA_KEY,
    Person,
    RevealRecord,
    RevealState,
    fam_key,
)
from ptk.sim.streams import RngFactory

OFFSET_LOW = -0.5  # tunable-exempt: centre offset o ~ Uniform(-0.5, 0.5) (formulas.md 4)
OFFSET_HIGH = 0.5  # tunable-exempt: centre offset o ~ Uniform(-0.5, 0.5) (formulas.md 4)


def reveal_keys(data: GameData) -> list[str]:
    """Record keys in draw order: skills, personality, PA, then familiarity by practice."""
    return [
        *data.skill_keys,
        *data.personality_keys,
        PA_KEY,
        *(fam_key(p) for p in data.practice_keys),
    ]


def new_reveal_state(
    *,
    observer_firm_id: int,
    person: Person,
    turn: int,
    rng: RngFactory,
    data: GameData,
    balance: Balance,
    knows_exactly: bool = False,
) -> RevealState:
    """Create an observer's first knowledge record of a person.

    Offsets come from stream `reveal` keyed (observer, person), one per attribute in
    `reveal_keys` order. All are drawn even when `knows_exactly` (a firm and its own
    founding partners: every attribute at hw 0 except PA, which starts at
    reveal.founder_pa_hw; formulas.md sections 4-5).
    """
    gen = rng.stream(turn, "reveal", observer_firm_id, person.id)
    initial = balance.reveal.initial_hw
    skill_keys = set(data.skill_keys)
    records = []
    for key in reveal_keys(data):
        offset = float(gen.uniform(OFFSET_LOW, OFFSET_HIGH))
        if key == PA_KEY:
            hw = balance.reveal.founder_pa_hw if knows_exactly else initial.pa
        elif knows_exactly:
            hw = 0.0
        elif key in skill_keys:
            hw = initial.skill
        elif key.startswith(FAM_PREFIX):
            hw = initial.familiarity
        else:
            hw = initial.personality
        records.append((key, RevealRecord(hw=hw, offset=offset, last_updated_turn=turn)))
    return RevealState(
        observer_firm_id=observer_firm_id,
        person_id=person.id,
        attributes=tuple(records),
        profile_revealed_turn=turn if knows_exactly else None,
        revealed_tags=tuple((tag, turn) for tag in person.tags) if knows_exactly else (),
    )


# --- Knowledge actions (formulas.md section 4) ----------------------------------------------

SKILLS = "skills"
PERSONALITY = "personality"
PA = "pa"
FAMILIARITY = "familiarity"
# Which attribute groups each action narrows (formulas.md section 4 table). Familiarity
# narrows wherever skills do (ADR PT-0006 section 2: it is on a CV).
ACTION_GROUPS: Final = MappingProxyType(
    {
        "job_post_screen": frozenset({SKILLS, FAMILIARITY, PA}),
        "network_intro": frozenset({SKILLS, FAMILIARITY, PERSONALITY, PA}),
        "interview": frozenset({SKILLS, FAMILIARITY, PERSONALITY, PA}),
        "reference_check": frozenset({PERSONALITY, PA}),
        "scouting_month": frozenset({SKILLS, FAMILIARITY, PERSONALITY, PA}),
        "employed_month": frozenset({SKILLS, FAMILIARITY, PERSONALITY, PA}),
    }
)
# Interests and work style are shown exactly after the first of these (formulas.md section 4).
PROFILE_ACTIONS: Final = frozenset({"network_intro", "interview"})


def _group(key: str, skill_keys: frozenset[str]) -> str:
    if key == PA_KEY:
        return PA
    if key.startswith(FAM_PREFIX):
        return FAMILIARITY
    return SKILLS if key in skill_keys else PERSONALITY


def apply_knowledge_action(
    reveal: RevealState,
    action: str,
    scout_judgment: float,
    balance: Balance,
    *,
    turn: int,
    skill_keys: frozenset[str],
) -> RevealState:
    """Narrow every attribute the action applies to: hw <- hw x (1 - strength x scout_factor),
    with PA's own strength and scout factor (formulas.md section 4, M2b).

    Ranges never widen: hw can only shrink. Offsets never change.
    """
    if action not in ACTION_GROUPS:
        raise UnknownKnowledgeActionError(f"unknown knowledge action {action!r}")
    cfg = balance.reveal
    groups = ACTION_GROUPS[action]
    unit = narrow(1.0, cfg.strength[action], scout_judgment, cfg)

    def narrowed(key: str, rec: RevealRecord) -> RevealRecord:
        if _group(key, skill_keys) not in groups:
            return rec
        if key == PA_KEY:  # potential uses its own strength and scout factor (M2b)
            hw = narrow_pa(rec.hw, cfg.pa_strength[action], scout_judgment, cfg)
        else:
            hw = rec.hw * unit
        return RevealRecord(hw, rec.offset, turn)

    attributes = tuple((key, narrowed(key, rec)) for key, rec in reveal.attributes)
    profile = reveal.profile_revealed_turn
    if profile is None and action in PROFILE_ACTIONS:
        profile = turn
    return replace(reveal, attributes=attributes, profile_revealed_turn=profile)


def revealed_range(person: Person, reveal: RevealState, attribute: str) -> tuple[int, int]:
    """The (min, max) an observer sees for one of a person's attributes, from true values."""
    rec = reveal.record(attribute)
    if attribute == PA_KEY:
        true_value, lo, hi = person.potential_ability, ABILITY_MIN, ABILITY_MAX
    elif attribute.startswith(FAM_PREFIX):
        practice = attribute.removeprefix(FAM_PREFIX)
        true_value, lo, hi = person.familiarity[practice], ATTR_MIN, ATTR_MAX
    elif attribute in person.skills:
        true_value, lo, hi = person.skills[attribute], ATTR_MIN, ATTR_MAX
    else:
        true_value, lo, hi = person.personality[attribute], ATTR_MIN, ATTR_MAX
    return displayed_range(true_value, rec.hw, rec.offset, lo, hi)


def shown_rating(person: Person, reveal: RevealState, skills: tuple[str, ...]) -> float:
    """A person's rating as an observer sees it (formulas.md 17.2): the mean midpoint of the
    displayed ranges of `skills` (their role's primary skills). Displayed values only."""
    mids = [sum(revealed_range(person, reveal, key)) / 2 for key in skills]
    return sum(mids) / len(mids) if mids else 0.0
