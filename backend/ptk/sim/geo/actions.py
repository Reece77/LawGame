"""The player's office, admission and training actions (PT-M11; ADR-0014; spec 8.8, 11.1, 5.7).

- **Open an office** in a city (energy `open_office`): a lease of `seats` lawyer seats
  (signing and fit-out post at once, `ptk.sim.geo.offices`), the city's clients join the world
  (`ptk.sim.geo.markets`), and its people come one of three ways:
  - *organic*: one of the firm's partners moves there (admitted on motion or by exam in a US
    city, registered as a foreign lawyer in London) and brings introductions to
    `geo.organic_clients` local clients;
  - *lateral group*: partners and associates hired from the local market through a recruiter
    (PT-M4's lateral arrival: the recruiter's fee, their books over 12-24 months);
  - *team lift*: partners and associates lifted from a rival present in the city's region:
    no recruiter, their book clients follow within `geo.lift_months`, the rival loses the
    book (its demand offset) and grows hostile.
  The team is generated on stream `office_team` (102), keyed (office id, n).
- **Close an office** (energy `close_office`, a one-off): the lease is broken
  (`close_penalty_months` of rent) and its people move to the home office.
- **Move a lawyer** to another office (relocation; no cost).
- **Seek admission** for a lawyer: a bar exam, a motion or a foreign lawyer's registration
  (`ptk.sim.geo.admissions`).
- **Offer training contracts** in an office in England and Wales (`ptk.sim.geo.uk`).
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Literal

import numpy as np

from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import InvalidActionError
from ptk.sim.geo import formulas as gf
from ptk.sim.geo.admissions import FOREIGN, start_admission
from ptk.sim.geo.cities import office_in, rival_region
from ptk.sim.geo.markets import make_city_clients
from ptk.sim.geo.models import HOME_OFFICE_ID, Office, OpenHow, with_office
from ptk.sim.geo.offices import closing_entries, signing_entries
from ptk.sim.hiring.actions import Outcome, acting_firm, spend_energy
from ptk.sim.hiring.pay import firm_pay_cents
from ptk.sim.interfaces import LateralArrival
from ptk.sim.ledger import LedgerBalances, LedgerEntry
from ptk.sim.log import LogItem, inbox_item
from ptk.sim.matters.intake import with_relationship
from ptk.sim.matters.market import client_weight
from ptk.sim.matters.models import Relationship
from ptk.sim.money import BP_DENOMINATOR, pct_of
from ptk.sim.people.generator import generate_person
from ptk.sim.people.models import Employment, Person
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

type Draws = Callable[[], np.random.Generator]

PARTNER_LEVELS = frozenset({"equity_partner", "income_partner"})
LIFT_LEVELS = ("associate_2", "associate_3", "associate_4", "associate_5", "associate_6")


@dataclass(frozen=True, slots=True)
class OpenOffice:
    actor_id: int
    city: str
    seats: int
    how: OpenHow
    practice: str | None = None  # lateral group and team lift: the team's practice
    partner_id: int | None = None  # organic: the partner who moves
    rival_key: str | None = None  # team lift: the rival the team leaves
    partners: int = 1  # lateral group and team lift: partners in the team
    associates: int = 0  # ... and associates
    kind: Literal["open_office"] = "open_office"


@dataclass(frozen=True, slots=True)
class CloseOffice:
    actor_id: int
    office_id: int
    kind: Literal["close_office"] = "close_office"


@dataclass(frozen=True, slots=True)
class MoveLawyer:
    actor_id: int
    person_id: int
    office_id: int  # 0: the home office
    kind: Literal["move_lawyer"] = "move_lawyer"


@dataclass(frozen=True, slots=True)
class SeekAdmission:
    actor_id: int
    person_id: int
    jurisdiction: str
    route: Literal["exam", "motion", "register"] = "exam"
    kind: Literal["seek_admission"] = "seek_admission"


@dataclass(frozen=True, slots=True)
class OfferTrainingContracts:
    actor_id: int
    office_id: int
    count: int
    kind: Literal["offer_training_contracts"] = "offer_training_contracts"


type GeoAction = OpenOffice | CloseOffice | MoveLawyer | SeekAdmission | OfferTrainingContracts

GEO_ACTION_TYPES: dict[str, type[GeoAction]] = {
    "open_office": OpenOffice,
    "close_office": CloseOffice,
    "move_lawyer": MoveLawyer,
    "seek_admission": SeekAdmission,
    "offer_training_contracts": OfferTrainingContracts,
}


def team_stream(rng: RngFactory, turn: int, office_id: int, n: int) -> np.random.Generator:
    """Stream `office_team` (102): the office's n-th lifted or lateral person; n = 0 the book
    clients and portability. This is the stream's one call site."""
    return rng.stream(turn, "office_team", office_id, n)


