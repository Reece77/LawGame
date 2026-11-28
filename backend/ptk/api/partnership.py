"""Partnership endpoints (PT-M4; spec 5.5, 5.7, 8, 16's Partnership screen; ADR PT-0007).

The partnership as the managing partner sees it: partners (points, comp, contribution,
capital, a market band and a confidence label with a range), the agreement, the whip count,
votes with their predicted ranges, the December candidates and their business cases, approaches
and departures, lateral partner candidates, the revolver and its covenants, and the Explain
decomposition of PEP. Writes are one action each (`saves.run_action`).

Hidden values never leave the engine (CLAUDE.md section 10): a partner's confidence and
satisfaction, their portability and true market value, a vote's utilities and a lateral's
true book. The API shows labels, bands and ranges built here.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel
from simcore.kernel.calendar import format_turn

from ptk import loader
from ptk.config import get_settings
from ptk.db import saves
from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import NotFoundError
from ptk.sim.interfaces import ApproachRequest, Suitor, partner_flight
from ptk.sim.ledger import CASH, PARTNERS_CAPITAL
from ptk.sim.macro import lateral_heat
from ptk.sim.macro_seed import world_data
from ptk.sim.partnership import actions as pa
from ptk.sim.partnership import formulas as fx
from ptk.sim.partnership.books import drawn_cents, headroom_cents
from ptk.sim.partnership.careers import eligible, tracks_for
from ptk.sim.partnership.common import book_cents, home_practice, name, profit_12m, revenue_12m
from ptk.sim.partnership.comp import comp_shares, credits
from ptk.sim.partnership.governance import (
    confidence_band,
    contribution,
    practice_utilisation,
    predicted,
    vote_title,
    whip_count,
)
from ptk.sim.partnership.kpis import explain
from ptk.sim.partnership.models import AGREEMENT_TERMS, FirmPartnership
from ptk.sim.people.reveal import revealed_range, shown_rating
from ptk.sim.state import GameState

BAND_STEP = 10_000_000  # tunable-exempt: market bands are shown in $100,000 steps
BAND_WIDTH_BP = 2_000  # tunable-exempt: +-20% around the market value
YEAR = 12  # tunable-exempt: months shown of recent approaches and departures' covenant


class RangeOut(BaseModel):
    lo: int
    hi: int


class PartnerOut(BaseModel):
    person_id: int
    name: str
    practice: str
    klass: Literal["equity", "income"]
    is_mp: bool
    is_you: bool
    points: float
    admitted_label: str
    comp_last_cents: int
    budget_cents: int
    projected_comp_cents: int  # this year's pool at the run rate, by the agreement's system
    drawn_ytd_cents: int
    capital_cents: int
    capital_required_cents: int
    current_cents: int
    guarantee_cents: int
    guarantee_until_label: str | None
    origination_cents: int  # this year's origination credit
    working_cents: int  # this year's working credit (own hours at standard value)
    contribution_bp: int  # share by spec 8.5's credit formula
    market_band: RangeOut  # what a rival might pay a year (a band, never the value)
    confidence_label: str  # supportive, neutral, restless (never the number)
    confidence_range: RangeOut
    gate_steps: int
    adjust_bp: int
    promised_points: float
    lobbied: bool  # this month


class TermOut(BaseModel):
    term: str
    value: str | int | bool


class WhipOut(BaseModel):
    supportive: RangeOut
    neutral: RangeOut
    restless: RangeOut


class VoteOut(BaseModel):
    vote_id: int
    kind: str
    title: str
    status: str
    opened_label: str
    threshold_bp: int
    predicted_yes: RangeOut | None  # open votes: weight in favour, as a range
    total_weight: float
    needed_weight: float
    yes_weight: float
    no_weight: float


class PartnerCandidateOut(BaseModel):
    person_id: int
    name: str
    level: str
    practice: str
    sponsor_id: int | None
    sponsor_name: str | None
    tracks: list[str]
    proposed: str | None
    rating: float  # the firm's view of the primary skills (1-20, displayed ranges)
    business_development: RangeOut  # book potential (displayed range)
    client_care: RangeOut
    relationships: int  # clients they work for this year
    practice_need_bp: int  # the practice's utilisation last month
    moving_on_label: str | None


class ApproachOut(BaseModel):
    approach_id: int
    person_id: int
    name: str
    suitor: str
    offer_comp_cents: int
    guarantee_years: int
    respond_by_label: str
    status: str
    countered: bool
    counter_comp_cents: int
    counter_points: float
    counter_guarantee_years: int
    counter_seat: bool
    stay_label: str


class DepartureOut(BaseModel):
    person_id: int
    name: str
    practice: str
    reason: str
    destination: str | None
    label: str
    leave_label: str
    clients_following: int


class LateralOut(BaseModel):
    person_id: int
    name: str
    practice: str
    ask_cents: int
    guarantee_ask_years: int
    book: RangeOut
    diligence: bool
    clients: list[str]  # named after diligence
    conflicts: int | None  # known after diligence
    status: str
    offer_comp_cents: int
    expires_label: str


class CovenantOut(BaseModel):
    name: str
    value_cents: int
    limit_cents: int
    floor: bool
    holds: bool
    near: bool


class ForecastOut(BaseModel):
    """PT-M7b: the CFO's projected breach on the trailing trend (spec 8.7)."""

    covenant: str
    months: int
    drawn_cents: int


