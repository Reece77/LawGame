"""Practices, clients and matters endpoints (PT-M3a; ADR-0009, ADR-0014).

What the player's firm sees: demand and rate cards; its clients with their relationship,
relationship partner, practices, fees and a wallet *estimate* (a range); its named matters
with team, phases, hours and WIP at standard value. Never a matter's merits or win chance,
opposing counsel's quality, a judge's traits, a general counsel's personality or an error
that has not come to light (CLAUDE.md section 10; tests/integration/test_matters_api.py
enumerates every schema here for them). Every write is one action in its own transaction
(`saves.run_action`) and returns the fresh view.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ptk import loader
from ptk.api.tech import matter_ai_fields
from ptk.config import get_settings
from ptk.db import saves
from ptk.sim.calendar import format_turn, turn_to_ym
from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import NotFoundError
from ptk.sim.macro_seed import world_data
from ptk.sim.matters.actions import (
    AssessCase,
    AssignToMatter,
    ChooseForum,
    DefaultStaffing,
    Introduce,
    MatterAction,
    RemoveFromMatter,
    RespondSettlement,
    SeekWaiver,
    SetConflictChecks,
    SetHoursPolicy,
    SetMatterHours,
    SetMatterLead,
    SetProBonoCredit,
    SetRatePolicy,
)
from ptk.sim.matters.assessment import merits_words
from ptk.sim.matters.formulas import TENTHS
from ptk.sim.matters.intake import key_clients
from ptk.sim.matters.market import base_monthly_demand, wallets
from ptk.sim.matters.models import Client, Matter, Relationship
from ptk.sim.matters.rates import market_index, market_rise_bp
from ptk.sim.matters.staffing import completed_share, credit_hours, home_practice
from ptk.sim.rivals.views import name_for_key, opposing_counsel
from ptk.sim.state import GameState

type MatterStatusOut = Literal["open", "conflicted", "closed", "declined"]
WALLET_BAND = (0.75, 1.25)  # tunable-exempt: the firm's wallet estimate, a +/-25% range
WALLET_ROUND_CENTS = 10_000_000  # tunable-exempt: estimates in $100,000 steps
MONTHS = 12  # tunable-exempt


class RefOut(BaseModel):
    id: int
    name: str


class RateOut(BaseModel):
    band: str
    cents: int  # an hour


class PracticeMarketOut(BaseModel):
    key: str
    label: str
    short_label: str
    driver: str
    demand_cents: int  # the New York market's demand last month, standard value
    demand_base_cents: int  # the month's base before season and noise (D0 / 12)
    rates: list[RateOut]
    leverage_norm: float
    margin_norm_bp: int
    clients: int  # clients instructing the firm in the practice
    people: int  # fee earners whose home practice it is
    hours_last_month: float
    value_last_month_cents: int


class RangeCentsOut(BaseModel):
    lo: int
    hi: int


class RangeBpOut(BaseModel):
    lo: int
    hi: int


type PanelStatusOut = Literal["key", "active", "dormant"]
type RiskOut = Literal["low", "medium", "high"]


class ClientRowOut(BaseModel):
    id: int
    name: str
    sector: str
    real: bool
    size_class: Literal["large", "mid"]
    relationship: int  # 0-100, the firm's own relationship
    partner: RefOut | None
    practices: list[str]
    fees_12m_cents: int
    key_client: bool
    open_matters: int
    wallet_estimate: RangeCentsOut  # a year, all practices: an estimate, never the true wallet
    share_estimate: RangeBpOut  # our 12-month fees over the wallet estimate (PT-M3c)
    panel_status: PanelStatusOut  # key client, instructed in the last year, or dormant (PT-M3c)


class GeneralCounselOut(BaseModel):
    name: str
    age: int


class CrossSellOut(BaseModel):
    practice: str
    label: str
    affinity: Literal["high", "medium", "low"]
    colleagues: list[RefOut]  # who could be introduced (home practice)


class ClientOut(ClientRowOut):
    general_counsel: GeneralCounselOut
    panel: list[str]  # the other panel firms' names
    advance_waiver: bool
    cross_sell: list[CrossSellOut]
    matters: list[MatterRowOut]


class SettlementOut(BaseModel):
    offer_cents: int
    expires_label: str


class MatterRowOut(BaseModel):
    id: int
    name: str
    client: RefOut
    practice: str
    kind: str
    kind_label: str
    status: MatterStatusOut
    outcome: str | None
    lead: RefOut | None
    phase: str | None
    progress_pct: int  # 0-100 of the work done
    opened_label: str
    due_label: str
    overdue: bool
    budget_hours: float
    worked_hours: float
    hours_last_month: float
    expected_fees_cents: int
    wip_cents: int  # standard value of hours worked (billed from PT-M3b)
    critical: bool
    adverse: str
    court: str | None
    judge: str | None
    errors_caught: int  # errors the team caught (escaped ones surface later)
    missed_deadlines: int
    settlement: SettlementOut | None
    risk: RiskOut  # from what the firm sees: pace, budget, deadlines (PT-M3c)
    risk_notes: list[str]
    pro_bono: bool = False  # PT-M7a: work for the pro bono client, no fees (spec 7.8)


class TeamMemberOut(BaseModel):
    person: RefOut
    role: str
    level: str
    planned_hours: float
    hours_last_month: float


class PhaseOut(BaseModel):
    key: str
    share_pct: int
    state: Literal["done", "current", "next"]


class MatterOut(MatterRowOut):
    team: list[TeamMemberOut]
    phases: list[PhaseOut]
    forums: list[str]  # courts the case may move to now (forum choice), else empty
    checked: bool  # conflicts were checked at intake
    waiver: bool
    opposing_counsel: str | None = None  # PT-M5: the other side's firm (a name, never quality)
    opposing_firm_id: int | None = None  # a rival firm's page, when it is one
    # PT-M7a: early case assessment (spec 7.6): the revealed range in words, never the merits
    assessed_merits: str | None = None
    can_assess: bool = False
    # PT-M14 (spec 13): AI on this matter: the current phase's hours per 100 base hours, the
    # kind's share of hours on exposed tasks, clients' cut on its hourly bills, a product
    ai_hours_pct: int = 100
    ai_exposed_pct: int = 0
    ai_client_cut_bp: int = 0
    ai_product: bool = False


class ConflictChecksOut(BaseModel):
    enabled: bool


ClientOut.model_rebuild()  # it lists MatterRowOut, defined after it


# --- Views ---------------------------------------------------------------------------------------


def _name(state: GameState, person_id: int | None) -> RefOut | None:
    if person_id is None:
        return None
    p = state.person(person_id)
    return RefOut(id=p.id, name=f"{p.first_name} {p.last_name}")


def practices_view(state: GameState, data: GameData, balance: Balance) -> list[PracticeMarketOut]:
    data = world_data(data, balance, state.save_meta.master_seed)  # PT-M10: the save's world
    firm = state.player.id
    base = base_monthly_demand(data)
    demand = state.market.demand_cents or base
    staff = set(state.staff_ids(firm))
    homes = [
        home_practice(p, data)
        for p in state.people
        if p.id in staff and data.market.rate_bands.get(p.level) is not None
    ]
    out = []
    for i, p in enumerate(data.practices):
        rels = [r for r in state.market.relationships if r.firm_id == firm and p.key in r.practices]
        hours = [h for h in state.market.hours if h.practice == p.key]
        out.append(
            PracticeMarketOut(
                key=p.key,
                label=p.label,
                short_label=p.short_label,
                driver=p.driver,
                demand_cents=demand[i],
                demand_base_cents=base[i],
                rates=[RateOut(band=b, cents=c) for b, c in p.rates.items()],
                leverage_norm=p.leverage,
                margin_norm_bp=p.margin_bp,
                clients=len(rels),
                people=homes.count(p.key),
                hours_last_month=sum(h.tenths for h in hours) / TENTHS,
                value_last_month_cents=sum(h.value_cents for h in hours),
            )
        )
    return out


def _wallet_estimate(
    client: Client, state: GameState, data: GameData, balance: Balance
) -> RangeCentsOut:
    shares = wallets(state.market.clients, data, balance, state.turn, state.save_meta.start_ym)
    base = base_monthly_demand(data)
    annual = sum(shares.wallet(client.id, i, base) for i in range(len(base))) * MONTHS
    lo, hi = WALLET_BAND
    return RangeCentsOut(
        lo=int(round(annual * lo / WALLET_ROUND_CENTS) * WALLET_ROUND_CENTS),
        hi=int(round(annual * hi / WALLET_ROUND_CENTS) * WALLET_ROUND_CENTS),
    )


def _client_row(
    rel: Relationship, state: GameState, data: GameData, balance: Balance, key: frozenset[int]
) -> dict[str, Any]:
    client = state.market.client(rel.client_id)
    wallet = _wallet_estimate(client, state, data, balance)
    recent = rel.last_instructed_turn is not None and state.turn - rel.last_instructed_turn < MONTHS
    return {
        "id": client.id,
        "name": client.name,
        "sector": data.clients.sector(client.sector).label,
        "real": client.real,
        "size_class": client.size_class,
        "relationship": round(rel.score),
        "partner": _name(state, rel.partner_id),
        "practices": list(rel.practices),
        "fees_12m_cents": rel.fees_12m,
        "key_client": client.id in key,
        "open_matters": sum(
            1 for m in state.market.open_matters(rel.firm_id) if m.client_id == client.id
        ),
        "wallet_estimate": wallet,
        "share_estimate": RangeBpOut(
            lo=10000 * rel.fees_12m // wallet.hi if wallet.hi else 0,
            hi=10000 * rel.fees_12m // wallet.lo if wallet.lo else 0,
        ),
        "panel_status": "key" if client.id in key else "active" if recent else "dormant",
    }


def clients_view(state: GameState, data: GameData, balance: Balance) -> list[ClientRowOut]:
    data = world_data(data, balance, state.save_meta.master_seed)  # PT-M10: the save's world
    firm = state.player.id
    key = key_clients(state.market, firm, balance)
    return [
        ClientRowOut.model_validate(_client_row(r, state, data, balance, key))
        for r in state.market.relationships
        if r.firm_id == firm
    ]


def _affinity(value: float) -> Literal["high", "medium", "low"]:
    return "high" if value >= 0.6 else "medium" if value >= 0.4 else "low"


def client_view(state: GameState, client_id: int, data: GameData, balance: Balance) -> ClientOut:
    data = world_data(data, balance, state.save_meta.master_seed)  # PT-M10: the save's world
    firm = state.player.id
    rel = state.market.relationship(client_id, firm)
    if rel is None:
        raise NotFoundError(f"no client {client_id} on the firm's books")
    client = state.market.client(client_id)
    key = key_clients(state.market, firm, balance)
    staff = set(state.staff_ids(firm))
    cross = []
    for p in data.practices:
        if p.key in rel.practices:
            continue
        affinity = max(
            (data.practice(q).cross_sell.get(p.key, 0.0) for q in rel.practices), default=0.0
        )
        colleagues = [
            ref
            for person in state.people
            if person.id in staff and data.role(person.role).practice == p.key
            if (ref := _name(state, person.id)) is not None
        ]
        cross.append(
            CrossSellOut(
                practice=p.key, label=p.label, affinity=_affinity(affinity), colleagues=colleagues
            )
        )
    gc = client.gc
    return ClientOut.model_validate(
        {
            **_client_row(rel, state, data, balance, key),
            "general_counsel": GeneralCounselOut(
                name=f"{gc.first_name} {gc.last_name}", age=(state.turn - gc.birth_turn) // MONTHS
            ),
            "panel": [name_for_key(state, data, k) for k in client.panel],  # PT-M5: live rivals
            "advance_waiver": rel.advance_waiver,
            "cross_sell": cross,
            "matters": [
                matter_row(m, state, data)
                for m in state.market.matters
                if m.client_id == client_id and m.firm_id == firm
            ],
        }
    )


def _risk(m: Matter, overdue: bool) -> tuple[RiskOut, list[str]]:
    """A matter's risk as the firm sees it (PT-M3c): never its merits or outcome."""
    if not m.is_open:
        return "low", []
    notes = []
    if overdue:
        notes.append("Past its due month")
    if m.missed_deadlines:
        notes.append(f"{m.missed_deadlines} missed deadline{'s' if m.missed_deadlines > 1 else ''}")
    if m.worked_tenths > m.hours_needed_tenths:
        notes.append("Over its hours budget")
    if m.under_months:
        notes.append("Behind the planned pace")
    if not m.team:
        notes.append("Nobody staffed")
    if m.critical:
        notes.append("Critical to the client")
    severe = overdue or m.missed_deadlines > 0 or not m.team
    level: RiskOut = "high" if severe or len(notes) >= 3 else "medium" if notes else "low"
    return level, notes


