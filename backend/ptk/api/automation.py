"""Automation endpoints and schemas (PT-M9; spec 9.4; TST formulas.md 40.8, 40.11).

The Automation screen reads one view: every area (one row per practice group for staffing)
with its owner or why it cannot be automated yet, the eligible people with their displayed fit
band, the money limits, priority, guardrails, the routine-events switch, last month's actions
and the proposals waiting; each owner's record (decisions and proposals over the kept months,
the area's KPIs now). The digest view lists one month's lines with their links. Screens an area
drives ask `run-by` for their header's "Run by <name> · Take over".

Never in a schema (a test enumerates them): an owner's true skills or score, the quality
probability or overload, the draws, which option was best, or whether a decision was a mistake
(a mistake is shown as the decision it was). Every write is one player action in its own
transaction (ADR-0014), logged to `decision_log`, and returns the fresh view.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from ptk import loader
from ptk.config import get_settings
from ptk.db import saves
from ptk.sim.actions import Action
from ptk.sim.automation import owners
from ptk.sim.automation.actions import AnswerProposal, GiveArea, SetAreaSettings, TakeOverArea
from ptk.sim.automation.digest import area_months, kpis, owner_note
from ptk.sim.automation.models import AreaDecision, AreaOwner, AutoProposal
from ptk.sim.calendar import format_turn
from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import NotFoundError
from ptk.sim.ledger import CASH
from ptk.sim.org.seat_models import PGL
from ptk.sim.org.seats import FitBand, managing_partner
from ptk.sim.state import GameState

SHOWN_KINDS = {"mistake": "decision"}  # a mistake is shown as the decision it was
LAST_PROPOSALS = 30  # tunable-exempt: proposals listed (pending first, then newest)


class AreaPersonOut(BaseModel):
    person_id: int
    name: str
    level: str
    fit: FitBand  # from the displayed score's band, never the score


class GuardrailValueOut(BaseModel):
    key: str
    label: str
    value: int
    default: int
    min: int
    max: int


class AreaLineOut(BaseModel):
    turn: int
    date_label: str
    kind: str  # decision, proposal, over_budget, stretched, event, note
    text: str
    commitment_cents: int
    link_kind: str | None
    link_id: int | None
    proposal_id: int | None


class KpiOut(BaseModel):
    key: str
    value: int


class AreaRowOut(BaseModel):
    area: str
    slot: int
    label: str
    does: str
    seat: str | None
    status: str  # "manual", "automated", "unavailable" (can't automate yet)
    reason: str | None  # why it can't be automated yet, and how to fix it
    owner: AreaPersonOut | None
    eligible: list[AreaPersonOut]
    limit_cents: int | None
    monthly_cents: int | None
    default_limit_cents: int
    priority: int | None
    answer_events: bool | None
    energy: int  # the area's workload a month
    guardrails: list[GuardrailValueOut]
    last_month: list[AreaLineOut]
    kpis: list[KpiOut]


class ProposalOut(BaseModel):
    id: int
    area: str
    area_label: str
    person_id: int
    name: str
    made_label: str
    expires_label: str
    title: str
    why: str
    recommendation: str
    commitment_cents: int
    status: str


class OwnerRecordOut(BaseModel):
    person_id: int
    name: str
    areas: list[str]
    workload: int  # the areas' energy a month
    capacity: int  # the energy an owner has a month
    decisions: int  # over the kept months
    proposals: int
    approved: int
    declined: int
    note: str  # their own words for last month


class AutomationOut(BaseModel):
    month_label: str
    areas: list[AreaRowOut]
    proposals: list[ProposalOut]
    owners: list[OwnerRecordOut]


class DigestAreaOut(BaseModel):
    area: str
    slot: int
    label: str
    owner: str
    committed_cents: int
    monthly_cents: int
    near_limit: int  # decisions near a limit
    proposals_waiting: int
    note: str
    lines: list[AreaLineOut]


class DigestOut(BaseModel):
    turn: int
    month_label: str
    areas: list[DigestAreaOut]


class RunByOut(BaseModel):
    area: str
    slot: int
    label: str
    owner: AreaPersonOut | None  # None: the player runs it
    can_automate: bool


class GiveIn(BaseModel):
    area: str
    slot: int = 0
    person_id: int
    limit_cents: int | None = None
    monthly_cents: int | None = None


class TakeOverIn(BaseModel):
    area: str
    slot: int = 0


class GuardrailIn(BaseModel):
    key: str
    value: int


class SettingsIn(BaseModel):
    area: str
    slot: int = 0
    limit_cents: int | None = None
    monthly_cents: int | None = None
    priority: int | None = None
    answer_events: bool | None = None
    guardrails: list[GuardrailIn] | None = None


class AnswerIn(BaseModel):
    approve: bool


# --- Views ---------------------------------------------------------------------------------------


def _name(state: GameState, pid: int) -> str:
    p = state.person(pid)
    return f"{p.first_name} {p.last_name}"


def _person(
    state: GameState, firm: int, area: str, pid: int, b: Balance, data: GameData
) -> AreaPersonOut:
    p = state.person(pid)
    return AreaPersonOut(
        person_id=pid,
        name=_name(state, pid),
        level=p.level,
        fit=owners.area_fit(state, firm, area, pid, b, data),
    )


def _label(state: GameState, area: str, slot: int, b: Balance) -> str:
    label = owners.area_def(b, area).label
    if slot:
        unit = state.org.unit(slot)
        if unit is not None:
            label = f"{label}: {unit.name}"
    return label


def _line(state: GameState, d: AreaDecision) -> AreaLineOut:
    return AreaLineOut(
        turn=d.turn,
        date_label=format_turn(d.turn, state.save_meta.start_ym),
        kind=SHOWN_KINDS.get(d.kind, d.kind),
        text=d.text,
        commitment_cents=d.commitment_cents,
        link_kind=d.link_kind,
        link_id=d.link_id,
        proposal_id=d.proposal_id,
    )


def _rails(o: AreaOwner | None, area: str, b: Balance, data: GameData) -> list[GuardrailValueOut]:
    values = dict(o.guardrails) if o is not None else {}
    return [
        GuardrailValueOut(key=k, label=label, value=values.get(k, d), default=d, min=lo, max=hi)
        for k, label, d, lo, hi in owners.guardrails(area, b, data)
    ]


def proposal_out(state: GameState, p: AutoProposal, b: Balance) -> ProposalOut:
    start = state.save_meta.start_ym
    return ProposalOut(
        id=p.id,
        area=p.area,
        area_label=_label(state, p.area, p.slot, b),
        person_id=p.person_id,
        name=_name(state, p.person_id),
        made_label=format_turn(p.made_turn, start),
        expires_label=format_turn(p.expires_turn, start),
        title=p.title,
        why=p.why,
        recommendation=p.recommendation,
        commitment_cents=p.commitment_cents,
        status=p.status,
    )


def automation_out(state: GameState, data: GameData, b: Balance, cash: int) -> AutomationOut:
    firm = state.player.id
    auto = state.automation
    last = state.turn - 1
    rows = []
    for area in owners.area_keys(b):
        a = owners.area_def(b, area)
        if a.seat == PGL and not owners.area_slots(state, firm, area, b):
            rows.append(_no_group_row(state, area, cash, b, data))
        for slot in owners.area_slots(state, firm, area, b):
            o = auto.owner(firm, area, slot)
            people = owners.eligible_people(state, firm, area, slot, b, data)
            reason = owners.cant_automate(state, firm, area, slot, b, data)
            status = "automated" if o is not None else ("unavailable" if reason else "manual")
            lines = [
                d for d in auto.decisions if d.turn == last and (d.area, d.slot) == (area, slot)
            ]
            rows.append(
                AreaRowOut(
                    area=area,
                    slot=slot,
                    label=_label(state, area, slot, b),
                    does=a.does,
                    seat=a.seat,
                    status=status,
                    reason=reason,
                    owner=_person(state, firm, area, o.person_id, b, data) if o else None,
                    eligible=[_person(state, firm, area, p, b, data) for p in people],
                    limit_cents=o.limit_cents if o else None,
                    monthly_cents=o.monthly_cents if o else None,
                    default_limit_cents=owners.default_limit(cash, b),
                    priority=o.priority if o else None,
                    answer_events=o.answer_events if o else None,
                    energy=a.energy,
                    guardrails=_rails(o, area, b, data),
                    last_month=[_line(state, d) for d in lines],
                    kpis=[KpiOut(key=k, value=v) for k, v in kpis(state, o, b, data)]
                    if o is not None
                    else [],
                )
            )
    proposals = sorted(
        (p for p in auto.proposals if p.firm_id == firm),
        key=lambda p: (p.status != "pending", -p.id),
    )[:LAST_PROPOSALS]
    return AutomationOut(
        month_label=format_turn(state.turn, state.save_meta.start_ym),
        areas=rows,
        proposals=[proposal_out(state, p, b) for p in proposals],
        owners=owner_records(state, b),
    )


def _no_group_row(state: GameState, area: str, cash: int, b: Balance, data: GameData) -> AreaRowOut:
    a = owners.area_def(b, area)
    return AreaRowOut(
        area=area, slot=0, label=a.label, does=a.does, seat=a.seat, status="unavailable",
        reason="create a practice group with an equity partner as its leader", owner=None,
        eligible=[], limit_cents=None, monthly_cents=None,
        default_limit_cents=owners.default_limit(cash, b), priority=None, answer_events=None,
        energy=a.energy, guardrails=_rails(None, area, b, data), last_month=[], kpis=[],
    )  # fmt: skip


def owner_records(state: GameState, b: Balance) -> list[OwnerRecordOut]:
    """Each owner's visible record (TST 40.3): decisions and proposals, never the draws."""
    firm = state.player.id
    auto = state.automation
    out = []
    for pid in sorted({o.person_id for o in auto.owners if o.firm_id == firm}):
        mine = [o for o in auto.owners if o.person_id == pid and o.firm_id == firm]
        lines = [d for d in auto.decisions if d.person_id == pid]
        props = [p for p in auto.proposals if p.person_id == pid]
        last = tuple(d for d in lines if d.turn == state.turn - 1)
        waiting = sum(1 for p in props if p.status == "pending")
        out.append(
            OwnerRecordOut(
                person_id=pid,
                name=_name(state, pid),
                areas=[_label(state, o.area, o.slot, b) for o in mine],
                workload=sum(owners.area_def(b, o.area).energy for o in mine),
                capacity=b.automation.owner_energy,
                decisions=sum(1 for d in lines if d.kind in ("decision", "mistake", "event")),
                proposals=len(props),
                approved=sum(1 for p in props if p.status == "approved"),
                declined=sum(1 for p in props if p.status in ("declined", "expired")),
                note=owner_note(state, mine[0], last, waiting),
            )
        )
    return out


