"""Load and write billing (schema v6, PT-M3b) and the client-money book.

Engagements and bills keep every row: closed ones stay for the Finance and Matters screens'
history; the state loads only open engagements, open bills (and bills closed in the turn
being played) and the last twelve months' totals. Client funds are derived from the
client book, as cash is from the ledger; the provisions and deferred income from the
ledger's balances.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from sqlalchemy import delete, func, insert, or_, select
from sqlalchemy.orm import Session

from ptk.db.models import (
    BillingMonthRow,
    BillingPadderRow,
    BillRow,
    ClientBookEntryRow,
    ClientBookLineRow,
    EngagementRow,
    FlowAccountRow,
    LedgerEntryRow,
    LedgerLineRow,
)
from ptk.sim.billing.kpis import TRAILING
from ptk.sim.billing.models import (
    EMPTY_BILLING,
    Bill,
    BillingState,
    ClientBookEntry,
    ClientFunds,
    Dispute,
    Engagement,
    FlowAccount,
    MonthTotals,
)
from ptk.sim.ledger import (
    BAD_DEBT_PROVISION,
    DEFERRED_FEES,
    OWED_TO_CLIENTS,
    WIP_PROVISION,
    LedgerEntry,
    LedgerLine,
)


def _json(obj: Any) -> str:
    return json.dumps(asdict(obj), sort_keys=True)


def _bill(data: dict[str, Any]) -> Bill:
    d = data.pop("dispute")
    return Bill(**data, dispute=Dispute(**d) if d is not None else None)


def load_billing(session: Session, current_turn: int, player_id: int | None) -> BillingState:
    engagements = tuple(
        Engagement(**json.loads(r.data_json))
        for r in session.scalars(
            select(EngagementRow)
            .where(EngagementRow.closed.is_(False))
            .order_by(EngagementRow.matter_id)
        )
    )
    flows = tuple(
        sorted(
            (
                FlowAccount(**json.loads(r.data_json))
                for r in session.scalars(select(FlowAccountRow))
            ),
            key=lambda f: (f.client_id, f.practice),
        )
    )
    bills = tuple(
        _bill(json.loads(r.data_json))
        for r in session.scalars(
            select(BillRow)
            .where(
                or_(
                    BillRow.status.in_(("open", "disputed")),
                    BillRow.closed_turn >= current_turn - 1,
                )
            )
            .order_by(BillRow.id)
        )
    )
    months = tuple(
        MonthTotals(**json.loads(r.data_json))
        for r in session.scalars(
            select(BillingMonthRow)
            .where(BillingMonthRow.turn >= current_turn - TRAILING)
            .order_by(BillingMonthRow.firm_id, BillingMonthRow.turn)
        )
    )
    months = tuple(m for m in months if m.turn >= _cutoff(months, m.firm_id))
    last_id = session.scalar(select(func.max(BillRow.id)))
    owed = session.execute(
        select(
            ClientBookEntryRow.firm_id,
            ClientBookLineRow.client_id,
            func.sum(ClientBookLineRow.amount_cents),
        )
        .join(ClientBookEntryRow, ClientBookLineRow.entry_id == ClientBookEntryRow.id)
        .where(ClientBookLineRow.account == OWED_TO_CLIENTS)
        .group_by(ClientBookEntryRow.firm_id, ClientBookLineRow.client_id)
        .order_by(ClientBookEntryRow.firm_id, ClientBookLineRow.client_id)
    )
    funds = tuple(
        ClientFunds(client_id=int(c), firm_id=int(f), owed_cents=-int(total))
        for f, c, total in owed
        if int(total) != 0
    )
    padders = tuple(
        int(p)
        for p in session.scalars(
            select(BillingPadderRow.person_id).order_by(BillingPadderRow.person_id)
        )
    )
    if not (engagements or flows or bills or months or funds or last_id):
        return EMPTY_BILLING
    balances = _ledger(session, player_id)
    return BillingState(
        engagements=engagements,
        flows=flows,
        bills=bills,
        funds=funds,
        months=months,
        next_bill_id=(last_id or 0) + 1,
        wip_provision_cents=-balances.get(WIP_PROVISION, 0),
        bad_debt_provision_cents=-balances.get(BAD_DEBT_PROVISION, 0),
        deferred_cents=-balances.get(DEFERRED_FEES, 0),
        padding_found=padders,
    )


def _cutoff(months: tuple[MonthTotals, ...], firm_id: int) -> int:
    turns = sorted(m.turn for m in months if m.firm_id == firm_id)
    return turns[-TRAILING] if len(turns) >= TRAILING else (turns[0] if turns else 0)


def _ledger(session: Session, firm_id: int | None) -> dict[str, int]:
    if firm_id is None:
        return {}
    rows = session.execute(
        select(LedgerLineRow.account, func.sum(LedgerLineRow.amount_cents))
        .join(LedgerEntryRow, LedgerLineRow.entry_id == LedgerEntryRow.id)
        .where(
            LedgerEntryRow.firm_id == firm_id,
            LedgerLineRow.account.in_((WIP_PROVISION, BAD_DEBT_PROVISION, DEFERRED_FEES)),
        )
        .group_by(LedgerLineRow.account)
    )
    return {str(a): int(v) for a, v in rows}


def write_billing(session: Session, billing: BillingState) -> None:
    """Upsert engagements, bills and months in the state; rewrite flows and padders."""
    for e in billing.engagements:
        session.merge(
            EngagementRow(
                matter_id=e.matter_id,
                firm_id=e.firm_id,
                client_id=e.client_id,
                model=e.model,
                closed=e.closed,
                closed_turn=e.closed_turn,
                data_json=_json(e),
            )
        )
    for b in billing.bills:
        session.merge(
            BillRow(
                id=b.id,
                firm_id=b.firm_id,
                client_id=b.client_id,
                matter_id=b.matter_id,
                practice=b.practice,
                model=b.model,
                kind=b.kind,
                issued_turn=b.issued_turn,
                status=b.status,
                closed_turn=b.closed_turn,
                billed_cents=b.billed_cents,
                data_json=_json(b),
            )
        )
    for m in billing.months:
        session.merge(BillingMonthRow(firm_id=m.firm_id, turn=m.turn, data_json=_json(m)))
    session.execute(delete(FlowAccountRow))
    if billing.flows:
        session.execute(
            insert(FlowAccountRow),
            [
                {
                    "firm_id": f.firm_id,
                    "client_id": f.client_id,
                    "practice": f.practice,
                    "data_json": _json(f),
                }
                for f in billing.flows
            ],
        )
    session.execute(delete(BillingPadderRow))
    if billing.padding_found:
        session.execute(insert(BillingPadderRow), [{"person_id": p} for p in billing.padding_found])


def write_client_book(session: Session, entries: tuple[ClientBookEntry, ...]) -> None:
    for entry in entries:
        row = ClientBookEntryRow(turn=entry.turn, firm_id=entry.firm_id, memo=entry.memo)
        session.add(row)
        session.flush()
        session.add_all(
            ClientBookLineRow(
                entry_id=row.id,
                account=line.account,
                client_id=line.client_id,
                amount_cents=line.amount,
            )
            for line in entry.lines
        )


def client_book_balances(session: Session) -> dict[tuple[int, str, int], int]:
    """(firm id, account, client id) -> balance: the client book's trial balance."""
    rows = session.execute(
        select(
            ClientBookEntryRow.firm_id,
            ClientBookLineRow.account,
            ClientBookLineRow.client_id,
            func.sum(ClientBookLineRow.amount_cents),
        )
        .join(ClientBookEntryRow, ClientBookLineRow.entry_id == ClientBookEntryRow.id)
        .group_by(
            ClientBookEntryRow.firm_id, ClientBookLineRow.account, ClientBookLineRow.client_id
        )
    )
    return {(int(f), str(a), int(c)): int(v) for f, a, c, v in rows}