def _err(msg: str) -> InvalidActionError:
    return InvalidActionError(msg)


def _relocate(state: GameState, person: Person, city: str) -> GameState:
    return with_person(state, replace(person, city=city))


def _city_clients(state: GameState, city: str) -> list[int]:
    return [c.id for c in state.market.clients if c.city == city]


def _book_clients(
    state: GameState,
    gen: np.random.Generator,
    city: str,
    practice: str,
    k: int,
    taken: set[int],
    data: GameData,
    balance: Balance,
) -> tuple[int, ...]:
    """k of the city's clients, drawn by their wallets in the practice."""
    pool = [state.market.client(cid) for cid in _city_clients(state, city) if cid not in taken]
    weights = np.array([client_weight(c, practice, data, balance) for c in pool])
    if not pool or weights.sum() <= 0:
        return ()
    k = min(k, int((weights > 0).sum()))
    idx = gen.choice(len(pool), size=k, replace=False, p=weights / weights.sum())
    out = tuple(sorted(pool[int(j)].id for j in idx))
    taken.update(out)
    return out


def _know(
    state: GameState,
    firm_id: int,
    person: Person,
    rng: RngFactory,
    data: GameData,
    balance: Balance,
) -> GameState:
    return with_reveals(
        state,
        [
            new_reveal_state(
                observer_firm_id=firm_id,
                person=person,
                turn=state.turn,
                rng=rng,
                data=data,
                balance=balance,
            )
        ],
    )


def _hire(
    state: GameState, firm_id: int, person: Person, city: str, data: GameData, balance: Balance
) -> GameState:
    from ptk.sim.calendar import turn_to_ym

    firm = state.firm(firm_id)
    ym = turn_to_ym(state.turn, state.save_meta.start_ym)
    salary = firm_pay_cents(data, balance, person.level, ym, city, firm.pay_policy)
    state = with_employment(
        state,
        Employment(
            id=state.next_id("employment"),
            person_id=person.id,
            firm_id=firm_id,
            start_turn=state.turn,
            salary_cents=salary,
        ),
    )
    ps = state.person_state(person.id)
    return with_person_states(state, [replace(ps, morale=balance.morale.new_hire)])


