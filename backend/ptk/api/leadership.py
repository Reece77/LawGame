"""Leadership endpoints and schemas (PT-M8; spec 9.1-9.3; TST formulas.md 18.8, 24.4, 27.6).

The Org screen's Leadership panel reads one view: every seat in play with its holder (their
revealed ranges on the seat's weighted attributes and a fit band from the DISPLAYED score),
vacancies with their best-fit candidates, each seat's authority and guardrails, the holders'
recent decisions (what was done, never whether it was a mistake), the executive committee's
mode, and the pitches with their low, central and high cases and follow-through record.

Never in a schema (a test enumerates them): a seat score or effect, a true skill or trait,
the decision-quality or pitch probability, a holder's true ambition, which candidate was
best, or whether a decision was a mistake. Every write is one player action in its own
transaction (ADR-0014), logged to `decision_log`, and returns the fresh view.
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
from ptk.sim.actions import Action
from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import NotFoundError
from ptk.sim.org.pitches import CASE_UNIT, MODIFIABLE, AnswerPitch, record
from ptk.sim.org.seat_models import EXCO, PGL, Pitch
from ptk.sim.org.seats import (
    AppointSeat,
    FitBand,
    ProposeExcoTerm,
    SetAuthority,
    candidates,
    displayed_score,
    exco_elected,
    fit_band,
    holder_of,
    in_play,
    managing_partner,
    seated_holder,
    slots,
)
from ptk.sim.people.reveal import revealed_range
from ptk.sim.state import GameState

type CaseUnitOut = Literal["cents", "people", "bp", "morale"]
type PitchStatusOut = Literal["pending", "approved", "declined", "lapsed", "failed"]
type FollowThroughOut = Literal["hit", "miss"]
RECENT_PITCHES = 20  # tunable-exempt: pitches the panel lists (pending first, then newest)


class SkillRangeOut(BaseModel):
    key: str
    label: str
    lo: int
    hi: int


class SeatHolderOut(BaseModel):
    person_id: int
    name: str
    level: str
    ranges: list[SkillRangeOut]  # the seat's weighted attributes as the firm sees them
    fit: FitBand  # from the displayed score's band, never the score
    eligible: bool  # still eligible (else the seat counts vacant)
    hits: int  # follow-through record (TST 27.1)
    misses: int


class SeatCandidateOut(BaseModel):
    person_id: int
    name: str
    level: str
    fit: FitBand


class SeatGuardrailOut(BaseModel):
    key: str
    label: str
    value: int
    min: int
    max: int


class SeatDecisionOut(BaseModel):
    turn: int
    date_label: str
    text: str


class SeatSlotOut(BaseModel):
    slot: int
    label: str  # the seat, the group's name, or "Member 2"
    holder: SeatHolderOut | None
    candidates: list[SeatCandidateOut]
    authority_enabled: bool
    guardrails: list[SeatGuardrailOut]
    decisions: list[SeatDecisionOut]  # newest first, the last months'


class SeatOut(BaseModel):
    key: str
    label: str
    short: str
    stage: int
    open: bool  # the firm has reached the seat's stage
    who: str
    effect: str
    authority_does: str  # empty: the seat has no authority to give
    slots: list[SeatSlotOut]


class SeatPitchOut(BaseModel):
    id: int
    seat: str
    seat_label: str
    holder_id: int
    holder_name: str
    kind: str
    title: str
    why: str
    made_label: str
    cost_cents: int
    case_unit: CaseUnitOut
    low: int
    central: int
    high: int
    status: PitchStatusOut
    modifiable: bool
    follow_through: FollowThroughOut | None
    measured: int | None
    text: str


class LeadershipOut(BaseModel):
    stage: int
    exco_mode: Literal["appointed", "elected"]
    exco_proposed: bool | None  # a term waiting for the December vote
    seats: list[SeatOut]
    pitches: list[SeatPitchOut]


class AppointIn(BaseModel):
    seat: str
    slot: int = 0
    person_id: int | None = None  # None vacates


class GuardrailIn(BaseModel):
    key: str
    value: int


class AuthorityIn(BaseModel):
    seat: str
    slot: int = 0
    enabled: bool
    guardrails: list[GuardrailIn] = []


class ExcoTermIn(BaseModel):
    elected: bool


class AnswerIn(BaseModel):
    answer: Literal["approve", "modify", "decline"]
    value: int | None = None


def _name(state: GameState, pid: int) -> str:
    p = state.person(pid)
    return f"{p.first_name} {p.last_name}"


def _label(data: GameData, key: str) -> str:
    for s in data.skills:
        if s.key == key:
            return s.label
    for t in data.personality:
        if t.key == key:
            return t.label
    return key


def _holder(
    state: GameState, firm: int, pid: int, seat_key: str, data: GameData, b: Balance
) -> SeatHolderOut:
    seat = data.seat(seat_key)
    person = state.person(pid)
    reveal = state.reveal(firm, pid)
    ranges = []
    for key in seat.weights:
        lo, hi = revealed_range(person, reveal, key) if reveal is not None else (1, 20)
        ranges.append(SkillRangeOut(key=key, label=_label(data, key), lo=lo, hi=hi))
    hits, misses = record(state, pid)
    from ptk.sim.org.seats import ineligible_reason

    return SeatHolderOut(
        person_id=pid,
        name=_name(state, pid),
        level=person.level,
        ranges=ranges,
        fit=fit_band(displayed_score(state, firm, pid, seat, b), b) if reveal else "unknown",
        eligible=ineligible_reason(state, firm, pid, seat, b) is None,
        hits=hits,
        misses=misses,
    )


def _slot_label(state: GameState, seat_key: str, slot: int, label: str) -> str:
    if seat_key == PGL:
        unit = state.org.unit(slot)
        return unit.name if unit is not None else label
    if seat_key == EXCO:
        return f"Member {slot}"
    return label


def pitch_out(state: GameState, p: Pitch, data: GameData) -> SeatPitchOut:
    from ptk.sim.org.pitches import pitch_text

    return SeatPitchOut(
        id=p.id,
        seat=p.seat,
        seat_label=data.seat(p.seat).label,
        holder_id=p.person_id,
        holder_name=_name(state, p.person_id),
        kind=p.kind,
        title=p.title,
        why=p.why,
        made_label=format_turn(p.made_turn, state.save_meta.start_ym),
        cost_cents=p.cost_cents,
        case_unit=CASE_UNIT[p.kind],
        low=p.low,
        central=p.central,
        high=p.high,
        status=p.status,
        modifiable=p.kind in MODIFIABLE,
        follow_through=p.outcome,
        measured=p.measured,
        text=pitch_text(state, p),
    )


def leadership_out(state: GameState, data: GameData, b: Balance) -> LeadershipOut:
    firm = state.player.id
    seats_out = []
    for seat in data.seats.seats:
        open_ = in_play(state, firm, seat)
        slots_out = []
        for slot in slots(state, firm, seat, b) if open_ else ():
            pid = holder_of(state, firm, seat.key, slot)
            auth = state.leadership.authority(firm, seat.key, slot)
            rails = [
                SeatGuardrailOut(
                    key=g.key,
                    label=g.label,
                    value=auth.value(g.key, g.default) if auth else g.default,
                    min=g.min,
                    max=g.max,
                )
                for g in seat.authority.guardrails
            ]
            seated = seated_holder(state, firm, seat, slot, b)
            shown = (
                [
                    SeatCandidateOut(
                        person_id=c,
                        name=_name(state, c),
                        level=state.person(c).level,
                        fit=fit_band(s, b),
                    )
                    for c, s in candidates(state, firm, seat, b)[: b.seats.candidates_shown]
                ]
                if seated is None and seat.who != "player"
                else []
            )
            decisions = [
                SeatDecisionOut(
                    turn=d.turn,
                    date_label=format_turn(d.turn, state.save_meta.start_ym),
                    text=d.text,
                )
                for d in reversed(state.leadership.decisions)
                if d.firm_id == firm and d.seat == seat.key and d.slot == slot
            ]
            slots_out.append(
                SeatSlotOut(
                    slot=slot,
                    label=_slot_label(state, seat.key, slot, seat.label),
                    holder=_holder(state, firm, pid, seat.key, data, b)
                    if pid is not None
                    else None,
                    candidates=shown,
                    authority_enabled=bool(auth and auth.enabled),
                    guardrails=rails,
                    decisions=decisions,
                )
            )
        seats_out.append(
            SeatOut(
                key=seat.key,
                label=seat.label,
                short=seat.short,
                stage=seat.stage,
                open=open_,
                who=seat.who,
                effect=seat.effect,
                authority_does=seat.authority.does,
                slots=slots_out,
            )
        )
    pitches = sorted(
        (p for p in state.leadership.pitches if p.firm_id == firm),
        key=lambda p: (p.status != "pending", -p.id),
    )[:RECENT_PITCHES]
    record_ = state.leadership.firm(firm)
    return LeadershipOut(
        stage=state.player.stage,
        exco_mode="elected" if exco_elected(state, firm, b, data) else "appointed",
        exco_proposed=record_.exco_proposed,
        seats=seats_out,
        pitches=[pitch_out(state, p, data) for p in pitches],
    )


# --- Router -------------------------------------------------------------------------------------


def _path(slug: str) -> Path:
    return saves.open_save(get_settings().resolved_save_dir(), slug)


def _view(path: Path) -> LeadershipOut:
    state = saves.read_state(path)[0]
    return leadership_out(state, loader.game_data(), loader.balance())


def _act(slug: str, build: Any) -> LeadershipOut:
    path = _path(slug)
    state = saves.read_state(path)[0]
    actor = managing_partner(state, state.player.id)
    if actor is None:
        raise NotFoundError("the firm has no managing partner to act")
    action: Action = build(actor)
    saves.run_action(path, action, loader.balance(), loader.game_data())
    return _view(path)


def make_leadership_router(errors: dict[int | str, dict[str, Any]]) -> APIRouter:
    router = APIRouter()
    base = "/api/saves/{slug}/leadership"
    kw: dict[str, Any] = {"response_model": LeadershipOut, "responses": errors}

    @router.get(base, operation_id="getLeadership", **kw)
    def get_leadership(slug: str) -> LeadershipOut:
        return _view(_path(slug))

    @router.post(f"{base}/appoint", operation_id="appointSeat", **kw)
    def appoint(slug: str, body: AppointIn) -> LeadershipOut:
        return _act(slug, lambda a: AppointSeat(a, body.seat, body.slot, body.person_id))

    @router.post(f"{base}/authority", operation_id="setSeatAuthority", **kw)
    def authority(slug: str, body: AuthorityIn) -> LeadershipOut:
        rails = tuple(sorted((g.key, g.value) for g in body.guardrails))
        return _act(slug, lambda a: SetAuthority(a, body.seat, body.slot, body.enabled, rails))

    @router.post(f"{base}/exco-term", operation_id="proposeExcoTerm", **kw)
    def exco_term(slug: str, body: ExcoTermIn) -> LeadershipOut:
        return _act(slug, lambda a: ProposeExcoTerm(a, body.elected))

    @router.post(f"{base}/pitches/{{pitch_id}}/answer", operation_id="answerPitch", **kw)
    def answer(slug: str, pitch_id: int, body: AnswerIn) -> LeadershipOut:
        return _act(slug, lambda a: AnswerPitch(a, pitch_id, body.answer, body.value))

    if os.environ.get("PTK_DEBUG_ROUTES") == "1":  # test-only (the e2e suite)

        @router.post(
            "/api/saves/{slug}/debug/pitch",
            include_in_schema=False,
            operation_id="debugPitch",
            **kw,
        )
        def debug_pitch(slug: str) -> LeadershipOut:
            """Every holder with authority pitches now (the draw forced), as phase 2 would."""
            from ptk.db.core import make_sessionmaker, shared_engine
            from ptk.db.leadership_io import write_leadership
            from ptk.db.state_io import load_state, write_log
            from ptk.sim.org.pitches import draw_pitches
            from ptk.sim.streams import RngFactory

            path = _path(slug)
            balance, data = loader.balance(), loader.game_data()
            with make_sessionmaker(shared_engine(path))() as session, session.begin():
                state = load_state(session)
                rng = RngFactory(state.save_meta.master_seed)
                state, logs = draw_pitches(state, rng, balance, data, force=True)
                write_log(session, state, tuple(logs), data.inbox_templates)
                write_leadership(session, state.leadership)
            return _view(path)

    return router
