"""Fee arbitration and public fee disputes (spec 7.7, 11.6; ADR PT-0017 6).

When the firm holds firm on a disputed bill and the client is paid nothing back, the client may
go further:

- where the bar provides fee arbitration (bar_rules.yaml: New York's Part 137, for amounts in
  its range), it files with chance `arbitration_bp` (the action's own draw); the arbitrator
  decides after `arbitration_months` (stream `arbitration`, (2, id)): for the client with
  chance `award_fee_bp`, cutting a uniform share of the disputed amount (a credit note on the
  bill while it is open, a refund from cash once it is paid);
- a held dispute of at least `public_min_cents` becomes a fee suit in the press: reputation in
  the practice.
"""

from __future__ import annotations

from dataclasses import replace

from ptk.sim.billing.models import Bill
from ptk.sim.data_models import Balance, GameData
from ptk.sim.ledger import CASH, LedgerEntry, LedgerLine
from ptk.sim.log import LogItem, inbox_item
from ptk.sim.risk import draws as dr
from ptk.sim.risk import formulas as fx
from ptk.sim.risk.common import FEES, RECEIVABLES, Books, with_risk
from ptk.sim.risk.models import Arbitration, take_id, with_arbitration
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState


def home_rules(state: GameState, data: GameData):  # type: ignore[no-untyped-def]
    scenario = data.scenario(state.save_meta.scenario_id)
    key = scenario.home_jurisdiction if scenario is not None else "us_ny"
    return data.geo.rules(key)


def after_hold(
    state: GameState,
    bill: Bill,
    amount: int,
    u: float,
    u_months: float,
    balance: Balance,
    data: GameData,
) -> tuple[GameState, tuple[LogItem, ...]]:
    """A dispute the firm held and won: the client may file for arbitration, and a large one
    goes public."""
    if not balance.risk.enabled or amount <= 0:
        return state, ()
    a = balance.risk.audits
    logs: list[LogItem] = []
    if amount >= a.public_min_cents:
        from ptk.sim.reputation.formulas import apply_pulse

        state = apply_pulse(
            state, bill.firm_id, a.public_points, "a public fee dispute", balance, bill.practice
        )
        logs.append(
            inbox_item(state.turn, bill.firm_id, "fee_suit", link_kind="risk", amount_cents=amount)
        )
    rules = home_rules(state, data)
    d = rules.discipline if rules is not None else None
    if (
        d is None
        or not d.fee_arbitration
        or not d.arbitration_min_cents <= amount <= d.arbitration_max_cents
    ):
        return state, tuple(logs)
    if u >= a.arbitration_bp / fx.BP:
        return state, tuple(logs)
    risk, aid = take_id(state.risk)
    arb = Arbitration(
        id=aid,
        bill_id=bill.id,
        firm_id=bill.firm_id,
        client_id=bill.client_id,
        practice=bill.practice,
        amount_cents=amount,
        filed_turn=state.turn,
        decide_turn=state.turn + fx.span(u_months, a.arbitration_months),
    )
    logs.append(
        inbox_item(
            state.turn,
            bill.firm_id,
            "arbitration_filed",
            link_kind="risk",
            link_id=aid,
            amount_cents=amount,
        )
    )
    return with_risk(state, with_arbitration(risk, arb)), tuple(logs)


def awards_month(state: GameState, rng: RngFactory, books: Books, balance: Balance) -> GameState:
    a = balance.risk.audits
    billing = state.billing
    for arb in [x for x in state.risk.arbitrations if x.firm_id == books.firm_id and not x.decided]:
        if books.turn < arb.decide_turn:
            continue
        u = dr.arbitration_draws(rng, books.turn, dr.AWARD, arb.id).random(2)
        award = 0
        if float(u[0]) < a.award_fee_bp / fx.BP:
            award = round(arb.amount_cents * fx.uniform(float(u[1]), a.award_share))
        bill = billing.bill(arb.bill_id)
        if award > 0 and bill is not None and bill.is_open:
            award = min(award, bill.outstanding_cents)
            books.entries.append(
                LedgerEntry(
                    turn=books.turn,
                    firm_id=books.firm_id,
                    memo="Credit notes (fee arbitration)",
                    lines=(
                        LedgerLine(FEES, award, practice=arb.practice),
                        LedgerLine(RECEIVABLES, -award, practice=arb.practice),
                    ),
                )
            )
            out = replace(bill, credited_cents=bill.credited_cents + award)
            if out.outstanding_cents <= 0:
                out = replace(out, status="paid", closed_turn=books.turn)
            billing = replace(
                billing, bills=tuple(out if b.id == bill.id else b for b in billing.bills)
            )
        elif award > 0:
            books.entries.append(
                LedgerEntry(
                    turn=books.turn,
                    firm_id=books.firm_id,
                    memo="Fee arbitration refund",
                    lines=(
                        LedgerLine(FEES, award, practice=arb.practice),
                        LedgerLine(CASH, -award),
                    ),
                )
            )
            books.cash -= award
        books.inbox("arbitration_decided", arb.id, award_cents=award, amount_cents=arb.amount_cents)
        state = with_risk(
            replace(state, billing=billing),
            with_arbitration(state.risk, replace(arb, award_cents=award, decided=True)),
        )
        billing = state.billing
    return state
