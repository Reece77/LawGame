"""The Family setting at a new game (TST formulas.md 45.1): none (the default: no family
record and nothing in this package runs), a partner, or a partner and children of chosen
ages.

Ported from backend/tst/sim/family/setup.py @ 121d318a (Tech Startup Tycoon); changed:
Partner Track's state (`GameState.family`), the scenario's jurisdiction for the generator,
no generations record (dynasty mode is v3); a founder flagged real never has a family
(ADR PT-0013).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Final

from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import FamilyError
from ptk.sim.family.models import (
    CHILD,
    PARTNER,
    Family,
    FamilyMember,
    with_family_record,
    with_member,
)
from ptk.sim.family.people import add_member_person, family_stream, generate_child, generate_partner
from ptk.sim.founder.config import SETTINGS
from ptk.sim.people.models import Person
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState

MIN_PARENT_AGE: Final = 18  # tunable-exempt: a parent is at least this much older than a child


@dataclass(frozen=True, slots=True)
class FamilySpec:
    setting: str = "none"  # config.SETTINGS
    child_ages: tuple[int, ...] = ()  # "children": each child's age at the start


NO_FAMILY: Final = FamilySpec()


def check_spec(spec: FamilySpec, founder_age: int, balance: Balance) -> None:
    fb = balance.family
    if spec.setting not in SETTINGS:
        raise FamilyError(f"family setting must be one of {list(SETTINGS)}")
    if spec.setting != "children" and spec.child_ages:
        raise FamilyError("children's ages need the 'children' setting")
    if spec.setting == "children":
        if not 1 <= len(spec.child_ages) <= fb.max_children:
            raise FamilyError(f"choose 1 to {fb.max_children} children")
        for age in spec.child_ages:
            if not fb.start_child_ages.lo <= age <= fb.start_child_ages.hi:
                raise FamilyError(
                    f"a child's age must be {fb.start_child_ages.lo:.0f}"
                    f"-{fb.start_child_ages.hi:.0f}"
                )
            if age > founder_age - MIN_PARENT_AGE:
                raise FamilyError(f"a child of {age} needs an older founder")


def jurisdiction(state: GameState, data: GameData) -> str:
    scenario = data.scenario(state.save_meta.scenario_id)
    return scenario.home_jurisdiction if scenario is not None else "ny"


def start_family(
    state: GameState, spec: FamilySpec, rng: RngFactory, balance: Balance, data: GameData
) -> GameState:
    """The family at the game's start; the state unchanged for Family none."""
    if spec.setting == "none":
        return state
    founder_id = state.founder_of(state.player.id)
    if founder_id is None:
        raise FamilyError("a family needs a founding partner")
    founder = state.person(founder_id)
    if founder.real:
        raise FamilyError("a real person has no game family (ADR PT-0013)")
    check_spec(spec, founder.age(state.turn), balance)
    fb = balance.family
    family = Family(
        id=founder.id,
        setting=spec.setting,
        head_id=founder.id,
        created_turn=state.turn,
        family_time=fb.default_time,
    )
    state = replace(state, family=with_family_record(state.family, family))
    state, partner = add_partner(state, founder, rng, balance, data, married=True)
    for age in sorted(spec.child_ages, reverse=True):  # the eldest first
        state, _ = add_child(state, (founder, partner), age, rng, balance, data)
    return state


def _next_index(state: GameState) -> tuple[GameState, int]:
    family = state.family.family
    assert family is not None
    index = family.next_index + 1
    fs = with_family_record(state.family, replace(family, next_index=index))
    return replace(state, family=fs), index


def add_partner(
    state: GameState,
    head: Person,
    rng: RngFactory,
    balance: Balance,
    data: GameData,
    *,
    married: bool = False,
) -> tuple[GameState, Person]:
    state, index = _next_index(state)
    gen = family_stream(rng, state.turn, head.id, index)
    pid = state.next_id("person")
    person = generate_partner(gen, head, state.turn, pid, balance, data, jurisdiction(state, data))
    state = add_member_person(state, person, rng, balance, data)
    member = FamilyMember(pid, PARTNER, index, head.id, state.turn)
    family = state.family.family
    assert family is not None
    family = replace(
        family,
        relationship=balance.family.relationship_start,
        partner_since=state.turn,
        married=married,
        low_months=0,
    )
    fs = with_member(with_family_record(state.family, family), member)
    return replace(state, family=fs), person


def add_child(
    state: GameState,
    parents: tuple[Person, ...],
    age: int,
    rng: RngFactory,
    balance: Balance,
    data: GameData,
) -> tuple[GameState, Person]:
    head = parents[0]
    state, index = _next_index(state)
    gen = family_stream(rng, state.turn, head.id, index)
    pid = state.next_id("person")
    child = generate_child(
        gen, parents, age, state.turn, pid, balance, data, jurisdiction(state, data)
    )
    state = add_member_person(state, child, rng, balance, data)
    member = FamilyMember(
        pid,
        CHILD,
        index,
        head.id,
        state.turn,
        parent_ids=tuple(p.id for p in parents),
        closeness=balance.family.closeness_start,
        milestones=tuple(m for m in balance.family.milestones if m <= age),
    )
    return replace(state, family=with_member(state.family, member)), child
