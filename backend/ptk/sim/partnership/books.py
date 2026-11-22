"""Capital, draws, the December allocation and true-up, the revolver and insolvency
(spec 8.4; ADR PT-0003 sections 5-6; TST 20.3's lender pattern and 14.7's insolvency).

Phase 7, in this order, for each firm with a partnership:

1. capital instalments come in (new partners pay capital in over 36 months; 3000);
2. a departed partner's capital and current account go out (over 36 months; 3000, 2700);
3. revolver interest on the opening balance (6800);
4. draws: each equity partner's share of their budget a month (3200), or their guarantee;
5. January-April: the true-up (2700 to cash) as cash above the buffer allows;
6. December: the year's profit is allocated (3100 to 2700 by partner) and the drawings close
   against the current accounts (2700 to 3200); points step; next year's budgets are set;
7. the revolver draws when cash is short, repays when it is ample; the bank's covenants are
   tested; a called revolver must be repaid; three month ends below zero dissolve the firm.

Each partner's capital and current account is a sub-ledger kept in `Partner` and
`CapitalReturn`; a property test holds them equal to the ledger's 3000 and 2700.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace

from ptk.sim.data_models import Balance, GameData
from ptk.sim.ledger import (
    BAD_DEBT_PROVISION,
    CASH,
    DEFERRED_FEES,
    DRAWINGS,
    INTEREST,
    PARTNER_CURRENT,
    PARTNERS_CAPITAL,
    RECEIVABLES,
    REVOLVER,
    UNDISTRIBUTED_PROFIT,
    WIP,
    WIP_PROVISION,
    AccountCode,
    LedgerEntry,
    apply_entries,
)
from ptk.sim.log import LinkKind, LogItem, inbox_item
from ptk.sim.money import pct_of, round_half_even
from ptk.sim.partnership import formulas as fx
from ptk.sim.partnership.common import (
    cash,
    cumulative_pnl,
    last_month_costs,
    profit_12m,
    put,
    queue_event,
    revenue_12m,
    ym,
)
from ptk.sim.partnership.models import (
    Agreement,
    FirmPartnership,
    Partner,
    with_capital_return,
    with_partner,
)
from ptk.sim.partnership.setup import revolver_floor
from ptk.sim.state import GameState

FINANCE: LinkKind = "finance"


@dataclass(frozen=True, slots=True)
class MoneyMonth:
    state: GameState
    entries: tuple[LedgerEntry, ...]
    log: tuple[LogItem, ...]


class _Books:
    """Posts entries and keeps the running balances in step (cash decisions read them)."""

    def __init__(self, state: GameState, balances: Mapping[tuple[int, AccountCode], int]):
        self.state = state
        self.balances = dict(balances)
        self.entries: list[LedgerEntry] = []
        self.logs: list[LogItem] = []

    def move(self, firm_id: int, memo: str, debit: str, credit: str, amount: int) -> None:
        if amount == 0:
            return
        if amount < 0:
            debit, credit, amount = credit, debit, -amount
        entry = LedgerEntry.transfer(
            turn=self.state.turn,
            firm_id=firm_id,
            memo=memo,
            debit=debit,
            credit=credit,
            amount=amount,
        )
        self.entries.append(entry)
        self.balances = apply_entries(self.balances, (entry,))

    def cash(self, firm_id: int) -> int:
        return cash(self.balances, firm_id)

    def bal(self, firm_id: int, account: str) -> int:
        return self.balances.get((firm_id, account), 0)


def drawn_cents(balances: Mapping[tuple[int, AccountCode], int], firm_id: int) -> int:
    """The revolver's drawn balance (a credit on 2300)."""
    return -balances.get((firm_id, REVOLVER), 0)


