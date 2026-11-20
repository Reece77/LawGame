"""Read views for the Matters, Clients and Practices screens (PT-M3c; ADR-0009).

Views only: nothing here changes the game. The staffing board (who has free capacity and
familiarity for a matter, with strain warnings and the matter's events), the Practices screen
(demand trend, our revenue and share, capacity, utilisation, leverage, rates against the rate
card) and Explain (utilisation, realisation, matter margin and a matter's outlook as a band).

Hidden values (CLAUDE.md section 10): a matter's outlook is built from what the firm *sees*:
the team's revealed skill and familiarity ranges against an average opposing counsel with
neutral merits. Merits, opposing counsel's quality, hidden traits and the true chance never
enter a view; `tests/integration/test_screens_api.py` enumerates every schema here for them.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, Final, Literal

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from ptk import loader
from ptk.config import get_settings
from ptk.db import saves
from ptk.db.models import InboxItemRow
from ptk.db.session import make_sessionmaker, shared_engine
from ptk.sim.calendar import format_turn
from ptk.sim.data_models import PARTNER_LEVELS, Balance, GameData
from ptk.sim.errors import NotFoundError
from ptk.sim.matters import formulas as fx
from ptk.sim.matters.market import monthly_demand
from ptk.sim.matters.models import Matter
from ptk.sim.matters.staffing import fee_earners, planned_load
from ptk.sim.people.formulas import fam_factor
from ptk.sim.people.models import Person, fam_key
from ptk.sim.people.reveal import revealed_range
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState

TENTHS: Final = fx.TENTHS
TREND_MONTHS: Final = 12  # tunable-exempt: the Practices screen's demand trend, months
STRAIN_WARN: Final = 60.0  # tunable-exempt: the strain bar's warning band (lib/attr.ts strainBand)
# The outlook bands (a matter's chance of winning or closing, never the number): upper bounds
# on the chance, as the team sees it. tunable-exempt: display bands, not game rules.
OUTLOOK_BANDS: Final = (
    (0.30, "Uphill"),
    (0.45, "Leaning against"),
    (0.55, "Even"),
    (0.70, "Leaning our way"),
    (1.01, "Strong"),
)

type Unit = Literal["cents", "hours", "percent", "ratio", "text", "range"]
type Metric = Literal["utilisation", "realisation", "matter_margin", "outlook"]


class RefOut(BaseModel):
    id: int
    name: str


class RangeOut(BaseModel):
    lo: int
    hi: int


class MatterEventOut(BaseModel):
    id: int
    date_label: str
    title: str
    body: str


class BoardPersonOut(BaseModel):
    """One fee earner on the staffing board, as the firm sees them."""

    person: RefOut
    level: str
    role_label: str
    home_practice: str
    familiarity: RangeOut  # revealed, in the matter's practice
    capacity_hours: float  # this month
    planned_hours: float  # on all the firm's named matters
    free_hours: float  # named hours the engine would still accept (max load less planned)
    hours_last_month: float  # all work, named and flow
    strain: float
    burnt_out: bool
    on_team: bool
    planned_here: float  # planned hours on this matter
    warnings: list[str]


class StaffingBoardOut(BaseModel):
    matter_id: int
    practice: str
    practice_label: str
    people: list[BoardPersonOut]  # on the team first, then by free hours
    events: list[MatterEventOut]  # inbox items about the matter, newest first


class TrendPointOut(BaseModel):
    date_label: str
    cents: int


class PracticeRateOut(BaseModel):
    band: str
    card_cents: int  # the rate card, an hour
    ours_cents: int | None  # the firm's standard value an hour last month in the band


class PracticeScreenOut(BaseModel):
    key: str
    label: str
    short_label: str
    demand_trend: list[TrendPointOut]  # the New York market, oldest first
    demand_cents: int  # last month
    revenue_cents: int  # our standard value of work last month
    share_bp: int  # our revenue / the market's demand, last month
    lawyers: int  # fee earners whose home practice it is
    partners: int
    capacity_hours: float  # their monthly capacity
    hours_last_month: float  # hours worked in the practice (anyone's)
    utilisation_bp: int | None  # home people's hours / their capacity
    leverage: float | None  # non-partner fee earners per partner
    leverage_norm: float
    rates: list[PracticeRateOut]


class ExplainItemOut(BaseModel):
    label: str
    amount: float | None  # in `unit`; None when the item is text
    unit: Unit
    text: str | None = None
    range: RangeOut | None = None  # unit "range": a revealed range, 1-20


class ExplainOut(BaseModel):
    metric: Metric
    label: str
    subject: str
    value: float | None
    unit: Unit
    band: str | None  # a matter's outlook (never its number)
    items: list[ExplainItemOut]
    note: str


# --- Helpers ---------------------------------------------------------------------------------


def _name(person: Person) -> str:
    return f"{person.first_name} {person.last_name}"


def _seen(state: GameState, person: Person, key: str) -> tuple[int, int]:
    reveal = state.reveal(state.player.id, person.id)
    if reveal is None:
        return (1, 20)
    return revealed_range(person, reveal, key)


def _own_matter(state: GameState, matter_id: int) -> Matter:
    m = state.market.matter(matter_id)
    if m is None or m.firm_id != state.player.id:
        raise NotFoundError(f"no matter {matter_id}")
    return m


def _hours_by_person(state: GameState) -> dict[int, int]:
    out: dict[int, int] = {}
    for h in state.market.hours:
        out[h.person_id] = out.get(h.person_id, 0) + h.tenths
    return out


def matter_events(path: Path, state: GameState, matter_id: int) -> list[MatterEventOut]:
    with make_sessionmaker(shared_engine(path))() as session:
        rows = session.scalars(
            select(InboxItemRow)
            .where(
                InboxItemRow.firm_id == state.player.id,
                InboxItemRow.link_kind == "matter",
                InboxItemRow.link_id == matter_id,
            )
            .order_by(InboxItemRow.id.desc())
        )
        return [
            MatterEventOut(
                id=r.id,
                date_label=format_turn(r.turn, state.save_meta.start_ym),
                title=r.title,
                body=r.body,
            )
            for r in rows
        ]


# --- Staffing board --------------------------------------------------------------------------


def staffing_board(
    state: GameState,
    matter_id: int,
    data: GameData,
    balance: Balance,
    events: list[MatterEventOut] | None = None,
) -> StaffingBoardOut:
    m = _own_matter(state, matter_id)
    firm = state.player.id
    load = planned_load(state.market, firm)
    worked = _hours_by_person(state)
    people = []
    for e in fee_earners(state, firm, data, balance):
        p = e.person
        limit = int(balance.matters.max_load * e.capacity) - e.other
        planned = load.get(p.id, 0)
        member = m.member(p.id)
        warnings = []
        if p.burnt_out:
            warnings.append("Burnt out: capacity and output are down")
        elif p.strain >= STRAIN_WARN:
            warnings.append("High strain: more hours risk burnout")
        if planned + e.other > e.capacity:
            warnings.append("Planned beyond capacity: overtime")
        lo, hi = _seen(state, p, fam_key(m.practice))
        people.append(
            BoardPersonOut(
                person=RefOut(id=p.id, name=_name(p)),
                level=p.level,
                role_label=data.role(p.role).label,
                home_practice=e.home,
                familiarity=RangeOut(lo=lo, hi=hi),
                capacity_hours=e.capacity / TENTHS,
                planned_hours=planned / TENTHS,
                free_hours=max(0, limit - planned) // TENTHS,
                hours_last_month=worked.get(p.id, 0) / TENTHS,
                strain=round(p.strain, 1),
                burnt_out=p.burnt_out,
                on_team=member is not None,
                planned_here=(member.planned_tenths / TENTHS) if member else 0.0,
                warnings=warnings,
            )
        )
    people.sort(key=lambda b: (not b.on_team, -b.free_hours, b.person.id))
    return StaffingBoardOut(
        matter_id=m.id,
        practice=m.practice,
        practice_label=data.practice(m.practice).label,
        people=people,
        events=events or [],
    )


# --- Practices screen ------------------------------------------------------------------------


def demand_trend(state: GameState, data: GameData) -> list[tuple[int, tuple[int, ...]]]:
    """The market's demand in the months played (up to TREND_MONTHS), oldest first: the same
    seeded draws the turn made, recomputed (a pure function of the seed and the month)."""
    rng = RngFactory(state.save_meta.master_seed)
    first = max(0, state.turn - TREND_MONTHS)
    return [(t, monthly_demand(rng, t, state, data)) for t in range(first, state.turn)]


def practices_screen(state: GameState, data: GameData, balance: Balance) -> list[PracticeScreenOut]:
    firm = state.player.id
    start = state.save_meta.start_ym
    trend = demand_trend(state, data)
    last = trend[-1][1] if trend else tuple(0 for _ in data.practices)
    earners = fee_earners(state, firm, data, balance)
    worked = _hours_by_person(state)
    out = []
    for i, p in enumerate(data.practices):
        home = [e for e in earners if e.home == p.key]
        partners = sum(1 for e in home if e.person.level in PARTNER_LEVELS)
        lawyers = [e for e in home if data.role(e.person.role).kind == "lawyer"]
        capacity = sum(e.capacity for e in home)
        home_hours = sum(worked.get(e.id, 0) for e in home)
        records = [h for h in state.market.hours if h.practice == p.key]
        revenue = sum(h.value_cents for h in records)
        rates = []
        for band, card in p.rates.items():
            tenths = value = 0
            for h in records:
                person = state.person(h.person_id)
                if fx.rate_band(person.level, data) == band:
                    tenths += h.tenths
                    value += h.value_cents
            rates.append(
                PracticeRateOut(
                    band=band,
                    card_cents=card,
                    ours_cents=round(value * TENTHS / tenths) if tenths else None,
                )
            )
        out.append(
            PracticeScreenOut(
                key=p.key,
                label=p.label,
                short_label=p.short_label,
                demand_trend=[
                    TrendPointOut(date_label=format_turn(t, start), cents=d[i]) for t, d in trend
                ],
                demand_cents=last[i],
                revenue_cents=revenue,
                share_bp=round(10000 * revenue / last[i]) if last[i] else 0,
                lawyers=len(lawyers),
                partners=partners,
                capacity_hours=capacity / TENTHS,
                hours_last_month=sum(h.tenths for h in records) / TENTHS,
                utilisation_bp=round(10000 * home_hours / capacity) if capacity else None,
                leverage=round((len(home) - partners) / partners, 2) if partners else None,
                leverage_norm=p.leverage,
                rates=rates,
            )
        )
    return out


# --- Explain ---------------------------------------------------------------------------------


def _item(label: str, amount: float | None, unit: Unit, text: str | None = None) -> ExplainItemOut:
    return ExplainItemOut(label=label, amount=amount, unit=unit, text=text)


def _explain_utilisation(
    state: GameState, entity: str | None, data: GameData, balance: Balance
) -> ExplainOut:
    firm = state.player.id
    earners = fee_earners(state, firm, data, balance)
    worked = _hours_by_person(state)
    if entity is None or entity == "firm":
        group, subject = list(earners), "the firm"
    elif entity.startswith("practice:"):
        key = entity.removeprefix("practice:")
        group, subject = [e for e in earners if e.home == key], data.practice(key).label
    else:
        if not entity.isdigit():
            raise NotFoundError(f"no person {entity}")
        pid = int(entity)
        group = [e for e in earners if e.id == pid]
        if not group:
            raise NotFoundError(f"person {entity} is not a fee earner at the firm")
        subject = _name(group[0].person)
    capacity = sum(e.capacity for e in group)
    hours = sum(worked.get(e.id, 0) for e in group)
    named = sum(
        h.tenths
        for h in state.market.hours
        if h.matter_id is not None and h.person_id in {e.id for e in group}
    )
    return ExplainOut(
        metric="utilisation",
        label="Utilisation",
        subject=subject,
        value=round(100 * hours / capacity, 1) if capacity else None,
        unit="percent",
        band=None,
        items=[
            _item("Hours on named matters", named / TENTHS, "hours"),
            _item("Hours on flow work", (hours - named) / TENTHS, "hours"),
            _item("Capacity this month", capacity / TENTHS, "hours"),
        ],
        note="Utilisation is hours worked last month over capacity (spec 8.2). Partners keep "
        f"{balance.matters.partner_other_hours} hours a month for business development and "
        "management.",
    )


def _explain_realisation(state: GameState, m: Matter) -> ExplainOut:
    return ExplainOut(
        metric="realisation",
        label="Realisation",
        subject=m.name,
        value=None,
        unit="percent",
        band=None,
        items=[_item("Work in progress at standard rates", m.wip_cents, "cents")],
        note="Realisation is billed value over standard value (spec 8.2); no bill yet.",
    )


def _explain_margin(state: GameState, m: Matter, data: GameData, balance: Balance) -> ExplainOut:
    records = [h for h in state.market.hours if h.matter_id == m.id]
    value = sum(h.value_cents for h in records)
    cost = 0
    for h in records:
        person = state.person(h.person_id)
        emp = state.employment_of(person.id)
        salary = emp.salary_cents if emp is not None else 0
        capacity = balance.people.levels[person.level].capacity_hours
        cost += salary * h.tenths // (capacity * TENTHS) if capacity else 0
    return ExplainOut(
        metric="matter_margin",
        label="Matter margin",
        subject=m.name,
        value=round(100 * (value - cost) / value, 1) if value else None,
        unit="percent",
        band=None,
        items=[
            _item("Standard value of last month's hours", value, "cents"),
            _item("Salary cost of those hours", -cost, "cents"),
            _item("Margin", value - cost, "cents"),
        ],
        note="Last month's work at standard rates less the team's salary cost per hour of "
        "capacity. Founding partners draw no salary; overheads are not allocated.",
    )


def _team_craft(
    state: GameState, m: Matter, weights: Mapping[str, float], balance: Balance
) -> tuple[float, float] | None:
    """The team's craft as the firm sees it (revealed ranges), weighted by planned hours."""
    total = sum(t.planned_tenths for t in m.team)
    if total == 0:
        return None
    lo = hi = 0.0
    for t in m.team:
        person = state.person(t.person_id)
        f_lo, f_hi = _seen(state, person, fam_key(m.practice))
        s_lo = sum(w * _seen(state, person, k)[0] for k, w in weights.items())
        s_hi = sum(w * _seen(state, person, k)[1] for k, w in weights.items())
        share = t.planned_tenths / total
        lo += share * s_lo * fam_factor(f_lo, balance.familiarity)
        hi += share * s_hi * fam_factor(f_hi, balance.familiarity)
    return lo, hi