def _row_fields(m: Matter, state: GameState, data: GameData) -> dict[str, Any]:
    start = state.save_meta.start_ym
    kind = data.market.kinds[m.kind]
    hours = [h for h in state.market.hours if h.matter_id == m.id]
    phase = (
        kind.phases[m.phase_index].key if m.is_open and m.phase_index < len(kind.phases) else None
    )
    judge = state.market.judge(m.judge_id) if m.judge_id is not None else None
    s = m.settlement
    due = m.opened_turn + m.planned_months
    client = state.market.client(m.client_id)
    overdue = m.is_open and state.turn > due
    risk, risk_notes = _risk(m, overdue)
    return {
        "id": m.id,
        "name": m.name,
        "client": RefOut(id=client.id, name=client.name),
        "practice": m.practice,
        "kind": m.kind,
        "kind_label": data.practice(m.practice).kind(m.kind_key).label,
        "status": m.status,
        "outcome": m.outcome,
        "lead": _name(state, m.lead_id),
        "phase": phase,
        "progress_pct": round(100 * completed_share(m, kind)),
        "opened_label": format_turn(m.opened_turn, start),
        "due_label": format_turn(due, start),
        "overdue": overdue,
        "risk": risk,
        "risk_notes": risk_notes,
        "budget_hours": m.hours_needed_tenths / TENTHS,
        "worked_hours": m.worked_tenths / TENTHS,
        "hours_last_month": sum(h.tenths for h in hours) / TENTHS,
        "expected_fees_cents": m.expected_fees_cents,
        "wip_cents": m.wip_cents,
        "critical": m.critical,
        "adverse": m.adverse_name,
        "court": data.courts.court(m.court).label if m.court else None,
        "judge": f"Judge {judge.first_name} {judge.last_name}" if judge is not None else None,
        "errors_caught": m.errors_caught,
        "missed_deadlines": m.missed_deadlines,
        "pro_bono": m.pro_bono,
        "settlement": None
        if s is None or state.turn > s.expires_turn
        else SettlementOut(
            offer_cents=m.stakes_cents * s.fraction_bp // 10000,
            expires_label=format_turn(s.expires_turn, start),
        ),
    }