def headroom_cents(
    fp: FirmPartnership, receivables: int, wip: int, drawn: int, balance: Balance
) -> int:
    """What the firm may still draw: the facility and the borrowing base, less what is drawn;
    nothing once the bank has called the revolver."""
    if fp.called_turn is not None:
        return 0
    cfg = balance.partnership.revolver
    base = max(
        fx.borrowing_base_cents(receivables, wip, cfg), pct_of(fp.facility_cents, cfg.unsecured_bp)
    )
    return max(0, min(fp.facility_cents, base) - drawn)


def monthly_draw_cents(p: Partner, fp: FirmPartnership, turn: int) -> int:
    """A guaranteed partner draws their guarantee; others draw_share of their budget a
    month, nothing while draws are suspended or the budget is not positive."""
    if not p.equity or p.admitted_turn > turn:
        return 0
    if p.guaranteed(turn):
        return round_half_even(p.guarantee_cents, fx.MONTHS_PER_YEAR)
    if fp.draws_suspended or p.budget_cents <= 0:
        return 0
    return round_half_even(pct_of(p.budget_cents, fp.agreement.draw_share_bp), fx.MONTHS_PER_YEAR)


def working_capital_cents(balances: Mapping[tuple[int, AccountCode], int], firm_id: int) -> int:
    """What profit is tied up in: WIP and receivables net of their provisions, less money
    received in advance (ADR PT-0003 3: the cash view leaves out their change)."""
    return sum(
        balances.get((firm_id, a), 0)
        for a in (WIP, WIP_PROVISION, RECEIVABLES, BAD_DEBT_PROVISION, DEFERRED_FEES)
    )


def reforecast(fp: FirmPartnership) -> FirmPartnership:
    """Budgets cut to base x (trailing-12-month profit / last year's), never above base."""
    last = fp.last_profit_cents
    if not last or last <= 0:
        return fp
    ratio = max(0.0, min(1.0, profit_12m(fp) / last))
    for p in fp.partners:
        base = p.budget_base_cents or p.budget_cents
        fp = with_partner(fp, replace(p, budget_cents=min(p.budget_cents, round(base * ratio))))
    return fp


def capital_required_cents(target_comp_cents: int, agreement: Agreement) -> int:
    return pct_of(max(target_comp_cents, 0), agreement.capital_share_bp)


# --- Phase 7 -------------------------------------------------------------------------------