def outlook_band(chance: float) -> str:
    return next(label for top, label in OUTLOOK_BANDS if chance < top)


def _explain_outlook(state: GameState, m: Matter, data: GameData, balance: Balance) -> ExplainOut:
    kind = data.market.kinds[m.kind]
    out = balance.outcomes
    case = kind.outcome == "case"
    weights = out.craft_skills if case else out.deal_skills if kind.outcome == "deal" else None
    label = "Chance of winning" if case else "Chance of closing"
    if weights is None:
        return ExplainOut(
            metric="outlook",
            label="Outlook",
            subject=m.name,
            value=None,
            unit="text",
            band=None,
            items=[],
            note="Advice and filings have no win or lose: the client judges the quality.",
        )
    craft = _team_craft(state, m, weights, balance)
    items = []
    band = None
    if craft is not None:
        lo, hi = craft
        mid = (lo + hi) / 2
        if case:
            chance = fx.sigmoid(out.case_k * (mid - out.opposing_mean))
        else:
            chance = fx.p_close(mid, m.critical, out)
        band = outlook_band(chance)
        items.append(
            ExplainItemOut(
                label="Team craft, as you see it",
                amount=None,
                unit="range",
                range=RangeOut(lo=round(lo), hi=round(hi)),
            )
        )
    else:
        items.append(_item("Team craft", None, "text", "Nobody is staffed yet"))
    if case:
        items += [
            _item("Opposing counsel", None, "text", "Unknown: taken as a typical large firm"),
            _item("Merits", None, "text", "Not assessed: taken as even"),
            _item("Judge", None, "text", "A judge never favours a side"),
        ]
    else:
        items.append(
            _item("Contested deal", None, "text", "Yes: harder to close" if m.critical else "No")
        )
    return ExplainOut(
        metric="outlook",
        label=label,
        subject=m.name,
        value=None,
        unit="text",
        band=band,
        items=items,
        note="A band from the team's revealed skills and familiarity, never the number. "
        "Better scouting narrows the ranges; preparation and the lead at trial still count.",
    )


