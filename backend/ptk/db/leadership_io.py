"""Load and write seats, authority, pitches and seat decisions (schema v12, PT-M8): one row
holding the `LeadershipState` as JSON (current state, rewritten when it changes).

The codec rebuilds the frozen dataclasses of `ptk.sim.org.seat_models` from their type hints,
as `ptk.db.partnership_io` does for the partnership.
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

from ptk.db.models import LeadershipRow
from ptk.sim.org import seat_models as sm
from ptk.sim.org.seat_models import EMPTY_LEADERSHIP, LeadershipState, SeatDecision

ROW_ID = 1  # the one row


@cache
def _hints(cls: type) -> dict[str, Any]:
    return typing.get_type_hints(cls, vars(sm))


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


def load_leadership(session: Session) -> LeadershipState:
    row = session.scalar(select(LeadershipRow).where(LeadershipRow.id == ROW_ID))
    if row is None:
        return EMPTY_LEADERSHIP
    return from_dict(LeadershipState, json.loads(row.data_json))


def write_leadership(session: Session, ls: LeadershipState) -> None:
    text = json.dumps(asdict(ls), sort_keys=True)
    row = session.get(LeadershipRow, ROW_ID)
    if row is None:
        if ls != EMPTY_LEADERSHIP:
            session.add(LeadershipRow(id=ROW_ID, data_json=text))
    elif row.data_json != text:
        row.data_json = text


def write_seat_decisions(session: Session, turn: int, decisions: tuple[SeatDecision, ...]) -> None:
    """Seat holders' actions go to the decision log for history (ADR-0015 5); replay
    recomputes them from the state."""
    from ptk.db.org_io import log_decision

    for d in decisions:
        log_decision(session, turn, "seat", json.dumps(asdict(d), sort_keys=True))
