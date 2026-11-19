"""Turn phase 8 for people (spec 4.1): strain, growth and familiarity, class years, reveals.

People are processed in ascending id order (formulas.md 0). Each person on a firm's books
(active or notice) takes, in order: growth and familiarity from their month of work
(spec 5.3), strain and burnout (spec 5.6), the September class-year step (ADR PT-0006 1),
then one `employed_month` of reveal for the firm that employs them, with the firm's best
true judgment of talent as scout (formulas.md 4). A person with no `WorkMonth` worked no
hours that month.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace

from ptk.sim.calendar import YearMonth, turn_to_ym
from ptk.sim.data_models import Balance, GameData
from ptk.sim.people.growth import grow_person
from ptk.sim.people.models import Person, RevealState, WorkMonth
from ptk.sim.people.reveal import apply_knowledge_action
from ptk.sim.people.strain import strain_month
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState

EMPLOYED_ACTION = "employed_month"


def advance_class_year(person: Person, turn: int, start: YearMonth, balance: Balance) -> Person:
    """Associates advance one class year each September (ADR PT-0006 section 1)."""
    if turn_to_ym(turn, start)[1] != balance.people.class_year_month:
        return person
    nxt = balance.people.levels[person.level].next_level
    return person if nxt is None else replace(person, level=nxt)


def people_month(
    state: GameState,
    rng: RngFactory,
    data: GameData,
    balance: Balance,
    work: Mapping[int, WorkMonth],
) -> GameState:
    turn, start = state.turn, state.save_meta.start_ym
    employer = {e.person_id: e.firm_id for e in state.employments if e.counts_as_staff}
    updated: dict[int, Person] = {}
    for person in state.people:  # sorted by id
        if person.id not in employer:
            continue
        month = work.get(person.id, WorkMonth(person_id=person.id))
        p = grow_person(person, turn, rng, data, balance, month)
        p = strain_month(p, turn, month, balance)
        updated[p.id] = advance_class_year(p, turn, start, balance)
    people = tuple(updated.get(p.id, p) for p in state.people)

    scouts: dict[int, float] = {}
    for p in people:
        if p.id in employer:
            firm = employer[p.id]
            scouts[firm] = max(scouts.get(firm, 0.0), p.skills["judgment_of_talent"])
    skill_keys = frozenset(data.skill_keys)

    def known(rv: RevealState) -> RevealState:
        if employer.get(rv.person_id) != rv.observer_firm_id:
            return rv
        return apply_knowledge_action(
            rv,
            EMPLOYED_ACTION,
            scouts[rv.observer_firm_id],
            balance,
            turn=turn,
            skill_keys=skill_keys,
        )

    return replace(state, people=people, reveals=tuple(known(rv) for rv in state.reveals))
