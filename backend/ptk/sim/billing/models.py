"""Frozen billing models (spec 7.7; ADR PT-0003 sections 2 and 7, PT-0005). Never mutate.

Billing keeps its own books of the firm's revenue chain beside the ledger: unbilled WIP at
standard value per engagement (a named matter) and per flow account (a client's flow work in
one practice), the open bills, the client-money balances and twelve months of totals for the
KPIs. Every amount here is integer cents; hours are integer tenths.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

# spec 7.7's billing models
type BillingModel = Literal[
    "hourly", "blended", "capped", "fixed", "success", "contingency", "retainer"
]
BILLING_MODELS: tuple[BillingModel, ...] = (
    "hourly",
    "blended",
    "capped",
    "fixed",
    "success",
    "contingency",
    "retainer",
)
type BillStatus = Literal["open", "disputed", "paid", "written_off"]
type BillKind = Literal["fees", "retainer_advance", "final", "contingency", "success"]
type DisputeChoice = Literal["concede", "negotiate", "hold"]
DISPUTE_CHOICES: tuple[DisputeChoice, ...] = ("concede", "negotiate", "hold")


@dataclass(frozen=True, slots=True)
class Engagement:
    """A named matter's billing terms (drawn when billing first sees the matter) and its
    unbilled work. `price_cents` is the cap (capped), the price (fixed) or the monthly fee
    (retainer); `rate_cents` the blended rate an hour (blended)."""

    matter_id: int
    firm_id: int
    client_id: int
    practice: str
    model: BillingModel
    opened_turn: int
    cycle_months: int = 1  # bills issue every this many months
    term_months: int = 0  # retainer: the months the fee covers; then the matter bills hourly
    months_billed: int = 0  # retainer: months earned so far
    discount_bp: int = 0  # off standard rates (hourly, capped, success, blended)
    price_cents: int = 0
    rate_cents: int = 0
    share_bp: int = 0  # success: the hourly share of standard; contingency: the fee share
    bonus_cents: int = 0  # success: paid on a win or a closed deal
    wip_cents: int = 0  # unbilled, at standard value
    wip_tenths: int = 0  # unbilled hours
    standard_cents: int = 0  # all work so far at standard value
    billed_cents: int = 0  # all fees billed so far (net of rejections, before credit notes)
    last_bill_turn: int | None = None
    writedown_bp: int = 0  # the partner's write-down on the next bill (an action)
    advance_turn: int | None = None  # retainer: the month the last advance bill covers
    offer_bp: int | None = None  # the last settlement offer seen (cases)
    funds_cents: int = 0  # money on account in the client book for this matter
    closed: bool = False
    closed_turn: int | None = None  # the turn billing closed it (final bill)

    @property
    def key(self) -> int:
        return self.matter_id


@dataclass(frozen=True, slots=True)
class FlowAccount:
    """A client's flow work in one practice (ADR PT-0004 section 2): hourly, billed monthly."""

    client_id: int
    practice: str
    firm_id: int
    wip_cents: int = 0
    wip_tenths: int = 0
    last_bill_turn: int | None = None

    @property
    def key(self) -> tuple[int, str]:
        return (self.client_id, self.practice)


@dataclass(frozen=True, slots=True)
class Dispute:
    """A billing dispute (spec 7.7), a pending item the player answers (TST ADR-0014)."""

    amount_cents: int  # the part of the bill the client disputes
    raised_turn: int
    expires_turn: int  # unanswered by then, the default rule negotiates
    padded: bool = False  # the bill carries a padder's time; a dispute brings it to light


@dataclass(frozen=True, slots=True)
class Bill:
    id: int
    firm_id: int
    client_id: int
    matter_id: int | None  # None: flow work
    practice: str
    model: BillingModel
    kind: BillKind
    issued_turn: int
    due_turn: int  # the month the client pays, if nothing intervenes
    standard_cents: int  # WIP at standard value the bill relieves
    billed_cents: int  # the invoice
    paid_cents: int = 0
    credited_cents: int = 0  # credit notes (disputes, short payments): fee reductions
    written_off_cents: int = 0  # bad debts (bankruptcy, age): 6700
    padding_cents: int = 0  # a padder's time in the bill (hidden until a dispute)
    short_cents: int = 0  # what the client will leave unpaid when it pays (drawn at issue)
    status: BillStatus = "open"
    dispute: Dispute | None = None
    closed_turn: int | None = None

    @property
    def outstanding_cents(self) -> int:
        return self.billed_cents - self.paid_cents - self.credited_cents - self.written_off_cents

    @property
    def is_open(self) -> bool:
        return self.status in ("open", "disputed")


