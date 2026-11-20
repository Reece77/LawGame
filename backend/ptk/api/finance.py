"""Finance endpoints (PT-M3b; spec 8.2, 16's Finance screen; ADR-0009, ADR-0014).

The firm's revenue chain as the player sees it: KPIs (utilisation, realisation, collection,
lockup), the P&L in its accrual and cash views, the balance sheet, WIP and receivables
ageing, the client account's total, open bills with their disputes, and each named matter's
money (model, WIP, billed, collected, realisation) for the Matters screen. Writes are one
action each (`saves.run_action`): a partner's write-down, an answer to a dispute.

Nothing here is hidden: billing holds no hidden values (a padder's time is shown only once a
dispute brings it to light, as a credit note).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ptk import loader
from ptk.config import get_settings
from ptk.db import saves
from ptk.db.billing_io import all_engagements, firm_entries, matter_bills
from ptk.db.session import make_sessionmaker, shared_engine
from ptk.sim.billing import statements
from ptk.sim.billing.actions import BillingAction, RespondDispute, WriteDownMatter
from ptk.sim.billing.kpis import DAYS_PER_MONTH
from ptk.sim.billing.models import BillingState, Engagement
from ptk.sim.calendar import format_turn, turn_to_ym
from ptk.sim.data_models import GameData
from ptk.sim.errors import NotFoundError
from ptk.sim.ledger import UNDISTRIBUTED_PROFIT
from ptk.sim.money import BP_DENOMINATOR, round_half_even
from ptk.sim.partnership.common import cumulative_pnl
from ptk.sim.state import GameState

RECEIVABLE_BUCKETS = ((0, 30), (31, 60), (61, 90), (91, 180), (181, None))  # tunable-exempt: days
WIP_BUCKETS = ((0, 30), (31, 90), (91, 180), (181, 365), (366, None))  # tunable-exempt: days


class KpisOut(BaseModel):
    revenue_cents: int  # last month, accrual view
    collections_cents: int  # last month, the cash view's revenue
    wip_cents: int
    receivables_cents: int
    client_money_cents: int  # held in the client account (never firm cash)
    utilisation_bp: int | None
    realisation_bp: int | None
    collection_bp: int | None
    lockup_days: int | None
    open_disputes: int


class PnlLineOut(BaseModel):
    account: str
    label: str
    amount_cents: int  # income and costs both positive


class PnlOut(BaseModel):
    label: str  # "2006", "2007 to date"
    basis: Literal["accrual", "cash"]
    revenue_cents: int
    costs_cents: int
    profit_cents: int
    lines: list[PnlLineOut]


class BalanceLineOut(BaseModel):
    account: str
    label: str
    kind: Literal["asset", "liability", "equity"]
    amount_cents: int  # assets positive; liabilities and equity positive as owed


class AgeBucketOut(BaseModel):
    label: str
    amount_cents: int
    count: int


class MonthOut(BaseModel):
    turn: int
    label: str
    revenue_cents: int
    collections_cents: int
    lockup_days: int | None


class FinanceOut(BaseModel):
    date_label: str
    kpis: KpisOut
    months: list[MonthOut]
    statements: list[PnlOut]
    balance_sheet: list[BalanceLineOut]
    wip_ageing: list[AgeBucketOut]
    receivables_ageing: list[AgeBucketOut]


class DisputeOut(BaseModel):
    amount_cents: int
    raised_label: str
    expires_label: str


class BillOut(BaseModel):
    id: int
    client_id: int
    client: str
    matter_id: int | None
    matter: str | None  # None: flow work
    practice: str
    model: str
    issued_label: str
    age_days: int
    billed_cents: int
    outstanding_cents: int
    status: str
    dispute: DisputeOut | None


class MatterMoneyOut(BaseModel):
    matter_id: int
    model: str
    closed: bool
    wip_cents: int  # unbilled, at standard
    standard_cents: int  # all work at standard so far
    billed_cents: int
    collected_cents: int
    realisation_bp: int | None  # billed / standard of the work billed
    writedown_bp: int  # the partner's write-down waiting for the next bill
    funds_cents: int  # money on account held for the matter


class WriteDownIn(BaseModel):
    matter_id: int
    bp: int = Field(ge=0, le=10_000)


class DisputeIn(BaseModel):
    choice: Literal["concede", "negotiate", "hold"]


def _path(slug: str) -> Path:
    return saves.open_save(get_settings().resolved_save_dir(), slug)


def _label(state: GameState, turn: int) -> str:
    return format_turn(turn, state.save_meta.start_ym)


def _names(data: GameData) -> dict[str, tuple[str, str]]:
    return {a.code: (a.name, a.type) for a in data.accounts}


def _age(bucket: tuple[int, int | None]) -> str:
    lo, hi = bucket
    return f"{lo}+ days" if hi is None else f"{lo}-{hi} days"


def _bucket(days: int, buckets: tuple[tuple[int, int | None], ...]) -> int:
    for i, (_lo, hi) in enumerate(buckets):
        if hi is None or days <= hi:
            return i
    return len(buckets) - 1


def _days(months: int) -> int:
    return round(months * DAYS_PER_MONTH)


def finance_view(path: Path, state: GameState, data: GameData) -> FinanceOut:
    firm = state.player.id
    billing = state.billing
    last = state.turn - 1
    year = turn_to_ym(max(0, last), state.save_meta.start_ym)[0]
    start_year = state.save_meta.start_ym[0]
    # turn of January of `year`: months since the start
    jan = (year - start_year) * 12 - (state.save_meta.start_ym[1] - 1)
    sessions = make_sessionmaker(shared_engine(path))
    with sessions() as session:
        entries = firm_entries(session, firm, max(0, jan - 12), last)
        snaps = saves_snapshots(session, firm)
    _, balances = saves.read_state(path)
    names = _names(data)
    statements_out: list[PnlOut] = []
    for label, lo, hi in (
        (f"{year} to date", jan, last),
        (str(year - 1), jan - 12, jan - 1),
    ):
        if hi < 0:
            continue
        period = [e for e in entries if lo <= e.turn <= hi]
        for basis, pnl in (
            ("accrual", statements.accrual_pnl(period)),
            ("cash", statements.cash_pnl(period)),
        ):
            statements_out.append(
                PnlOut(
                    label=label,
                    basis=basis,
                    revenue_cents=pnl.revenue_cents,
                    costs_cents=pnl.costs_cents,
                    profit_cents=pnl.profit_cents,
                    lines=[
                        PnlLineOut(
                            account=a,
                            label=names.get(a, ("Collections", ""))[0],
                            amount_cents=v,
                        )
                        for a, v in pnl.lines
                        if v != 0
                    ],
                )
            )
    sheet = [
        BalanceLineOut(
            account=a,
            label=names[a][0],
            kind=names[a][1],
            amount_cents=v if a[0] == "1" else -v,
        )
        for a, v in statements.balance_sheet(balances, firm)
        if a in names
    ]
    # PT-M4: income and cost accounts are never closed; the profit of the years before this
    # one (less what was allocated to partners, on 3100) is shown as undistributed profit, so
    # the sheet balances against this year's profit
    revenue, costs = cumulative_pnl(balances, firm)
    ytd = next((s.profit_cents for s in statements_out if s.basis == "accrual"), 0)
    earlier = revenue - costs - ytd
    if earlier:
        names3100 = names.get(UNDISTRIBUTED_PROFIT, ("Undistributed profit", "equity"))
        line = next((x for x in sheet if x.account == UNDISTRIBUTED_PROFIT), None)
        if line is None:
            sheet.append(
                BalanceLineOut(
                    account=UNDISTRIBUTED_PROFIT,
                    label=names3100[0],
                    kind=names3100[1],
                    amount_cents=earlier,
                )
            )
            sheet.sort(key=lambda x: x.account)
        else:
            line.amount_cents += earlier
    latest = snaps[-1][1] if snaps else {}
    kpis = KpisOut(
        revenue_cents=_int(latest.get("revenue_cents")),
        collections_cents=_int(latest.get("collections_cents")),
        wip_cents=_wip(billing, firm),
        receivables_cents=sum(b.outstanding_cents for b in billing.bills if b.is_open),
        client_money_cents=sum(f.owed_cents for f in billing.funds if f.firm_id == firm),
        utilisation_bp=_opt(latest.get("utilisation_bp")),
        realisation_bp=_opt(latest.get("realisation_bp")),
        collection_bp=_opt(latest.get("collection_bp")),
        lockup_days=_opt(latest.get("lockup_days")),
        open_disputes=sum(1 for b in billing.bills if b.dispute is not None),
    )
    months = [
        MonthOut(
            turn=t,
            label=_label(state, t),
            revenue_cents=_int(k.get("revenue_cents")),
            collections_cents=_int(k.get("collections_cents")),
            lockup_days=_opt(k.get("lockup_days")),
        )
        for t, k in snaps[-24:]
    ]
    return FinanceOut(
        date_label=_label(state, state.turn),
        kpis=kpis,
        months=months,
        statements=statements_out,
        balance_sheet=sheet,
        wip_ageing=_wip_ageing(billing, firm, state.turn),
        receivables_ageing=_ar_ageing(billing, firm, state.turn),
    )


def _opt(v: object) -> int | None:
    return v if isinstance(v, int) else None


def _int(v: object) -> int:
    return v if isinstance(v, int) else 0


def _wip(billing: BillingState, firm: int) -> int:
    return sum(
        e.wip_cents for e in billing.engagements if e.firm_id == firm and not e.closed
    ) + sum(f.wip_cents for f in billing.flows if f.firm_id == firm)


def _wip_ageing(billing: BillingState, firm: int, turn: int) -> list[AgeBucketOut]:
    """Unbilled WIP by the months since the account was last billed (or opened)."""
    sums = [0] * len(WIP_BUCKETS)
    counts = [0] * len(WIP_BUCKETS)
    rows: list[tuple[int, int]] = [
        (e.wip_cents, turn - (e.last_bill_turn if e.last_bill_turn is not None else e.opened_turn))
        for e in billing.engagements
        if e.firm_id == firm and not e.closed and e.wip_cents > 0
    ]
    rows += [
        (f.wip_cents, turn - f.last_bill_turn if f.last_bill_turn is not None else 1)
        for f in billing.flows
        if f.firm_id == firm and f.wip_cents > 0
    ]
    for cents, months in rows:
        i = _bucket(_days(months), WIP_BUCKETS)
        sums[i] += cents
        counts[i] += 1
    return [
        AgeBucketOut(label=_age(b), amount_cents=s, count=c)
        for b, s, c in zip(WIP_BUCKETS, sums, counts, strict=True)
    ]


def _ar_ageing(billing: BillingState, firm: int, turn: int) -> list[AgeBucketOut]:
    sums = [0] * len(RECEIVABLE_BUCKETS)
    counts = [0] * len(RECEIVABLE_BUCKETS)
    for b in billing.bills:
        if b.firm_id != firm or not b.is_open:
            continue
        i = _bucket(_days(turn - b.issued_turn), RECEIVABLE_BUCKETS)
        sums[i] += b.outstanding_cents
        counts[i] += 1
    return [
        AgeBucketOut(label=_age(b), amount_cents=s, count=c)
        for b, s, c in zip(RECEIVABLE_BUCKETS, sums, counts, strict=True)
    ]


def saves_snapshots(session: Any, firm_id: int) -> list[tuple[int, dict[str, object]]]:
    import json

    from sqlalchemy import select

    from ptk.db.models import TurnSnapshotRow

    rows = session.scalars(
        select(TurnSnapshotRow)
        .where(TurnSnapshotRow.firm_id == firm_id)
        .order_by(TurnSnapshotRow.turn)
    )
    return [(r.turn, json.loads(r.kpis_json)) for r in rows]


def bills_view(state: GameState, status: str) -> list[BillOut]:
    out = []
    for b in state.billing.bills:
        if b.firm_id != state.player.id:
            continue
        if status == "open" and not b.is_open:
            continue
        if status == "disputed" and b.dispute is None:
            continue
        m = state.market.matter(b.matter_id) if b.matter_id is not None else None
        out.append(
            BillOut(
                id=b.id,
                client_id=b.client_id,
                client=state.market.client(b.client_id).name,
                matter_id=b.matter_id,
                matter=m.name if m is not None else None,
                practice=b.practice,
                model=b.model,
                issued_label=_label(state, b.issued_turn),
                age_days=_days(state.turn - b.issued_turn),
                billed_cents=b.billed_cents,
                outstanding_cents=b.outstanding_cents,
                status=b.status,
                dispute=None
                if b.dispute is None
                else DisputeOut(
                    amount_cents=b.dispute.amount_cents,
                    raised_label=_label(state, b.dispute.raised_turn),
                    expires_label=_label(state, b.dispute.expires_turn),
                ),
            )
        )
    return out


def matter_money_view(path: Path, state: GameState) -> list[MatterMoneyOut]:
    firm = state.player.id
    sessions = make_sessionmaker(shared_engine(path))
    with sessions() as session:
        stored = {e.matter_id: e for e in all_engagements(session, firm)}
        bills = matter_bills(session, firm)
    current = {e.matter_id: e for e in state.billing.engagements if e.firm_id == firm}
    merged: dict[int, Engagement] = {**stored, **current}
    out = []
    for mid in sorted(merged):
        e = merged[mid]
        _billed, paid, _lost = bills.get(mid, (0, 0, 0))
        relieved = e.standard_cents - e.wip_cents
        out.append(
            MatterMoneyOut(
                matter_id=mid,
                model=e.model,
                closed=e.closed,
                wip_cents=0 if e.closed else e.wip_cents,
                standard_cents=e.standard_cents,
                billed_cents=e.billed_cents,
                collected_cents=paid,
                realisation_bp=None
                if relieved <= 0
                else round_half_even(e.billed_cents * BP_DENOMINATOR, relieved),
                writedown_bp=e.writedown_bp,
                funds_cents=e.funds_cents,
            )
        )
    return out


def _founder(state: GameState) -> int:
    founder = state.founder_of(state.player.id)
    if founder is None:
        raise NotFoundError("the firm has no founding partner to act")
    return founder


def _act(slug: str, make: Any) -> tuple[Path, GameState]:
    path = _path(slug)
    state = saves.read_state(path)[0]
    action: BillingAction = make(_founder(state))
    saves.run_action(path, action, loader.balance(), loader.game_data())
    return path, saves.read_state(path)[0]


def make_finance_router(errors: dict[int | str, dict[str, Any]]) -> APIRouter:
    router = APIRouter()
    base = "/api/saves/{slug}/finance"

    @router.get(base, response_model=FinanceOut, responses=errors, operation_id="getFinance")
    def get_finance(slug: str) -> FinanceOut:
        path = _path(slug)
        state = saves.read_state(path)[0]
        return finance_view(path, state, loader.game_data())

    @router.get(
        f"{base}/bills", response_model=list[BillOut], responses=errors, operation_id="listBills"
    )
    def list_bills(
        slug: str, status: Literal["open", "disputed", "recent"] = "open"
    ) -> list[BillOut]:
        return bills_view(saves.read_state(_path(slug))[0], status)

    @router.get(
        f"{base}/matters",
        response_model=list[MatterMoneyOut],
        responses=errors,
        operation_id="listMatterMoney",
    )
    def list_matter_money(slug: str) -> list[MatterMoneyOut]:
        path = _path(slug)
        return matter_money_view(path, saves.read_state(path)[0])

    @router.post(
        f"{base}/write-down",
        response_model=list[MatterMoneyOut],
        responses=errors,
        operation_id="writeDownMatter",
    )
    def write_down(slug: str, body: WriteDownIn) -> list[MatterMoneyOut]:
        path, state = _act(slug, lambda a: WriteDownMatter(a, body.matter_id, body.bp))
        return matter_money_view(path, state)

    @router.post(
        f"{base}/bills/{{bill_id}}/dispute",
        response_model=list[BillOut],
        responses=errors,
        operation_id="respondDispute",
    )
    def respond(slug: str, bill_id: int, body: DisputeIn) -> list[BillOut]:
        _, state = _act(slug, lambda a: RespondDispute(a, bill_id, body.choice))
        return bills_view(state, "open")

    return router