def build_team(
    state: GameState,
    office: Office,
    how: OpenHow,
    practice: str,
    partners: int,
    associates: int,
    rival_key: str | None,
    rng: RngFactory,
    data: GameData,
    balance: Balance,
    *,
    stream: Callable[[int], np.random.Generator] | None = None,
    client_city: str | None = None,
) -> tuple[GameState, tuple[LedgerEntry, ...], tuple[LogItem, ...]]:
    """A lateral group's or a lifted team's partners (with their books) and associates.
    PT-M12: `stream` (the n-th person's generator) and `client_city` (the clients' market key)
    let a team join the home office (entering a practice, `ptk.sim.org.practices`)."""
    from ptk.sim.partnership.common import firm_partnership, put
    from ptk.sim.partnership.laterals import CLIENT_BOOK_CENTS, arrive_partner
    from ptk.sim.partnership.models import Arrival

    gb, lc = balance.geo, balance.partnership.lateral
    firm_id, city = office.firm_id, office.city
    cdef = data.geo.city(city)
    role = data.practice_role(practice)
    entries: list[LedgerEntry] = []
    logs: list[LogItem] = []
    taken = {r.client_id for r in state.market.relationships if r.firm_id == firm_id}
    lost_book = 0.0
    n = 0
    draw = stream or (lambda k: team_stream(rng, state.turn, office.id, k))
    market_city = city if client_city is None else client_city
    for _ in range(partners):
        n += 1
        gen = draw(n)
        pid = state.next_id("person")
        person = generate_person(
            gen,
            data,
            balance,
            state.turn,
            role,
            "equity_partner",
            person_id=pid,
            city=city,
            jurisdiction=cdef.jurisdiction,
        )
        blo, bhi = lc.book_cents
        book = round(math.exp(gen.uniform(math.log(blo), math.log(bhi))))
        port = float(gen.uniform(*gb.lift_portability)) if how == "team_lift" else None
        if port is not None:  # a lateral group keeps the generated person's portability
            person = replace(person, portability_bp=round(port * BP_DENOMINATOR))
        person = replace(person, book_cents=book)
        k = max(
            1, min(8, round(book * gb.lift_book_share / CLIENT_BOOK_CENTS))
        )  # tunable-exempt: 1-8
        clients = _book_clients(state, gen, market_city, practice, k, taken, data, balance)
        state = with_people(state, [person])
        state = _know(state, firm_id, person, rng, data, balance)
        comp = pct_of(book, lc.comp_of_book_bp)
        lateral = how == "lateral_group"
        res = arrive_partner(
            state,
            LateralArrival(
                person_id=pid,
                firm_id=firm_id,
                from_suitor=None,
                comp_cents=comp,
                guarantee_years=1 if lateral else 0,
                equity=True,
                client_ids=clients if lateral else (),
            ),
            gen,
            balance,
            data,
            recruiter_fee=lateral,
        )
        state = res.state
        entries.extend(res.entries)
        logs.extend(res.log)
        if not lateral:  # a lifted team's clients follow fast, each with the partner's chance
            fp = firm_partnership(state, firm_id)
            arrivals = list(fp.arrivals)
            for i_c, cid in enumerate(clients):
                # the partner's anchor client (the first drawn) always follows a lifted team
                if float(gen.random()) < (port or 0.0) or i_c == 0:
                    when = state.turn + int(gen.integers(1, gb.lift_months + 1))
                    arrivals.append(Arrival(pid, firm_id, cid, when, practice))
            fp = replace(fp, arrivals=tuple(sorted(arrivals, key=lambda a: (a.turn, a.client_id))))
            state = put(state, fp)
            lost_book += book * (port or 0.0)
    for _ in range(associates):
        n += 1
        gen = draw(n)
        level = LIFT_LEVELS[int(gen.integers(len(LIFT_LEVELS)))]
        pid = state.next_id("person")
        person = generate_person(
            gen,
            data,
            balance,
            state.turn,
            role,
            level,
            person_id=pid,
            city=city,
            jurisdiction=cdef.jurisdiction,
        )
        state = with_people(state, [person])
        state = _know(state, firm_id, person, rng, data, balance)
        state = _hire(state, firm_id, person, city, data, balance)
    if rival_key is not None and lost_book > 0:
        rivals = state.rivals
        firm = rivals.by_key(rival_key)
        if firm is not None:
            firm = replace(
                firm, offset_cents=firm.offset_cents - lost_book, stance=firm.stance + 1.0
            )
            rivals = replace(
                rivals, firms=tuple(firm if f.id == firm.id else f for f in rivals.firms)
            )
            state = replace(state, rivals=rivals)
    return state, tuple(entries), tuple(logs)