@dataclass(frozen=True, slots=True)
class ClientFunds:
    """Money held for one client in the firm's client account (ADR PT-0003 section 7)."""

    client_id: int
    firm_id: int
    owed_cents: int  # C2000 owed to the client; the client bank holds the sum


@dataclass(frozen=True, slots=True)
class MonthTotals:
    """One month's revenue-chain totals for a firm (the KPIs' trailing windows)."""

    turn: int
    firm_id: int
    worked_cents: int = 0  # WIP posted at standard value
    standard_cents: int = 0  # WIP relieved by bills and retainer months
    billed_cents: int = 0  # fees for that work (realisation's numerator)
    invoiced_cents: int = 0  # all invoices, retainer advances included
    collected_cents: int = 0  # cash received against bills, client money included
    credited_cents: int = 0  # credit notes
    written_off_cents: int = 0  # bad debts
    fees_cents: int = 0  # accrual revenue (4000 + 4100, net)
    premium_cents: int = 0  # success and contingency premiums over standard (4100)
    resolved_billed_cents: int = 0  # invoices of bills closed this month (paid or written off)
    resolved_paid_cents: int = 0  # cash those bills brought in
    billable_tenths: int = 0
    capacity_tenths: int = 0


@dataclass(frozen=True, slots=True)
class BillingState:
    engagements: tuple[Engagement, ...] = ()  # open and closed last turn, by matter id
    flows: tuple[FlowAccount, ...] = ()  # by (client id, practice)
    bills: tuple[Bill, ...] = ()  # open bills and those closed since last turn began, by id
    funds: tuple[ClientFunds, ...] = ()  # by (firm id, client id); zero balances dropped
    months: tuple[MonthTotals, ...] = ()  # the last 12 months played per firm, by (firm, turn)
    next_bill_id: int = 1
    wip_provision_cents: int = 0  # 1110's balance as a positive amount (expected write-downs)
    bad_debt_provision_cents: int = 0  # 1210's balance as a positive amount
    deferred_cents: int = 0  # 2200's balance as a positive amount
    padding_found: tuple[int, ...] = ()  # people whose padding came to light (sorted)

    def engagement(self, matter_id: int) -> Engagement | None:
        return next((e for e in self.engagements if e.matter_id == matter_id), None)

    def bill(self, bill_id: int) -> Bill | None:
        return next((b for b in self.bills if b.id == bill_id), None)

    def funds_of(self, client_id: int, firm_id: int) -> int:
        return next(
            (f.owed_cents for f in self.funds if f.client_id == client_id and f.firm_id == firm_id),
            0,
        )


EMPTY_BILLING = BillingState()


@dataclass(frozen=True, slots=True)
class ClientBookLine:
    account: str  # C1000_client_bank or C2000_owed_to_clients
    client_id: int
    amount: int  # debit positive, credit negative


@dataclass(frozen=True, slots=True)
class ClientBookEntry:
    """An entry in the client-money book (ADR PT-0003 section 7): its own double entry, never
    in a firm entry. A transfer to the firm is recorded here and in the firm's ledger."""

    turn: int
    firm_id: int
    memo: str
    lines: tuple[ClientBookLine, ...]

    def __post_init__(self) -> None:
        from ptk.sim.errors import UnbalancedEntryError

        if len(self.lines) < 2 or sum(line.amount for line in self.lines) != 0:
            raise UnbalancedEntryError(f"client-book entry {self.memo!r} does not balance")
        for line in self.lines:
            if not line.account.startswith("C") or isinstance(line.amount, bool):
                raise UnbalancedEntryError(f"client-book entry {self.memo!r}: bad line {line}")
