"""Load and write the partnership (schema v8, PT-M4): one row per firm, its
`FirmPartnership` as JSON, and the counters for vote and approach ids.

The JSON codec is generic over the frozen dataclasses of `ptk.sim.partnership.models`:
tuples, optionals and nested dataclasses are rebuilt from the type hints.
"""

from __future__ import annotations

import dataclasses
import json
import types
import typing
from dataclasses import asdict, replace
from functools import cache
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ptk.db.models import PartnershipRow
from ptk.sim.partnership import models as pm
from ptk.sim.partnership.models import EMPTY_PARTNERSHIP, FirmPartnership, PartnershipState

COUNTERS_FIRM = 0  # the row holding the id counters (no firm has id 0)


@cache
def _hints(cls: type) -> dict[str, Any]:
    return typing.get_type_hints(cls, vars(pm))


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
    kwargs = {k: _decode(hints[k], v) for k, v in data.items() if k in hints}
    return cls(**kwargs)


def load_partnership(session: Session) -> PartnershipState:
    firms: list[FirmPartnership] = []
    counters: dict[str, int] = {}
    for row in session.scalars(select(PartnershipRow).order_by(PartnershipRow.firm_id)):
        data = json.loads(row.data_json)
        if row.firm_id == COUNTERS_FIRM:
            counters = data
        else:
            firms.append(from_dict(FirmPartnership, data))
    if not firms and not counters:
        return EMPTY_PARTNERSHIP
    return replace(
        EMPTY_PARTNERSHIP,
        firms=tuple(firms),
        next_vote_id=counters.get("next_vote_id", 1),
        next_approach_id=counters.get("next_approach_id", 1),
    )


def write_partnership(session: Session, ps: PartnershipState) -> None:
    rows = {
        COUNTERS_FIRM: {"next_vote_id": ps.next_vote_id, "next_approach_id": ps.next_approach_id}
    }
    for fp in ps.firms:
        rows[fp.firm_id] = asdict(fp)
    for firm_id, data in rows.items():
        text = json.dumps(data, sort_keys=True)
        row = session.get(PartnershipRow, firm_id)
        if row is None:
            session.add(PartnershipRow(firm_id=firm_id, data_json=text))
        elif row.data_json != text:
            row.data_json = text
