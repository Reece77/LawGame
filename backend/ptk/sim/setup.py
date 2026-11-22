"""Game creation: the initial state, its people and the turn-0 capital entry (ADR PT-0003).

PT-M1a: the founding partners (the player's and the scenario's co-founders, spec 2.1) and
the scenario's starting staff, employed by the player's firm from turn 0. The firm knows its
founding partners exactly; it knows its starting staff as it would a hire it interviewed
(stranger ranges narrowed by one interview with the player's founding partner as scout).
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from ptk.sim.data_models import Balance, GameData, Scenario
from ptk.sim.errors import UnknownDifficultyError, UnknownScenarioError
from ptk.sim.family.setup import FamilySpec, start_family
from ptk.sim.hiring.phases import starting_pay
from ptk.sim.ledger import CASH, PARTNERS_CAPITAL, LedgerEntry
from ptk.sim.macro_seed import world_data
from ptk.sim.matters.rates import starting_card
from ptk.sim.matters.setup import new_market
from ptk.sim.money import BP_DENOMINATOR, pct_of
from ptk.sim.partnership.setup import founding_partnership
from ptk.sim.people.founder import FounderSpec, build_founder
from ptk.sim.people.generator import generate_person, people_gen_stream
from ptk.sim.people.models import Employment, Person, RevealState
from ptk.sim.people.reveal import apply_knowledge_action, new_reveal_state
from ptk.sim.people.strain import initial_strain
from ptk.sim.reputation.phase import seed as seed_reputation
from ptk.sim.rivals.setup import new_rivals
from ptk.sim.rng import RngFactory
from ptk.sim.state import FirmState, GameState, SaveMeta

PLAYER_FIRM_ID = 1
STARTING_STAFF_SEARCH = 0  # people_gen key: search 0 is a scenario's starting staff
HIRE_ACTION = "interview"  # what the firm learnt of its starting staff when it hired them


@dataclass(frozen=True, slots=True)
class NewGame:
    state: GameState
    ledger_entries: tuple[LedgerEntry, ...]


def new_game(
    *,
    name: str,
    firm_name: str,
    master_seed: int,
    scenario_id: str,
    difficulty: str,
    data: GameData,
    balance: Balance,
    founder: FounderSpec | None = None,
    real_people: bool | None = None,
    family: FamilySpec | None = None,
) -> NewGame:
    data = world_data(data, balance, master_seed)  # PT-M10: the save's world
    scenario = data.scenario(scenario_id)
    if scenario is None or not scenario.available:
        raise UnknownScenarioError(f"unknown or unavailable scenario {scenario_id!r}")
    level = data.difficulty(difficulty)
    if level is None:
        raise UnknownDifficultyError(f"unknown difficulty {difficulty!r}")
    meta = SaveMeta(
        name=name,
        master_seed=master_seed,
        scenario_id=scenario.id,
        difficulty=level.id,
        start_ym=scenario.start_ym,
    )
    firm = FirmState(
        id=PLAYER_FIRM_ID,
        name=firm_name,
        is_player=True,
        stage=0,
        founded_turn=0,
        home_city=scenario.home_city,
        rate_card=starting_card(level.id, data, balance),  # PT-M7b: a new firm's card
    )
    people, employments, reveals = _starting_people(
        scenario, founder, RngFactory(master_seed), data, balance
    )
    if level.books_mult_bp != BP_DENOMINATOR:  # PT-M7b: the difficulty's books
        people = tuple(
            replace(p, book_cents=pct_of(p.book_cents, level.books_mult_bp))
            if p.founding_partner
            else p
            for p in people
        )
    state = GameState(
        save_meta=meta,
        turn=0,
        firms=(firm,),
        people=people,
        employments=employments,
        reveals=reveals,
    )
    state = starting_pay(state, balance, data)  # PT-M1b: salaries, morale, energy
    # PT-M3a: the client universe, judges and the founding partners' clients
    state = replace(
        state, market=new_market(state, firm.id, RngFactory(master_seed), data, balance)
    )
    # PT-M5: rival firms, their key people and real judges (ADR PT-0013's world.real_people)
    real = balance.world.real_people if real_people is None else real_people
    state = new_rivals(state, RngFactory(master_seed), data, balance, real)
    capital = pct_of(scenario.partners_capital_cents, level.capital_mult_bp)
    # PT-M4: the founders' agreement, capital accounts and the revolver's facility
    state = replace(
        state, partnership=founding_partnership(state, firm.id, capital, scenario, balance, data)
    )
    state = seed_reputation(state, data, balance)  # PT-M16: 2005's standing (spec 12.1)
    if family is not None:  # PT-M17: the player's family (default none: no record)
        state = start_family(state, family, RngFactory(master_seed), balance, data)
    entries: tuple[LedgerEntry, ...] = ()
    if capital:
        entries = (
            LedgerEntry.transfer(
                turn=0,
                firm_id=firm.id,
                memo="Founding partners' capital",
                debit=CASH,
                credit=PARTNERS_CAPITAL,
                amount=capital,
            ),
        )
    return NewGame(state=state, ledger_entries=entries)


def _starting_people(
    scenario: Scenario,
    founder: FounderSpec | None,
    rng: RngFactory,
    data: GameData,
    balance: Balance,
) -> tuple[tuple[Person, ...], tuple[Employment, ...], tuple[RevealState, ...]]:
    turn, city, bar = 0, scenario.home_city, scenario.home_jurisdiction
    specs = [founder or FounderSpec(background=scenario.default_background)]
    specs += [FounderSpec(background=c.background, age=c.age) for c in scenario.co_founders]
    founders = [
        build_founder(
            spec,
            rng,
            data,
            balance,
            turn,
            person_id=index + 1,
            founder_index=index,
            city=city,
            jurisdiction=bar,
        )
        for index, spec in enumerate(specs)
    ]
    staff = []
    for n, spec in enumerate(scenario.starting_staff):
        person_id = len(founders) + n + 1
        person = generate_person(
            people_gen_stream(rng, turn, STARTING_STAFF_SEARCH, n),
            data,
            balance,
            turn,
            data.role(spec.role),
            spec.level,
            person_id=person_id,
            city=city,
            jurisdiction=bar,
            practice=spec.practice,
        )
        staff.append(replace(person, strain=initial_strain(rng, turn, person_id, balance)))
    scout = founders[0].skills["judgment_of_talent"]
    skill_keys = frozenset(data.skill_keys)
    reveals = []
    for person in (*founders, *staff):
        known = new_reveal_state(
            observer_firm_id=PLAYER_FIRM_ID,
            person=person,
            turn=turn,
            rng=rng,
            data=data,
            balance=balance,
            knows_exactly=person.founding_partner,
        )
        if not person.founding_partner:
            known = apply_knowledge_action(
                known, HIRE_ACTION, scout, balance, turn=turn, skill_keys=skill_keys
            )
        reveals.append(known)
    people = (*founders, *staff)
    employments = tuple(
        Employment(id=p.id, person_id=p.id, firm_id=PLAYER_FIRM_ID, start_turn=turn) for p in people
    )
    return people, employments, tuple(reveals)
