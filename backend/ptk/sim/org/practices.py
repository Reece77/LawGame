"""Entering a practice (PT-M12; spec 6, 8.1; PT-M2's practice groups, PT-M4's laterals).

A firm practises a practice when it has a lawyer whose home practice it is (their role,
spec 5.1): the staffing rule staffs that practice's matters from them, cross-selling can
introduce them, and clients may instruct the firm in it. `EnterPractice` opens one by:

- **a lateral partner** (`route="lateral"`): PT-M4's lateral partner search in the practice
  (a recruiter's retainer; the candidates, diligence and offer follow PT-M4's rules, and the
  practice is the firm's once the partner arrives with their book);
- **a lateral team** (`route="team"`): `org.enter.team_partners` partners with their books and
  `org.enter.team_associates` associates join the home office at once, as PT-M11's lateral
  group does for an office (a recruiter's fee and a year's guarantee for each partner); stream
  `practice_team` (121), keyed (practice index, n);
- **a partner retraining** (`route="retrain"`): an equity or income partner of the firm takes
  the practice as their home practice (their role). Their familiarity with it starts where it
  is (1-6 for most) and grows only with hours in it (ADR PT-0006's slow familiarity), so their
  work in it is weak at first; their old practice's familiarity decays without hours.

When the firm has unlocked practice groups (PT-M2: `org.practice_group_unlock_lawyers`) and
has no group for the practice, a team or a retrained partner opens one (PT-M2's
`create_unit`, its rules); a lateral partner's practice waits for the player's group. The
scenario's starting practices are unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

import numpy as np

from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import OrgActionError, OrgRuleError
from ptk.sim.hiring.actions import Outcome, acting_firm, spend_energy
from ptk.sim.ledger import LedgerEntry
from ptk.sim.log import LogItem, inbox_item
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState, with_person

type EnterRoute = Literal["lateral", "team", "retrain"]
ROUTES: tuple[EnterRoute, ...] = ("lateral", "team", "retrain")
PARTNER_LEVELS = frozenset({"equity_partner", "income_partner"})


@dataclass(frozen=True, slots=True)
class EnterPractice:
    actor_id: int
    practice: str
    route: EnterRoute
    person_id: int | None = None  # retrain: the partner who takes the practice
    kind: Literal["enter_practice"] = "enter_practice"


ENTER_ACTION_TYPES: dict[str, type[EnterPractice]] = {"enter_practice": EnterPractice}


def firm_practices(state: GameState, firm_id: int, data: GameData) -> tuple[str, ...]:
    """The practices the firm has a lawyer in (their home practice), in practices.yaml order."""
    staff = set(state.staff_ids(firm_id))
    held = {
        data.role(p.role).practice
        for p in state.people
        if p.id in staff and data.role(p.role).practice is not None
    }
    return tuple(k for k in data.practice_keys if k in held)


def team_stream(rng: RngFactory, turn: int, practice_index: int, n: int) -> np.random.Generator:
    """Stream `practice_team` (121): the n-th person of a team entering a practice."""
    return rng.stream(turn, "practice_team", practice_index, n)


def _group(
    state: GameState, firm_id: int, actor_id: int, practice: str, balance: Balance, data: GameData
) -> GameState:
    """PT-M2's practice group for the practice, when its rules allow one."""
    from ptk.sim.org.actions import CreateUnit, create_unit
    from ptk.sim.org.rules import practice_groups_unlocked

    if not practice_groups_unlocked(state, firm_id, data, balance):
        return state
    if any(u.practice == practice for u in state.org.firm_units(firm_id)):
        return state
    return create_unit(
        state, CreateUnit(actor_id, "practice_group", practice=practice), balance, data
    ).state


def enter_practice(
    state: GameState, a: EnterPractice, rng: RngFactory, balance: Balance, data: GameData
) -> Outcome:
    firm = acting_firm(state, a.actor_id)
    if a.practice not in data.practice_keys:
        raise OrgActionError(f"unknown practice {a.practice!r}")
    if a.route not in ROUTES:
        raise OrgActionError(f"a practice is entered by {ROUTES}, got {a.route!r}")
    if a.practice in firm_practices(state, firm, data):
        raise OrgRuleError(f"the firm already practises {data.practice(a.practice).label}")
    entries: tuple[LedgerEntry, ...] = ()
    logs: tuple[LogItem, ...] = ()
    label = data.practice(a.practice).label
    if a.route == "lateral":
        from ptk.sim.partnership.laterals import search

        state, entries, logs = search(state, firm, a.actor_id, a.practice, rng, balance, data)
        return Outcome(state=state, entries=entries, log=logs)
    if a.route == "team":
        state, entries, logs = _team(state, firm, a, rng, balance, data)
        how = "a lateral team"
    else:
        state = _retrain(state, firm, a, balance, data)
        how = "a partner retraining"
    state = _group(state, firm, a.actor_id, a.practice, balance, data)
    log = inbox_item(
        state.turn, firm, "practice_entered", link_kind="org", link_id=0, practice=label, how=how
    )
    return Outcome(state=state, entries=entries, log=(*logs, log))


def _team(
    state: GameState,
    firm: int,
    a: EnterPractice,
    rng: RngFactory,
    balance: Balance,
    data: GameData,
) -> tuple[GameState, tuple[LedgerEntry, ...], tuple[LogItem, ...]]:
    from ptk.sim.geo.actions import build_team
    from ptk.sim.geo.cities import home_city
    from ptk.sim.geo.models import HOME_OFFICE_ID, Office

    cfg = balance.org.enter
    city = home_city(state, firm)
    home = Office(
        id=HOME_OFFICE_ID,
        firm_id=firm,
        city=city,
        seats=0,
        opened_turn=0,
        how="lateral_group",
        term_months=0,
        rent_cents=0,
        fit_out_cents=0,
        lease_start_turn=0,
    )
    index = data.practice_keys.index(a.practice)
    turn = state.turn
    return build_team(
        state,
        home,
        "lateral_group",
        a.practice,
        cfg.team_partners,
        cfg.team_associates,
        None,
        rng,
        data,
        balance,
        stream=lambda n: team_stream(rng, turn, index, n),
        client_city="",  # the home market's clients
    )


def _retrain(
    state: GameState, firm: int, a: EnterPractice, balance: Balance, data: GameData
) -> GameState:
    if a.person_id is None:
        raise OrgActionError("a partner retrains: name the partner")
    if a.person_id not in set(state.staff_ids(firm)):
        raise OrgActionError(f"person {a.person_id} is not on the firm's staff")
    person = state.person(a.person_id)
    if person.level not in PARTNER_LEVELS:
        raise OrgRuleError("only a partner can retrain into a new practice")
    state = spend_energy(state, a.actor_id, "enter_practice", balance)
    role = data.practice_role(a.practice)
    return with_person(state, replace(person, role=role.key))