def matter_row(m: Matter, state: GameState, data: GameData) -> MatterRowOut:
    return MatterRowOut.model_validate(_row_fields(m, state, data))


def matters_view(state: GameState, data: GameData, status: str = "open") -> list[MatterRowOut]:
    firm = state.player.id
    return [
        matter_row(m, state, data)
        for m in state.market.matters
        if m.firm_id == firm and (status == "all" or m.status == status)
    ]


def matter_view(state: GameState, matter_id: int, data: GameData, balance: Balance) -> MatterOut:
    data = world_data(data, balance, state.save_meta.master_seed)  # PT-M10: the save's world
    m = state.market.matter(matter_id)
    if m is None or m.firm_id != state.player.id:
        raise NotFoundError(f"no matter {matter_id}")
    kind = data.market.kinds[m.kind]
    worked = {h.person_id: h.tenths for h in state.market.hours if h.matter_id == m.id}
    team = []
    for tm in m.team:
        person = state.person(tm.person_id)
        ref = _name(state, tm.person_id)
        assert ref is not None
        team.append(
            TeamMemberOut(
                person=ref,
                role=tm.role,
                level=person.level,
                planned_hours=tm.planned_tenths / TENTHS,
                hours_last_month=worked.get(tm.person_id, 0) / TENTHS,
            )
        )
    phases = [
        PhaseOut(
            key=p.key,
            share_pct=round(100 * p.share),
            state="done"
            if i < m.phase_index
            else "current"
            if i == m.phase_index and m.is_open
            else "next",
        )
        for i, p in enumerate(kind.phases)
    ]
    forums: list[str] = []
    if (
        m.is_open
        and m.judge_id is None
        and state.turn - m.opened_turn <= balance.matters.forum_change_turns
    ):
        forums = list(data.practice(m.practice).kind(m.kind_key).forums)
    return MatterOut.model_validate(
        {
            **_row_fields(m, state, data),
            "team": team,
            "phases": phases,
            "assessed_merits": None
            if m.assessment is None
            else merits_words(m.assessment.lo, m.assessment.hi),
            "can_assess": m.is_open
            and kind.outcome == "case"
            and m.assessment is None
            and m.lead_id is not None,
            "forums": forums,
            "checked": m.checked,
            "waiver": m.waiver,
            "opposing_counsel": opposing_counsel(state, m.id)[0],
            "opposing_firm_id": opposing_counsel(state, m.id)[1],
            **matter_ai_fields(state, m, data, balance),  # PT-M14
        }
    )