def explain(
    state: GameState, metric: Metric, entity: str | None, data: GameData, balance: Balance
) -> ExplainOut:
    entity = entity or None
    if metric == "utilisation":
        return _explain_utilisation(state, entity, data, balance)
    if entity is None or not entity.isdigit():
        raise NotFoundError(f"{metric} needs a matter id")
    m = _own_matter(state, int(entity))
    if metric == "realisation":
        return _explain_realisation(state, m)
    if metric == "matter_margin":
        return _explain_margin(state, m, data, balance)
    return _explain_outlook(state, m, data, balance)


# --- Router ----------------------------------------------------------------------------------


def _path(slug: str) -> Path:
    return saves.open_save(get_settings().resolved_save_dir(), slug)


def make_screens_router(errors: dict[int | str, dict[str, Any]]) -> APIRouter:
    router = APIRouter()
    base = "/api/saves/{slug}"

    @router.get(
        f"{base}/matters/{{matter_id}}/board",
        response_model=StaffingBoardOut,
        responses=errors,
        operation_id="getStaffingBoard",
    )
    def get_board(slug: str, matter_id: int) -> StaffingBoardOut:
        path = _path(slug)
        state = saves.read_state(path)[0]
        events = matter_events(path, state, matter_id)
        return staffing_board(state, matter_id, loader.game_data(), loader.balance(), events)

    @router.get(
        f"{base}/practices/screen",
        response_model=list[PracticeScreenOut],
        responses=errors,
        operation_id="listPracticesScreen",
    )
    def list_practices_screen(slug: str) -> list[PracticeScreenOut]:
        state = saves.read_state(_path(slug))[0]
        return practices_screen(state, loader.game_data(), loader.balance())

    @router.get(
        f"{base}/explain/{{metric}}",
        response_model=ExplainOut,
        responses=errors,
        operation_id="explain",
    )
    def get_explain(slug: str, metric: Metric, entity: str | None = None) -> ExplainOut:
        state = saves.read_state(_path(slug))[0]
        return explain(state, metric, entity, loader.game_data(), loader.balance())

    return router
