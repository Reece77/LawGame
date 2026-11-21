"""The History screen and the Overview's guidance (PT-M7; TST M29's What next and Getting
started, TST's History screen).

History: the firm's years (revenue, PEP, revenue per lawyer, margin, equity partners, its rank
among the rival firms by that year's revenue) from the turn snapshots; and the firm's timeline
(the inbox's notable items, and the legal market's dated events as they happened). Read-only.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Final

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from ptk import loader
from ptk.config import get_settings
from ptk.db import saves
from ptk.db.models import InboxItemRow
from ptk.db.session import make_sessionmaker, shared_engine
from ptk.sim.calendar import format_turn, turn_to_ym, ym_to_turn
from ptk.sim.data_models import GameData
from ptk.sim.state import GameState
from ptk.sim.whatnext import getting_started, what_next

# Inbox templates that make the firm's timeline (its milestones, not the month's routine).
TIMELINE: Final = (
    "stage_reached",
    "partner_admitted",
    "lateral_joined",
    "partner_leaving",
    "class_started",
    "client_failed",
    "client_rescued",
    "rfp_won",
    "election_won",
    "election_lost",
    "covenant_breach",
    "revolver_called",
    "firm_dissolved",
)
EVENT_WORDS: Final = {
    "merger": "merges with",
    "collapse": "collapses",
    "absorbed": "is absorbed",
    "rename": "is renamed",
    "outside_merger": "merges abroad",
}


class HistoryYearOut(BaseModel):
    year: int
    revenue_cents: int
    pep_cents: int | None
    rpl_cents: int | None
    margin_bp: int | None
    equity_partners: int
    rank: int | None  # among active firms with a recorded year, the player included
    firms_ranked: int
    complete: bool  # all twelve months played


class TimelineItemOut(BaseModel):
    turn: int
    date_label: str
    kind: str  # an inbox template id, or "market"
    title: str
    link_kind: str | None = None
    link_id: int | None = None


class HistoryOut(BaseModel):
    years: list[HistoryYearOut]
    timeline: list[TimelineItemOut]


class GuidanceItemOut(BaseModel):
    key: str
    text: str
    link_kind: str
    link_id: int | None = None


class GettingStartedStepOut(BaseModel):
    key: str
    text: str
    done: bool
    link_kind: str


class GuidanceOut(BaseModel):
    what_next: list[GuidanceItemOut]
    getting_started: list[GettingStartedStepOut]
    first_year: bool  # the guided first year runs (shown until done, at most two years)


def years_view(state: GameState, snaps: list[tuple[int, dict[str, Any]]]) -> list[HistoryYearOut]:
    start = state.save_meta.start_ym
    by_year: dict[int, list[tuple[int, dict[str, Any]]]] = {}
    for turn, kpis in snaps:
        by_year.setdefault(turn_to_ym(turn, start)[0], []).append((turn, kpis))
    out = []
    for year in sorted(by_year):
        rows = by_year[year]
        last = rows[-1][1]
        revenue = sum(int(k.get("revenue_cents") or 0) for _, k in rows)
        rivals = [
            next((h.revenue_cents for h in f.history if h.year == year), None)
            for f in state.rivals.firms
        ]
        known = [r for r in rivals if r is not None]
        complete = len(rows) == 12  # tunable-exempt: months in a year
        rank = 1 + sum(1 for r in known if r > revenue) if complete and known else None
        out.append(
            HistoryYearOut(
                year=year,
                revenue_cents=revenue,
                pep_cents=last.get("pep_cents"),
                rpl_cents=last.get("rpl_cents"),
                margin_bp=last.get("margin_bp"),
                equity_partners=int(last.get("equity_partners") or 0),
                rank=rank,
                firms_ranked=len(known) + 1 if rank is not None else 0,
                complete=complete,
            )
        )
    return out


def timeline_view(path: Path, state: GameState, data: GameData) -> list[TimelineItemOut]:
    start = state.save_meta.start_ym
    sessions = make_sessionmaker(shared_engine(path))
    with sessions() as session:
        rows = session.scalars(
            select(InboxItemRow)
            .where(InboxItemRow.template.in_(TIMELINE))
            .order_by(InboxItemRow.turn, InboxItemRow.id)
        ).all()
        items = [
            TimelineItemOut(
                turn=r.turn,
                date_label=format_turn(r.turn, start),
                kind=r.template,
                title=r.title,
                link_kind=r.link_kind,
                link_id=r.link_id,
            )
            for r in rows
        ]
    names = {f.key: f.name for f in data.rivals.firms.firms}
    for e in data.rivals.firms.events:
        turn = ym_to_turn(e.ym[0], e.ym[1], start)
        if 0 <= turn < state.turn:
            other = f" {names.get(e.other, e.other)}" if e.other and e.kind == "merger" else ""
            title = f"{names.get(e.firm, e.firm)} {EVENT_WORDS.get(e.kind, e.kind)}{other}"
            items.append(
                TimelineItemOut(
                    turn=turn, date_label=format_turn(turn, start), kind="market", title=title
                )
            )
    return sorted(items, key=lambda i: (i.turn, i.kind != "market", i.title))


def _path(slug: str) -> Path:
    return saves.open_save(get_settings().resolved_save_dir(), slug)


def make_history_router(errors: dict[int | str, dict[str, Any]]) -> APIRouter:
    router = APIRouter()
    base = "/api/saves/{slug}"

    @router.get(
        f"{base}/history", response_model=HistoryOut, responses=errors, operation_id="getHistory"
    )
    def get_history(slug: str) -> HistoryOut:
        path = _path(slug)
        state = saves.read_state(path)[0]
        snaps = saves.snapshots(path, state.player.id)
        return HistoryOut(
            years=years_view(state, snaps), timeline=timeline_view(path, state, loader.game_data())
        )

    @router.get(
        f"{base}/guidance", response_model=GuidanceOut, responses=errors, operation_id="getGuidance"
    )
    def get_guidance(slug: str) -> GuidanceOut:
        path = _path(slug)
        state = saves.read_state(path)[0]
        data, balance = loader.game_data(), loader.balance()
        snaps = saves.snapshots(path, state.player.id)
        raw = snaps[-1][1].get("utilisation_bp") if snaps else None
        util = int(raw) if isinstance(raw, int | float) else None
        sessions = make_sessionmaker(shared_engine(path))
        with sessions() as session:
            recent = tuple(
                session.scalars(
                    select(InboxItemRow.template).where(InboxItemRow.turn == state.turn - 1)
                ).all()
            )
        items = what_next(state, recent, util, data, balance)
        steps = getting_started(state, data, balance)
        return GuidanceOut(
            what_next=[GuidanceItemOut(**vars_of(i)) for i in items],
            getting_started=[GettingStartedStepOut(**vars_of(s)) for s in steps],
            first_year=state.turn < 24
            and not all(s.done for s in steps),  # tunable-exempt: 2 years
        )

    return router


def vars_of(obj: object) -> dict[str, Any]:
    return {k: getattr(obj, k) for k in obj.__slots__}  # type: ignore[attr-defined]