def digest_out(state: GameState, turn: int, b: Balance) -> DigestOut:
    areas = []
    for m in area_months(state, turn, b):
        o = m.owner
        areas.append(
            DigestAreaOut(
                area=o.area,
                slot=o.slot,
                label=_label(state, o.area, o.slot, b),
                owner=_name(state, o.person_id),
                committed_cents=m.committed_cents,
                monthly_cents=o.monthly_cents,
                near_limit=len(m.near_limit),
                proposals_waiting=m.proposals_waiting,
                note=m.note,
                lines=[_line(state, d) for d in m.lines],
            )
        )
    return DigestOut(
        turn=turn, month_label=format_turn(turn, state.save_meta.start_ym), areas=areas
    )


def run_by(state: GameState, area: str, slot: int, b: Balance, data: GameData) -> RunByOut:
    firm = state.player.id
    if area not in b.automation.areas:
        raise NotFoundError(f"no area {area!r}")
    o = state.automation.owner(firm, area, slot)
    return RunByOut(
        area=area,
        slot=slot,
        label=_label(state, area, slot, b),
        owner=_person(state, firm, area, o.person_id, b, data) if o else None,
        can_automate=owners.cant_automate(state, firm, area, slot, b, data) is None,
    )


# --- Router -------------------------------------------------------------------------------------


