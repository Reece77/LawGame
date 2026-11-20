"""Load and write the rivals' state (schema v9, PT-M5).

The rivals' state (`RivalsState` without its people) is one JSON document in `rival_state`,
rewritten each turn; a generic codec turns the frozen dataclasses into JSON and back from
their type hints, so floats round-trip exactly (repr) and a reloaded save plays identically.
Rival key people are not stored: each is generated on demand from its member record (a pure
function of the seed; ptk.sim.rivals.people). Rival firms also get `firm` rows (not the
player's), because ledger entries and the turn log refer to firm ids.
"""

from __future__ import annotations

import dataclasses
import json
import types
import typing
from functools import cache
from typing import Any

from sqlalchemy import func, insert, select
from sqlalchemy.orm import Session

from ptk.db.models import (
    ClientRow,
    DecisionLogRow,
    FirmRow,
    RivalStateRow,
)
from ptk.sim.matters.models import MarketState
from ptk.sim.rivals.models import RivalMove, RivalsState

STATE_ID = 1

# Decoding the rivals is the slowest part of loading a save, so the last state written or
# read is kept per save file and reused when the stored text is identical (a cache of
# immutable values, checked against the database every time: ADR-0004 still holds, the
# database is the truth).
_CACHE: dict[str, tuple[str, RivalsState]] = {}


def _key(session: Session) -> str:
    bind = session.get_bind()
    return str(bind.engine.url)


# --- A codec for frozen dataclasses ----------------------------------------------------------


_PRIMITIVE = (int, float, str, bool, type(None))


_FIELDS: dict[type, tuple[str, ...]] = {}


def _names(cls: type) -> tuple[str, ...]:
    names = _FIELDS.get(cls)
    if names is None:
        names = _FIELDS[cls] = tuple(f.name for f in dataclasses.fields(cls))
    return names


def encode(value: Any) -> Any:
    if isinstance(value, _PRIMITIVE):
        return value
    if isinstance(value, tuple | list):
        if all(isinstance(v, _PRIMITIVE) for v in value):
            return list(value)
        return [encode(v) for v in value]
    return {name: encode(getattr(value, name)) for name in _names(type(value))}


@cache
def _hints(cls: type) -> dict[str, Any]:
    import ptk.sim.rivals.models as models

    return typing.get_type_hints(cls, globalns=vars(models))


def decode(tp: Any, value: Any) -> Any:
    tp = _resolve(tp)
    origin = typing.get_origin(tp)
    if value is None:
        return None
    if origin is typing.Union or origin is types.UnionType:
        options = [a for a in typing.get_args(tp) if a is not type(None)]
        return decode(options[0], value)
    if origin is tuple:
        args = typing.get_args(tp)
        if len(args) == 2 and args[1] is Ellipsis:
            return tuple(decode(args[0], v) for v in value)
        return tuple(decode(a, v) for a, v in zip(args, value, strict=True))
    if origin is typing.Literal:
        return value
    if dataclasses.is_dataclass(tp) and isinstance(tp, type):
        hints = _hints(tp)
        return tp(**{k: decode(hints[k], v) for k, v in value.items()})
    if tp is float:
        return float(value)
    return value


def _resolve(tp: Any) -> Any:
    """Unwrap `type X = ...` aliases."""
    while isinstance(tp, typing.TypeAliasType):
        tp = tp.__value__
    return tp


# --- Persistence ------------------------------------------------------------------------------


def rivals_json(rivals: RivalsState) -> str:
    doc = encode(rivals)
    return json.dumps(doc, separators=(",", ":"))


def insert_rivals(session: Session, rivals: RivalsState) -> None:
    if not rivals.firms:
        return
    _firm_rows(session, rivals)
    session.add(
        RivalStateRow(id=STATE_ID, real_people=rivals.real_people, data_json=rivals_json(rivals))
    )


def _firm_rows(session: Session, rivals: RivalsState) -> None:
    known = set(session.scalars(select(FirmRow.id)))
    for f in rivals.firms:
        if f.id in known:
            continue
        session.add(
            FirmRow(
                id=f.id,
                name=f.name,
                is_player=False,
                stage=0,
                founded_turn=f.founded_turn,
                home_city=f.hq,
                pay_policy_mode="match",
                pay_policy_bp=10_000,  # tunable-exempt
                conflict_checks=True,
            )
        )
    session.flush()


def write_rivals(session: Session, rivals: RivalsState) -> None:
    row = session.get(RivalStateRow, STATE_ID)
    if row is None:
        return
    _firm_rows(session, rivals)
    text = rivals_json(rivals)
    row.data_json = text
    _CACHE[_key(session)] = (text, rivals)


def load_rivals(session: Session) -> RivalsState:
    row = session.get(RivalStateRow, STATE_ID)
    if row is None:
        return RivalsState()
    key = _key(session)
    cached = _CACHE.get(key)
    if cached is not None and cached[0] == row.data_json:
        return cached[1]
    rivals: RivalsState = decode(RivalsState, json.loads(row.data_json))
    _CACHE[key] = (row.data_json, rivals)
    return rivals


_PANELS: dict[str, dict[int, tuple[str, ...]]] = {}


def write_panels(session: Session, market: MarketState) -> None:
    """Client panels change with RFP awards, mergers and collapses (PT-M5): rewrite the client
    rows whose panel differs from what is stored (clients are otherwise written once)."""
    key = _key(session)
    stored = _PANELS.get(key)
    if stored is None:
        stored = {
            r.id: tuple(json.loads(r.data_json)["panel"])
            for r in session.scalars(select(ClientRow))
        }
    for c in market.clients:
        if stored.get(c.id) == c.panel:
            continue
        row = session.get(ClientRow, c.id)
        if row is None:
            continue
        doc = json.loads(row.data_json)
        doc["panel"] = list(c.panel)
        row.data_json = json.dumps(doc)
        stored[c.id] = c.panel
    _PANELS[key] = stored


def write_rival_moves(session: Session, turn: int, moves: tuple[RivalMove, ...]) -> None:
    """Rival decisions go to the decision log for history (ADR-0015 5); replay recomputes
    them from the state, never re-applies them."""
    if not moves:
        return
    last = session.scalar(select(func.max(DecisionLogRow.seq)).where(DecisionLogRow.turn == turn))
    seq = last or 0
    rows = []
    for m in moves:
        seq += 1
        payload = json.dumps(encode(m), sort_keys=True)
        rows.append({"turn": turn, "seq": seq, "source": "rival", "payload_json": payload})
    session.execute(insert(DecisionLogRow), rows)


def rival_firm_ids(session: Session) -> set[int]:
    row = session.get(RivalStateRow, STATE_ID)
    if row is None:
        return set()
    return {int(f["id"]) for f in json.loads(row.data_json)["firms"]}