# --- Router ----------------------------------------------------------------------------------


class AssignIn(BaseModel):
    person_id: int
    hours: int = Field(gt=0)
    role: Literal["senior", "junior", "paralegal"] | None = None


class HoursIn(BaseModel):
    hours: int = Field(gt=0)


class LeadIn(BaseModel):
    person_id: int


class WaiverIn(BaseModel):
    advance: bool = False


class SettlementIn(BaseModel):
    accept: bool


class ForumIn(BaseModel):
    court: str


class IntroduceIn(BaseModel):
    colleague_id: int
    practice: str
    introducer_id: int | None = None  # a partner; the player's founding partner by default


class ConflictChecksIn(BaseModel):
    enabled: bool


class FirmPoliciesOut(BaseModel):
    """PT-M7a: the Org screen's firm policies: pro bono credit (spec 7.8) and rates."""

    pro_bono_credit_hours: int  # hours a year counting toward each lawyer's billable target
    pro_bono_credit_max_hours: int
    pro_bono_hours_per_lawyer: float  # the firm's pro bono, hours a lawyer a year (average)
    rate_rise_bp: int | None  # None: follows the market's
    market_rise_bp: int
    rate_rise_min_bp: int
    rate_rise_max_bp: int
    rate_index_bp: int  # the firm's card against 2005's (10000 = the 2005 card)
    market_index_bp: int
    # PT-M7b: the hours policy, a firm-wide billable target (hours a year); None: the levels'
    billable_target_hours: int | None
    billable_target_min_hours: int
    billable_target_max_hours: int
    associate_target_hours: int  # the levels' default for an associate (shown beside it)


