"""Billing actions (ADR-0014): they take effect at once.

- `WriteDownMatter`: the partner's write-down (spec 7.7) on a named matter's next bill, in
  bp, up to `billing.writedown_max_bp`; the client notices when the bill goes out.
- `RespondDispute`: answer a billing dispute (a pending item): concede, negotiate or hold
  firm. Holding firm draws from the action's generator (stream `actions`).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Literal

import numpy as np

from ptk.sim.billing import books as bk
from ptk.sim.billing.models import DISPUTE_CHOICES, BillingState, DisputeChoice
from ptk.sim.billing.phase import resolve_dispute
from ptk.sim.data_models import Balance
from ptk.sim.errors import BillingActionError, UnknownBillError, UnknownMatterError
from ptk.sim.hiring.actions import Outcome, acting_firm, spend_energy
from ptk.sim.interfaces import bump_relationship, relationship_score
from ptk.sim.ledger import FEES, RECEIVABLES, LedgerEntry, LedgerLine
from ptk.sim.state import GameState

type Draws = Callable[[], np.random.Generator]


@dataclass(frozen=True, slots=True)
class WriteDownMatter:
    actor_id: int
    matter_id: int
    bp: int  # off the matter's next bill; 0 cancels
    kind: Literal["write_down_matter"] = "write_down_matter"


@dataclass(frozen=True, slots=True)
class RespondDispute:
    actor_id: int
    bill_id: int
    choice: DisputeChoice
    kind: Literal["respond_dispute"] = "respond_dispute"


type BillingAction = WriteDownMatter | RespondDispute

BILLING_ACTION_TYPES: dict[str, type[BillingAction]] = {
    "write_down_matter": WriteDownMatter,
    "respond_dispute": RespondDispute,
}


def _with_billing(state: GameState, billing: BillingState) -> GameState:
    return replace(state, billing=billing)


def write_down(state: GameState, a: WriteDownMatter, balance: Balance) -> Outcome:
    firm = acting_firm(state, a.actor_id)
    e = state.billing.engagement(a.matter_id)
    if e is None or e.firm_id != firm or e.closed:
        raise UnknownMatterError(f"no open engagement for matter {a.matter_id}")
    if e.model in ("fixed", "retainer", "contingency"):
        raise BillingActionError(f"a {e.model} matter's bills are not written down by the hour")
    if not 0 <= a.bp <= balance.billing.writedown_max_bp:
        raise BillingActionError(
            f"a write-down is 0 to {balance.billing.writedown_max_bp} bp, got {a.bp}"
        )
    state = spend_energy(state, a.actor_id, "write_down", balance)
    engagements = tuple(
        replace(x, writedown_bp=a.bp) if x.matter_id == a.matter_id else x
        for x in state.billing.engagements
    )
    return Outcome(state=_with_billing(state, replace(state.billing, engagements=engagements)))


def respond_dispute(state: GameState, a: RespondDispute, draws: Draws, balance: Balance) -> Outcome:
    firm = acting_firm(state, a.actor_id)
    if a.choice not in DISPUTE_CHOICES:
        raise BillingActionError(f"a dispute is answered by {DISPUTE_CHOICES}, got {a.choice!r}")
    bill = state.billing.bill(a.bill_id)
    if bill is None or bill.firm_id != firm:
        raise UnknownBillError(f"no bill {a.bill_id}")
    if bill.dispute is None:
        raise BillingActionError(f"bill {a.bill_id} is not disputed")
    state = spend_energy(state, a.actor_id, "dispute", balance)
    u = float(draws().random()) if a.choice == "hold" else 0.0
    rel = relationship_score(state, bill.client_id, firm)
    out, credit, points = resolve_dispute(bill, a.choice, u, rel, state.turn, balance.billing)
    bills = tuple(out if b.id == bill.id else b for b in state.billing.bills)
    state = _with_billing(state, replace(state.billing, bills=bills))
    state = bump_relationship(state, bill.client_id, firm, points)
    entries: tuple[LedgerEntry, ...] = ()
    if credit > 0:
        entries = (
            LedgerEntry(
                turn=state.turn,
                firm_id=firm,
                memo=bk.CREDIT_NOTES,
                lines=(
                    LedgerLine(FEES, credit, practice=bill.practice),
                    LedgerLine(RECEIVABLES, -credit, practice=bill.practice),
                ),
            ),
        )
    return Outcome(state=state, entries=entries)


def apply_billing_action(
    state: GameState, action: BillingAction, draws: Draws, balance: Balance
) -> Outcome:
    match action:
        case WriteDownMatter():
            return write_down(state, action, balance)
        case RespondDispute():
            return respond_dispute(state, action, draws, balance)
