"""Shared builders for the seats tests (PT-M8): a grown firm at a stage, with equity
partners, business-services managers and the seat holders a test asks for."""

from __future__ import annotations

from dataclasses import replace

from simcore.kernel.calendar import turn_to_ym

from ptk.sim.data_models import Balance, GameData
from ptk.sim.hiring.models import PersonState
from ptk.sim.hiring.pay import firm_pay_cents
from ptk.sim.org.actions import CreateUnit, MovePerson, apply_org_action
from ptk.sim.org.seats import AppointSeat, SetAuthority, apply_seat_action
from ptk.sim.partnership.effects import admit
from ptk.sim.people.generator import generate_person, people_gen_stream
from ptk.sim.people.models import Employment
from ptk.sim.state import GameState, with_firm, with_people, with_person_states
from ptk.sim.streams import RngFactory
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
    firm = state.player
    ym = turn_to_ym(state.turn, state.save_meta.start_ym)
    salary = firm_pay_cents(data, balance, level, ym, firm.home_city, firm.pay_policy)
    emp = Employment(
        id=pid, person_id=pid, firm_id=firm.id, start_turn=state.turn, salary_cents=salary
    )
    state = with_person_states(state, [PersonState(pid, morale=balance.morale.start)])
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


def steady(balance: Balance) -> Balance:
    """Resignations and partner flight off: the seats' comparisons hold the people constant
    (the grown fixture otherwise sheds a fifth of its people a year, on main as here)."""
    resign = balance.resign.model_copy(update={"base_bp": 0.0})
    flight = balance.partnership.flight.model_copy(update={"base_bp": 0.0, "cap_bp": 0})
    p = balance.partnership.model_copy(update={"flight": flight})
    return balance.model_copy(update={"resign": resign, "partnership": p})


CHIEFS = (
    ("finance", "cfo"),
    ("operations", "coo"),
    ("marketing_bd", "cmo"),
    ("human_resources", "chro"),
    ("finance", "pricing_director"),
)


def led_firm(data: GameData, balance: Balance, seed: int = 1, lawyers: int = 110) -> GameState:
    """A stage-3 firm with a practice group per practice and every seat filled by the best
    displayed fit (chiefs hired at chief level), each given authority with default rails."""
    from ptk.sim.org.seats import candidates

    state = appointed_committee(staged(data, balance, lawyers=lawyers, seed=seed))
    for practice in data.practice_keys:
        if any(
            state.person(e.person_id).role == data.practice_role(practice).key
            for e in state.staff(state.player.id)
        ):
            state, _ = group(state, data, balance, practice)
    for n, (role, seat) in enumerate(CHIEFS):
        state, pid = add_bs(state, data, balance, role, n=n)
        state = appoint(state, data, balance, seat, pid)
    firm = state.player.id
    used: set[int] = set()
    for u in state.org.firm_units(firm):
        if u.kind != "practice_group":
            continue
        pick = next(
            (
                pid
                for pid, _ in candidates(state, firm, data.seat("practice_group_leader"), balance)
                if pid not in used
            ),
            None,
        )
        if pick is not None:
            state = appoint(state, data, balance, "practice_group_leader", pick, slot=u.id)
            used.add(pick)
    gc = next(
        pid
        for pid, _ in candidates(state, firm, data.seat("general_counsel"), balance)
        if pid not in used
    )
    state = appoint(state, data, balance, "general_counsel", gc)
    for slot, (pid, _) in enumerate(
        candidates(state, firm, data.seat("executive_committee"), balance)[:3], start=1
    ):
        state = appoint(state, data, balance, "executive_committee", pid, slot=slot)
    for seat in ("cfo", "coo", "cmo", "chro", "pricing_director", "general_counsel"):
        state = authorise(state, data, balance, seat)
    for u in state.org.firm_units(firm):
        if u.kind == "practice_group" and u.leader_id is not None:
            state = authorise(state, data, balance, "practice_group_leader", slot=u.id)
    return state


def funded(state: GameState) -> dict[tuple[int, str], int]:
    """$50M of partners' capital in cash, so a carried ledger stays solvent."""
    from ptk.sim.ledger import CASH, PARTNERS_CAPITAL

    firm = state.player.id
    return {(firm, CASH): 5_000_000_000, (firm, PARTNERS_CAPITAL): -5_000_000_000}


def run(
    state: GameState,
    data: GameData,
    balance: Balance,
    turns: int,
    balances: dict[tuple[int, str], int] | None = None,
):  # type: ignore[no-untyped-def]
    """Advance `turns` months carrying the ledger; returns (state, results, balances)."""
    from ptk.sim.decisions import Decisions
    from ptk.sim.ledger import apply_entries
    from ptk.sim.turn import advance_turn

    carried = dict(balances if balances is not None else funded(state))
    results = []
    rng = RngFactory(state.save_meta.master_seed)
    for _ in range(turns):
        r = advance_turn(state, Decisions(), rng, balance, data, carried, answer_critical=True)
        carried = dict(apply_entries(carried, r.ledger_entries))
        results.append(r)
        state = r.new_state
    return state, results, carried