class ProBonoCreditIn(BaseModel):
    hours: int


class RatePolicyIn(BaseModel):
    rise_bp: int | None  # None: follow the market


class HoursPolicyIn(BaseModel):
    hours: int | None  # None: the levels' billable targets


def policies_view(state: GameState, data: GameData, balance: Balance) -> FirmPoliciesOut:
    data = world_data(data, balance, state.save_meta.master_seed)  # PT-M10: the save's world
    firm = state.player
    year = turn_to_ym(state.turn, state.save_meta.start_ym)[0]
    return FirmPoliciesOut(
        pro_bono_credit_hours=credit_hours(state, firm.id, balance),
        pro_bono_credit_max_hours=balance.pro_bono.credit_max_hours,
        pro_bono_hours_per_lawyer=round(firm.pro_bono_avg_tenths * 12 / TENTHS, 1),
        rate_rise_bp=firm.rate_rise_bp,
        market_rise_bp=market_rise_bp(year, data, balance),
        rate_rise_min_bp=balance.rates.rise_min_bp,
        rate_rise_max_bp=balance.rates.rise_max_bp,
        rate_index_bp=round(firm.rate_index * 10000),
        market_index_bp=round(
            market_index(state.turn, state.save_meta.start_ym, data, balance) * 10000
        ),
        billable_target_hours=firm.billable_target_hours,
        billable_target_min_hours=balance.staffing.policy_min_hours,
        billable_target_max_hours=balance.staffing.policy_max_hours,
        associate_target_hours=balance.people.levels["associate_1"].billable_target_hours,
    )


def _path(slug: str) -> Path:
    return saves.open_save(get_settings().resolved_save_dir(), slug)


def _state(slug: str) -> GameState:
    return saves.read_state(_path(slug))[0]


def _founder(state: GameState) -> int:
    founder = state.founder_of(state.player.id)
    if founder is None:
        raise NotFoundError("the firm has no founding partner to act")
    return founder


