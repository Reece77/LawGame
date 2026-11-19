"""Shared builders for the org tests (PT-M2)."""

from __future__ import annotations

from dataclasses import replace

from ptk.sim.data_models import Balance, GameData
from ptk.sim.interfaces import PAY
from ptk.sim.org.actions import OrgAction, apply_org_action
from ptk.sim.people.models import Employment, Person
from ptk.sim.setup import new_game
from ptk.sim.state import GameState
from tests.unit.test_people_generation import make

FIRM = 1


def game(
    data: GameData, balance: Balance, scenario: str = "group_lift", seed: int = 7
) -> GameState:
    return new_game(
        name="org",
        firm_name="Org LLP",
        master_seed=seed,
        scenario_id=scenario,
        difficulty="standard",
        data=data,
        balance=balance,
    ).state


def founder(state: GameState) -> int:
    fid = state.founder_of(FIRM)
    assert fid is not None
    return fid


def staff(state: GameState) -> list[Person]:
    """Everyone on the books but the player's founding partner, by id."""
    ids = set(state.staff_ids(FIRM))
    return [p for p in state.people if p.id in ids and not p.is_founder]


def hire(
    state: GameState, data: GameData, balance: Balance, role: str, level: str, n: int
) -> tuple[GameState, int]:
    """Add a generated person to the firm's books (a test shortcut for PT-M1b's hiring)."""
    pid = max(p.id for p in state.people) + 1
    person = replace(make(data, balance, role, level, n=n), id=pid)
    emp = Employment(id=pid, person_id=pid, firm_id=FIRM, start_turn=state.turn)
    return replace(
        state, people=(*state.people, person), employments=(*state.employments, emp)
    ), pid


def with_skills(state: GameState, person_id: int, **skills: float) -> GameState:
    return replace(
        state,
        people=tuple(
            replace(p, skills=p.skills.updated(skills)) if p.id == person_id else p
            for p in state.people
        ),
    )


def with_tags(state: GameState, person_id: int, *tags: str) -> GameState:
    return replace(
        state,
        people=tuple(replace(p, tags=tags) if p.id == person_id else p for p in state.people),
    )


def act(state: GameState, action: OrgAction, data: GameData, balance: Balance) -> GameState:
    return apply_org_action(state, action, balance, data, PAY).state
