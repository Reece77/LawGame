"""Recruitment, inbox and payroll endpoints (PT-M1b; ADR-0009, ADR-0014, ADR-0016).

What the player's firm sees: candidates as revealed ranges and the potential phrase (never
true values); each candidate's ask exactly (TST 7); the offer hint band, never the true
probability. Every action runs in its own short transaction through `saves.run_action`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ptk import loader
from ptk.api.people import RangeOut, _row_fields
from ptk.config import get_settings
from ptk.db import inbox, saves
from ptk.db.session import make_sessionmaker, shared_engine
from ptk.sim.actions import Action
from ptk.sim.calendar import MONTH_ABBR, format_turn, turn_to_ym
from ptk.sim.data_models import LATERAL_CHANNELS, SCALE_LEVELS, Balance, GameData
from ptk.sim.errors import NotFoundError
from ptk.sim.hiring.actions import (
    LATERAL_PARTNER_LEVELS,
    CloseSearch,
    Interview,
    MakeOffer,
    OpenSearch,
    ReferenceCheck,
    Scout,
    SetPayPolicy,
    WithdrawOffer,
)
from ptk.sim.hiring.models import CHANNELS, Candidate
from ptk.sim.hiring.pay import market_scale_cents, policy_pay_cents
from ptk.sim.hiring.phases import bonus_cents, monthly_cost_lines
from ptk.sim.hiring.rules import (
    campus_offers_open,
    campus_registration_open,
    offer_allowed,
    offer_preview,
)
from ptk.sim.interfaces import HiringChannel
from ptk.sim.macro_seed import world_data
from ptk.sim.state import GameState

CHANNEL_LABELS: dict[str, str] = {
    "campus": "Campus (summer programme)",
    "recruiter": "Recruiter",
    "job_post": "Job post",
    "referral": "Referral",
}


class OptionOut(BaseModel):
    key: str
    label: str


class RoleOptionOut(OptionOut):
    kind: str


class ChannelOptionOut(OptionOut):
    energy: int
    fee_note: str


class SignedOut(BaseModel):
    person_id: int
    name: str
    role_label: str
    salary_cents: int
    start_label: str


class CampusOut(BaseModel):
    registration_open: bool
    registration_label: str  # "Jan-Apr"
    summer_label: str  # "May-Jul"
    offer_label: str  # "Aug"
    start_label: str  # "Sep"
    in_summer: bool
    offers_open: bool
    registered_roles: list[str]  # open campus searches' role labels
    summer_associates: int  # open campus candidates
    signed: list[SignedOut]  # accepted, starting next September


class SearchOut(BaseModel):
    id: int
    role: str
    role_label: str
    channel: str
    channel_label: str
    level: str | None
    school_tiers: list[str]
    status: str
    opened_label: str
    open_candidates: int


class CandidateOut(BaseModel):
    id: int
    name: str
    role_label: str
    level: str
    age: int
    school_tier: str | None
    channel: str
    search_id: int
    ask_cents: int
    ability: RangeOut  # revealed role-skill ranges only
    potential: str  # phrase from the revealed potential range
    interviewed: bool
    offer_allowed: bool
    offer_blocked_reason: Literal["interview_required", "campus_offer_month"] | None
    pending_offer_id: int | None
    expires_label: str


class OfferOut(BaseModel):
    id: int
    candidate_id: int
    name: str
    salary_cents: int
    status: str
    made_label: str
    start_label: str


class ScaleRowOut(BaseModel):
    level: str
    class_year: int
    market_cents: int
    firm_cents: int
    market_bonus_cents: int


class PayPolicyOut(BaseModel):
    mode: Literal["match", "lag", "lead"]
    pct_bp: int
    min_bp: int
    max_bp: int


class RecruitmentOut(BaseModel):
    date_label: str
    actor_id: int  # the player's founding partner, who acts
    energy: int
    energy_per_month: int
    campus: CampusOut
    searches: list[SearchOut]
    candidates: list[CandidateOut]
    offers: list[OfferOut]
    pay_policy: PayPolicyOut
    scale: list[ScaleRowOut]
    roles: list[RoleOptionOut]
    channels: list[ChannelOptionOut]
    levels: dict[str, list[str]]  # lateral target levels by role kind
    school_tiers: list[OptionOut]


class OpenSearchIn(BaseModel):
    role: str
    channel: HiringChannel
    level: str | None = None
    school_tiers: list[str] = Field(default_factory=list)


class OfferIn(BaseModel):
    candidate_id: int
    salary_cents: int = Field(gt=0)


class PayPolicyIn(BaseModel):
    mode: Literal["match", "lag", "lead"]
    pct_bp: int = 10_000  # tunable-exempt: 100%


class OfferPreviewOut(BaseModel):
    hint: Literal["likely", "uncertain", "unlikely"]
    ratio: float
    floor_cents: int
    ask_cents: int


class InboxItemOut(BaseModel):
    id: int
    turn: int
    date_label: str
    template: str
    title: str
    body: str
    link_kind: str | None
    link_id: int | None
    read: bool


class CostLineOut(BaseModel):
    label: str
    account: str
    amount_cents: int


class PayrollOut(BaseModel):
    """This month's phase-6 costs as they stand (the Overview's payroll panel)."""

    date_label: str
    headcount: int
    lines: list[CostLineOut]
    total_cents: int
    annual_salaries_cents: int
    bonus_month_label: str
    bonus_estimate_cents: int  # this year's bonuses if paid at today's staff and scale


# --- Builders ------------------------------------------------------------------------------


def _label(turn: int, state: GameState) -> str:
    return format_turn(turn, state.save_meta.start_ym)


def _months(lo: float, hi: float) -> str:
    return f"{MONTH_ABBR[int(lo) - 1]}-{MONTH_ABBR[int(hi) - 1]}"


def _full_name(state: GameState, person_id: int) -> str:
    person = state.person(person_id)
    return f"{person.first_name} {person.last_name}"


def _founder(state: GameState) -> int:
    return next(p.id for p in state.people if p.is_founder)


def _candidate_out(
    state: GameState, c: Candidate, data: GameData, balance: Balance
) -> CandidateOut:
    person = state.person(c.person_id)
    reveal = state.reveal(c.firm_id, person.id)
    assert reveal is not None
    fields = _row_fields(person, reveal, state, data, balance, False)
    pending = state.pending_offer_for(person.id)
    allowed = offer_allowed(state, c, balance)
    reason: Literal["interview_required", "campus_offer_month"] | None = None
    if not allowed:
        reason = "campus_offer_month"
    elif c.interviewed_turn is None:
        reason = "interview_required"
    return CandidateOut(
        id=person.id,
        name=str(fields["name"]),
        role_label=str(fields["role_label"]),
        level=person.level,
        age=person.age(state.turn),
        school_tier=data.school_tier(person.school_tier).label if person.school_tier else None,
        channel=c.channel,
        search_id=c.search_id,
        ask_cents=c.ask_cents,
        ability=fields["ability"],
        potential=str(fields["potential"]),
        interviewed=c.interviewed_turn is not None,
        offer_allowed=allowed and c.interviewed_turn is not None,
        offer_blocked_reason=reason,
        pending_offer_id=pending.id if pending else None,
        expires_label=_label(c.expires_turn, state),
    )


def recruitment_view(state: GameState, data: GameData, balance: Balance) -> RecruitmentOut:
    data = world_data(data, balance, state.save_meta.master_seed)  # PT-M10: the save's world
    firm = state.player
    founder = _founder(state)
    ym = turn_to_ym(state.turn, state.save_meta.start_ym)
    campus_cfg = balance.campus
    open_cands = [c for c in state.candidates if c.firm_id == firm.id and c.status == "open"]
    signed = []
    for o in state.offers:
        cand = state.candidate(o.candidate_id)
        if o.firm_id == firm.id and o.status == "accepted" and cand and cand.status == "signed":
            person = state.person(o.candidate_id)
            signed.append(
                SignedOut(
                    person_id=person.id,
                    name=f"{person.first_name} {person.last_name}",
                    role_label=data.role(person.role).label,
                    salary_cents=o.salary_cents,
                    start_label=_label(o.start_turn, state),
                )
            )
    campus = CampusOut(
        registration_open=campus_registration_open(state, balance),
        registration_label=_months(campus_cfg.register_months.lo, campus_cfg.register_months.hi),
        summer_label=_months(campus_cfg.summer_months.lo, campus_cfg.summer_months.hi),
        offer_label=MONTH_ABBR[campus_cfg.offer_month - 1],
        start_label=MONTH_ABBR[campus_cfg.start_month - 1],
        in_summer=campus_cfg.summer_months.lo <= ym[1] <= campus_cfg.summer_months.hi,
        offers_open=campus_offers_open(state, balance),
        registered_roles=[
            data.role(s.role).label
            for s in state.searches
            if s.firm_id == firm.id and s.channel == "campus" and s.status == "open"
        ],
        summer_associates=sum(1 for c in open_cands if c.channel == "campus"),
        signed=signed,
    )
    searches = [
        SearchOut(
            id=s.id,
            role=s.role,
            role_label=data.role(s.role).label,
            channel=s.channel,
            channel_label=CHANNEL_LABELS[s.channel],
            level=s.level,
            school_tiers=list(s.school_tiers),
            status=s.status,
            opened_label=_label(s.opened_turn, state),
            open_candidates=sum(1 for c in open_cands if c.search_id == s.id),
        )
        for s in sorted(state.searches, key=lambda s: -s.id)
        if s.firm_id == firm.id
        and (s.status == "open" or any(c.search_id == s.id for c in open_cands))
    ]
    offers = [
        OfferOut(
            id=o.id,
            candidate_id=o.candidate_id,
            name=_full_name(state, o.candidate_id),
            salary_cents=o.salary_cents,
            status=o.status,
            made_label=_label(o.made_turn, state),
            start_label=_label(o.start_turn, state),
        )
        for o in state.offers
        if o.firm_id == firm.id and o.status == "pending"
    ]
    policy = firm.pay_policy
    scale = [
        ScaleRowOut(
            level=level,
            class_year=i + 1,
            market_cents=market_scale_cents(data, ym, level),
            firm_cents=policy_pay_cents(market_scale_cents(data, ym, level), policy),
            market_bonus_cents=data.salary_scale.market_bonuses(ym[0])[i],
        )
        for i, level in enumerate(SCALE_LEVELS[:8])  # tunable-exempt: class years 1-8
    ]
    levels: dict[str, list[str]] = {}
    for key, lv in balance.people.levels.items():
        if key not in LATERAL_PARTNER_LEVELS and key != "trainee":
            levels.setdefault(lv.kind, []).append(key)
    cost = balance.energy.cost
    fees = {
        "campus": "summer pay May-Jul",
        "recruiter": "20-25% of salary on hire",
        "job_post": f"${balance.hiring.job_post_cost_cents // 100:,} a month while open",
        "referral": "free",
    }
    return RecruitmentOut(
        date_label=_label(state.turn, state),
        actor_id=founder,
        energy=state.person_state(founder).energy or 0,
        energy_per_month=balance.energy.per_month,
        campus=campus,
        searches=searches,
        candidates=[_candidate_out(state, c, data, balance) for c in open_cands],
        offers=offers,
        pay_policy=PayPolicyOut(
            mode=policy.mode,
            pct_bp=policy.pct_bp,
            min_bp=balance.pay.policy.min_bp,
            max_bp=balance.pay.policy.max_bp,
        ),
        scale=scale,
        roles=[RoleOptionOut(key=r.key, label=r.label, kind=r.kind) for r in data.roles],
        channels=[
            ChannelOptionOut(key=ch, label=CHANNEL_LABELS[ch], energy=cost[ch], fee_note=fees[ch])
            for ch in CHANNELS
            if ch == "campus" or ch in LATERAL_CHANNELS
        ],
        levels=levels,
        school_tiers=[
            OptionOut(key=t.key, label=t.label) for t in data.school_tiers if t.available_in == "v1"
        ],
    )


def payroll_view(state: GameState, data: GameData, balance: Balance) -> PayrollOut:
    data = world_data(data, balance, state.save_meta.master_seed)  # PT-M10: the save's world
    firm = state.player
    lines = monthly_cost_lines(state, firm.id, balance, data)
    staff = state.staff(firm.id)
    bonus = sum(bonus_cents(state, e, state.person(e.person_id), balance, data)[0] for e in staff)
    return PayrollOut(
        date_label=_label(state.turn, state),
        headcount=len(staff),
        lines=[CostLineOut(label=c.label, account=c.account, amount_cents=c.amount) for c in lines],
        total_cents=sum(c.amount for c in lines),
        annual_salaries_cents=sum(e.salary_cents for e in staff),
        bonus_month_label=MONTH_ABBR[balance.pay.bonus_month - 1],
        bonus_estimate_cents=bonus,
    )


# --- Router --------------------------------------------------------------------------------


def _path(slug: str) -> Path:
    return saves.open_save(get_settings().resolved_save_dir(), slug)


def _view(slug: str) -> RecruitmentOut:
    state = saves.read_state(_path(slug))[0]
    return recruitment_view(state, loader.game_data(), loader.balance())


def _act(slug: str, make: Any) -> RecruitmentOut:
    path = _path(slug)
    state = saves.read_state(path)[0]
    action: Action = make(_founder(state))
    saves.run_action(path, action, loader.balance(), loader.game_data())
    return _view(slug)


def make_router(errors: dict[int | str, dict[str, Any]]) -> APIRouter:
    router = APIRouter()
    base = "/api/saves/{slug}/recruitment"

    @router.get(
        base, response_model=RecruitmentOut, responses=errors, operation_id="getRecruitment"
    )
    def get_recruitment(slug: str) -> RecruitmentOut:
        return _view(slug)

    @router.post(
        f"{base}/searches",
        response_model=RecruitmentOut,
        responses=errors,
        operation_id="openSearch",
    )
    def open_search(slug: str, body: OpenSearchIn) -> RecruitmentOut:
        return _act(
            slug,
            lambda a: OpenSearch(
                a, body.role, body.channel, level=body.level, school_tiers=tuple(body.school_tiers)
            ),
        )

    @router.post(
        f"{base}/searches/{{search_id}}/close",
        response_model=RecruitmentOut,
        responses=errors,
        operation_id="closeSearch",
    )
    def close_search(slug: str, search_id: int) -> RecruitmentOut:
        return _act(slug, lambda a: CloseSearch(a, search_id))

    @router.post(
        f"{base}/searches/{{search_id}}/scout",
        response_model=RecruitmentOut,
        responses=errors,
        operation_id="scoutSearch",
    )
    def scout_search(slug: str, search_id: int) -> RecruitmentOut:
        return _act(slug, lambda a: Scout(a, search_id))

    @router.post(
        f"{base}/candidates/{{candidate_id}}/interview",
        response_model=RecruitmentOut,
        responses=errors,
        operation_id="interviewCandidate",
    )
    def interview(slug: str, candidate_id: int) -> RecruitmentOut:
        return _act(slug, lambda a: Interview(a, candidate_id))

    @router.post(
        f"{base}/candidates/{{candidate_id}}/reference",
        response_model=RecruitmentOut,
        responses=errors,
        operation_id="checkReferences",
    )
    def reference(slug: str, candidate_id: int) -> RecruitmentOut:
        return _act(slug, lambda a: ReferenceCheck(a, candidate_id))

    @router.get(
        f"{base}/candidates/{{candidate_id}}/offer-preview",
        response_model=OfferPreviewOut,
        responses=errors,
        operation_id="previewOffer",
    )
    def preview(slug: str, candidate_id: int, salary_cents: int) -> OfferPreviewOut:
        state = saves.read_state(_path(slug))[0]
        cand = state.candidate(candidate_id)
        if cand is None or cand.firm_id != state.player.id or cand.status != "open":
            raise NotFoundError(f"no open candidate {candidate_id}")
        p = offer_preview(
            state, cand, salary_cents, loader.balance(), loader.game_data(), _founder(state)
        )
        return OfferPreviewOut(
            hint=p.hint, ratio=round(p.ratio, 4), floor_cents=p.floor_cents, ask_cents=p.ask_cents
        )

    @router.post(
        f"{base}/offers", response_model=RecruitmentOut, responses=errors, operation_id="makeOffer"
    )
    def make_offer(slug: str, body: OfferIn) -> RecruitmentOut:
        return _act(slug, lambda a: MakeOffer(a, body.candidate_id, body.salary_cents))

    @router.post(
        f"{base}/offers/{{offer_id}}/withdraw",
        response_model=RecruitmentOut,
        responses=errors,
        operation_id="withdrawOffer",
    )
    def withdraw(slug: str, offer_id: int) -> RecruitmentOut:
        return _act(slug, lambda a: WithdrawOffer(a, offer_id))

    @router.put(
        f"{base}/pay-policy",
        response_model=RecruitmentOut,
        responses=errors,
        operation_id="setPayPolicy",
    )
    def pay_policy(slug: str, body: PayPolicyIn) -> RecruitmentOut:
        return _act(slug, lambda a: SetPayPolicy(a, body.mode, body.pct_bp))

    @router.get(
        "/api/saves/{slug}/inbox",
        response_model=list[InboxItemOut],
        responses=errors,
        operation_id="listInbox",
    )
    def list_inbox(slug: str) -> list[InboxItemOut]:
        path = _path(slug)
        state = saves.read_state(path)[0]
        with make_sessionmaker(shared_engine(path))() as session:
            items = inbox.list_inbox(session, state.player.id)
        return [
            InboxItemOut(
                id=i.id,
                turn=i.turn,
                date_label=_label(i.turn, state),
                template=i.template,
                title=i.title,
                body=i.body,
                link_kind=i.link_kind,
                link_id=i.link_id,
                read=i.read,
            )
            for i in items
        ]

    @router.post(
        "/api/saves/{slug}/inbox/read",
        response_model=list[InboxItemOut],
        responses=errors,
        operation_id="markInboxRead",
    )
    def mark_read(slug: str) -> list[InboxItemOut]:
        path = _path(slug)
        state = saves.read_state(path)[0]
        with make_sessionmaker(shared_engine(path))() as session, session.begin():
            inbox.mark_all_read(session, state.player.id)
        return list_inbox(slug)

    @router.get(
        "/api/saves/{slug}/payroll",
        response_model=PayrollOut,
        responses=errors,
        operation_id="getPayroll",
    )
    def get_payroll(slug: str) -> PayrollOut:
        state = saves.read_state(_path(slug))[0]
        return payroll_view(state, loader.game_data(), loader.balance())

    return router
