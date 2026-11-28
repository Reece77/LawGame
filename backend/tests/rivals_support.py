"""Helpers for PT-M5 tests: games played with rivals, and the player hiring rivals' people."""

from __future__ import annotations

import math
from dataclasses import replace

from simcore.kernel.calendar import ym_to_turn

from ptk.sim.data_models import Balance, GameData
from ptk.sim.decisions import Decisions
from ptk.sim.ledger import apply_entries
from ptk.sim.people.models import Employment
from ptk.sim.rivals import phase as rival_phase
from ptk.sim.rivals.people import person_of, update_member
from ptk.sim.setup import new_game
from ptk.sim.state import GameState, with_people
from ptk.sim.streams import RngFactory
from ptk.sim.turn import TurnResult, advance_turn


def start(
    data: GameData, balance: Balance, seed: int, real_people: bool | None = None
) -> GameState:
    return new_game(
        name="r",
        firm_name="Founders LLP",
        master_seed=seed,
        scenario_id="biglaw_spinout",
        difficulty="standard",
        data=data,
        balance=balance,
        real_people=real_people,
    ).state


def rivals_month(state: GameState, rng: RngFactory, data: GameData, balance: Balance) -> GameState:
    """The rivals' phases alone (spec 4.1's PT-M5 steps, in order) and the month's end: the
    rivals' market goes on after the player's unmanaged firm has dissolved (PT-M4: do-nothing
    fails, T1), so rival measurements do not depend on the player's survival."""
    for step in (
        rival_phase.answer_approaches,
        rival_phase.decide,
        rival_phase.rfps_before_intake,
        rival_phase.after_intake,
        rival_phase.people,
        rival_phase.market,
    ):
        state = step(state, rng, data, balance).state
    return replace(state, turn=state.turn + 1)


def play_until(
    state: GameState, data: GameData, balance: Balance, turn: int, seed: int
) -> tuple[GameState, list[TurnResult]]:
    """Play to `turn`: whole turns while the player's firm lives, then the rivals' months."""
    balances: dict[tuple[int, str], int] = {}
    results = []
    while state.turn < turn:
        if state.ended:
            state = rivals_month(state, RngFactory(seed), data, balance)
            continue
        result = advance_turn(state, Decisions(), RngFactory(seed), balance, data, balances)
        balances = dict(apply_entries(balances, result.ledger_entries))
        results.append(result)
        state = result.new_state
    return state, results


def turn_of(state: GameState, year: int, month: int) -> int:
    return ym_to_turn(year, month, state.save_meta.start_ym)


def hire_away(
    state: GameState, firm_key: str, share: float, data: GameData, balance: Balance
) -> GameState:
    """The player's firm hires `share` of a rival's key partners (the biggest books first),
    as accepted offers would: each joins the player's books this turn."""
    firm = state.rivals.by_key(firm_key)
    assert firm is not None and firm.active
    partners = sorted(
        (m for m in state.rivals.members_of(firm.id) if m.kind == "partner"),
        key=lambda m: (-m.book_cents, m.person_id),
    )
    chosen = partners[: math.ceil(len(partners) * share)]
    people, employments = [], list(state.employments)
    rivals = state.rivals
    next_id = state.next_id("employment")
    for i, m in enumerate(chosen):
        people.append(person_of(state, m, data, balance))
        employments.append(
            Employment(
                id=next_id + i,
                person_id=m.person_id,
                firm_id=state.player.id,
                start_turn=state.turn,
                salary_cents=50_000_000,
            )
        )
        rivals = update_member(rivals, replace(m, outside=True))
    state = replace(state, rivals=rivals, employments=tuple(employments))
    return with_people(state, people)
