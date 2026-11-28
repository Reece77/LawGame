"""Rankings and Press endpoints and schemas (PT-M16; spec 12.1-12.3; TST formulas.md 29.6).

The Rankings screen reads one view: the latest spring tables, the quarter's league tables by
practice, October's directory bands by practice with every year's bands for the firm (the
save's `ranking_entry` history), named individuals, Best places to work, the player's own places
over time, and the March submission (open or made, with the matters and referees it may name).
The Press screen reads another: credibility and its causes, moments (open to answer first),
public claims with their public progress, rival managing partners' statements and the feuds.

Everything here is public (spec 12; TST 29.6). Never in a schema: a hidden true value, a bold
answer's baseline or a backfire before it happens, or a rival's decision weights. Every write is
one player action in its own transaction (ADR-0014) and returns the fresh view.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel
from simcore.kernel.calendar import format_turn, turn_to_ym
from sqlalchemy import select

from ptk import loader
from ptk.config import get_settings
from ptk.db import saves
from ptk.db.models import RankingEntryRow
from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import NotFoundError
from ptk.sim.interfaces import relationship_score, rival_name
from ptk.sim.press import claims as claim_rules
from ptk.sim.press.actions import AnswerPress
from ptk.sim.press.config import CLAIM_KINDS, TONES
from ptk.sim.press.models import Claim
from ptk.sim.press.moments import TRIGGER_WORDS, credibility
from ptk.sim.rankings.actions import GOOD, SHOWCASE_MONTHS, MakeSubmission
from ptk.sim.state import GameState

MOMENTS_SHOWN = 20  # tunable-exempt: recent moments on the Press screen
STATEMENTS_SHOWN = 20  # tunable-exempt: recent statements


# --- Rankings ------------------------------------------------------------------------------


class TableRowOut(BaseModel):
    place: int
    firm_id: int
    name: str
    value_cents: int
    lawyers: int
    is_player: bool


class LeagueRowOut(BaseModel):
    place: int
    firm_id: int
    name: str
    deals: int
    value_cents: int
    is_player: bool


class LeagueOut(BaseModel):
    practice: str
    label: str
    rows: list[LeagueRowOut]


class BandFirmOut(BaseModel):
    firm_id: int
    name: str
    band: int
    is_player: bool


class BandHistoryOut(BaseModel):
    year: int
    band: int


class PracticeBandsOut(BaseModel):
    practice: str
    label: str
    firms: list[BandFirmOut]  # the latest October's, band 1 first
    player_band: int | None
    player_history: list[BandHistoryOut]  # every October the firm was ranked, oldest first


class PersonBandOut(BaseModel):
    person_id: int
    name: str
    firm_id: int
    firm: str
    practice: str
    band: int
    is_player: bool


class PlacesRowOut(BaseModel):
    place: int
    firm_id: int
    name: str
    score: float
    is_player: bool


class PlayerPlaceOut(BaseModel):
    date_label: str
    kind: str
    practice: str | None
    place: int


class SubmissionMatterOut(BaseModel):
    matter_id: int
    name: str
    practice: str
    status: str  # open, or how it ended
    fees_cents: int


class SubmissionRefereeOut(BaseModel):
    client_id: int
    name: str
    relationship: int


class SubmissionOut(BaseModel):
    year: int
    window_open: bool  # March-April
    made: bool
    strength_pct: int | None
    matter_ids: list[int]
    referee_ids: list[int]
    max_matters: int
    max_referees: int
    referee_cost: float
    energy: int
    matters: list[SubmissionMatterOut]  # what it may showcase
    referees: list[SubmissionRefereeOut]  # whom it may name


class RankingsOut(BaseModel):
    tables_year: int | None
    revenue: list[TableRowOut]
    pep: list[TableRowOut]
    league_label: str | None
    league: list[LeagueOut]
    bands_year: int | None
    bands: list[PracticeBandsOut]
    people: list[PersonBandOut]
    places_year: int | None
    places: list[PlacesRowOut]
    history: list[PlayerPlaceOut]
    submission: SubmissionOut


class SubmissionIn(BaseModel):
    matter_ids: list[int]
    referee_ids: list[int]


def _band_history(path: Path, firm_id: int) -> dict[str, list[BandHistoryOut]]:
    from ptk.db.core import make_sessionmaker, shared_engine

    out: dict[str, list[BandHistoryOut]] = {}
    with make_sessionmaker(shared_engine(path))() as session:
        q = (
            select(RankingEntryRow)
            .where(RankingEntryRow.kind == "bands", RankingEntryRow.firm_id == firm_id)
            .order_by(RankingEntryRow.turn, RankingEntryRow.id)
        )
        for r in session.scalars(q):
            if r.practice is not None and r.year is not None:
                out.setdefault(r.practice, []).append(BandHistoryOut(year=r.year, band=r.place))
    return out


def _submission(state: GameState, data: GameData, balance: Balance) -> SubmissionOut:
    db = balance.rankings.directory
    pid = state.player.id
    year, month = turn_to_ym(state.turn, state.save_meta.start_ym)
    lo, hi = db.submission_months
    sub = state.standing.rankings.submission
    made = sub is not None and sub.year == year
    matters = [
        SubmissionMatterOut(
            matter_id=m.id,
            name=m.name,
            practice=m.practice,
            status=m.status if m.status == "open" else (m.outcome or "closed"),
            fees_cents=m.expected_fees_cents,
        )
        for m in state.market.matters
        if m.firm_id == pid
        and not m.pro_bono
        and (
            m.status == "open"
            or (
                m.status == "closed"
                and m.outcome in GOOD
                and m.closed_turn is not None
                and m.closed_turn >= state.turn - SHOWCASE_MONTHS
            )
        )
    ]
    matters.sort(key=lambda m: (-m.fees_cents, m.matter_id))
    referees = [
        SubmissionRefereeOut(
            client_id=r.client_id,
            name=state.market.client(r.client_id).name,
            relationship=round(relationship_score(state, r.client_id, pid)),
        )
        for r in state.market.relationships
        if r.firm_id == pid
    ]
    referees.sort(key=lambda r: (-r.relationship, r.client_id))
    return SubmissionOut(
        year=year,
        window_open=lo <= month <= hi,
        made=made,
        strength_pct=round(sub.strength * 100) if made and sub is not None else None,
        matter_ids=list(sub.matter_ids) if made and sub is not None else [],
        referee_ids=list(sub.referee_ids) if made and sub is not None else [],
        max_matters=db.max_matters,
        max_referees=db.max_referees,
        referee_cost=db.referee_cost,
        energy=balance.energy.cost["submission"],
        matters=matters[:40],
        referees=referees[:40],
    )


def rankings_out(state: GameState, path: Path, data: GameData, balance: Balance) -> RankingsOut:
    rk = state.standing.rankings
    pid = state.player.id
    start = state.save_meta.start_ym
    history = _band_history(path, pid)
    revenue = [r for r in rk.tables if r.kind == "revenue"]
    league: dict[str, list[LeagueRowOut]] = {}
    for row in rk.league:
        league.setdefault(row.practice, []).append(
            LeagueRowOut(
                place=row.place,
                firm_id=row.firm_id,
                name=row.name,
                deals=row.deals,
                value_cents=row.value_cents,
                is_player=row.firm_id == pid,
            )
        )
    bands: list[PracticeBandsOut] = []
    for p in data.practices:
        firms = [
            BandFirmOut(firm_id=b.firm_id, name=b.name, band=b.band, is_player=b.firm_id == pid)
            for b in rk.bands
            if b.practice == p.key
        ]
        firms.sort(key=lambda f: (f.band, f.name))
        bands.append(
            PracticeBandsOut(
                practice=p.key,
                label=p.label,
                firms=firms,
                player_band=rk.band(pid, p.key),
                player_history=history.get(p.key, []),
            )
        )
    league_turn = rk.published_turn("league")
    return RankingsOut(
        tables_year=revenue[0].year if revenue else None,
        revenue=[
            TableRowOut(
                place=r.place,
                firm_id=r.firm_id,
                name=r.name,
                value_cents=r.value_cents,
                lawyers=r.lawyers,
                is_player=r.firm_id == pid,
            )
            for r in revenue
        ],
        pep=[
            TableRowOut(
                place=r.place,
                firm_id=r.firm_id,
                name=r.name,
                value_cents=r.value_cents,
                lawyers=r.lawyers,
                is_player=r.firm_id == pid,
            )
            for r in rk.tables
            if r.kind == "pep"
        ],
        league_label=format_turn(league_turn, start) if league_turn is not None else None,
        league=[
            LeagueOut(practice=k, label=data.practice(k).label, rows=v) for k, v in league.items()
        ],
        bands_year=rk.bands[0].year if rk.bands else None,
        bands=bands,
        people=[
            PersonBandOut(
                person_id=x.person_id,
                name=_person_name(state, x.person_id, data, balance),
                firm_id=x.firm_id,
                firm=state.player.name
                if x.firm_id == pid
                else (rival_name(state, x.firm_id) or ""),
                practice=x.practice,
                band=x.band,
                is_player=x.firm_id == pid,
            )
            for x in rk.people
        ],
        places_year=rk.places[0].year if rk.places else None,
        places=[
            PlacesRowOut(
                place=r.place,
                firm_id=r.firm_id,
                name=r.name,
                score=r.score,
                is_player=r.firm_id == pid,
            )
            for r in rk.places
        ],
        history=[
            PlayerPlaceOut(
                date_label=format_turn(h.turn, start),
                kind=h.kind,
                practice=h.practice,
                place=h.place,
            )
            for h in rk.history
        ],
        submission=_submission(state, data, balance),
    )


# --- Press ---------------------------------------------------------------------------------


class CauseOut(BaseModel):
    date_label: str
    delta: float
    cause: str


class MomentOut(BaseModel):
    id: int
    person: str | None  # the person it is about (professional moments only, ADR PT-0013)
    trigger: str
    about: str
    date_label: str
    status: str  # pending, open, skipped, answered
    open: bool  # can be answered now
    detail: str
    practice: str | None
    rival: str | None
    tone: str | None
    by_office: bool
    backfired: bool  # shown once it has happened


class ClaimOut(BaseModel):
    id: int
    kind: str
    words: str
    made_label: str
    deadline_label: str
    status: str
    progress: str  # public: where the claim stands


class StatementOut(BaseModel):
    id: int
    rival_id: int
    rival: str
    date_label: str
    kind: str
    text: str


class FeudOut(BaseModel):
    rival_id: int
    rival: str
    score: int
    rivalry: bool
    causes: list[CauseOut]


class PressOut(BaseModel):
    credibility: int
    credibility_causes: list[CauseOut]
    moments: list[MomentOut]
    claims: list[ClaimOut]
    statements: list[StatementOut]
    feuds: list[FeudOut]
    tones: list[str]
    claim_kinds: list[str]
    claims_open: int
    claims_max: int
    claim_months: tuple[int, int]
    energy: int
    lawyers: int  # today's, for a headcount claim


class AnswerIn(BaseModel):
    tone: str
    claim: str | None = None
    practice: str | None = None
    target: int | None = None
    months: int | None = None


def _progress(state: GameState, c: Claim, data: GameData) -> str:
    match c.kind:
        case "headcount":
            return f"{claim_rules.public_lawyers(state, data)} of {c.target} lawyers"
        case "band":
            band = claim_rules.current_band(state, c.practice or "")
            now = "not ranked" if band >= claim_rules.NO_BAND else f"band {band}"
            return f"{now}; target band {c.target}"
        case "no_layoffs":
            return "no layoffs so far" if c.open else c.status
    return "paying the scale" if c.open else c.status


def press_out(state: GameState, data: GameData, balance: Balance) -> PressOut:
    press = state.standing.press
    start = state.save_meta.start_ym

    def label(turn: int) -> str:
        return format_turn(turn, start)

    moments = sorted(press.moments, key=lambda m: (m.status != "open", -m.id))[:MOMENTS_SHOWN]
    fb = balance.press.feud
    return PressOut(
        credibility=round(credibility(state, balance)),
        credibility_causes=[
            CauseOut(date_label=label(t), delta=d, cause=c)
            for t, d, c in reversed(press.cred_history)
        ],
        moments=[
            MomentOut(
                id=m.id,
                trigger=m.trigger,
                about=TRIGGER_WORDS.get(m.trigger, m.trigger),
                date_label=label(m.turn),
                status=m.status,
                open=m.status == "open" and m.due_turn == state.turn,
                detail=str(dict(m.facts).get("result", dict(m.facts).get("promise", ""))),
                person=(
                    _person_name(state, m.person_id, data, balance)
                    if m.person_id is not None
                    else None
                ),
                practice=m.practice,
                rival=rival_name(state, m.rival_id) if m.rival_id is not None else None,
                tone=m.tone,
                by_office=m.by_office,
                backfired=m.backfired,
            )
            for m in moments
        ],
        claims=[
            ClaimOut(
                id=c.id,
                kind=c.kind,
                words=claim_rules.claim_words(c, data, start),
                made_label=label(c.made_turn),
                deadline_label=label(c.deadline_turn),
                status=c.status,
                progress=_progress(state, c, data),
            )
            for c in sorted(press.claims, key=lambda c: (not c.open, -c.id))
        ],
        statements=[
            StatementOut(
                id=s.id,
                rival_id=s.rival_id,
                rival=rival_name(state, s.rival_id) or "",
                date_label=label(s.turn),
                kind=s.kind,
                text=_spoken(state, s.rival_id, s.person_id, s.text, data, balance),
            )
            for s in sorted(press.statements, key=lambda s: -s.id)[:STATEMENTS_SHOWN]
        ],
        feuds=[
            FeudOut(
                rival_id=f.rival_id,
                rival=rival_name(state, f.rival_id) or "",
                score=round(f.score),
                rivalry=f.score >= fb.rivalry,
                causes=[CauseOut(date_label=label(t), delta=d, cause=c) for t, d, c in f.causes],
            )
            for f in sorted(press.feuds, key=lambda f: -f.score)
            if f.score > 0 or f.causes
        ],
        tones=list(TONES),
        claim_kinds=list(CLAIM_KINDS),
        claims_open=len(press.open_claims),
        claims_max=balance.press.claims.max_open,
        claim_months=balance.press.claims.months,
        energy=balance.energy.cost["press_answer"],
        lawyers=claim_rules.public_lawyers(state, data),
    )


def _person_name(state: GameState, person_id: int, data: GameData, balance: Balance) -> str:
    """A person's name as the save shows it (`world.real_people` applies)."""
    from ptk.sim.rivals.people import find_person

    person = find_person(state, person_id, data, balance)
    return f"{person.first_name} {person.last_name}" if person is not None else "a partner"