class RevolverOut(BaseModel):
    facility_cents: int
    drawn_cents: int
    headroom_cents: int
    rate_bp: int
    breach_months: int
    called: bool
    covenants: list[CovenantOut]
    forecast: ForecastOut | None  # PT-M7b: None while the trend breaks no covenant


class PepExplainOut(BaseModel):
    pep_cents: int | None
    rpl_cents: int | None
    margin_bp: int | None
    leverage: float | None
    revenue_cents: int
    profit_cents: int
    lawyers: float
    equity_partners: float
    hours_per_lawyer: float | None
    average_rate_cents: int | None
    realisation_bp: int | None
    collection_bp: int | None


class PracticeOut(BaseModel):
    key: str
    label: str


class PartnershipOut(BaseModel):
    stage: int
    practices: list[PracticeOut]  # for the lateral search
    mp_name: str | None
    you_are_mp: bool
    election_choice_pending: bool
    term_ends_label: str | None
    december: bool
    comp_system: str
    agreement: list[TermOut]
    whip: WhipOut
    partners: list[PartnerOut]
    votes: list[VoteOut]
    candidates: list[PartnerCandidateOut]
    approaches: list[ApproachOut]
    departures: list[DepartureOut]
    laterals: list[LateralOut]
    draws_suspended: bool
    capital_cents: int
    capital_returns_cents: int  # still owed to partners who left
    true_up_owed_cents: int
    cash_cents: int
    last_profit_cents: int | None
    last_pep_cents: int | None
    revolver: RevolverOut
    explain: PepExplainOut


# --- Requests ----------------------------------------------------------------------------------


class TermsIn(BaseModel):
    term: str
    value: str | int | bool


class AmountIn(BaseModel):
    amount_cents: int


class ProposeIn(BaseModel):
    person_id: int
    track: Literal["equity", "income", "counsel", "not_this_year"]
    sponsor_id: int | None = None


class DeequitiseIn(BaseModel):
    person_id: int
    mode: Literal["income", "out"]


class PersonIn(BaseModel):
    person_id: int


class PromiseIn(BaseModel):
    person_id: int
    points: float


class DrawsIn(BaseModel):
    suspended: bool


class CompRoundIn(BaseModel):
    person_id: int
    gate_steps: int = 0
    adjust_bp: int = 0


class SponsorIn(BaseModel):
    person_id: int
    sponsor_id: int


class PracticeIn(BaseModel):
    practice: str


class LateralOfferIn(BaseModel):
    comp_cents: int
    guarantee_years: int = 0
    equity: bool = True


class CounterIn(BaseModel):
    comp_cents: int = 0
    points: float = 0.0
    guarantee_years: int = 0
    seat: bool = False


class ElectionIn(BaseModel):
    choice: Literal["stay", "hand_over"]
    successor_id: int | None = None


# --- Views -------------------------------------------------------------------------------------


