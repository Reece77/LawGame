"""Conflicts of interest as an engine rule (ADR PT-0009).

The index: a firm's **current clients** are those on whose panel it sits that instructed it
within `conflicts.current_months`; **former clients** within `conflicts.former_months`; the
**adverse parties** are the adverse clients of its open matters. A new matter is a direct
conflict when its adverse party is a current client, or when its client is adverse on one
of the firm's open matters. A direct conflict is refused (the matter waits, `conflicted`,
for a waiver) unless the affected client has given an advance waiver. With checks off, the
matter opens unseen with `hidden_conflict` set, and may surface later (stream `conflict`).

Invariant (tests/property/test_matters.py): no open matter is adverse to a current client
unless it carries a waiver, the adverse client's advance waiver, or (checks skipped) a
hidden conflict.
"""

from __future__ import annotations

from dataclasses import dataclass

from ptk.sim.data_models import Balance
from ptk.sim.matters.models import MarketState, Matter


@dataclass(frozen=True, slots=True)
class ConflictIndex:
    current: frozenset[int]
    former: frozenset[int]
    adverse: frozenset[int]  # adverse clients of open matters
    advance_waivers: frozenset[int]


def conflict_index(market: MarketState, firm_id: int, turn: int, balance: Balance) -> ConflictIndex:
    cfg = balance.conflicts
    current, former, waivers = set(), set(), set()
    for rel in market.relationships:
        if rel.firm_id != firm_id or rel.last_instructed_turn is None:
            continue
        age = turn - rel.last_instructed_turn
        if age <= cfg.current_months:
            current.add(rel.client_id)
        elif age <= cfg.former_months:
            former.add(rel.client_id)
        if rel.advance_waiver:
            waivers.add(rel.client_id)
    adverse = {
        m.adverse_client_id for m in market.open_matters(firm_id) if m.adverse_client_id is not None
    }
    return ConflictIndex(
        current=frozenset(current),
        former=frozenset(former),
        adverse=frozenset(adverse),
        advance_waivers=frozenset(waivers),
    )


def affected_client(matter: Matter, index: ConflictIndex) -> int | None:
    """The client whose waiver the matter needs, or None if it is not a direct conflict."""
    adverse = matter.adverse_client_id
    if adverse is not None and adverse in index.current and adverse not in index.advance_waivers:
        return adverse
    if matter.client_id in index.adverse and matter.client_id not in index.advance_waivers:
        return matter.client_id
    return None


def open_conflicts(market: MarketState, firm_id: int, turn: int, balance: Balance) -> list[int]:
    """Open matters adverse to a current client with no waiver and no hidden flag (the
    invariant's violations; always empty)."""
    index = conflict_index(market, firm_id, turn, balance)
    out = []
    for m in market.open_matters(firm_id):
        adverse = m.adverse_client_id
        if adverse is None or adverse not in index.current:
            continue
        if m.waiver or m.hidden_conflict or adverse in index.advance_waivers:
            continue
        out.append(m.id)
    return out


def adverse_to(market: MarketState, firm_id: int, client_id: int) -> bool:
    """The firm acts against this client on an open matter (its flow is suspended)."""
    return any(m.adverse_client_id == client_id for m in market.open_matters(firm_id))
