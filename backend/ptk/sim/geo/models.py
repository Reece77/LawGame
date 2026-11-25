"""Frozen geography models: offices, admissions in progress, the UK path (PT-M11).

Ported from backend/tst/sim/geo/models.py @ 718997f0 (Tech Startup Tycoon); changed: an
office is a law firm's lease (term, rent per lawyer seat, fit-out, how it was opened); the home
city's office is implicit (office id 0, v1's rent per head) so a firm that never opens another
office plays exactly as before; TST's regional markets, marketing splits and product regions
have no counterpart (a city's market is its clients, `Client.city`). Partner Track's own
records: bar exams and motions in progress, admissions' history, pro hac vice grants, training
contracts and trainees' seats, and each city's demand last month.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

type OfficeStatus = Literal["open", "closed"]
type OpenHow = Literal["organic", "lateral_group", "team_lift", "merger"]  # PT-M13: assumed
type AdmissionHow = Literal["home", "exam", "motion", "qualified", "rfl", "hire"]
type ExamKind = Literal["exam", "motion"]

HOME_OFFICE_ID = 0  # the home city's office: implicit, v1's rent per head


@dataclass(frozen=True, slots=True)
class Office:
    """A leased office in a city other than the firm's home city (spec 8.8). A closed office
    keeps its row."""

    id: int
    firm_id: int
    city: str  # cities.yaml key
    seats: int  # lawyer seats the lease is sized for
    opened_turn: int
    how: OpenHow
    term_months: int
    rent_cents: int  # a month, full or not
    fit_out_cents: int  # once, to 1500, amortised over the term
    lease_start_turn: int  # the current term's first month (a renewal starts a new term)
    status: OfficeStatus = "open"
    closed_turn: int | None = None

    @property
    def is_open(self) -> bool:
        return self.status == "open"

    def lease_month(self, turn: int) -> int:
        """0-based month of the current term."""
        return turn - self.lease_start_turn


@dataclass(frozen=True, slots=True)
class Exam:
    """A bar exam or an application on motion in progress (spec 11.1)."""

    id: int
    person_id: int
    jurisdiction: str
    kind: ExamKind
    started_turn: int
    result_turn: int


@dataclass(frozen=True, slots=True)
class AdmissionRecord:
    """When and how a lawyer was admitted (the Person screen's admissions)."""

    person_id: int
    jurisdiction: str
    turn: int
    how: AdmissionHow


@dataclass(frozen=True, slots=True)
class ProHacVice:
    """A lead admitted for one case in a court of another jurisdiction (spec 11.1)."""

    matter_id: int
    person_id: int
    jurisdiction: str
    turn: int


@dataclass(frozen=True, slots=True)
class TrainingContract:
    """Training contracts offered two years ahead (spec 5.7): `count` trainees join the office
    in September of `start_year`."""

    id: int
    firm_id: int
    office_id: int
    offered_turn: int
    start_turn: int
    count: int
    filled: bool = False


@dataclass(frozen=True, slots=True)
class Trainee:
    """A trainee solicitor's two years of seats (spec 5.2): six-month seats rotating through
    practices; qualification (newly qualified, class 1) each September."""

    person_id: int
    office_id: int
    started_turn: int
    qualify_turn: int
    seats: tuple[str, ...]  # the practices of their seats, in order

    def seat(self, turn: int, months: int) -> str:
        i = min(max(0, (turn - self.started_turn) // months), len(self.seats) - 1)
        return self.seats[i]


@dataclass(frozen=True, slots=True)
class GeoState:
    offices: tuple[Office, ...] = ()  # sorted by id (ids from 1; 0 is the home office)
    exams: tuple[Exam, ...] = ()  # in progress, sorted by id
    admissions: tuple[AdmissionRecord, ...] = ()  # history, sorted by (person, turn, key)
    pro_hac_vice: tuple[ProHacVice, ...] = ()  # sorted by (matter, person)
    contracts: tuple[TrainingContract, ...] = ()  # sorted by id
    trainees: tuple[Trainee, ...] = ()  # in training, sorted by person id
    demand: tuple[tuple[str, tuple[int, ...]], ...] = ()  # city -> last month's demand
    search_cities: tuple[tuple[int, str], ...] = ()  # (search id, city) for local searches
    next_exam_id: int = 1
    next_contract_id: int = 1

    def office(self, office_id: int) -> Office | None:
        return next((o for o in self.offices if o.id == office_id), None)

    def firm_offices(self, firm_id: int) -> tuple[Office, ...]:
        return tuple(o for o in self.offices if o.firm_id == firm_id and o.is_open)

    def city_demand(self, city: str) -> tuple[int, ...] | None:
        return next((d for c, d in self.demand if c == city), None)

    def trainee(self, person_id: int) -> Trainee | None:
        return next((t for t in self.trainees if t.person_id == person_id), None)

    @property
    def next_office_id(self) -> int:
        return max((o.id for o in self.offices), default=HOME_OFFICE_ID) + 1


EMPTY_GEO = GeoState()


def with_office(geo: GeoState, office: Office) -> GeoState:
    rest = [o for o in geo.offices if o.id != office.id]
    return replace(geo, offices=tuple(sorted([*rest, office], key=lambda o: o.id)))


def with_admission(geo: GeoState, record: AdmissionRecord) -> GeoState:
    rows = sorted([*geo.admissions, record], key=lambda r: (r.person_id, r.turn, r.jurisdiction))
    return replace(geo, admissions=tuple(rows))