def _path(slug: str) -> Path:
    return saves.open_save(get_settings().resolved_save_dir(), slug)


def _label(state: GameState, turn: int) -> str:
    return format_turn(turn, state.save_meta.start_ym)


def _fp(state: GameState) -> FirmPartnership:
    fp = state.partnership.of(state.player.id)
    if fp is None:
        raise NotFoundError("the firm keeps no partnership")
    return fp


def market_band(value: int) -> RangeOut:
    half = value * BAND_WIDTH_BP // 10_000
    lo = max(0, (value - half) // BAND_STEP * BAND_STEP)
    hi = -(-(value + half) // BAND_STEP) * BAND_STEP
    return RangeOut(lo=lo, hi=hi)


def _range(person_id: int, state: GameState, key: str) -> RangeOut:
    rv = state.reveal(state.player.id, person_id)
    if rv is None:
        return RangeOut(lo=1, hi=20)
    lo, hi = revealed_range(state.person(person_id), rv, key)
    return RangeOut(lo=lo, hi=hi)


def partnership_view(
    state: GameState,
    balances: dict[tuple[int, str], int],
    balance: Balance,
    data: GameData,
) -> PartnershipOut:
    data = world_data(data, balance, state.save_meta.master_seed)  # PT-M10: the save's world
    fp = _fp(state)
    firm = state.player.id
    you = state.founder_of(firm)
    cfg = balance.partnership
    turn = state.turn
    from simcore.kernel.calendar import turn_to_ym

    december = turn_to_ym(turn, state.save_meta.start_ym)[1] == 12  # tunable-exempt
    pool = max(profit_12m(fp), 0)
    projected = comp_shares(state, fp, pool, balance)
    cr = credits(state, fp, balance)
    contrib = contribution(state, fp, balance)
    partners = []
    for p in fp.partners:
        person = state.person(p.person_id)
        lo, hi = confidence_band(p, balance)
        c = cr.get(p.person_id)
        partners.append(
            PartnerOut(
                person_id=p.person_id,
                name=name(person),
                practice=home_practice(person, data),
                klass=p.klass,
                is_mp=p.person_id == fp.mp_id,
                is_you=p.person_id == you,
                points=p.points,
                admitted_label=_label(state, p.admitted_turn),
                comp_last_cents=p.comp_last_cents,
                budget_cents=p.budget_cents,
                projected_comp_cents=projected.get(p.person_id, 0),
                drawn_ytd_cents=p.drawn_ytd_cents,
                capital_cents=p.capital_cents,
                capital_required_cents=p.capital_required_cents,
                current_cents=p.current_cents,
                guarantee_cents=p.guarantee_cents if p.guaranteed(turn) else 0,
                guarantee_until_label=_label(state, p.guarantee_until_turn)
                if p.guaranteed(turn) and p.guarantee_until_turn is not None
                else None,
                origination_cents=c.origination_cents if c else 0,
                working_cents=c.working_cents if c else p.working_ytd_cents,
                contribution_bp=round(contrib.get(p.person_id, 0.0) * 10_000),
                market_band=market_band(
                    fx.market_value_cents(
                        book_cents(state, person),
                        cfg.flight,
                        lateral_heat(state.turn, state.save_meta.start_ym, data, balance),
                    )
                ),
                confidence_label="managing partner"
                if p.person_id == fp.mp_id
                else fx.whip_label(p.confidence, cfg.confidence),
                confidence_range=RangeOut(lo=lo, hi=hi),
                gate_steps=p.gate_steps,
                adjust_bp=p.adjust_bp,
                promised_points=p.promised_points,
                lobbied=p.lobbied_turn == turn,
            )
        )
    votes = []
    for v in fp.votes:
        if v.status != "open" and (v.resolved_turn or 0) < turn - 24:  # tunable-exempt: 2 years
            continue
        pred = predicted(state, fp, v, balance, data) if v.status == "open" else None
        votes.append(
            VoteOut(
                vote_id=v.id,
                kind=v.kind,
                title=vote_title(state, v),
                status=v.status,
                opened_label=_label(state, v.opened_turn),
                threshold_bp=v.threshold_bp,
                predicted_yes=RangeOut(lo=round(pred.yes_lo), hi=round(pred.yes_hi))
                if pred
                else None,
                total_weight=pred.total if pred else v.yes_weight + v.no_weight,
                needed_weight=pred.needed if pred else 0.0,
                yes_weight=v.yes_weight,
                no_weight=v.no_weight,
            )
        )
    candidates = []
    moving = {m.person_id: m for m in fp.moving_on}
    for e in state.staff(firm):
        pid = e.person_id
        person = state.person(pid)
        if e.status != "active" or not eligible(state, fp, pid, balance):
            continue
        rv = state.reveal(firm, pid)
        sponsor = fp.sponsor_of(pid)
        cand = fp.candidacy(pid)
        practice = home_practice(person, data)
        m = moving.get(pid)
        primary = data.role(person.role).primary
        need = practice_utilisation(state, firm, practice, balance, data)
        candidates.append(
            PartnerCandidateOut(
                person_id=pid,
                name=name(person),
                level=person.level,
                practice=practice,
                sponsor_id=sponsor,
                sponsor_name=name(state.person(sponsor)) if sponsor else None,
                tracks=list(tracks_for(state, fp, pid)),
                proposed=cand.track if cand else None,
                rating=round(shown_rating(person, rv, primary), 1) if rv else 10.0,
                business_development=_range(pid, state, "business_development"),
                client_care=_range(pid, state, "client_care"),
                relationships=len({r.client_id for r in state.market.hours if r.person_id == pid}),
                practice_need_bp=round(need * 10_000),
                moving_on_label=_label(state, m.leave_turn) if m else None,
            )
        )
    approaches = [
        ApproachOut(
            approach_id=a.id,
            person_id=a.person_id,
            name=name(state.person(a.person_id)),
            suitor=a.suitor_name,
            offer_comp_cents=a.offer_comp_cents,
            guarantee_years=a.guarantee_years,
            respond_by_label=_label(state, a.respond_by_turn),
            status=a.status,
            countered=a.countered,
            counter_comp_cents=a.counter_comp_cents,
            counter_points=a.counter_points,
            counter_guarantee_years=a.counter_guarantee_years,
            counter_seat=a.counter_seat,
            stay_label=a.stay_hint,
        )
        for a in fp.approaches
        if a.status in ("open", "countered")
        or (a.resolved_turn or 0) >= turn - 12  # tunable-exempt
    ]
    departures = [
        DepartureOut(
            person_id=d.person_id,
            name=name(state.person(d.person_id)),
            practice=d.practice,
            reason=d.reason,
            destination=d.suitor_name,
            label=_label(state, d.turn),
            leave_label=_label(state, d.leave_turn),
            clients_following=len(d.follows),
        )
        for d in fp.departures
        if d.turn >= turn - 24  # tunable-exempt: two years
    ]
    laterals = [
        LateralOut(
            person_id=c.person_id,
            name=name(state.person(c.person_id)),
            practice=c.practice,
            ask_cents=c.ask_cents,
            guarantee_ask_years=c.guarantee_ask_years,
            book=RangeOut(lo=c.book_lo_cents, hi=c.book_hi_cents),
            diligence=c.diligence,
            clients=[state.market.client(i).name for i in c.client_ids] if c.diligence else [],
            conflicts=len(c.conflict_ids) if c.diligence else None,
            status=c.status,
            offer_comp_cents=c.offer_comp_cents,
            expires_label=_label(state, c.expires_turn),
        )
        for c in fp.laterals
        if c.status in ("open", "offered") or (c.resolved_turn or 0) >= turn - 3  # tunable-exempt
    ]
    from ptk.sim.billing.kpis import receivables_cents, wip_cents

    drawn = drawn_cents(balances, firm)
    departed = sum(
        d.book_cents for d in fp.departures if d.equity and turn - d.turn < 12
    )  # tunable-exempt
    ahead = (
        fx.forecast_breach(fp.pnl, departed, cfg.revolver)
        if fp.called_turn is None and fp.breach_months == 0
        else None
    )
    covs = fx.covenants(
        drawn,
        revenue_12m(fp),
        -balances.get((firm, PARTNERS_CAPITAL), 0),
        sum(
            d.book_cents for d in fp.departures if d.equity and turn - d.turn < 12
        ),  # tunable-exempt
        cfg.revolver,
    )
    revolver = RevolverOut(
        facility_cents=fp.facility_cents,
        drawn_cents=drawn,
        headroom_cents=headroom_cents(
            fp,
            receivables_cents(state.billing, firm),
            wip_cents(state.billing, firm),
            drawn,
            balance,
        ),
        rate_bp=cfg.revolver.rate_bp,
        breach_months=fp.breach_months,
        called=fp.called_turn is not None,
        covenants=[
            CovenantOut(
                name=c.name,
                value_cents=c.value,
                limit_cents=c.limit,
                floor=c.floor,
                holds=c.holds,
                near=c.near(cfg.revolver.warning_headroom_bp),
            )
            for c in covs
        ],
        forecast=(
            ForecastOut(covenant=ahead.covenant, months=ahead.months, drawn_cents=ahead.drawn_cents)
            if ahead is not None
            else None
        ),
    )
    ex = explain(state, fp)
    whip = whip_count(fp, balance)
    mp = fp.mp_id
    return PartnershipOut(
        stage=state.player.stage,
        practices=[PracticeOut(key=pr.key, label=pr.label) for pr in data.practices],
        mp_name=name(state.person(mp)) if mp else None,
        you_are_mp=mp is not None and mp == you,
        election_choice_pending=fp.election_lost_turn is not None,
        term_ends_label=_label(state, fp.term_ends_turn) if fp.term_ends_turn is not None else None,
        december=december,
        comp_system=fp.agreement.comp_system,
        agreement=[TermOut(term=t, value=getattr(fp.agreement, t)) for t in AGREEMENT_TERMS],
        whip=WhipOut(**{k: RangeOut(lo=lo, hi=hi) for k, (lo, hi) in whip.items()}),
        partners=partners,
        votes=votes,
        candidates=candidates,
        approaches=approaches,
        departures=departures,
        laterals=laterals,
        draws_suspended=fp.draws_suspended,
        capital_cents=-balances.get((firm, PARTNERS_CAPITAL), 0),
        capital_returns_cents=sum(
            r.remaining_capital_cents + r.remaining_current_cents for r in fp.capital_returns
        ),
        true_up_owed_cents=sum(max(0, p.current_cents) for p in fp.partners),
        cash_cents=balances.get((firm, CASH), 0),
        last_profit_cents=fp.last_profit_cents,
        last_pep_cents=fp.last_pep_cents,
        revolver=revolver,
        explain=PepExplainOut(
            pep_cents=ex.pep_cents,
            rpl_cents=ex.rpl_cents,
            margin_bp=ex.margin_bp,
            leverage=ex.leverage,
            revenue_cents=ex.revenue_cents,
            profit_cents=ex.profit_cents,
            lawyers=ex.lawyers,
            equity_partners=ex.equity_partners,
            hours_per_lawyer=ex.hours_per_lawyer,
            average_rate_cents=ex.average_rate_cents,
            realisation_bp=ex.realisation_bp,
            collection_bp=ex.collection_bp,
        ),
    )


def _view(path: Path) -> PartnershipOut:
    state, balances = saves.read_state(path)
    return partnership_view(state, balances, loader.balance(), loader.game_data())


def _act(slug: str, make: Any) -> PartnershipOut:
    path = _path(slug)
    state = saves.read_state(path)[0]
    actor = state.founder_of(state.player.id)
    if actor is None:
        raise NotFoundError("the firm has no founding partner to act")
    action: pa.PartnershipAction = make(actor)
    saves.run_action(path, action, loader.balance(), loader.game_data())
    return _view(path)


def make_partnership_router(errors: dict[int | str, dict[str, Any]]) -> APIRouter:
    router = APIRouter()
    base = "/api/saves/{slug}/partnership"
    kw: dict[str, Any] = {"response_model": PartnershipOut, "responses": errors}

    @router.get(base, operation_id="getPartnership", **kw)
    def get_partnership(slug: str) -> PartnershipOut:
        return _view(_path(slug))

    @router.post(f"{base}/terms", operation_id="proposeTerms", **kw)
    def propose_terms(slug: str, body: TermsIn) -> PartnershipOut:
        return _act(slug, lambda a: pa.ProposeTerms(a, body.term, body.value))

    @router.post(f"{base}/capital-call", operation_id="capitalCall", **kw)
    def capital_call(slug: str, body: AmountIn) -> PartnershipOut:
        return _act(slug, lambda a: pa.CapitalCall(a, body.amount_cents))

    @router.post(f"{base}/propose", operation_id="proposePartner", **kw)
    def propose(slug: str, body: ProposeIn) -> PartnershipOut:
        return _act(
            slug, lambda a: pa.ProposePartner(a, body.person_id, body.track, body.sponsor_id)
        )

    @router.post(f"{base}/deequitise", operation_id="deequitise", **kw)
    def deequitise(slug: str, body: DeequitiseIn) -> PartnershipOut:
        return _act(slug, lambda a: pa.Deequitise(a, body.person_id, body.mode))

    @router.post(f"{base}/lobby", operation_id="lobbyPartner", **kw)
    def lobby(slug: str, body: PersonIn) -> PartnershipOut:
        return _act(slug, lambda a: pa.Lobby(a, body.person_id))

    @router.post(f"{base}/promise", operation_id="promisePoints", **kw)
    def promise(slug: str, body: PromiseIn) -> PartnershipOut:
        return _act(slug, lambda a: pa.PromisePoints(a, body.person_id, body.points))

    @router.post(f"{base}/votes/{{vote_id}}/withdraw", operation_id="withdrawVote", **kw)
    def withdraw(slug: str, vote_id: int) -> PartnershipOut:
        return _act(slug, lambda a: pa.WithdrawVote(a, vote_id))

    @router.post(f"{base}/draws", operation_id="setDraws", **kw)
    def draws(slug: str, body: DrawsIn) -> PartnershipOut:
        return _act(slug, lambda a: pa.SetDraws(a, body.suspended))

    @router.post(f"{base}/comp-round", operation_id="setCompRound", **kw)
    def comp_round(slug: str, body: CompRoundIn) -> PartnershipOut:
        return _act(
            slug, lambda a: pa.CompRound(a, body.person_id, body.gate_steps, body.adjust_bp)
        )

    @router.post(f"{base}/sponsor", operation_id="setSponsor", **kw)
    def sponsor(slug: str, body: SponsorIn) -> PartnershipOut:
        return _act(slug, lambda a: pa.SetSponsor(a, body.person_id, body.sponsor_id))

    @router.post(f"{base}/laterals/search", operation_id="searchLateralPartners", **kw)
    def lateral_search(slug: str, body: PracticeIn) -> PartnershipOut:
        return _act(slug, lambda a: pa.LateralSearch(a, body.practice))

    @router.post(f"{base}/laterals/{{person_id}}/diligence", operation_id="lateralDiligence", **kw)
    def diligence(slug: str, person_id: int) -> PartnershipOut:
        return _act(slug, lambda a: pa.Diligence(a, person_id))

    @router.post(f"{base}/laterals/{{person_id}}/offer", operation_id="lateralOffer", **kw)
    def lateral_offer(slug: str, person_id: int, body: LateralOfferIn) -> PartnershipOut:
        return _act(
            slug,
            lambda a: pa.LateralOffer(
                a, person_id, body.comp_cents, body.guarantee_years, body.equity
            ),
        )

    @router.post(f"{base}/approaches/{{approach_id}}/counter", operation_id="counterApproach", **kw)
    def counter(slug: str, approach_id: int, body: CounterIn) -> PartnershipOut:
        return _act(
            slug,
            lambda a: pa.Counter(
                a, approach_id, body.comp_cents, body.points, body.guarantee_years, body.seat
            ),
        )

    @router.post(f"{base}/revolver/repay", operation_id="repayRevolver", **kw)
    def repay(slug: str, body: AmountIn) -> PartnershipOut:
        return _act(slug, lambda a: pa.RepayRevolver(a, body.amount_cents))

    @router.post(f"{base}/election", operation_id="electionChoice", **kw)
    def election(slug: str, body: ElectionIn) -> PartnershipOut:
        return _act(slug, lambda a: pa.ElectionChoice(a, body.choice, body.successor_id))

    if os.environ.get("PTK_DEBUG_ROUTES") == "1":
        router.include_router(_debug_router(errors))
    return router


# --- Test-only routes (PTK_DEBUG_ROUTES=1; the e2e suite) ------------------------------------


class DebugIn(BaseModel):
    person_id: int | None = None  # default: the first partner who is not the player


def _debug_router(errors: dict[int | str, dict[str, Any]]) -> APIRouter:
    router = APIRouter()
    base = "/api/saves/{slug}/debug"

    def _apply(slug: str, body: DebugIn, kind: str) -> PartnershipOut:
        from ptk.db.core import make_sessionmaker, shared_engine
        from ptk.db.market_io import write_market
        from ptk.db.partnership_io import write_partnership
        from ptk.db.state_io import ledger_balances as read_balances
        from ptk.db.state_io import load_state, write_entries, write_log, write_people
        from ptk.sim.streams import RngFactory

        path = _path(slug)
        balance, data = loader.balance(), loader.game_data()
        hook = partner_flight()
        with make_sessionmaker(shared_engine(path))() as session, session.begin():
            state = load_state(session)
            balances = read_balances(session)
            fp = _fp(state)
            you = state.founder_of(state.player.id)
            pid = body.person_id or next(
                p.person_id for p in fp.equity_partners if p.person_id != you
            )
            rng = RngFactory(state.save_meta.master_seed)
            panel = data.clients.panel_firms[0]
            suitor = Suitor(panel.key, panel.name)
            if kind == "candidate":
                from dataclasses import replace as _replace

                from ptk.sim.interfaces import HookResult
                from ptk.sim.partnership.models import with_partner
                from ptk.sim.state import with_people

                pid = body.person_id or next(
                    e.person_id
                    for e in state.staff(state.player.id)
                    if state.person(e.person_id).level.startswith("associate")
                )
                person = state.person(pid)
                primary = data.role(person.role).primary
                skills = person.skills.updated(dict.fromkeys(primary, 18.0))
                st = with_people(state, [_replace(person, level="associate_8", skills=skills)])
                for p in fp.partners:
                    fp = with_partner(fp, _replace(p, confidence=100.0))
                st = _replace(st, partnership=_replace(st.partnership, firms=(fp,)))
                res = HookResult(st)
            elif kind == "approach":
                value = hook.market_value_cents(state, pid, balance, data)
                res = hook.approach(
                    state, ApproachRequest(pid, suitor, value, 1), balance=balance, data=data
                )
            else:
                res = hook.depart(
                    state,
                    pid,
                    suitor,
                    "approach",
                    draws=lambda: rng.stream(state.turn, "misc", pid),
                    balance=balance,
                    data=data,
                    balances=balances,
                )
            write_entries(session, res.entries)
            write_log(session, res.state, res.log, data.inbox_templates)
            write_people(session, res.state)
            write_market(session, res.state.market, append_hours=False)
            write_partnership(session, res.state.partnership)
        return _view(path)

    @router.post(
        f"{base}/approach",
        response_model=PartnershipOut,
        responses=errors,
        operation_id="debugApproach",
        include_in_schema=False,
    )
    def approach(slug: str, body: DebugIn) -> PartnershipOut:
        return _apply(slug, body, "approach")

    @router.post(
        f"{base}/candidate",
        response_model=PartnershipOut,
        responses=errors,
        operation_id="debugCandidate",
        include_in_schema=False,
    )
    def candidate(slug: str, body: DebugIn) -> PartnershipOut:
        return _apply(slug, body, "candidate")

    @router.post(
        f"{base}/depart",
        response_model=PartnershipOut,
        responses=errors,
        operation_id="debugDepart",
        include_in_schema=False,
    )
    def depart(slug: str, body: DebugIn) -> PartnershipOut:
        return _apply(slug, body, "depart")

    return router
