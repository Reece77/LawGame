"""Load and write automation (schema v14, PT-M9): one row holding the `AutomationState` as JSON
(areas' owners, their decisions and proposals; rewritten when it changes), and the owners'
decisions in the decision log for history (ADR-0015 5: replay recomputes them).

The codec rebuilds the frozen dataclasses of `ptk.sim.automation.models` from their type hints,
as `ptk.db.leadership_io` does for the seats.
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

from ptk.db.models import AutomationRow
from ptk.sim.automation import models as am
from ptk.sim.automation.models import EMPTY_AUTOMATION, AreaDecision, AutomationState

ROW_ID = 1  # the one row


@cache
def _hints(cls: type) -> dict[str, Any]:
    return typing.get_type_hints(cls, vars(am))


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


def decode_with[T](cls: type[T], data: dict[str, Any], namespace: dict[str, Any]) -> T:
    """PT-M11: `from_dict` for another module's dataclasses (their type hints resolved in
    `namespace`), so a JSON row of any state section decodes the same way."""
    hints = typing.get_type_hints(cls, namespace)
    out: dict[str, Any] = {}
    for k, v in data.items():
        if k not in hints:
            continue
        out[k] = _decode_ns(hints[k], v, namespace)
    return cls(**out)


def _decode_ns(tp: Any, value: Any, namespace: dict[str, Any]) -> Any:
    if value is None:
        return None
    origin = typing.get_origin(tp)
    if origin is typing.Union or origin is types.UnionType:
        opts = [a for a in typing.get_args(tp) if a is not type(None)]
        return _decode_ns(opts[0], value, namespace) if len(opts) == 1 else value
    if isinstance(tp, typing.TypeAliasType):
        return _decode_ns(tp.__value__, value, namespace)
    if origin is tuple:
        args = typing.get_args(tp)
        if len(args) == 2 and args[1] is Ellipsis:
            return tuple(_decode_ns(args[0], v, namespace) for v in value)
        return tuple(_decode_ns(a, v, namespace) for a, v in zip(args, value, strict=True))
    if dataclasses.is_dataclass(tp) and isinstance(tp, type):
        return decode_with(tp, value, namespace)
    return value


def load_automation(session: Session) -> AutomationState:
    row = session.scalar(select(AutomationRow).where(AutomationRow.id == ROW_ID))
    if row is None:
        return EMPTY_AUTOMATION
    return from_dict(AutomationState, json.loads(row.data_json))


def write_automation(session: Session, auto: AutomationState) -> None:
    text = json.dumps(asdict(auto), sort_keys=True)
    row = session.get(AutomationRow, ROW_ID)
    if row is None:
        if auto != EMPTY_AUTOMATION:
            session.add(AutomationRow(id=ROW_ID, data_json=text))
    elif row.data_json != text:
        row.data_json = text


def write_area_decisions(session: Session, turn: int, decisions: tuple[AreaDecision, ...]) -> None:
    """Owners' decisions go to the decision log (source "area") for history; replay
    recomputes them from the state (ADR-0015 5)."""
    from ptk.db.org_io import log_decision

    for d in decisions:
        log_decision(session, turn, "area", json.dumps(asdict(d), sort_keys=True))