def open_office(
    state: GameState, a: OpenOffice, rng: RngFactory, balance: Balance, data: GameData
) -> Outcome:
    firm_id = acting_firm(state, a.actor_id)
    firm = state.firm(firm_id)
    if not data.geo.has_city(a.city):
        raise _err(f"unknown city {a.city!r}")
    cdef = data.geo.city(a.city)
    if cdef.key == firm.home_city:
        raise _err("the firm's home city already has its office")
    if office_in(state, firm_id, cdef.key) is not None:
        raise _err(f"the firm already has an office in {cdef.label}")
    if a.seats not in balance.geo.seat_sizes:
        raise _err(f"an office has one of {list(balance.geo.seat_sizes)} seats")
    team = a.partners + a.associates if a.how != "organic" else 1
    if team > a.seats:
        raise _err(f"{team} lawyers will not fit in {a.seats} seats")
    partner: Person | None = None
    if a.how == "organic":
        e = state.employment_of(a.partner_id) if a.partner_id is not None else None
        if a.partner_id is None or e is None or e.firm_id != firm_id or e.status != "active":
            raise _err("an organic start needs one of the firm's partners (not leaving) to move")
        partner = state.person(a.partner_id)
        if partner.level not in PARTNER_LEVELS:
            raise _err("an organic start needs a partner")
    else:
        if a.practice is None or a.practice not in data.practice_keys:
            raise _err("a team needs a practice")
        if a.partners < 1 or a.associates < 0:
            raise _err("a team needs at least one partner")
    if a.how == "team_lift":
        rival = state.rivals.by_key(a.rival_key or "")
        if rival is None or not rival.active:
            raise _err(f"no active rival {a.rival_key!r}")
        if rival_region(data, rival.hq) != cdef.region:
            raise _err(f"{rival.name} has no team to lift in {cdef.label}")
    state = spend_energy(state, a.actor_id, "open_office", balance)
    oid = state.geo.next_office_id
    rent = gf.lease_rent_cents(a.seats, cdef)
    office = Office(
        id=oid,
        firm_id=firm_id,
        city=cdef.key,
        seats=a.seats,
        opened_turn=state.turn,
        how=a.how,
        term_months=balance.geo.lease_months,
        rent_cents=rent,
        fit_out_cents=gf.fit_out_cents(a.seats, balance.geo),
        lease_start_turn=state.turn,
    )
    state = replace(state, geo=with_office(state.geo, office))
    state = make_city_clients(state, cdef.key, rng, data, balance)
    entries: list[LedgerEntry] = list(signing_entries(office, state.turn))
    logs: list[LogItem] = []
    if partner is not None:
        state = _relocate(state, partner, cdef.key)
        state, more, _ = _admit_where(state, partner.id, cdef.key, data, balance)
        entries.extend(more)
        state = _introductions(state, partner.id, cdef.key, rng, oid, data, balance)
    else:
        assert a.practice is not None
        state, more, team_logs = build_team(
            state,
            office,
            a.how,
            a.practice,
            a.partners,
            a.associates,
            a.rival_key,
            rng,
            data,
            balance,
        )
        entries.extend(more)
        logs.extend(team_logs)
    logs.append(
        inbox_item(
            state.turn,
            firm_id,
            "office_opened",
            link_kind="offices",
            link_id=oid,
            city=cdef.label,
            seats=a.seats,
            rent_cents=rent,
        )
    )
    return Outcome(state, tuple(entries), tuple(logs))


def _admit_where(
    state: GameState, person_id: int, city: str, data: GameData, balance: Balance
) -> tuple[GameState, tuple[LedgerEntry, ...], tuple[LogItem, ...]]:
    """A partner who moves seeks admission there: registration in London, a motion where they
    qualify, else the bar exam (nothing where already admitted)."""
    j = data.geo.city(city).jurisdiction
    person = state.person(person_id)
    if j in person.bar_admissions:
        return state, (), ()
    if data.geo.city(city).region == "uk":
        return start_admission(state, person_id, FOREIGN, "register", data, balance)
    try:
        return start_admission(state, person_id, j, "motion", data, balance)
    except ValueError:
        return start_admission(state, person_id, j, "exam", data, balance)


