"""Market endpoints (PT-M5; spec 10, 7.2, 16): rival firms, a rival's page, market news,
the firm's RFPs, rivals' approaches to the firm's people, and the player's market actions.

What the player sees of a rival is what the legal press would print: its name, personality
label, offices, and each December's revenue, lawyers, equity partners and PEP (Am Law's
figures, rounded as published), a money label and its stance toward the player. Its key
people show only names, levels and practices, and a person the firm has met is linked to
the People screen, which shows revealed ranges. Never a rival's demand, utility, history
offsets, a person's book, portability or hidden traits (CLAUDE.md section 10;
tests/integration/test_market_api.py checks every schema here).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ptk import loader
from ptk.config import get_settings
from ptk.db import saves
from ptk.sim.calendar import format_turn
from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import NotFoundError
from ptk.sim.reputation.formulas import reputation
from ptk.sim.rivals import formulas as f
from ptk.sim.rivals.actions import (
    ApproachFreeAgents,
    ApproachRival,
    CounterApproach,
    PitchRfp,
    RivalAction,
)
from ptk.sim.rivals.decisions import NEWSLESS
from ptk.sim.rivals.models import PLAYER_PANEL_KEY, RivalFirm
from ptk.sim.rivals.people import person_of
from ptk.sim.rivals.rfp import CLAIMS
from ptk.sim.rivals.views import name_for_key
from ptk.sim.state import GameState

NEWS_MONTHS = 12  # tunable-exempt: the news screen's window
MILLION = 100_000_000  # tunable-exempt: $1M in cents (published figures round to it)

type RivalStatusOut = Literal["active", "merged", "collapsed", "failed"]


class FirmRefOut(BaseModel):
    id: int
    name: str


class YearOut(BaseModel):
    year: int
    revenue_cents: int  # rounded to $1M, as published
    lawyers: int  # rounded as the press shows headcount
    equity_partners: int
    pep_cents: int  # rounded to $1,000


class RivalRowOut(BaseModel):
    id: int
    name: str
    short: str
    kind: Literal["real", "generated", "boutique"]
    personality: str  # the label (spec 10.1)
    status: RivalStatusOut
    hq: str
    offices: int
    ny_office: bool
    revenue_cents: int  # the last published fiscal year
    lawyers: int
    pep_cents: int
    money: str  # strong, steady, strained
    stance: str  # neutral, wary, hostile
    key_people: int
    on_panels: int  # client panels it sits on


class KeyPersonOut(BaseModel):
    id: int
    name: str
    level: str
    practice: str
    real: bool  # a real lawyer (shown only with world.real_people on)
    met: bool  # the firm has met them (a candidate before): their profile has ranges


class PracticeHeadcountOut(BaseModel):
    practice: str
    label: str
    lawyers: int
    reputation: int  # PT-M16: its public reputation 0-100 in the practice (spec 12.1)
    band: int | None  # the latest October's directory band (None: not ranked)


class NewsOut(BaseModel):
    turn: int
    date_label: str
    firm: FirmRefOut
    action: str
    text: str


class RivalOut(RivalRowOut):
    comp: str
    founded_label: str
    ended_label: str | None
    successor: str | None
    history: list[YearOut]
    practices: list[PracticeHeadcountOut]
    people: list[KeyPersonOut]
    news: list[NewsOut]


class RfpOut(BaseModel):
    id: int
    client: FirmRefOut
    kind: Literal["panel", "matter"]
    practices: list[str]
    opened_label: str
    award_label: str
    status: Literal["open", "awarded"]
    seats: int
    incumbent: bool  # the firm holds a seat it is defending
    contenders: list[str]  # firm names (incumbents first)
    pitched: bool
    team: list[FirmRefOut]  # the pitch team (people), if pitched
    claims: list[str]
    won: bool | None  # None while open


class RivalApproachOut(BaseModel):
    id: int
    person: FirmRefOut
    firm: FirmRefOut
    offer_cents: int  # what the rival offers (the person tells the firm)
    made_label: str
    status: str
    odds: str  # likely to stay, might go, likely to go: a band, never the number


class MarketOut(BaseModel):
    rivals: list[RivalRowOut]
    rfps: list[RfpOut]
    approaches: list[RivalApproachOut]
    news: list[NewsOut]
    free_agents: int
    claims: list[str]  # the pitch claims the firm may make
    real_people: bool


# --- Views --------------------------------------------------------------------------------


def _round(cents: int, step: int) -> int:
    return round(cents / step) * step


def _last_year(firm: RivalFirm) -> tuple[int, int, int]:
    if firm.history:
        h = firm.history[-1]
        return h.revenue_cents, h.lawyers, h.pep_cents
    eq = max(firm.equity_partners, 1.0)
    return firm.revenue_12m, round(firm.lawyers), round(firm.profit_12m / eq)


def _labels(firm: RivalFirm, balance: Balance) -> tuple[str, str]:
    margin = firm.profit_12m / firm.revenue_12m if firm.revenue_12m > 0 else 0.0
    change = None
    if len(firm.history) >= 2 and firm.history[-2].pep_cents > 0:
        change = firm.history[-1].pep_cents / firm.history[-2].pep_cents - 1.0
    return f.money_label(margin, change), f.stance_label(firm.stance)


def _row(
    state: GameState, firm: RivalFirm, balance: Balance, panels: dict[str, int]
) -> RivalRowOut:
    revenue, lawyers, pep = _last_year(firm)
    money, stance = _labels(firm, balance)
    return RivalRowOut(
        id=firm.id,
        name=firm.name,
        short=firm.short,
        kind=firm.kind,
        personality=balance.rivals.personalities[firm.personality].label,
        status=firm.status,
        hq=firm.hq.replace("_", " ").title(),
        offices=firm.offices,
        ny_office=firm.ny_office,
        revenue_cents=_round(revenue, MILLION),
        lawyers=f.rounded_headcount(lawyers),
        pep_cents=_round(pep, 100_000),  # tunable-exempt: $1,000s
        money=money,
        stance=stance,
        key_people=len(state.rivals.members_of(firm.id)),
        on_panels=panels.get(firm.key, 0),
    )


def _panels(state: GameState) -> dict[str, int]:
    out: dict[str, int] = {}
    for c in state.market.clients:
        for k in c.panel:
            out[k] = out.get(k, 0) + 1
    return out


def _news(state: GameState, firm_id: int | None = None) -> list[NewsOut]:
    start = state.save_meta.start_ym
    out = []
    for m in reversed(state.rivals.moves):
        if m.action in NEWSLESS or m.turn < state.turn - NEWS_MONTHS:
            continue
        if firm_id is not None and m.firm_id != firm_id and m.other_firm_id != firm_id:
            continue
        firm = state.rivals.firm(m.firm_id)
        out.append(
            NewsOut(
                turn=m.turn,
                date_label=format_turn(m.turn, start),
                firm=FirmRefOut(id=m.firm_id, name=firm.name if firm else ""),
                action=m.action,
                text=m.detail,
            )
        )
    return out


def _person_ref(state: GameState, person_id: int) -> FirmRefOut:
    p = state.person(person_id)
    return FirmRefOut(id=p.id, name=f"{p.first_name} {p.last_name}")


def _rfp(state: GameState, r: Any, data: GameData) -> RfpOut:
    start = state.save_meta.start_ym
    client = state.market.client(r.client_id)
    contenders = [
        state.player.name if k == PLAYER_PANEL_KEY else name_for_key(state, data, k)
        for k in (*r.incumbents, *r.bidders)
    ]
    team = [_person_ref(state, pid) for pid in r.pitch.team] if r.pitch else []
    return RfpOut(
        id=r.id,
        client=FirmRefOut(id=client.id, name=client.name),
        kind=r.kind,
        practices=list(r.practices),
        opened_label=format_turn(r.opened_turn, start),
        award_label=format_turn(r.award_turn, start),
        status=r.status,
        seats=r.seats,
        incumbent=PLAYER_PANEL_KEY in r.incumbents,
        contenders=contenders,
        pitched=r.pitch is not None,
        team=team,
        claims=list(r.pitch.claims) if r.pitch else [],
        won=None if r.status == "open" else PLAYER_PANEL_KEY in r.winners,
    )


def market_view(state: GameState, data: GameData, balance: Balance) -> MarketOut:
    from ptk.sim.rivals.poaching import answer_odds

    panels = _panels(state)
    rivals = sorted(
        (_row(state, x, balance, panels) for x in state.rivals.firms if x.active),
        key=lambda r: (-r.revenue_cents, r.id),
    )
    start = state.save_meta.start_ym
    approaches = []
    for a in state.rivals.approaches:
        if a.status != "pending" or state.employer_of(a.person_id) != state.player.id:
            continue
        firm = state.rivals.firm(a.firm_id)
        approaches.append(
            RivalApproachOut(
                id=a.id,
                person=_person_ref(state, a.person_id),
                firm=FirmRefOut(id=a.firm_id, name=firm.name if firm else ""),
                offer_cents=a.offer_cents,
                made_label=format_turn(a.made_turn, start),
                status=a.status,
                odds=answer_odds(state, a, data, balance).band,
            )
        )
    rfps = [
        _rfp(state, r, data)
        for r in state.rivals.rfps
        if r.player_invited
        and (r.status == "open" or PLAYER_PANEL_KEY in (*r.incumbents, *r.winners) or r.pitch)
    ]
    return MarketOut(
        rivals=rivals,
        rfps=sorted(rfps, key=lambda r: (r.status != "open", -r.id)),
        approaches=approaches,
        news=_news(state),
        free_agents=len(state.rivals.free_agents),
        claims=list(CLAIMS),
        real_people=state.rivals.real_people,
    )


def rival_view(state: GameState, firm_id: int, data: GameData, balance: Balance) -> RivalOut:
    firm = state.rivals.firm(firm_id)
    if firm is None:
        raise NotFoundError(f"no rival firm {firm_id}")
    start = state.save_meta.start_ym
    row = _row(state, firm, balance, _panels(state))
    people = []
    for m in state.rivals.members_of(firm.id):
        p = person_of(state, m, data, balance)
        people.append(
            KeyPersonOut(
                id=p.id,
                name=f"{p.first_name} {p.last_name}",
                level=p.level,
                practice=m.practice,
                real=p.real and state.rivals.real_people,
                met=state.reveal(state.player.id, p.id) is not None,
            )
        )
    people.sort(key=lambda k: (k.level != "equity_partner", k.practice, k.name))
    successor = None
    if firm.successor is not None:
        successor = name_for_key(state, data, firm.successor)
    defs = {x.key: x for x in data.rivals.firms.firms}
    return RivalOut(
        **row.model_dump(),
        comp=defs[firm.key].comp.split(" [")[0] if firm.key in defs else "modified lockstep",
        founded_label=format_turn(firm.founded_turn, start),
        ended_label=format_turn(firm.ended_turn, start) if firm.ended_turn is not None else None,
        successor=successor,
        history=[
            YearOut(
                year=h.year,
                revenue_cents=_round(h.revenue_cents, MILLION),
                lawyers=f.rounded_headcount(h.lawyers),
                equity_partners=h.equity_partners,
                pep_cents=_round(h.pep_cents, 100_000),  # tunable-exempt: $1,000s
            )
            for h in firm.history
        ],
        practices=[
            PracticeHeadcountOut(
                practice=p.practice,
                label=data.practice(p.practice).label,
                lawyers=f.rounded_headcount(p.lawyers),
                reputation=round(reputation(state, firm.id, p.practice, balance)),
                band=state.standing.rankings.band(firm.id, p.practice),
            )
            for p in firm.pools
            if p.lawyers >= 0.5  # tunable-exempt: shown when someone works there
        ],
        people=people,
        news=_news(state, firm.id),
    )


# --- Router -------------------------------------------------------------------------------


class PitchIn(BaseModel):
    team: list[int] = Field(min_length=1)
    claims: list[str] = []


class ApproachRivalIn(BaseModel):
    practice: str | None = None


def _path(slug: str) -> Path:
    return saves.open_save(get_settings().resolved_save_dir(), slug)


def _state(slug: str) -> GameState:
    return saves.read_state(_path(slug))[0]


def _act(slug: str, make: Any) -> GameState:
    path = _path(slug)
    state = saves.read_state(path)[0]
    founder = state.founder_of(state.player.id)
    if founder is None:
        raise NotFoundError("the firm has no founding partner to act")
    action: RivalAction = make(founder)
    saves.run_action(path, action, loader.balance(), loader.game_data())
    return saves.read_state(path)[0]


def make_market_router(errors: dict[int | str, dict[str, Any]]) -> APIRouter:
    router = APIRouter()
    base = "/api/saves/{slug}"

    @router.get(
        f"{base}/market", response_model=MarketOut, responses=errors, operation_id="getMarket"
    )
    def get_market(slug: str) -> MarketOut:
        return market_view(_state(slug), loader.game_data(), loader.balance())

    @router.get(
        f"{base}/rivals/{{firm_id}}",
        response_model=RivalOut,
        responses=errors,
        operation_id="getRival",
    )
    def get_rival(slug: str, firm_id: int) -> RivalOut:
        return rival_view(_state(slug), firm_id, loader.game_data(), loader.balance())

    @router.post(
        f"{base}/rfps/{{rfp_id}}/pitch",
        response_model=MarketOut,
        responses=errors,
        operation_id="pitchRfp",
    )
    def pitch_rfp(slug: str, rfp_id: int, body: PitchIn) -> MarketOut:
        state = _act(slug, lambda a: PitchRfp(a, rfp_id, tuple(body.team), tuple(body.claims)))
        return market_view(state, loader.game_data(), loader.balance())

    @router.post(
        f"{base}/rivals/{{firm_id}}/approach",
        response_model=MarketOut,
        responses=errors,
        operation_id="approachRival",
    )
    def approach_rival(slug: str, firm_id: int, body: ApproachRivalIn) -> MarketOut:
        state = _act(slug, lambda a: ApproachRival(a, firm_id, body.practice))
        return market_view(state, loader.game_data(), loader.balance())

    @router.post(
        f"{base}/market/free-agents/approach",
        response_model=MarketOut,
        responses=errors,
        operation_id="approachFreeAgents",
    )
    def approach_free_agents(slug: str) -> MarketOut:
        state = _act(slug, lambda a: ApproachFreeAgents(a))
        return market_view(state, loader.game_data(), loader.balance())

    @router.post(
        f"{base}/approaches/{{approach_id}}/counter",
        response_model=MarketOut,
        responses=errors,
        operation_id="counterRivalApproach",
    )
    def counter_approach(slug: str, approach_id: int) -> MarketOut:
        state = _act(slug, lambda a: CounterApproach(a, approach_id))
        return market_view(state, loader.game_data(), loader.balance())

    return router