def _act(slug: str, make: Any) -> GameState:
    path = _path(slug)
    state = saves.read_state(path)[0]
    action: MatterAction = make(_founder(state))
    saves.run_action(path, action, loader.balance(), loader.game_data())
    return saves.read_state(path)[0]


def make_matters_router(errors: dict[int | str, dict[str, Any]]) -> APIRouter:
    router = APIRouter()
    base = "/api/saves/{slug}"

    def matter_out(state: GameState, matter_id: int) -> MatterOut:
        return matter_view(state, matter_id, loader.game_data(), loader.balance())

    @router.get(
        f"{base}/practices",
        response_model=list[PracticeMarketOut],
        responses=errors,
        operation_id="listPractices",
    )
    def list_practices(slug: str) -> list[PracticeMarketOut]:
        return practices_view(_state(slug), loader.game_data(), loader.balance())

    @router.get(
        f"{base}/clients",
        response_model=list[ClientRowOut],
        responses=errors,
        operation_id="listClients",
    )
    def list_clients(slug: str) -> list[ClientRowOut]:
        return clients_view(_state(slug), loader.game_data(), loader.balance())

    @router.get(
        f"{base}/clients/{{client_id}}",
        response_model=ClientOut,
        responses=errors,
        operation_id="getClient",
    )
    def get_client(slug: str, client_id: int) -> ClientOut:
        return client_view(_state(slug), client_id, loader.game_data(), loader.balance())

    @router.post(
        f"{base}/clients/{{client_id}}/introduce",
        response_model=ClientOut,
        responses=errors,
        operation_id="introduce",
    )
    def introduce(slug: str, client_id: int, body: IntroduceIn) -> ClientOut:
        state = _act(
            slug,
            lambda a: Introduce(
                body.introducer_id or a, client_id, body.colleague_id, body.practice
            ),
        )
        return client_view(state, client_id, loader.game_data(), loader.balance())

    @router.get(
        f"{base}/matters",
        response_model=list[MatterRowOut],
        responses=errors,
        operation_id="listMatters",
    )
    def list_matters(
        slug: str, status: Literal["open", "conflicted", "closed", "declined", "all"] = "open"
    ) -> list[MatterRowOut]:
        return matters_view(_state(slug), loader.game_data(), status)

    @router.get(
        f"{base}/matters/{{matter_id}}",
        response_model=MatterOut,
        responses=errors,
        operation_id="getMatter",
    )
    def get_matter(slug: str, matter_id: int) -> MatterOut:
        return matter_out(_state(slug), matter_id)

    @router.post(
        f"{base}/matters/{{matter_id}}/team",
        response_model=MatterOut,
        responses=errors,
        operation_id="assignToMatter",
    )
    def assign(slug: str, matter_id: int, body: AssignIn) -> MatterOut:
        return matter_out(
            _act(
                slug, lambda a: AssignToMatter(a, matter_id, body.person_id, body.hours, body.role)
            ),
            matter_id,
        )

    @router.put(
        f"{base}/matters/{{matter_id}}/team/{{person_id}}",
        response_model=MatterOut,
        responses=errors,
        operation_id="setMatterHours",
    )
    def set_hours(slug: str, matter_id: int, person_id: int, body: HoursIn) -> MatterOut:
        return matter_out(
            _act(slug, lambda a: SetMatterHours(a, matter_id, person_id, body.hours)), matter_id
        )

    @router.delete(
        f"{base}/matters/{{matter_id}}/team/{{person_id}}",
        response_model=MatterOut,
        responses=errors,
        operation_id="removeFromMatter",
    )
    def remove(slug: str, matter_id: int, person_id: int) -> MatterOut:
        return matter_out(
            _act(slug, lambda a: RemoveFromMatter(a, matter_id, person_id)), matter_id
        )

    @router.post(
        f"{base}/matters/{{matter_id}}/lead",
        response_model=MatterOut,
        responses=errors,
        operation_id="setMatterLead",
    )
    def set_lead(slug: str, matter_id: int, body: LeadIn) -> MatterOut:
        return matter_out(
            _act(slug, lambda a: SetMatterLead(a, matter_id, body.person_id)), matter_id
        )

    @router.post(
        f"{base}/matters/{{matter_id}}/default-staffing",
        response_model=MatterOut,
        responses=errors,
        operation_id="defaultStaffing",
    )
    def default_staffing(slug: str, matter_id: int) -> MatterOut:
        return matter_out(_act(slug, lambda a: DefaultStaffing(a, matter_id)), matter_id)

    @router.post(
        f"{base}/matters/{{matter_id}}/waiver",
        response_model=MatterOut,
        responses=errors,
        operation_id="seekWaiver",
    )
    def seek_waiver(slug: str, matter_id: int, body: WaiverIn) -> MatterOut:
        return matter_out(_act(slug, lambda a: SeekWaiver(a, matter_id, body.advance)), matter_id)

    @router.post(
        f"{base}/matters/{{matter_id}}/settlement",
        response_model=MatterOut,
        responses=errors,
        operation_id="respondSettlement",
    )
    def respond_settlement(slug: str, matter_id: int, body: SettlementIn) -> MatterOut:
        return matter_out(
            _act(slug, lambda a: RespondSettlement(a, matter_id, body.accept)), matter_id
        )

    @router.post(
        f"{base}/matters/{{matter_id}}/forum",
        response_model=MatterOut,
        responses=errors,
        operation_id="chooseForum",
    )
    def choose_forum(slug: str, matter_id: int, body: ForumIn) -> MatterOut:
        return matter_out(_act(slug, lambda a: ChooseForum(a, matter_id, body.court)), matter_id)

    @router.post(
        f"{base}/matters/{{matter_id}}/assessment",
        response_model=MatterOut,
        responses=errors,
        operation_id="assessCase",
    )
    def assess_case(slug: str, matter_id: int) -> MatterOut:
        """PT-M7a: early case assessment (energy and the lead's hours this month)."""
        return matter_out(_act(slug, lambda a: AssessCase(a, matter_id)), matter_id)

    @router.get(
        f"{base}/policies",
        response_model=FirmPoliciesOut,
        responses=errors,
        operation_id="getFirmPolicies",
    )
    def get_policies(slug: str) -> FirmPoliciesOut:
        return policies_view(_state(slug), loader.game_data(), loader.balance())

    @router.put(
        f"{base}/policies/pro-bono",
        response_model=FirmPoliciesOut,
        responses=errors,
        operation_id="setProBonoCredit",
    )
    def set_pro_bono(slug: str, body: ProBonoCreditIn) -> FirmPoliciesOut:
        return policies_view(
            _act(slug, lambda a: SetProBonoCredit(a, body.hours)),
            loader.game_data(),
            loader.balance(),
        )

    @router.put(
        f"{base}/policies/rates",
        response_model=FirmPoliciesOut,
        responses=errors,
        operation_id="setRatePolicy",
    )
    def set_rates(slug: str, body: RatePolicyIn) -> FirmPoliciesOut:
        return policies_view(
            _act(slug, lambda a: SetRatePolicy(a, body.rise_bp)),
            loader.game_data(),
            loader.balance(),
        )

    @router.put(
        f"{base}/policies/hours",
        response_model=FirmPoliciesOut,
        responses=errors,
        operation_id="setHoursPolicy",
    )
    def set_hours_policy(slug: str, body: HoursPolicyIn) -> FirmPoliciesOut:
        """PT-M7b: the firm's billable target (hours a year), or None for the levels'."""
        return policies_view(
            _act(slug, lambda a: SetHoursPolicy(a, body.hours)),
            loader.game_data(),
            loader.balance(),
        )

    @router.get(
        f"{base}/conflict-checks",
        response_model=ConflictChecksOut,
        responses=errors,
        operation_id="getConflictChecks",
    )
    def get_checks(slug: str) -> ConflictChecksOut:
        return ConflictChecksOut(enabled=_state(slug).player.conflict_checks)

    @router.put(
        f"{base}/conflict-checks",
        response_model=ConflictChecksOut,
        responses=errors,
        operation_id="setConflictChecks",
    )
    def set_checks(slug: str, body: ConflictChecksIn) -> ConflictChecksOut:
        return ConflictChecksOut(
            enabled=_act(slug, lambda a: SetConflictChecks(a, body.enabled)).player.conflict_checks
        )

    return router
