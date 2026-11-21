"""Shared builders for the seats tests (PT-M8): a grown firm at a stage, with equity
partners, business-services managers and the seat holders a test asks for."""

from __future__ import annotations

from dataclasses import replace

from ptk.sim.data_models import Balance, GameData
from ptk.sim.org.actions import CreateUnit, MovePerson, apply_org_action
from ptk.sim.org.seats import AppointSeat, SetAuthority, apply_seat_action
from ptk.sim.partnership.effects import admit
from ptk.sim.people.generator import generate_person, people_gen_stream
from ptk.sim.people.models import Employment
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState, with_firm, with_people
from tests.matters_support import grown_firm

BS_SEARCH = 9_100  # people_gen search id for test business-services people


def mp(state: GameState) -> int:
    fid = state.founder_of(state.player.id)
    assert fid is not None
    return fid


def staged(
    data: GameData,
    balance: Balance,
    *,
    lawyers: int = 110,
    stage: int = 3,
    seed: int = 1,
    equity: int = 10,
) -> GameState:
    """The grown group-lift firm at `stage`, `equity` of its income partners made equity."""
    state = grown_firm(data, balance, lawyers, seed=seed)
    state = with_firm(state, replace(state.player, stage=stage))
    firm = state.player.id
    income = [p.id for p in state.people if p.level == "income_partner" and not p.is_founder]
    for pid in income[:equity]:
        state, _ = admit(state, firm, pid, "equity", balance, data)
    return state


def appointed_committee(state: GameState) -> GameState:
    """The agreement's exco_elected term voted false: the MP appoints the committee."""
    from ptk.sim.org.seat_models import FirmLeadership
    from ptk.sim.org.seats import with_firm_leadership

    return with_firm_leadership(state, FirmLeadership(state.player.id, exco_elected=False))


def add_bs(
    state: GameState, data: GameData, balance: Balance, role: str, level: str = "chief", n: int = 0
) -> tuple[GameState, int]:
    """A business-services person joins the books (a test shortcut for hiring)."""
    pid = max(p.id for p in state.people) + 1
    rng = RngFactory(state.save_meta.master_seed)
    person = generate_person(
        people_gen_stream(rng, state.turn, BS_SEARCH, pid + n),
        data,
        balance,
        state.turn,
        data.role(role),
        level,
        person_id=pid,
        city=state.player.home_city,
        jurisdiction="us_ny",
    )
    state = with_people(state, [person])
    emp = Employment(id=pid, person_id=pid, firm_id=state.player.id, start_turn=state.turn)
    return replace(state, employments=(*state.employments, emp)), pid


def with_score(state: GameState, data: GameData, pid: int, seat: str, value: float) -> GameState:
    """Every skill the seat weighs (and integrity) set to `value`: the seat score is `value`."""
    person = state.person(pid)
    weights = data.seat(seat).weights
    skills = {k: value for k in weights if k in person.skills}
    traits = {k: value for k in weights if k not in person.skills}
    person = replace(
        person,
        skills=person.skills.updated(skills),
        personality=person.personality.updated(traits),
    )
    return with_people(state, [person])


def appoint(
    state: GameState, data: GameData, balance: Balance, seat: str, pid: int | None, slot: int = 0
) -> GameState:
    state = _refill(state, balance)
    return apply_seat_action(state, AppointSeat(mp(state), seat, slot, pid), balance, data).state


def authorise(
    state: GameState,
    data: GameData,
    balance: Balance,
    seat: str,
    slot: int = 0,
    guardrails: tuple[tuple[str, int], ...] = (),
) -> GameState:
    state = _refill(state, balance)
    action = SetAuthority(mp(state), seat, slot, True, guardrails)
    return apply_seat_action(state, action, balance, data).state


def group(
    state: GameState, data: GameData, balance: Balance, practice: str
) -> tuple[GameState, int]:
    """A practice group for `practice` with every lawyer of that practice in it."""
    actor = mp(state)
    out = apply_org_action(
        state, CreateUnit(actor, "practice_group", practice=practice), balance, data
    )
    state, unit = out.state, out.unit_id
    assert unit is not None
    role = data.practice_role(practice).key
    for e in state.staff(state.player.id):
        p = state.person(e.person_id)
        if p.role == role and not p.is_founder:
            state = apply_org_action(state, MovePerson(actor, p.id, unit), balance, data).state
    return state, unit


def _refill(state: GameState, balance: Balance) -> GameState:
    from ptk.sim.state import with_person_states

    ps = state.person_state(mp(state))
    return with_person_states(state, [replace(ps, energy=balance.energy.per_month)])