def _introductions(
    state: GameState,
    person_id: int,
    city: str,
    rng: RngFactory,
    office_id: int,
    data: GameData,
    balance: Balance,
) -> GameState:
    """An organic start's partner is introduced to a few local clients (a low relationship)."""
    person = state.person(person_id)
    practice = data.role(person.role).practice or data.practice_keys[0]
    firm_id = state.player.id
    taken = {r.client_id for r in state.market.relationships if r.firm_id == firm_id}
    gen = team_stream(rng, state.turn, office_id, 0)
    lo, hi = balance.geo.organic_relationship
    market = state.market
    for cid in _book_clients(
        state, gen, city, practice, balance.geo.organic_clients, taken, data, balance
    ):
        market = with_relationship(
            market,
            Relationship(
                client_id=cid,
                firm_id=firm_id,
                score=float(gen.uniform(lo, hi)),
                partner_id=person_id,
                practices=(practice,),
                since_turn=state.turn,
            ),
        )
    return replace(state, market=market)


def close_office(state: GameState, a: CloseOffice, balance: Balance, data: GameData) -> Outcome:
    firm_id = acting_firm(state, a.actor_id)
    office = state.geo.office(a.office_id)
    if office is None or office.firm_id != firm_id or not office.is_open:
        raise _err(f"no open office {a.office_id}")
    state = spend_energy(state, a.actor_id, "close_office", balance)
    entries = closing_entries(office, state.turn, balance)
    home = state.firm(firm_id).home_city
    for pid in state.staff_ids(firm_id):
        p = state.person(pid)
        if p.city == office.city:
            state = _relocate(state, p, home)
    closed = replace(office, status="closed", closed_turn=state.turn)
    state = replace(state, geo=with_office(state.geo, closed))
    log = inbox_item(
        state.turn,
        firm_id,
        "office_closed",
        link_kind="offices",
        link_id=office.id,
        city=data.geo.city(office.city).label,
    )
    return Outcome(state, entries, (log,))


def move_lawyer(state: GameState, a: MoveLawyer, balance: Balance, data: GameData) -> Outcome:
    firm_id = acting_firm(state, a.actor_id)
    if a.person_id not in state.staff_ids(firm_id):
        raise _err(f"person {a.person_id} is not on the firm's books")
    if a.office_id == HOME_OFFICE_ID:
        city = state.firm(firm_id).home_city
    else:
        office = state.geo.office(a.office_id)
        if office is None or office.firm_id != firm_id or not office.is_open:
            raise _err(f"no open office {a.office_id}")
        city = office.city
    return Outcome(_relocate(state, state.person(a.person_id), city))


def seek_admission(state: GameState, a: SeekAdmission, balance: Balance, data: GameData) -> Outcome:
    firm_id = acting_firm(state, a.actor_id)
    if a.person_id not in state.staff_ids(firm_id):
        raise _err(f"person {a.person_id} is not on the firm's books")
    if data.role(state.person(a.person_id).role).kind != "lawyer":
        raise _err("only lawyers are admitted")
    state = spend_energy(state, a.actor_id, "bar_admission", balance)
    route = "register" if a.jurisdiction == FOREIGN else a.route
    try:
        state, entries, logs = start_admission(
            state, a.person_id, a.jurisdiction, route, data, balance
        )
    except ValueError as exc:
        raise _err(str(exc)) from exc
    return Outcome(state, entries, logs)


def apply_geo_action(
    state: GameState,
    action: GeoAction,
    rng: RngFactory,
    balance: Balance,
    data: GameData,
    ledger_balances: LedgerBalances,
) -> Outcome:
    if isinstance(action, OpenOffice):
        return open_office(state, action, rng, balance, data)
    if isinstance(action, CloseOffice):
        return close_office(state, action, balance, data)
    if isinstance(action, MoveLawyer):
        return move_lawyer(state, action, balance, data)
    if isinstance(action, SeekAdmission):
        return seek_admission(state, action, balance, data)
    from ptk.sim.geo.uk import offer_training_contracts

    return offer_training_contracts(state, action, balance, data)