def financing_month(
    state: GameState,
    balances: Mapping[tuple[int, AccountCode], int],
    receivables: Mapping[int, int],
    wip: Mapping[int, int],
    balance: Balance,
    data: GameData,
) -> MoneyMonth:
    from ptk.sim.partnership.comp import allocate_year

    books = _Books(state, balances)
    month = ym(state)[1]
    for fp0 in state.partnership.firms:
        firm = fp0.firm_id
        fp = fp0
        del fp0
        # 0. each January the bank resets the facility to a share of last year's revenue
        if month == 1 and fp.last_revenue_cents:
            scenario = data.scenario(state.save_meta.scenario_id)
            floor = revolver_floor(state.save_meta.difficulty, scenario, data) if scenario else 0
            sized = pct_of(
                fp.last_revenue_cents, balance.partnership.revolver.facility_of_revenue_bp
            )
            fp = replace(fp, facility_cents=max(floor, sized))
        # 1. capital instalments
        for p in fp.partners:
            due = min(p.capital_instalment_cents, p.capital_required_cents - p.capital_cents)
            if due > 0:
                books.move(firm, "Partner capital instalment", CASH, PARTNERS_CAPITAL, due)
                fp = with_partner(fp, replace(p, capital_cents=p.capital_cents + due))
        # 2. capital returned to departed partners (current account first)
        for r in fp.capital_returns:
            if r.start_turn > state.turn:
                continue
            pay = r.monthly_cents
            current = min(pay, r.remaining_current_cents)
            capital = min(pay - current, r.remaining_capital_cents)
            books.move(firm, "Departed partner's current account", PARTNER_CURRENT, CASH, current)
            books.move(firm, "Departed partner's capital returned", PARTNERS_CAPITAL, CASH, capital)
            fp = with_capital_return(
                fp,
                replace(
                    r,
                    remaining_current_cents=r.remaining_current_cents - current,
                    remaining_capital_cents=r.remaining_capital_cents - capital,
                ),
            )
        # 3. interest on the opening drawn balance
        interest = fx.monthly_interest_cents(
            drawn_cents(books.balances, firm), balance.partnership.revolver
        )
        books.move(firm, "Revolver interest", INTEREST, CASH, interest)
        # 4. draws (after a quarter's re-forecast: budgets follow the profit's run rate down)
        if month in balance.partnership.reforecast_months:
            fp = reforecast(fp)
        total_draws = 0
        for p in fp.partners:
            d = monthly_draw_cents(p, fp, state.turn)
            if d:
                total_draws += d
                fp = with_partner(fp, replace(p, drawn_ytd_cents=p.drawn_ytd_cents + d))
        books.move(firm, "Partner draws", DRAWINGS, CASH, total_draws)
        # 5. the true-up
        if month in balance.partnership.true_up_months:
            fp = _true_up(books, fp, balance)
        # 6. December
        if month == 12:  # tunable-exempt: the firm's year ends in December (ADR PT-0002)
            revenue, costs = cumulative_pnl(books.balances, firm)
            wc = working_capital_cents(books.balances, firm)
            drawn = sum(p.drawn_ytd_cents for p in fp.equity_partners)
            books.state = put(books.state, fp)
            books.state, fp, allocation = allocate_year(
                books.state, fp, revenue, costs, wc, balance, data
            )
            total = sum(allocation.values())
            books.move(
                firm, "Profit allocated to partners", UNDISTRIBUTED_PROFIT, PARTNER_CURRENT, total
            )
            books.move(
                firm, "Drawings closed to current accounts", PARTNER_CURRENT, DRAWINGS, drawn
            )
            books.logs.append(
                inbox_item(
                    state.turn,
                    firm,
                    "profit_allocated",
                    link_kind=FINANCE,
                    profit_cents=total,
                    partners=len(allocation),
                )
            )
        # 7. the revolver, covenants and insolvency
        fp = _revolver(books, fp, receivables.get(firm, 0), wip.get(firm, 0), balance)
        books.state = put(books.state, fp)
    return MoneyMonth(books.state, tuple(books.entries), tuple(books.logs))


def _buffer(fp: FirmPartnership, balance: Balance) -> int:
    return round(last_month_costs(fp) * balance.partnership.cash_buffer_months)


def _true_up(books: _Books, fp: FirmPartnership, balance: Balance) -> FirmPartnership:
    """Pay positive current accounts from cash above the buffer, pro rata; what cannot be paid
    stays owed (a liability on 2700) and is paid when cash allows."""
    owed = {p.person_id: p.current_cents for p in fp.partners if p.current_cents > 0}
    if not owed:
        return fp
    available = books.cash(fp.firm_id) - _buffer(fp, balance)
    total = sum(owed.values())
    pay_total = max(0, min(total, available))
    if pay_total <= 0:
        return fp
    shares = fx.split_cents(pay_total, {k: float(v) for k, v in owed.items()})
    for pid, amount in shares.items():
        amount = min(amount, owed[pid])
        p = fp.partner(pid)
        assert p is not None
        fp = with_partner(fp, replace(p, current_cents=p.current_cents - amount))
    books.move(fp.firm_id, "Partners' true-up paid", PARTNER_CURRENT, CASH, sum(shares.values()))
    return fp


