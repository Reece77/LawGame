"""Where people work, where clients' work is and which office a matter belongs to (PT-M11).

Ported from backend/tst/sim/geo/cities.py @ 718997f0 (Tech Startup Tycoon); changed: a person
works in the firm's office in their city (`Person.city`), else in the home office; there are no
units with offices, remote policies or flexible space (TST 19.2); a client's work is in its city
(`Client.city`, "" for the home market) and a matter belongs to the firm's office there; rivals
are present in their headquarters' region (a UK rival competes in London, a US rival in the US).

The home office is implicit (`HOME_OFFICE_ID`), so a firm with no other office plays as v1.
"""

from __future__ import annotations

from ptk.sim.data_models import GameData
from ptk.sim.geo.data import CityDef, Region
from ptk.sim.geo.models import HOME_OFFICE_ID, Office
from ptk.sim.matters.models import Client, Matter
from ptk.sim.people.models import Person
from ptk.sim.state import GameState

US: Region = "us"


def offices(state: GameState, firm_id: int) -> tuple[Office, ...]:
    """The firm's open offices beyond its home city, by id."""
    return state.geo.firm_offices(firm_id)


def has_offices(state: GameState, firm_id: int) -> bool:
    return bool(state.geo.firm_offices(firm_id))


def office_in(state: GameState, firm_id: int, city: str) -> Office | None:
    """The firm's open office in a city (None in its home city, whose office is implicit)."""
    return next((o for o in state.geo.firm_offices(firm_id) if o.city == city), None)


def home_city(state: GameState, firm_id: int) -> str:
    return state.firm(firm_id).home_city


def office_city(state: GameState, firm_id: int, office_id: int) -> str:
    if office_id == HOME_OFFICE_ID:
        return home_city(state, firm_id)
    office = state.geo.office(office_id)
    return office.city if office is not None else home_city(state, firm_id)


def person_office_id(state: GameState, firm_id: int, person: Person) -> int:
    """The office someone works in: the firm's open office in their city, else the home office."""
    if not state.geo.offices:
        return HOME_OFFICE_ID
    office = office_in(state, firm_id, person.city)
    return office.id if office is not None else HOME_OFFICE_ID


def work_city(state: GameState, firm_id: int, person: Person) -> str:
    return office_city(state, firm_id, person_office_id(state, firm_id, person))


def client_city(state: GameState, firm_id: int, client: Client) -> str:
    """Where a client's work is: its city, or the home market's ("")."""
    return client.city or home_city(state, firm_id)


def client_office_id(state: GameState, firm_id: int, client: Client) -> int:
    """The office a client's work belongs to: the firm's office in the client's city, else home."""
    if not client.city or not state.geo.offices:
        return HOME_OFFICE_ID
    office = office_in(state, firm_id, client.city)
    return office.id if office is not None else HOME_OFFICE_ID


def matter_office_id(state: GameState, matter: Matter) -> int:
    return client_office_id(state, matter.firm_id, state.market.client(matter.client_id))


def city_def(data: GameData, city: str) -> CityDef | None:
    return data.geo.city(city) if data.geo.has_city(city) else None


def office_jurisdiction(state: GameState, firm_id: int, office_id: int, data: GameData) -> str:
    """The jurisdiction where a lawyer must be admitted to lead the office's matters: the
    city's (cities.yaml), or the scenario's home jurisdiction for the home office."""
    city = city_def(data, office_city(state, firm_id, office_id))
    if office_id != HOME_OFFICE_ID and city is not None:
        return city.jurisdiction
    scenario = data.scenario(state.save_meta.scenario_id)
    return scenario.home_jurisdiction if scenario is not None else data.jurisdictions[0].key


def region_of_city(data: GameData, city: str) -> Region:
    c = city_def(data, city)
    return c.region if c is not None else US


def rival_region(data: GameData, hq: str) -> Region:
    """A rival's region from its headquarters (firms.yaml `hq`, aliases included)."""
    return region_of_city(data, hq)


def player_regions(state: GameState, data: GameData) -> frozenset[Region]:
    """Regions where the player's firm practises: its home city's and its offices'."""
    firm = state.player
    out = {region_of_city(data, firm.home_city)}
    out.update(region_of_city(data, o.city) for o in state.geo.firm_offices(firm.id))
    return frozenset(out)


def person_region(state: GameState, firm_id: int, person: Person, data: GameData) -> Region:
    return region_of_city(data, work_city(state, firm_id, person))
