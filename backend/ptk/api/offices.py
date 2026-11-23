"""Offices endpoints and schemas (PT-M11; spec 8.8, 11.1, 5.7; TST formulas.md 19.7).

The Offices screen reads one view: the cities a firm may open in (their local market's size,
rates, pay and rent, the rivals present), the firm's offices (the home office first) with their
lease, headcount, managing partner, local clients and P&L (last month and the trailing twelve
months, from the ledger's office dimension), the bar rules of each office's jurisdiction (the
SRA, compulsory insurance, client money and LLP status in London), admissions in progress and
the UK path's training contracts and trainees.

Everything here is the firm's own books or public rules. Never in a schema: a lifted partner's
hidden portability or a rival's decision weights. Every write is one player action in its own
transaction (ADR-0014) and returns the fresh view.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import func, select

from ptk import loader
from ptk.config import get_settings
from ptk.db import saves
from ptk.db.models import LedgerEntryRow, LedgerLineRow
from ptk.db.session import make_sessionmaker, shared_engine
from ptk.sim.calendar import format_turn
from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import NotFoundError
from ptk.sim.geo.actions import (
    CloseOffice,
    MoveLawyer,
    OfferTrainingContracts,
    OpenOffice,
    SeekAdmission,
)
from ptk.sim.geo.cities import person_office_id, rival_region
from ptk.sim.geo.models import HOME_OFFICE_ID
from ptk.sim.geo.offices import office_lawyers
from ptk.sim.state import GameState

WINDOW = 12  # tunable-exempt: the trailing months of the office P&L


class CityRivalOut(BaseModel):
    key: str
    name: str


class CityOut(BaseModel):
    key: str
    label: str
    region: str
    jurisdiction: str
    jurisdiction_label: str
    demand_pct: int  # the local market as % of the home market's
    rate_pct: int  # the local card as % of the firm's
    pay_pct: int
    rent_per_seat_cents: int
    rivals: list[CityRivalOut]  # the region's largest firms present there (a team to lift)
    has_office: bool
    is_home: bool


class PnlOut(BaseModel):
    month_fees_cents: int
    month_costs_cents: int
    month_profit_cents: int
    year_fees_cents: int  # the trailing twelve months
    year_costs_cents: int
    year_profit_cents: int


class OfficeOut(BaseModel):
    id: int
    city: str
    label: str
    how: str
    opened: str
    seats: int | None  # None: the home office (rent per head)
    lawyers: int
    staff: int
    rent_cents: int | None
    lease_months_left: int | None
    lease_liability_cents: int | None
    managing_partner: str | None
    clients: int  # the firm's clients whose work is this office's
    pnl: PnlOut


class RulesOut(BaseModel):
    jurisdiction: str
    label: str
    regulator: str
    insurance_min_cents: (
        int | None
    )  # compulsory cover a claim, a partnership (None: not compulsory)
    insurance_llp_min_cents: int | None  # ... an LLP or company
    client_money: str | None
    llp: bool
    foreign_lawyers: str | None
    ownership: str


class ContractOut(BaseModel):
    office_id: int
    offered: str
    starts: str
    count: int
    filled: bool


class TraineeOut(BaseModel):
    person_id: int
    name: str
    office_id: int
    seat: str
    seats: list[str]
    qualifies: str


class ExamOut(BaseModel):
    person_id: int
    name: str
    jurisdiction: str
    kind: str
    result: str


class LawyerOut(BaseModel):
    person_id: int
    name: str
    level: str
    office_id: int
    admissions: list[str]


class OfficesOut(BaseModel):
    cities: list[CityOut]
    offices: list[OfficeOut]
    rules: list[RulesOut]
    contracts: list[ContractOut]
    trainees: list[TraineeOut]
    exams: list[ExamOut]
    lawyers: list[LawyerOut]
    seat_sizes: list[int]
    lease_months: int
    fit_out_per_seat_cents: int
    lease_liabilities_cents: int


class OpenOfficeIn(BaseModel):
    city: str
    seats: int
    how: Literal["organic", "lateral_group", "team_lift"]
    practice: str | None = None
    partner_id: int | None = None
    rival_key: str | None = None
    partners: int = 1
    associates: int = 0


class ContractsIn(BaseModel):
    count: int


class AdmissionIn(BaseModel):
    person_id: int
    jurisdiction: str
    route: Literal["exam", "motion", "register"] = "exam"


class MoveIn(BaseModel):
    person_id: int
    office_id: int


def _name(state: GameState, pid: int) -> str:
    p = state.person(pid)
    return f"{p.first_name} {p.last_name}"


def _pnl(
    path: Path, firm_id: int, turn: int, data: GameData
) -> dict[int, tuple[int, int, int, int]]:
    """office id -> (month fees, month costs, year fees, year costs), from the saved ledger."""
    types = {a.code: a.type for a in data.accounts}
    pnl_accounts = [k for k, t in types.items() if t in ("income", "expense")]
    out: dict[int, list[int]] = {}
    with make_sessionmaker(shared_engine(path))() as session:
        rows = session.execute(
            select(
                LedgerEntryRow.turn,
                LedgerLineRow.office_id,
                LedgerLineRow.account,
                func.sum(LedgerLineRow.amount_cents),
            )
            .join(LedgerEntryRow, LedgerLineRow.entry_id == LedgerEntryRow.id)
            .where(
                LedgerEntryRow.firm_id == firm_id,
                LedgerEntryRow.turn >= turn - WINDOW,
                LedgerEntryRow.turn < turn,
                LedgerLineRow.account.in_(pnl_accounts),
            )
            .group_by(LedgerEntryRow.turn, LedgerLineRow.office_id, LedgerLineRow.account)
        )
        for t, office, account, total in rows:
            oid = int(office) if office is not None else HOME_OFFICE_ID
            acc = out.setdefault(oid, [0, 0, 0, 0])
            income = types[str(account)] == "income"
            amount = int(total)
            if income:
                acc[2] -= amount
                if t == turn - 1:
                    acc[0] -= amount
            else:
                acc[3] += amount
                if t == turn - 1:
                    acc[1] += amount
    return {k: (v[0], v[1], v[2], v[3]) for k, v in out.items()}


def _ownership(rules: Any, ym: tuple[int, int]) -> str:
    labels = {
        "lawyers_only": "lawyers only",
        "limited_non_lawyer": "lawyers, with limited non-lawyer partners",
        "abs": "alternative business structures licensed",
        "any_owner": "any owner",
    }
    current = "lawyers only"
    for o in rules.ownership:
        if tuple(o.from_ym) <= ym:
            current = labels[o.rule]
    return current


def offices_out(
    state: GameState,
    path: Path,
    balances: dict[tuple[int, str], int],
    data: GameData,
    balance: Balance,
) -> OfficesOut:
    from ptk.sim.calendar import turn_to_ym
    from ptk.sim.org.seats import holder_of

    firm = state.player
    fid = firm.id
    ym = turn_to_ym(state.turn, state.save_meta.start_ym)
    labels = {j.key: j.label for j in data.jurisdictions}
    open_cities = {o.city for o in state.geo.firm_offices(fid)}
    cities = []
    for c in data.geo.cities:
        present = sorted(
            (
                f
                for f in state.rivals.active
                if f.kind == "real" and rival_region(data, f.hq) == c.region
            ),
            key=lambda f: (-f.revenue_12m, f.id),
        )
        if c.region == "us":
            present = [
                f
                for f in present
                if data.geo.city_key(f.hq) == c.key or (f.ny_office and c.key == "new_york")
            ]
        cities.append(
            CityOut(
                key=c.key,
                label=c.label,
                region=c.region,
                jurisdiction=c.jurisdiction,
                jurisdiction_label=labels.get(c.jurisdiction, c.jurisdiction),
                demand_pct=round(c.demand * 100),
                rate_pct=round(c.rate_bp / 100),
                pay_pct=round(c.pay_bp / 100),
                rent_per_seat_cents=c.rent_per_seat_cents,
                rivals=[CityRivalOut(key=f.key, name=f.short) for f in present[:8]],
                has_office=c.key in open_cities,
                is_home=c.key == firm.home_city,
            )
        )
    pnl = _pnl(path, fid, state.turn, data)
    staff = [state.person(pid) for pid in state.staff_ids(fid)]
    city_label = {c.key: c.label for c in data.geo.cities}

    def office_row(oid: int) -> OfficeOut:
        o = state.geo.office(oid) if oid else None
        city = o.city if o is not None else firm.home_city
        mp = (
            holder_of(state, fid, "office_managing_partner", oid)
            if state.geo.firm_offices(fid)
            else None
        )
        people = [p for p in staff if person_office_id(state, fid, p) == oid]
        clients = sum(
            1
            for r in state.market.relationships
            if r.firm_id == fid
            and (
                (state.market.client(r.client_id).city == city)
                if oid
                else not state.market.client(r.client_id).city
            )
        )
        mf, mc, yf, yc = pnl.get(oid, (0, 0, 0, 0))
        left = None
        liability = None
        if o is not None:
            left = max(0, o.term_months - o.lease_month(state.turn))
            liability = left * o.rent_cents
        return OfficeOut(
            id=oid,
            city=city,
            label=city_label.get(city, city.replace("_", " ").title()),
            how=o.how if o is not None else "home",
            opened=format_turn(o.opened_turn, state.save_meta.start_ym)
            if o is not None
            else "founded",
            seats=o.seats if o is not None else None,
            lawyers=office_lawyers(state, fid, oid, data),
            staff=len(people),
            rent_cents=o.rent_cents if o is not None else None,
            lease_months_left=left,
            lease_liability_cents=liability,
            managing_partner=_name(state, mp) if mp is not None else None,
            clients=clients,
            pnl=PnlOut(
                month_fees_cents=mf,
                month_costs_cents=mc,
                month_profit_cents=mf - mc,
                year_fees_cents=yf,
                year_costs_cents=yc,
                year_profit_cents=yf - yc,
            ),
        )

    offices = [office_row(HOME_OFFICE_ID), *(office_row(o.id) for o in state.geo.firm_offices(fid))]
    juris = []
    seen: set[str] = set()
    for o in offices:
        cdef = data.geo.city(o.city) if data.geo.has_city(o.city) else None
        j = cdef.jurisdiction if cdef is not None else None
        rules = data.geo.rules(j) if j else None
        if rules is None or j in seen:
            continue
        seen.add(rules.key)
        ins = rules.insurance
        juris.append(
            RulesOut(
                jurisdiction=rules.key,
                label=rules.label,
                regulator=rules.regulator,
                insurance_min_cents=ins.min_cover_cents if ins.compulsory else None,
                insurance_llp_min_cents=ins.llp_min_cover_cents if ins.compulsory else None,
                client_money=rules.client_money or None,
                llp=rules.llp,
                foreign_lawyers=rules.foreign_lawyers or None,
                ownership=_ownership(rules, ym),
            )
        )
    start = state.save_meta.start_ym
    trainees = [
        TraineeOut(
            person_id=t.person_id,
            name=_name(state, t.person_id),
            office_id=t.office_id,
            seat=data.practice(t.seat(state.turn, balance.geo.trainee_seat_months)).label,
            seats=[data.practice(s).label for s in t.seats],
            qualifies=format_turn(t.qualify_turn, start),
        )
        for t in state.geo.trainees
        if state.employment_of(t.person_id) is not None
    ]
    exams = [
        ExamOut(
            person_id=e.person_id,
            name=_name(state, e.person_id),
            jurisdiction=labels.get(e.jurisdiction, e.jurisdiction),
            kind=e.kind,
            result=format_turn(e.result_turn, start),
        )
        for e in state.geo.exams
    ]
    lawyers = [
        LawyerOut(
            person_id=p.id,
            name=f"{p.first_name} {p.last_name}",
            level=p.level.replace("_", " "),
            office_id=person_office_id(state, fid, p),
            admissions=[labels.get(b, b) for b in p.bar_admissions],
        )
        for p in staff
        if data.role(p.role).kind == "lawyer"
    ]
    return OfficesOut(
        cities=cities,
        offices=offices,
        rules=juris,
        contracts=[
            ContractOut(
                office_id=c.office_id,
                offered=format_turn(c.offered_turn, start),
                starts=format_turn(c.start_turn, start),
                count=c.count,
                filled=c.filled,
            )
            for c in state.geo.contracts
            if c.firm_id == fid
        ],
        trainees=trainees,
        exams=exams,
        lawyers=lawyers,
        seat_sizes=list(balance.geo.seat_sizes),
        lease_months=balance.geo.lease_months,
        fit_out_per_seat_cents=balance.geo.fit_out_per_seat_cents,
        lease_liabilities_cents=-balances.get((fid, "2500_leases"), 0),
    )


def _path(slug: str) -> Path:
    return saves.open_save(get_settings().resolved_save_dir(), slug)


def _act(slug: str, make: Any) -> Path:
    path = _path(slug)
    state = saves.read_state(path)[0]
    actor = state.founder_of(state.player.id)
    if actor is None:
        raise NotFoundError("the firm has no player partner")
    saves.run_action(path, make(actor), loader.balance(), loader.game_data())
    return path


def _view(path: Path) -> OfficesOut:
    state, balances = saves.read_state(path)
    return offices_out(state, path, balances, loader.game_data(), loader.balance())


def make_offices_router(errors: dict[int | str, dict[str, Any]]) -> APIRouter:
    router = APIRouter()
    kw: dict[str, Any] = {"response_model": OfficesOut, "responses": errors}

    @router.get("/api/saves/{slug}/offices", operation_id="getOffices", **kw)
    def get_offices(slug: str) -> OfficesOut:
        return _view(_path(slug))

    @router.post("/api/saves/{slug}/offices", operation_id="openOffice", **kw)
    def open_office(slug: str, body: OpenOfficeIn) -> OfficesOut:
        return _view(
            _act(
                slug,
                lambda a: OpenOffice(
                    actor_id=a,
                    city=body.city,
                    seats=body.seats,
                    how=body.how,
                    practice=body.practice,
                    partner_id=body.partner_id,
                    rival_key=body.rival_key,
                    partners=body.partners,
                    associates=body.associates,
                ),
            )
        )

    @router.post("/api/saves/{slug}/offices/{office_id}/close", operation_id="closeOffice", **kw)
    def close_office(slug: str, office_id: int) -> OfficesOut:
        return _view(_act(slug, lambda a: CloseOffice(actor_id=a, office_id=office_id)))

    @router.post(
        "/api/saves/{slug}/offices/{office_id}/training-contracts",
        operation_id="offerTrainingContracts",
        **kw,
    )
    def contracts(slug: str, office_id: int, body: ContractsIn) -> OfficesOut:
        return _view(
            _act(
                slug,
                lambda a: OfferTrainingContracts(actor_id=a, office_id=office_id, count=body.count),
            )
        )

    @router.post("/api/saves/{slug}/offices/admissions", operation_id="seekAdmission", **kw)
    def admission(slug: str, body: AdmissionIn) -> OfficesOut:
        return _view(
            _act(
                slug,
                lambda a: SeekAdmission(
                    actor_id=a,
                    person_id=body.person_id,
                    jurisdiction=body.jurisdiction,
                    route=body.route,
                ),
            )
        )

    @router.post("/api/saves/{slug}/offices/move", operation_id="moveLawyer", **kw)
    def move(slug: str, body: MoveIn) -> OfficesOut:
        return _view(
            _act(
                slug,
                lambda a: MoveLawyer(
                    actor_id=a, person_id=body.person_id, office_id=body.office_id
                ),
            )
        )

    return router