def _path(slug: str) -> Path:
    return saves.open_save(get_settings().resolved_save_dir(), slug)


def _view(path: Path) -> AutomationOut:
    state, balances = saves.read_state(path)
    cash = balances.get((state.player.id, CASH), 0)
    return automation_out(state, loader.game_data(), loader.balance(), cash)


def _act(slug: str, build: Any) -> AutomationOut:
    path = _path(slug)
    state = saves.read_state(path)[0]
    actor = managing_partner(state, state.player.id)
    if actor is None:
        raise NotFoundError("the firm has no managing partner to act")
    action: Action = build(actor)
    saves.run_action(path, action, loader.balance(), loader.game_data())
    return _view(path)


def make_automation_router(errors: dict[int | str, dict[str, Any]]) -> APIRouter:
    router = APIRouter()
    base = "/api/saves/{slug}/automation"
    kw: dict[str, Any] = {"response_model": AutomationOut, "responses": errors}

    @router.get(base, operation_id="getAutomation", **kw)
    def get_automation(slug: str) -> AutomationOut:
        return _view(_path(slug))

    @router.post(f"{base}/give", operation_id="giveArea", **kw)
    def give(slug: str, body: GiveIn) -> AutomationOut:
        return _act(
            slug,
            lambda a: GiveArea(
                a, body.area, body.person_id, body.slot, body.limit_cents, body.monthly_cents
            ),
        )

    @router.post(f"{base}/take-over", operation_id="takeOverArea", **kw)
    def take_over(slug: str, body: TakeOverIn) -> AutomationOut:
        return _act(slug, lambda a: TakeOverArea(a, body.area, body.slot))

    @router.post(f"{base}/settings", operation_id="setAreaSettings", **kw)
    def settings(slug: str, body: SettingsIn) -> AutomationOut:
        rails = (
            None
            if body.guardrails is None
            else tuple(sorted((g.key, g.value) for g in body.guardrails))
        )
        return _act(
            slug,
            lambda a: SetAreaSettings(
                a,
                body.area,
                body.slot,
                body.limit_cents,
                body.monthly_cents,
                body.priority,
                body.answer_events,
                rails,
            ),
        )

    @router.post(f"{base}/proposals/{{proposal_id}}/answer", operation_id="answerProposal", **kw)
    def answer(slug: str, proposal_id: int, body: AnswerIn) -> AutomationOut:
        return _act(slug, lambda a: AnswerProposal(a, proposal_id, body.approve))

    @router.get(
        f"{base}/digest/{{turn}}",
        response_model=DigestOut,
        responses=errors,
        operation_id="getDigest",
    )
    def get_digest(slug: str, turn: int) -> DigestOut:
        state = saves.read_state(_path(slug))[0]
        return digest_out(state, turn, loader.balance())

    @router.get(
        f"{base}/run-by/{{area}}",
        response_model=RunByOut,
        responses=errors,
        operation_id="getRunBy",
    )
    def get_run_by(slug: str, area: str, slot: int = 0) -> RunByOut:
        state = saves.read_state(_path(slug))[0]
        return run_by(state, area, slot, loader.balance(), loader.game_data())

    return router
