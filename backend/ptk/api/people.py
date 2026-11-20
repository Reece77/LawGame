"""People endpoints and schemas (ADR-0007, ADR-0009; ADR PT-0006 section 5).

Everything here is what the player's firm *sees*: revealed ranges, the potential phrase and
revealed tags. True attribute values, potential ability, hidden traits (consistency, burnout
risk, big moments, poachability) and portability never reach a schema; a test enumerates
every people schema for them. Strain and a partner's book are shown for the player's own
firm only.
"""

from __future__ import annotations

import math
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from ptk import loader
from ptk.config import get_settings
from ptk.db import saves
from ptk.sim.calendar import turn_to_ym
from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import NotFoundError
from ptk.sim.people.formulas import current_ability, potential_phrase
from ptk.sim.people.models import PA_KEY, Person, RevealState, fam_key
from ptk.sim.people.reveal import revealed_range
from ptk.sim.state import GameState


class RangeOut(BaseModel):
    lo: int
    hi: int


class AttributeOut(BaseModel):
    key: str
    label: str
    group: str
    lo: int
    hi: int


class FamiliarityOut(BaseModel):
    practice: str
    label: str
    short_label: str
    lo: int
    hi: int


class TagOut(BaseModel):
    key: str
    label: str
    text: str


class PersonRowOut(BaseModel):
    """One row of the People screen."""

    id: int
    name: str
    role: str
    role_label: str
    kind: str
    level: str
    practice: str | None  # a lawyer's home practice
    age: int
    is_founder: bool
    founding_partner: bool
    own_firm: bool
    ability: RangeOut  # current ability (10-200) from the revealed role-skill ranges
    potential: str  # phrase from the revealed potential range (formulas.md 4)
    familiarity: list[FamiliarityOut]
    strain: float | None  # own firm only (ADR PT-0006 section 3)
    burnt_out: bool | None  # own firm only
    morale: float | None  # own firm only, founding partners none (PT-M1b)
    salary_cents: int | None  # own firm only (PT-M1b)
    pro_bono_hours: float | None = None  # own firm only: this calendar year's (PT-M7a)


class PersonOut(PersonRowOut):
    """The Person profile."""

    first_name: str
    last_name: str
    city: str
    school_tier: str | None
    bar_admissions: list[str]
    background: str | None
    skills: list[AttributeOut]
    personality: list[AttributeOut]
    interests: list[str] | None  # shown once the profile is revealed
    work_style: str | None
    tags: list[TagOut]  # revealed tags only
    capacity_hours: int
    billable_target_hours: int
    book_cents: int | None  # own firm's partners only
    burnout_since_turn: int | None  # own firm only


def _range(person: Person, reveal: RevealState, key: str) -> tuple[int, int]:
    return revealed_range(person, reveal, key)


def _familiarity(person: Person, reveal: RevealState, data: GameData) -> list[FamiliarityOut]:
    out = []
    for practice in data.practices:
        lo, hi = _range(person, reveal, fam_key(practice.key))
        out.append(
            FamiliarityOut(
                practice=practice.key,
                label=practice.label,
                short_label=practice.short_label,
                lo=lo,
                hi=hi,
            )
        )
    return out


def _row_fields(
    person: Person,
    reveal: RevealState,
    state: GameState,
    data: GameData,
    balance: Balance,
    own: bool,
) -> dict[str, object]:
    role = data.role(person.role)
    lows = {k: float(_range(person, reveal, k)[0]) for k in role.skills}
    highs = {k: float(_range(person, reveal, k)[1]) for k in role.skills}
    pa_lo, pa_hi = _range(person, reveal, PA_KEY)
    return {
        "id": person.id,
        "name": f"{person.first_name} {person.last_name}",
        "role": role.key,
        "role_label": role.label,
        "kind": role.kind,
        "level": person.level,
        "practice": role.practice,
        "age": person.age(state.turn),
        "is_founder": person.is_founder,
        "founding_partner": person.founding_partner,
        "own_firm": own,
        "ability": RangeOut(
            lo=math.floor(current_ability(lows, role.primary, role.secondary)),
            hi=math.ceil(current_ability(highs, role.primary, role.secondary)),
        ),
        "potential": potential_phrase(pa_lo, pa_hi, balance.reveal.pa_phrase_bounds),
        "familiarity": _familiarity(person, reveal, data),
        "strain": round(person.strain, 1) if own else None,
        "burnt_out": person.burnt_out if own else None,
        "morale": _morale(state, person.id) if own else None,
        "salary_cents": _salary(state, person.id) if own else None,
        "pro_bono_hours": _pro_bono(state, person.id) if own else None,
    }