def _spoken(
    state: GameState,
    rival_id: int,
    person_id: int | None,
    words: str,
    data: GameData,
    balance: Balance,
) -> str:
    firm = rival_name(state, rival_id) or "a rival"
    speaker = (
        f"a spokesperson for {firm}"
        if person_id is None
        else f"{_person_name(state, person_id, data, balance)} of {firm}"
    )
    return f"{speaker}: \u201c{words}\u201d"


# --- Router --------------------------------------------------------------------------------


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


def _rankings(path: Path) -> RankingsOut:
    state = saves.read_state(path)[0]
    return rankings_out(state, path, loader.game_data(), loader.balance())


def _press(path: Path) -> PressOut:
    state = saves.read_state(path)[0]
    return press_out(state, loader.game_data(), loader.balance())


def make_standing_router(errors: dict[int | str, dict[str, Any]]) -> APIRouter:
    router = APIRouter()
    rk: dict[str, Any] = {"response_model": RankingsOut, "responses": errors}
    pr: dict[str, Any] = {"response_model": PressOut, "responses": errors}

    @router.get("/api/saves/{slug}/rankings", operation_id="getRankings", **rk)
    def get_rankings(slug: str) -> RankingsOut:
        return _rankings(_path(slug))

    @router.post("/api/saves/{slug}/rankings/submission", operation_id="makeSubmission", **rk)
    def submit(slug: str, body: SubmissionIn) -> RankingsOut:
        return _rankings(
            _act(
                slug,
                lambda a: MakeSubmission(a, tuple(body.matter_ids), tuple(body.referee_ids)),
            )
        )

    @router.get("/api/saves/{slug}/press", operation_id="getPress", **pr)
    def get_press(slug: str) -> PressOut:
        return _press(_path(slug))

    @router.post("/api/saves/{slug}/press/{moment_id}/answer", operation_id="answerPress", **pr)
    def answer(slug: str, moment_id: int, body: AnswerIn) -> PressOut:
        return _press(
            _act(
                slug,
                lambda a: AnswerPress(
                    a, moment_id, body.tone, body.claim, body.practice, body.target, body.months
                ),
            )
        )

    return router
