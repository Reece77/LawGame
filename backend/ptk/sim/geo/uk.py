"""The UK path (PT-M11; spec 5.2, 5.7): training contracts, trainee seats and qualification.

An office in England and Wales offers training contracts two years ahead
(`geo.contract_lead_years`): `count` trainees join it in September of that year, each with four
six-month seats in practices drawn at their making (stream `trainees`, 104, keyed (contract id,
n); a trainee's home practice is their current seat's, so their work and familiarity rotate).
Trainees are paid the London scale (bar_rules.yaml `london_scale`: the first year's salary,
then the second year's) and are not admitted. Each September a trainee whose two years are up
qualifies: a newly qualified solicitor (class 1, admitted in England and Wales) in the practice
of their last seat, on the London scale.

The fees (the course and a grant) are paid when contracts are offered (6200, the office's).
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from ptk.sim.calendar import MONTHS_PER_YEAR, turn_to_ym, ym_to_turn
from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import InvalidActionError
from ptk.sim.geo.admissions import SOLICITOR, admit
from ptk.sim.geo.models import Trainee, TrainingContract
from ptk.sim.hiring.actions import Outcome, acting_firm, spend_energy
from ptk.sim.hiring.pay import firm_pay_cents, london_pay_cents
from ptk.sim.ledger import CASH, RECRUITING, LedgerEntry, LedgerLine
from ptk.sim.log import LogItem, inbox_item
from ptk.sim.people.generator import generate_person
from ptk.sim.people.models import Employment
from ptk.sim.people.reveal import new_reveal_state
from ptk.sim.rng import RngFactory
from ptk.sim.state import (
    GameState,
    with_employment,
    with_people,
    with_person,
    with_person_states,
    with_reveals,
)

TRAINEE = "trainee"
NQ = "associate_1"
SEATS = 4  # tunable-exempt: two years of six-month seats (spec 5.2)


def is_uk_office(state: GameState, office_id: int, data: GameData) -> bool:
    office = state.geo.office(office_id)
    return office is not None and office.is_open and data.geo.city(office.city).region == "uk"


def offer_training_contracts(
    state: GameState, a: object, balance: Balance, data: GameData
) -> Outcome:
    from ptk.sim.geo.actions import OfferTrainingContracts

    assert isinstance(a, OfferTrainingContracts)
    firm_id = acting_firm(state, a.actor_id)
    gb = balance.geo
    office = state.geo.office(a.office_id)
    if office is None or office.firm_id != firm_id or not is_uk_office(state, a.office_id, data):
        raise InvalidActionError("training contracts are offered by an office in England and Wales")
    if not 1 <= a.count <= gb.max_contracts:
        raise InvalidActionError(f"offer 1-{gb.max_contracts} training contracts")
    year = turn_to_ym(state.turn, state.save_meta.start_ym)[0]
    start_year = year + gb.contract_lead_years
    if any(
        c.office_id == office.id
        and c.offered_turn // MONTHS_PER_YEAR == state.turn // MONTHS_PER_YEAR
        for c in state.geo.contracts
    ):
        raise InvalidActionError("this office has offered its training contracts this year")
    state = spend_energy(state, a.actor_id, "training_contracts", balance)
    start = ym_to_turn(start_year, gb.qualify_month, state.save_meta.start_ym)
    geo = state.geo
    contract = TrainingContract(
        geo.next_contract_id, firm_id, office.id, state.turn, start, a.count
    )
    state = replace(
        state,
        geo=replace(geo, contracts=(*geo.contracts, contract), next_contract_id=contract.id + 1),
    )
    cost = gb.training_contract_cost_cents * a.count
    entries: tuple[LedgerEntry, ...] = ()
    if cost:
        entries = (
            LedgerEntry(
                turn=state.turn,
                firm_id=firm_id,
                memo=f"Training contracts ({a.count})",
                lines=(
                    LedgerLine(RECRUITING, cost, office_id=office.id),
                    LedgerLine(CASH, -cost, office_id=office.id),
                ),
            ),
        )
    log = inbox_item(
        state.turn,
        firm_id,
        "training_contracts",
        link_kind="offices",
        link_id=office.id,
        count=a.count,
        year=start_year,
    )
    return Outcome(state, entries, (log,))


def _seats(gen: np.random.Generator, data: GameData) -> tuple[str, ...]:
    keys = list(data.practice_keys)
    idx = gen.choice(len(keys), size=min(SEATS, len(keys)), replace=False)
    return tuple(keys[int(i)] for i in idx)


def trainees_join(
    state: GameState, rng: RngFactory, balance: Balance, data: GameData
) -> tuple[GameState, tuple[LogItem, ...]]:
    """Phase 1: contracts starting this month bring their trainees."""
    due = [c for c in state.geo.contracts if not c.filled and c.start_turn <= state.turn]
    logs: list[LogItem] = []
    for c in due:
        office = state.geo.office(c.office_id)
        geo = state.geo
        contracts = tuple(replace(x, filled=True) if x.id == c.id else x for x in geo.contracts)
        state = replace(state, geo=replace(geo, contracts=contracts))
        if office is None or not office.is_open:
            continue
        city = office.city
        firm = state.firm(c.firm_id)
        ym = turn_to_ym(state.turn, state.save_meta.start_ym)
        trainees = list(state.geo.trainees)
        for n in range(c.count):
            gen = rng.stream(state.turn, "trainees", c.id, n)
            seats = _seats(gen, data)
            role = data.practice_role(seats[0])
            pid = state.next_id("person")
            person = generate_person(
                gen,
                data,
                balance,
                state.turn,
                role,
                TRAINEE,
                person_id=pid,
                city=city,
                jurisdiction=SOLICITOR,
            )
            state = with_people(state, [person])
            state = with_reveals(
                state,
                [
                    new_reveal_state(
                        observer_firm_id=c.firm_id,
                        person=person,
                        turn=state.turn,
                        rng=rng,
                        data=data,
                        balance=balance,
                    )
                ],
            )
            salary = firm_pay_cents(data, balance, TRAINEE, ym, city, firm.pay_policy)
            state = with_employment(
                state,
                Employment(
                    id=state.next_id("employment"),
                    person_id=pid,
                    firm_id=c.firm_id,
                    start_turn=state.turn,
                    salary_cents=salary,
                ),
            )
            ps = state.person_state(pid)
            state = with_person_states(state, [replace(ps, morale=balance.morale.new_hire)])
            trainees.append(
                Trainee(pid, office.id, state.turn, state.turn + balance.geo.training_months, seats)
            )
        geo = state.geo
        state = replace(
            state, geo=replace(geo, trainees=tuple(sorted(trainees, key=lambda t: t.person_id)))
        )
        logs.append(
            inbox_item(
                state.turn,
                c.firm_id,
                "trainees_joined",
                link_kind="offices",
                link_id=office.id,
                count=c.count,
            )
        )
    return state, tuple(logs)


def trainees_month(
    state: GameState, balance: Balance, data: GameData
) -> tuple[GameState, tuple[LogItem, ...]]:
    """Phase 8: seats rotate; the second year's salary; trainees due qualify (newly qualified,
    admitted in England and Wales, on the London scale); a trainee who left is dropped."""
    if not state.geo.trainees:
        return state, ()
    gb = balance.geo
    logs: list[LogItem] = []
    keep: list[Trainee] = []
    ym = turn_to_ym(state.turn, state.save_meta.start_ym)
    for t in state.geo.trainees:
        e = state.employment_of(t.person_id)
        if e is None:
            continue
        person = state.person(t.person_id)
        firm = state.firm(e.firm_id)
        if state.turn >= t.qualify_turn:
            practice = t.seat(state.turn - 1, gb.trainee_seat_months)
            person = replace(person, level=NQ, role=data.practice_role(practice).key)
            state = with_person(state, person)
            state = admit(state, person.id, SOLICITOR, "qualified")
            pay = firm_pay_cents(data, balance, NQ, ym, person.city, firm.pay_policy)
            state = with_employment(state, replace(e, salary_cents=max(pay, e.salary_cents)))
            logs.append(
                inbox_item(
                    state.turn,
                    e.firm_id,
                    "trainee_qualified",
                    link_kind="person",
                    link_id=person.id,
                    name=f"{person.first_name} {person.last_name}",
                    practice=data.practice(practice).label,
                )
            )
            continue
        seat = t.seat(state.turn, gb.trainee_seat_months)
        role = data.practice_role(seat).key
        if person.role != role:
            state = with_person(state, replace(person, role=role))
        months = state.turn - t.started_turn
        if months == MONTHS_PER_YEAR:  # the second year's salary
            row = data.geo.london_row(ym)
            if row is not None and london_pay_cents(data, TRAINEE, ym, person.city) is not None:
                state = with_employment(
                    state, replace(e, salary_cents=max(e.salary_cents, row.trainee_cents[1]))
                )
        keep.append(t)
    return replace(state, geo=replace(state.geo, trainees=tuple(keep))), tuple(logs)