def _pro_bono(state: GameState, person_id: int) -> float:
    """PT-M7a: pro bono hours this calendar year (the save's state after the last month)."""
    ps = state.person_state(person_id)
    january = turn_to_ym(state.turn, state.save_meta.start_ym)[1] == 1  # tunable-exempt
    return 0.0 if january else ps.pro_bono_ytd_tenths / 10


def _morale(state: GameState, person_id: int) -> float | None:
    morale = state.person_state(person_id).morale
    return None if morale is None else round(morale, 1)


def _salary(state: GameState, person_id: int) -> int | None:
    employment = state.employment_of(person_id)
    return None if employment is None else employment.salary_cents


def _visible(state: GameState) -> list[tuple[Person, RevealState, bool]]:
    firm = state.player.id
    staff = set(state.staff_ids(firm))
    out = []
    for person in state.people:
        reveal = state.reveal(firm, person.id)
        if reveal is not None:
            out.append((person, reveal, person.id in staff))
    return out


def people_rows(state: GameState, data: GameData, balance: Balance) -> list[PersonRowOut]:
    """People on a firm's books (candidates are on the Recruitment screen, PT-M1b)."""
    employed = {e.person_id for e in state.employments if e.counts_as_staff}
    return [
        PersonRowOut.model_validate(_row_fields(p, rv, state, data, balance, own))
        for p, rv, own in _visible(state)
        if p.id in employed
    ]


def person_profile(state: GameState, person_id: int, data: GameData, balance: Balance) -> PersonOut:
    found = next(((p, rv, own) for p, rv, own in _visible(state) if p.id == person_id), None)
    if found is None:
        raise NotFoundError(f"no person {person_id} known to your firm")
    person, reveal, own = found
    skill_defs = {s.key: s for s in data.skills}
    revealed = {tag for tag, _turn in reveal.revealed_tags}
    tags = [
        TagOut(key=t.key, label=t.label, text=t.reveal_text) for t in data.tags if t.key in revealed
    ]
    profile = reveal.profile_revealed_turn is not None
    level = balance.people.levels[person.level]
    labels = {j.key: j.label for j in data.jurisdictions}
    tier = data.school_tier(person.school_tier).label if person.school_tier else None
    background = data.background(person.background) if person.background else None
    return PersonOut.model_validate(
        {
            **_row_fields(person, reveal, state, data, balance, own),
            "first_name": person.first_name,
            "last_name": person.last_name,
            "city": person.city,
            "school_tier": tier,
            "bar_admissions": [labels.get(b, b) for b in person.bar_admissions],
            "background": background.label if background else None,
            "skills": [
                AttributeOut(
                    key=k,
                    label=skill_defs[k].label,
                    group=skill_defs[k].group,
                    lo=_range(person, reveal, k)[0],
                    hi=_range(person, reveal, k)[1],
                )
                for k in data.skill_keys
            ],
            "personality": [
                AttributeOut(
                    key=t.key,
                    label=t.label,
                    group="personality",
                    lo=_range(person, reveal, t.key)[0],
                    hi=_range(person, reveal, t.key)[1],
                )
                for t in data.personality
            ],
            "interests": list(person.interests) if profile else None,
            "work_style": person.work_style if profile else None,
            "tags": tags,
            "capacity_hours": level.capacity_hours,
            "billable_target_hours": level.billable_target_hours,
            "book_cents": person.book_cents if own and person.book_cents else None,
            "burnout_since_turn": person.burnout_since if own else None,
        }
    )


def _state(slug: str) -> GameState:
    path = saves.open_save(get_settings().resolved_save_dir(), slug)
    return saves.read_state(path)[0]


def make_router(errors: dict[int | str, dict[str, Any]]) -> APIRouter:
    router = APIRouter()

    @router.get(
        "/api/saves/{slug}/people",
        response_model=list[PersonRowOut],
        responses=errors,
        operation_id="listPeople",
    )
    def list_people(slug: str) -> list[PersonRowOut]:
        return people_rows(_state(slug), loader.game_data(), loader.balance())

    @router.get(
        "/api/saves/{slug}/people/{person_id}",
        response_model=PersonOut,
        responses=errors,
        operation_id="getPerson",
    )
    def get_person(slug: str, person_id: int) -> PersonOut:
        return person_profile(_state(slug), person_id, loader.game_data(), loader.balance())

    return router
