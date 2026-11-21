"""Load and write PT-M17's state (schema v11): the founder-life and family states as JSON
documents, and the players' personal books' entries (their own double entry).

The founder-life state's `pending` personal entries (actions' since the last turn) are written
to the personal book and never stored in the JSON. The JSON codec is generic over the frozen
dataclasses of `ptk.sim.founder.models` and `ptk.sim.family.models` (as partnership_io's).
"""

from __future__ import annotations

import dataclasses
import json
import types
import typing
from dataclasses import asdict, replace
from functools import cache
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ptk.db.models import FounderLifeRow, PersonalEntryRow, PersonalLineRow
from ptk.sim.family import models as fam
from ptk.sim.family.models import EMPTY_FAMILY, FamilyState
from ptk.sim.founder import models as fm
from ptk.sim.founder.models import EMPTY_FOUNDER_LIFE, FounderLifeState, PersonalEntry, PersonalLine

FOUNDER_KEY = "founder_life"
FAMILY_KEY = "family"


@cache
def _hints(cls: type) -> dict[str, Any]:
    return typing.get_type_hints(cls, {**vars(fm), **vars(fam)})


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


def load_founder_life(session: Session) -> tuple[FounderLifeState, FamilyState]:
    fl, fs = EMPTY_FOUNDER_LIFE, EMPTY_FAMILY
    for row in session.scalars(select(FounderLifeRow)):
        data = json.loads(row.data_json)
        if row.key == FOUNDER_KEY:
            fl = from_dict(FounderLifeState, data)
        elif row.key == FAMILY_KEY:
            fs = from_dict(FamilyState, data)
    return fl, fs


def write_founder_life(session: Session, fl: FounderLifeState, fs: FamilyState) -> None:
    """Write the two documents (only when they changed) and any pending personal entries."""
    write_personal_book(session, fl.pending)
    docs = {FOUNDER_KEY: asdict(replace(fl, pending=())), FAMILY_KEY: asdict(fs)}
    for key, data in docs.items():
        text = json.dumps(data, sort_keys=True)
        row = session.get(FounderLifeRow, key)
        if row is None:
            if data == asdict(EMPTY_FOUNDER_LIFE if key == FOUNDER_KEY else EMPTY_FAMILY):
                continue  # nothing to store yet
            session.add(FounderLifeRow(key=key, data_json=text))
        elif row.data_json != text:
            row.data_json = text


def write_personal_book(session: Session, entries: tuple[PersonalEntry, ...]) -> None:
    for entry in entries:
        row = PersonalEntryRow(
            turn=entry.turn, person_id=entry.person_id, memo=entry.memo, source=entry.source
        )
        session.add(row)
        session.flush()
        for line in entry.lines:
            session.add(
                PersonalLineRow(entry_id=row.id, account=line.account, amount_cents=line.amount)
            )


def personal_entries(
    session: Session, person_id: int | None = None, since_turn: int = 0
) -> tuple[PersonalEntry, ...]:
    """The personal book's entries (a player's, or everyone's), in the order written."""
    q = select(PersonalEntryRow).where(PersonalEntryRow.turn >= since_turn)
    if person_id is not None:
        q = q.where(PersonalEntryRow.person_id == person_id)
    rows = list(session.scalars(q.order_by(PersonalEntryRow.id)))
    lines: dict[int, list[PersonalLine]] = {}
    ids = [r.id for r in rows]
    if ids:
        for ln in session.scalars(
            select(PersonalLineRow)
            .where(PersonalLineRow.entry_id.in_(ids))
            .order_by(PersonalLineRow.id)
        ):
            lines.setdefault(ln.entry_id, []).append(PersonalLine(ln.account, ln.amount_cents))
    return tuple(
        PersonalEntry(r.turn, r.person_id, r.memo, r.source, tuple(lines[r.id])) for r in rows
    )


def personal_balances(session: Session) -> dict[tuple[int, str], int]:
    """(person id, account) -> balance, summed from the entries (the book's own check)."""
    rows = session.execute(
        select(
            PersonalEntryRow.person_id,
            PersonalLineRow.account,
            func.sum(PersonalLineRow.amount_cents),
        )
        .join(PersonalEntryRow, PersonalLineRow.entry_id == PersonalEntryRow.id)
        .group_by(PersonalEntryRow.person_id, PersonalLineRow.account)
    )
    return {(int(p), str(a)): int(v) for p, a, v in rows if v}
