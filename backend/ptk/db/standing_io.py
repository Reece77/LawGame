"""Load and write reputation, the press and the rankings (schema v14, PT-M16).

One `standing` row holds the `StandingState` as JSON (current state, rewritten when it
changes). Every list the rankings publish is also appended to `ranking_entry` (one row a
place or band, never rewritten): the Rankings screen's history reads it, so the live state keeps
only each list's latest edition.

The codec rebuilds the frozen dataclasses from their type hints, as `ptk.db.leadership_io` does.
"""

from __future__ import annotations

import dataclasses
import json
import types
import typing
from dataclasses import asdict
from functools import cache
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ptk.db.models import RankingEntryRow, StandingRow
from ptk.sim.rankings.models import RankingsState
from ptk.sim.reputation.models import EMPTY_STANDING, StandingState

ROW_ID = 1  # the one row


@cache
def _hints(cls: type) -> dict[str, Any]:
    return typing.get_type_hints(cls)


def _decode(tp: Any, value: Any) -> Any:
    if value is None:
        return None
    origin = typing.get_origin(tp)
    if origin is typing.Union or origin is types.UnionType:
        opts = [a for a in typing.get_args(tp) if a is not type(None)]
        return _decode(opts[0], value) if len(opts) == 1 else value
    if isinstance(tp, typing.TypeAliasType):
        return _decode(tp.__value__, value)
    if origin is tuple:
        args = typing.get_args(tp)
        if len(args) == 2 and args[1] is Ellipsis:
            return tuple(_decode(args[0], v) for v in value)
        return tuple(_decode(a, v) for a, v in zip(args, value, strict=True))
    if dataclasses.is_dataclass(tp) and isinstance(tp, type):
        return from_dict(tp, value)
    return value


def from_dict[T](cls: type[T], data: dict[str, Any]) -> T:
    hints = _hints(cls)  # type: ignore[arg-type]
    return cls(**{k: _decode(hints[k], v) for k, v in data.items() if k in hints})


def load_standing(session: Session) -> StandingState:
    row = session.scalar(select(StandingRow).where(StandingRow.id == ROW_ID))
    if row is None:
        return EMPTY_STANDING
    return from_dict(StandingState, json.loads(row.data_json))


def write_standing(session: Session, standing: StandingState, turn: int | None = None) -> None:
    """The state's row; with `turn` (the month just played), that month's publications."""
    text = json.dumps(asdict(standing), sort_keys=True)
    row = session.get(StandingRow, ROW_ID)
    if row is None:
        if standing != EMPTY_STANDING:
            session.add(StandingRow(id=ROW_ID, data_json=text))
    elif row.data_json != text:
        row.data_json = text
    if turn is not None:
        session.add_all(published_rows(standing.rankings, turn))


def published_rows(rk: RankingsState, turn: int) -> list[RankingEntryRow]:
    """Rows for every list published in `turn` (its places, bands and named individuals)."""
    rows: list[RankingEntryRow] = []
    if rk.published_turn("tables") == turn:
        for t in rk.tables:
            rows.append(
                RankingEntryRow(
                    turn=turn,
                    kind=t.kind,
                    practice=None,
                    place=t.place,
                    firm_id=t.firm_id,
                    person_id=None,
                    name=t.name,
                    value_cents=t.value_cents,
                    count=t.lawyers,
                    year=t.year,
                )
            )
    if rk.published_turn("league") == turn:
        for r in rk.league:
            rows.append(
                RankingEntryRow(
                    turn=turn,
                    kind="league",
                    practice=r.practice,
                    place=r.place,
                    firm_id=r.firm_id,
                    person_id=None,
                    name=r.name,
                    value_cents=r.value_cents,
                    count=r.deals,
                    year=None,
                )
            )
    if rk.published_turn("places") == turn:
        for p in rk.places:
            rows.append(
                RankingEntryRow(
                    turn=turn,
                    kind="places",
                    practice=None,
                    place=p.place,
                    firm_id=p.firm_id,
                    person_id=None,
                    name=p.name,
                    value_cents=round(p.score * 100),
                    count=None,
                    year=p.year,
                )
            )
    if rk.published_turn("bands") == turn:
        for b in rk.bands:
            rows.append(
                RankingEntryRow(
                    turn=turn,
                    kind="bands",
                    practice=b.practice,
                    place=b.band,
                    firm_id=b.firm_id,
                    person_id=None,
                    name=b.name,
                    value_cents=round(b.score * 100),
                    count=None,
                    year=b.year,
                )
            )
        for x in rk.people:
            rows.append(
                RankingEntryRow(
                    turn=turn,
                    kind="people",
                    practice=x.practice,
                    place=x.band,
                    firm_id=x.firm_id,
                    person_id=x.person_id,
                    name=x.name,
                    value_cents=None,
                    count=None,
                    year=x.year,
                )
            )
    return rows


def band_history(session: Session, firm_id: int | None = None) -> list[RankingEntryRow]:
    """Every October's firm bands (one firm's, or all), oldest first."""
    q = select(RankingEntryRow).where(RankingEntryRow.kind == "bands")
    if firm_id is not None:
        q = q.where(RankingEntryRow.firm_id == firm_id)
    return list(session.scalars(q.order_by(RankingEntryRow.turn, RankingEntryRow.id)))