# --- Queries for the Finance and Matters screens (read-only) -----------------------------------


def firm_entries(session: Session, firm_id: int, first: int, last: int) -> list[LedgerEntry]:
    """The firm's ledger entries of turns first..last, in posting order."""
    entries = session.scalars(
        select(LedgerEntryRow)
        .where(
            LedgerEntryRow.firm_id == firm_id,
            LedgerEntryRow.turn >= first,
            LedgerEntryRow.turn <= last,
        )
        .order_by(LedgerEntryRow.id)
    ).all()
    if not entries:
        return []
    lines: dict[int, list[LedgerLine]] = {}
    for ln in session.scalars(
        select(LedgerLineRow)
        .where(LedgerLineRow.entry_id.in_([e.id for e in entries]))
        .order_by(LedgerLineRow.id)
    ):
        lines.setdefault(ln.entry_id, []).append(
            LedgerLine(ln.account, int(ln.amount_cents), ln.practice, ln.office_id)
        )
    return [
        LedgerEntry(turn=e.turn, firm_id=e.firm_id, memo=e.memo, lines=tuple(lines[e.id]))
        for e in entries
        if len(lines.get(e.id, ())) >= 2
    ]


def all_engagements(session: Session, firm_id: int) -> list[Engagement]:
    return [
        Engagement(**json.loads(r.data_json))
        for r in session.scalars(
            select(EngagementRow)
            .where(EngagementRow.firm_id == firm_id)
            .order_by(EngagementRow.matter_id)
        )
    ]


def matter_bills(session: Session, firm_id: int) -> dict[int, tuple[int, int, int]]:
    """matter id -> (billed, paid, credited + written off) over all its bills."""
    out: dict[int, tuple[int, int, int]] = {}
    for r in session.scalars(
        select(BillRow).where(BillRow.firm_id == firm_id, BillRow.matter_id.is_not(None))
    ):
        b = _bill(json.loads(r.data_json))
        assert b.matter_id is not None
        billed, paid, lost = out.get(b.matter_id, (0, 0, 0))
        out[b.matter_id] = (
            billed + b.billed_cents,
            paid + b.paid_cents,
            lost + b.credited_cents + b.written_off_cents,
        )
    return out