def _revolver(
    books: _Books, fp: FirmPartnership, receivables: int, wip: int, balance: Balance
) -> FirmPartnership:
    cfg = balance.partnership.revolver
    firm = fp.firm_id
    turn = books.state.turn
    drawn = drawn_cents(books.balances, firm)
    c = books.cash(firm)
    if fp.called_turn is not None and drawn <= 0:
        fp = replace(fp, called_turn=None, breach_months=0)  # repaid: the bank lends again
    if fp.called_turn is not None and drawn > 0:
        months_left = max(1, cfg.call_months - (turn - fp.called_turn))
        due = drawn if months_left <= 1 else -(-drawn // months_left)
        pay = max(0, min(due, c))
        books.move(firm, "Called revolver repaid", REVOLVER, CASH, pay)
        drawn -= pay
        if drawn > 0 and turn - fp.called_turn >= cfg.call_months:
            # in default: each month end past the deadline counts toward dissolution
            fp = replace(fp, insolvent_months=fp.insolvent_months + 1)
            books.logs.append(
                inbox_item(
                    turn,
                    firm,
                    "revolver_default",
                    link_kind=FINANCE,
                    drawn_cents=drawn,
                    months=balance.partnership.insolvency_months - fp.insolvent_months,
                )
            )
            return fp
        if drawn == 0:
            fp = replace(fp, called_turn=None, breach_months=0)
    elif c < 0:
        take = min(-c, headroom_cents(fp, receivables, wip, drawn, balance))
        books.move(firm, "Revolver drawn", CASH, REVOLVER, take)
        drawn += take
    else:
        # keep the buffer and what the firm owes its partners (the true-up) before repaying
        owed = sum(max(0, p.current_cents) for p in fp.partners)
        spare = c - _buffer(fp, balance) - owed
        pay = min(drawn, max(0, spare))
        books.move(firm, "Revolver repaid", REVOLVER, CASH, pay)
        drawn -= pay
    # covenants
    capital = -books.bal(firm, PARTNERS_CAPITAL)
    rev12 = revenue_12m(fp)
    departed = sum(
        d.book_cents for d in fp.departures if d.equity and turn - d.turn < fx.MONTHS_PER_YEAR
    )
    tests = fx.covenants(drawn, rev12, capital, departed, cfg)
    breached = [t for t in tests if not t.holds]
    if fp.called_turn is None:
        if breached:
            fp = replace(fp, breach_months=fp.breach_months + 1)
            if fp.breach_months == 1:
                books.state = queue_event(books.state, firm, "covenant_breach", balance)
                books.logs.append(
                    inbox_item(
                        turn,
                        firm,
                        "covenant_breach",
                        link_kind=FINANCE,
                        covenant=breached[0].name,
                        months=cfg.cure_months,
                    )
                )
            if fp.breach_months >= cfg.cure_months:
                fp = replace(fp, called_turn=turn)
                books.logs.append(
                    inbox_item(
                        turn,
                        firm,
                        "revolver_called",
                        link_kind=FINANCE,
                        drawn_cents=drawn,
                        months=cfg.call_months,
                    )
                )
        else:
            fp = replace(fp, breach_months=0)
    near = [t for t in tests if t.holds and t.near(cfg.warning_headroom_bp)]
    cooled = (
        fp.last_warning_turn is None
        or turn - fp.last_warning_turn >= balance.partnership.cfo_warning_cooldown
    )
    if (near or breached) and cooled:
        worst = (breached or near)[0]
        fp = replace(fp, last_warning_turn=turn)
        books.logs.append(
            inbox_item(
                turn, firm, "cfo_warning", link_kind=FINANCE, covenant=worst.name, drawn_cents=drawn
            )
        )
    # insolvency (TST 14.7 adapted): cash below zero after the revolver
    if books.cash(firm) < 0:
        fp = replace(fp, insolvent_months=fp.insolvent_months + 1)
        books.logs.append(
            inbox_item(
                turn,
                firm,
                "insolvent",
                link_kind=FINANCE,
                cash_cents=books.cash(firm),
                months=balance.partnership.insolvency_months - fp.insolvent_months,
            )
        )
    else:
        fp = replace(fp, insolvent_months=0)
    return fp
