"""Load and write technology (schema v16, PT-M14): one row holding the `TechState` as JSON (the
firm's adoption by era, its training programme and products; rewritten when it changes). The
codec is automation's (`ptk.db.automation_io`), over `ptk.sim.tech.models`' type hints.
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

from ptk.db.models import TechRow
from ptk.sim.tech import models as tm
from ptk.sim.tech.models import EMPTY_TECH, TechState

ROW_ID = 1  # the one row


@cache
def _hints(cls: type) -> dict[str, Any]:
    return typing.get_type_hints(cls, vars(tm))


def _decode(tp: Any, value: Any) -> Any:
    if value is None:
        return None
    origin = typing.get_origin(tp)
    if origin is typing.Union or origin is types.UnionType:
        opts = [a for a in typing.get_args(tp) if a is not type(None)]
        return _decode(opts[0], value) if len(opts) == 1 else value
    if origin is tuple:
        args = typing.get_args(tp)
        if len(args) == 2 and args[1] is Ellipsis:
            return tuple(_decode(args[0], v) for v in value)
        return tuple(_decode(a, v) for a, v in zip(args, value, strict=True))
    if dataclasses.is_dataclass(tp) and isinstance(tp, type):
        return _from_dict(tp, value)
    return value


def _from_dict[T](cls: type[T], data: dict[str, Any]) -> T:
    hints = _hints(cls)  # type: ignore[arg-type]
    return cls(**{k: _decode(hints[k], v) for k, v in data.items() if k in hints})


def load_tech(session: Session) -> TechState:
    row = session.scalar(select(TechRow).where(TechRow.id == ROW_ID))
    if row is None:
        return EMPTY_TECH
    return _from_dict(TechState, json.loads(row.data_json))


def write_tech(session: Session, tech: TechState) -> None:
    text = json.dumps(asdict(tech), sort_keys=True)
    row = session.get(TechRow, ROW_ID)
    if row is None:
        if tech != EMPTY_TECH:
            session.add(TechRow(id=ROW_ID, data_json=text))
    elif row.data_json != text:
        row.data_json = text
