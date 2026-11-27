"""Turn phase 5's billing half (spec 4.1, 7.7; ADR PT-0003 sections 2-3 and 7, PT-0005).

After PT-M3a's work phase, for the player's firm, in this order:

1. **Terms.** A named matter billing has not seen gets its terms (stream `billing`, key
   `(TERMS, matter_id)`): a model by the kind's mix (`billing.models`), the client's
   discount, a cycle, the cap, price, retainer, blended rate, success or contingency share,
   and money on account for some mid-size clients' matters (into the client book).
2. **Collections.** Open bills fall due and are paid (a short payment leaves a credit note);
   bankrupt clients' bills (generated clients only) and bills past `write_off_months` are
   written off as bad debts.
3. **Bills on cycle** for the WIP posted in earlier months: hourly, blended, capped and
   success-fee matters every cycle, fixed fees as phases complete, flow work monthly. The
   default rule writes overruns down; the partner's write-down (an action) applies next; the
   client's e-billing guidelines may reject a share; a padder's time rides along. A bill may be
   disputed (a pending item). Money on account pays a matter's bill at once.
4. **WIP**: the month's hours post at standard value, Σ tenths x rate / 10 rounded once per
   (person, matter, month) by PT-M3a (debit 1100, credit 4000).
5. **Retainers**: the month's fee is earned from deferred income (2200), or billed when no
   advance covered it; the next month is billed in advance.
6. **Closings**: final bills, success bonuses (4100), contingency fees from recoveries held in
   the client book, and money on account returned.
7. **Disputes** past their window are answered by the default rule (negotiate).
8. **Provisions**: the WIP provision (1110) to the expected write-downs of unbilled WIP; the
   bad-debt provision (1210) by the age of open bills.

Relationship points from write-downs, disputes and padding go through
`ptk.sim.interfaces.bump_relationship`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

from ptk.sim.billing import audits as au
from ptk.sim.billing import books as bk
from ptk.sim.billing import formulas as fx
from ptk.sim.billing import funding
from ptk.sim.billing.kpis import TRAILING
from ptk.sim.billing.models import (
    BILLING_MODELS,
    Bill,
    BillingModel,
    BillKind,
    ClientBookEntry,
    ClientFunds,
    Dispute,
    DisputeChoice,
    Engagement,
    FlowAccount,
    MonthTotals,
)
from ptk.sim.calendar import turn_to_ym
from ptk.sim.data_models import Balance, BillingBalance, GameData
from ptk.sim.fastcopy import replace
from ptk.sim.interfaces import (
    ClientBillingView,
    MatterBillingView,
    billing_client,
    billing_matters,
    blended_rate_cents,
    bump_relationship,
    fee_earner_capacity_tenths,
    kind_task_mix,
    month_hours,
    relationship_score,
    seat_effect,
    tech_billing,
)
from ptk.sim.ledger import (
    BAD_DEBT_PROVISION,
    CASH,
    DEFERRED_FEES,
    FEES,
    FUNDED_FEES,
    FUNDER_ADVANCES,
    FUNDING_COSTS,
    RECEIVABLES,
    SUCCESS_FEES,
    WIP,
    WIP_PROVISION,
    WRITE_OFFS,
    LedgerEntry,
)
from ptk.sim.log import LogItem, inbox_item
from ptk.sim.macro import bankrupt_by, collections_stress, crisis_factor, crisis_stress
from ptk.sim.matters.rates import client_indexes
from ptk.sim.money import BP_DENOMINATOR, pct_of, round_half_even, times
from ptk.sim.risk.models import Audit, keep_audits
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState, with_reveals

PADDER_TAG = "rule_bender"  # tags.yaml: billing padding risk (hidden until a dispute)
# PT-M7b: stream `crisis` keys: (CRISIS_MATTER, matter id) for a matter's bill,
# (CRISIS_FLOW + the practice's index, client id) for a client's flow bill in a practice
CRISIS_MATTER = 0
CRISIS_FLOW = 1
WIN_OUTCOMES = frozenset({"won", "closed"})
DONE_OUTCOMES = frozenset({"won", "closed", "done", "settled"})


@dataclass(frozen=True, slots=True)
class BillingMonth:
    state: GameState
    entries: tuple[LedgerEntry, ...]
    book: tuple[ClientBookEntry, ...]
    log: tuple[LogItem, ...]


PRODUCT_REPLACES: Final = frozenset({"hourly", "blended", "capped", "fixed"})  # PT-M14


class _Run:
    """One firm's billing month: working copies, posted at the end (the inputs never change)."""

    def __init__(
        self, state: GameState, firm_id: int, rng: RngFactory, data: GameData, balance: Balance
    ) -> None:
        b = state.billing
        self.state = state
        self.turn = state.turn
        self.firm_id = firm_id
        self.rng = rng
        self.data = data
        self.balance = balance
        self.cfg: BillingBalance = balance.billing
        # PT-M7: clients pay slower when the macro's collections index is stressed
        self.stress = collections_stress(state.turn, state.save_meta.start_ym, data, balance)
        # PT-M7b: the crisis's discounts and write-down requests (spec 14)
        self.crisis = crisis_stress(state.turn, state.save_meta.start_ym, data, balance)
        # PT-M8 (spec 9.1): the CFO's collections and the pricing director's realisation
        fx8 = balance.seats.effects
        self.pay_factor = 1.0 - fx8.cfo_collection * seat_effect(
            state, firm_id, "cfo", balance, data
        )
        self.discount_cut_bp = round(
            BP_DENOMINATOR
            * fx8.pricing_realisation
            * seat_effect(state, firm_id, "pricing_director", balance, data)
        )
        self.ym = turn_to_ym(state.turn, state.save_meta.start_ym)
        # PT-M14: client expectations on AI-exposed tasks, and the firm's fixed-fee products
        self.tech = tech_billing(state, firm_id, data, balance)
        self.factors: dict[int, float] = {}
        self.offices: dict[int, int | None] = {}  # PT-M11
        self.eng: dict[int, Engagement] = {
            e.matter_id: e for e in b.engagements if not e.closed and e.firm_id == firm_id
        }
        self.other_eng = tuple(e for e in b.engagements if e.firm_id != firm_id and not e.closed)
        self.flows: dict[tuple[int, str], FlowAccount] = {
            f.key: f for f in b.flows if f.firm_id == firm_id
        }
        self.other_flows = tuple(f for f in b.flows if f.firm_id != firm_id)
        self.bills: dict[int, Bill] = {
            x.id: x for x in b.bills if x.is_open or x.closed_turn == state.turn
        }
        self.funds: dict[tuple[int, int], int] = {
            (f.firm_id, f.client_id): f.owed_cents for f in b.funds
        }
        self.next_bill_id = b.next_bill_id
        self.found = set(b.padding_found)
        self.wip_provision = b.wip_provision_cents
        self.bad_debt_provision = b.bad_debt_provision_cents
        self.deferred = b.deferred_cents
        self.books = bk.Books(self.turn, firm_id)
        self.client_book = bk.ClientBook(self.turn, firm_id)
        self.logs: list[LogItem] = []
        self.points: dict[int, float] = {}
        self.totals: dict[str, int] = {}
        self.clients: dict[int, ClientBillingView] = {}
        self.views: dict[int, MatterBillingView] = {}
        self.audits: list[Audit] = []  # PT-M15: the month's e-billing audits

    # --- helpers ----------------------------------------------------------------------------

    def office(self, client_id: int) -> int | None:
        """PT-M11: the office a client's work belongs to (the ledger's office dimension); None
        for the home office, so a firm with no other office posts exactly as before."""
        if not self.state.geo.offices:
            return None
        if client_id not in self.offices:
            from ptk.sim.geo.cities import client_office_id

            client = self.state.market.client(client_id)
            oid = client_office_id(self.state, self.firm_id, client)
            self.offices[client_id] = oid or None
        return self.offices[client_id]

    def client(self, client_id: int) -> ClientBillingView:
        if client_id not in self.clients:
            self.clients[client_id] = billing_client(self.state, client_id)
        return self.clients[client_id]

    def add(self, key: str, amount: int) -> None:
        self.totals[key] = self.totals.get(key, 0) + amount

    def crisis_bp(self, client_id: int) -> int:
        """PT-M7b: the crisis discount a client asks on new work this month (bp)."""
        if self.crisis <= 0:
            return 0
        cfg = self.balance.macro.crisis
        factor = self.crisis_factor(client_id)
        return min(cfg.discount_max_bp, round(cfg.discount_bp * self.crisis * factor))

    def crisis_factor(self, client_id: int) -> float:
        """The client's crisis factor this month (memoised: it reads every practice's index)."""
        if client_id not in self.factors:
            c = self.client(client_id)
            self.factors[client_id] = crisis_factor(
                c.price_sensitivity, c.sector, self.ym, self.data, self.balance
            )
        return self.factors[client_id]

    def discount_bp(self, client_id: int) -> int:
        """The client's discount plus the crisis's (PT-M7b), never above the whole fee."""
        base = fx.client_discount_bp(self.client(client_id), self.cfg)
        total = base + self.crisis_bp(client_id) - self.discount_cut_bp  # PT-M8: pricing
        return max(0, min(BP_DENOMINATOR, total))

    def crisis_writedown(self, client_id: int, key: tuple[int, int], fee: int) -> int:
        """PT-M7b: a client under the crisis may ask for a bill to be written down (stream
        `crisis`, keyed by (kind, id): two draws, whether it asks and how much)."""
        if self.crisis <= 0 or fee <= 0:
            return 0
        cfg = self.balance.macro.crisis
        factor = self.crisis_factor(client_id)
        gen = self.rng.stream(self.turn, "crisis", *key)
        ask, size = (float(x) for x in gen.random(2))
        if ask >= cfg.ask_bp / BP_DENOMINATOR * self.crisis * factor:
            return 0
        lo, hi = cfg.writedown_bp
        cut = pct_of(fee, round(fx.uniform(lo, hi, size)))
        self.add("crisis_writedown_cents", cut)
        return cut

    def ai_cut(self, fee: int, tasks: Mapping[str, float]) -> int:
        """PT-M14 (ADR PT-0011 4): clients' cut on an hourly bill's AI-exposed tasks."""
        bp = self.tech.cut_bp(tasks)
        if bp <= 0 or fee <= 0:
            return 0
        cut = pct_of(fee, bp)
        self.add("ai_cut_cents", cut)
        return cut

    def point(self, client_id: int, points: float) -> None:
        if points:
            self.points[client_id] = self.points.get(client_id, 0.0) + points

    def hold_funds(self, client_id: int, amount: int) -> None:
        key = (self.firm_id, client_id)
        self.funds[key] = self.funds.get(key, 0) + amount

    # --- 1. terms ---------------------------------------------------------------------------

    def terms(self, v: MatterBillingView) -> Engagement:
        cfg = self.cfg
        u = fx.billing_draws(self.rng, self.turn, fx.TERMS, v.matter_id)
        client = self.client(v.client_id)
        # PT-M12: a practice's own mix (contingency in mass torts, retainers in private client)
        own = self.data.practice(v.practice).billing_models
        model = _pick_model(own or cfg.models.get(v.kind, {"hourly": 1.0}), u[0])
        if model == "contingency" and v.stakes_cents <= 0:
            model = "hourly"
        # PT-M14: the firm's fixed-fee product replaces hourly-type terms (hourly, blended,
        # capped, fixed); success, contingency and retainer terms stay the client's choice
        # (Reece, 2026-11-23) a product above the market's cost is taken by a falling share of
        # clients: draw u2 (unused by a product's price) decides whether this client takes it
        product = self.tech.products.get(v.kind_key)
        if (
            product is not None
            and model in PRODUCT_REPLACES
            and u[2] < self.tech.accept.get(v.kind_key, 1.0)
        ):
            model = "fixed"
        else:
            product = None
        months = max(1, v.planned_months)
        e = Engagement(
            matter_id=v.matter_id,
            firm_id=v.firm_id,
            client_id=v.client_id,
            practice=v.practice,
            model=model,
            opened_turn=self.turn,
            cycle_months=3 if u[1] < cfg.quarterly_bp / BP_DENOMINATOR else 1,
            discount_bp=self.discount_bp(v.client_id),  # PT-M7b: the crisis's too
        )
        if model == "capped":
            e = replace(
                e, price_cents=times(v.expected_fees_cents, fx.uniform(*cfg.cap_mult, u[2]))
            )
        elif model == "fixed" and product is not None:
            e = replace(e, price_cents=max(1, times(v.expected_fees_cents, product)))
        elif model == "fixed":
            e = replace(
                e, price_cents=times(v.expected_fees_cents, fx.uniform(*cfg.fixed_mult, u[2]))
            )
        elif model == "retainer":
            monthly = fx.uniform(*cfg.retainer_mult, u[2]) / months
            e = replace(
                e, price_cents=max(1, times(v.expected_fees_cents, monthly)), term_months=months
            )
        elif model == "blended":
            rate = times(
                blended_rate_cents(
                    v.practice,
                    v.kind_key,
                    self.data,
                    client_indexes(self.state, self.state.firm(self.firm_id), self.balance)(
                        v.practice, v.client_id
                    ),  # PT-M7b; PT-M7c: the client's tier
                ),
                cfg.blended_mult,
            )
            e = replace(e, rate_cents=rate)
        elif model == "success":
            e = replace(
                e,
                share_bp=cfg.success_share_bp,
                bonus_cents=pct_of(v.expected_fees_cents, cfg.success_bonus_bp),
            )
        elif model == "contingency":
            lo, hi = cfg.contingency_bp
            e = replace(e, share_bp=round(fx.uniform(lo, hi, u[3])), discount_bp=0)
        if client.size_class == "mid" and u[4] < cfg.deposit_bp / BP_DENOMINATOR:
            deposit = times(v.expected_fees_cents, cfg.deposit_months / months)
            if deposit > 0:
                self.client_book.receive(bk.DEPOSITS, v.client_id, deposit)
                self.hold_funds(v.client_id, deposit)
                e = replace(e, funds_cents=deposit)
        return e

    def sync(self) -> None:
        for v in billing_matters(self.state, self.firm_id, self.data):
            if v.status not in ("open", "closed"):
                continue
            self.views[v.matter_id] = v
            e = self.eng.get(v.matter_id)
            if e is None:
                if v.status == "closed" and v.closed_turn != self.turn:
                    continue
                if any(x.matter_id == v.matter_id for x in self.state.billing.engagements):
                    continue  # billed and closed before
                e = self.terms(v)
            if v.settlement_bp is not None:
                e = replace(e, offer_bp=v.settlement_bp)
            self.eng[v.matter_id] = e

    # --- 2. collections ---------------------------------------------------------------------

    def collect(self) -> None:
        cfg = self.cfg
        for bid in sorted(self.bills):
            bill = self.bills[bid]
            if bill.status != "open" or self.turn < bill.due_turn:
                continue
            short = min(bill.outstanding_cents, bill.short_cents)
            pay = bill.outstanding_cents - short
            self.books.move(
                bk.COLLECTIONS, CASH, RECEIVABLES, pay, bill.practice, self.office(bill.client_id)
            )
            self.books.move(
                bk.CREDIT_NOTES,
                FEES,
                RECEIVABLES,
                short,
                bill.practice,
                self.office(bill.client_id),
            )
            self.add("collected_cents", pay)
            self.add("credited_cents", short)
            self.bills[bid] = replace(
                bill,
                paid_cents=bill.paid_cents + pay,
                credited_cents=bill.credited_cents + short,
                status="paid",
                closed_turn=self.turn,
            )
        # bankruptcies (generated clients with open bills; real companies only on history's
        # dates, PT-M7: their open bills are written off every month from the filing)
        owing = sorted({b.client_id for b in self.bills.values() if b.is_open})
        start = self.state.save_meta.start_ym
        for cid in owing:
            client = self.client(cid)
            if client.real:
                if bankrupt_by(self.state.market.client(cid), self.turn, self.data, start):
                    for bid in sorted(self.bills):
                        bill = self.bills[bid]
                        if bill.client_id == cid and bill.is_open:
                            self.write_off(bill)
                continue
            u = fx.billing_draws(self.rng, self.turn, fx.CLIENT, cid)
            if u[0] >= cfg.bankruptcy_bp[client.size_class] / BP_DENOMINATOR:
                continue
            lost = 0
            for bid in sorted(self.bills):
                bill = self.bills[bid]
                if bill.client_id == cid and bill.is_open:
                    lost += self.write_off(bill)
            self.logs.append(
                inbox_item(
                    self.turn,
                    self.firm_id,
                    "client_bankrupt",
                    link_kind="client",
                    link_id=cid,
                    client=client.name,
                    lost_cents=lost,
                )
            )
        for bid in sorted(self.bills):
            bill = self.bills[bid]
            if bill.is_open and self.turn - bill.issued_turn >= cfg.write_off_months:
                self.write_off(bill)

    def write_off(self, bill: Bill) -> int:
        amount = bill.outstanding_cents
        self.books.move(
            bk.WRITE_OFFS,
            WRITE_OFFS,
            RECEIVABLES,
            amount,
            bill.practice,
            self.office(bill.client_id),
        )
        self.add("written_off_cents", amount)
        self.bills[bill.id] = replace(
            bill,
            written_off_cents=bill.written_off_cents + amount,
            status="written_off",
            dispute=None,
            closed_turn=self.turn,
        )
        return amount

    # --- bills --------------------------------------------------------------------------

    def issue(
        self,
        *,
        client_id: int,
        matter_id: int | None,
        practice: str,
        model: BillingModel,
        kind: BillKind,
        standard: int,
        fee: int,
        memo: str,
        padding: int = 0,
        disputable: bool = True,
        rejectable: bool = True,
        revenue: str = FEES,
    ) -> Bill:
        """Issue a bill of `fee` relieving `standard` of WIP: debit receivables, credit WIP,
        and the difference to fees (a write-down) or `revenue` (a write-up, a bonus, or
        deferred income for a retainer's advance). The client's e-billing guidelines may first
        reject a share of a fee bill (draws u0, u1 of the bill's own stream)."""
        cfg = self.cfg
        bid = self.next_bill_id
        self.next_bill_id += 1
        u = fx.billing_draws(self.rng, self.turn, fx.BILL, bid)
        client = self.client(client_id)
        rejected = False
        if rejectable and fee > 0:
            chance = fx.bp_chance(
                cfg.guideline_bp, cfg.guideline_per_point_bp, client.price_sensitivity
            )
            if u[0] < chance:
                fee -= times(fee, fx.uniform(*cfg.guideline_share, u[1]))
                rejected = True
        # PT-M15 (spec 11.6): the client's e-billing audit cuts the bill and finds padding
        checked = (
            au.audit(self.state, self.rng, bid, client, fee, padding, self.balance)
            if rejectable
            else None
        )
        if checked is not None:
            fee -= checked.cut_cents
            self.audits.append(
                Audit(
                    bill_id=bid,
                    turn=self.turn,
                    firm_id=self.firm_id,
                    client_id=client_id,
                    practice=practice,
                    cut_cents=checked.cut_cents,
                    padding_found_cents=padding if checked.finds_padding else 0,
                )
            )
        self.books.move(memo, RECEIVABLES, WIP, standard, practice, self.office(client_id))
        diff = fee - standard
        if diff < 0:
            self.books.move(memo, FEES, RECEIVABLES, -diff, practice, self.office(client_id))
        else:
            self.books.move(memo, RECEIVABLES, revenue, diff, practice, self.office(client_id))
        dispute = None
        overrun = self.overrun(matter_id)
        mult = au.dispute_mult(overrun, rejected, self.balance)  # PT-M15: overruns, guidelines
        if disputable and fee > 0 and u[2] < fx.dispute_chance(client, padding > 0, cfg) * mult:
            share = fx.uniform(*cfg.dispute_share, u[3])
            amount = min(fee, max(times(fee, share), padding))
            dispute = Dispute(
                amount_cents=amount,
                raised_turn=self.turn,
                expires_turn=self.turn + cfg.dispute_window,
                padded=padding > 0,
            )
        short = 0
        if u[5] < fx.bp_chance(
            cfg.short_pay_bp, cfg.short_pay_per_point_bp, client.price_sensitivity
        ):
            short = times(fee, fx.uniform(*cfg.short_pay_share, u[6]))
        bill = Bill(
            id=bid,
            firm_id=self.firm_id,
            client_id=client_id,
            matter_id=matter_id,
            practice=practice,
            model=model,
            kind=kind,
            issued_turn=self.turn,
            due_turn=fx.due_turn(
                self.turn, fx.days_to_pay(client, u[4], cfg, self.stress) * self.pay_factor, cfg
            ),
            standard_cents=standard,
            billed_cents=fee,
            padding_cents=padding,
            short_cents=short,
            status="disputed" if dispute is not None else "open",
            dispute=dispute,
        )
        self.add("invoiced_cents", fee)
        if dispute is not None:
            self.logs.append(
                inbox_item(
                    self.turn,
                    self.firm_id,
                    "bill_disputed",
                    link_kind="finance",
                    link_id=bid,
                    client=client.name,
                    amount_cents=dispute.amount_cents,
                    bill_cents=fee,
                )
            )
            if dispute.padded:
                bill = self.padding_found(bill)
        if checked is not None and checked.finds_padding and bill.padding_cents > 0:
            bill = self.padding_found(bill)  # PT-M15: the audit found it
        if fee <= 0 and bill.status == "open":
            bill = replace(bill, status="paid", closed_turn=self.turn)
        self.bills[bid] = bill
        return bill

    def overrun(self, matter_id: int | None) -> bool:
        """PT-M15: the matter's work at standard is over its budget (PT-M3b's tolerance)."""
        e = self.eng.get(matter_id) if matter_id is not None else None
        v = self.views.get(matter_id) if matter_id is not None else None
        if e is None or v is None or v.expected_fees_cents <= 0:
            return False
        return e.standard_cents > v.expected_fees_cents * (1 + self.cfg.overrun_tolerance)

    def realised(self, standard: int, fee: int) -> None:
        self.add("standard_cents", standard)
        self.add("billed_cents", fee)

    def pay_from_funds(self, e: Engagement, bill: Bill) -> Engagement:
        """Money on account pays the matter's undisputed bill at once (a transfer recorded in
        both books); never more than the client's own balance."""
        held = min(e.funds_cents, self.funds.get((self.firm_id, e.client_id), 0))
        if held <= 0 or bill.status != "open":
            return e
        amount = min(held, bill.outstanding_cents)
        if amount <= 0:
            return e
        self.transfer(bill, amount)
        return replace(e, funds_cents=e.funds_cents - amount)

    def transfer(self, bill: Bill, amount: int) -> None:
        self.client_book.pay_out(bk.TRANSFERS, bill.client_id, amount)
        self.hold_funds(bill.client_id, -amount)
        self.books.move(
            bk.CLIENT_TRANSFERS,
            CASH,
            RECEIVABLES,
            amount,
            bill.practice,
            self.office(bill.client_id),
        )
        self.add("collected_cents", amount)
        paid = replace(bill, paid_cents=bill.paid_cents + amount)
        if paid.outstanding_cents <= 0:
            paid = replace(paid, short_cents=0, status="paid", closed_turn=self.turn)
        self.bills[bill.id] = paid

    def fees_bill(self, e: Engagement, v: MatterBillingView, *, final: bool) -> Engagement:
        """A cycle (or final) bill for an hourly, blended, capped or success-fee matter."""
        cfg = self.cfg
        wip, tenths = e.wip_cents, e.wip_tenths
        if wip <= 0:
            return e
        fee = fx.hourly_fee(e, wip, tenths)
        fee -= fx.overrun_writedown(e, v.expected_fees_cents, wip, fee, cfg)
        if e.writedown_bp:
            fee -= pct_of(fee, e.writedown_bp)
            self.point(e.client_id, cfg.writedown_points * e.writedown_bp / 100)
        fee -= self.crisis_writedown(e.client_id, (CRISIS_MATTER, e.matter_id), fee)
        fee -= self.ai_cut(fee, kind_task_mix(v.kind, self.data))  # PT-M14
        pad_standard, pad_fee = self.padding(v, wip, fee)
        bill = self.issue(
            client_id=e.client_id,
            matter_id=e.matter_id,
            practice=e.practice,
            model=e.model,
            kind="final" if final else "fees",
            standard=wip + pad_standard,
            fee=fee + pad_fee,
            memo=bk.CLOSINGS if final else bk.BILLS,
            padding=pad_fee,
        )
        self.realised(wip + pad_standard, bill.billed_cents)
        e = replace(
            e,
            wip_cents=0,
            wip_tenths=0,
            billed_cents=e.billed_cents + bill.billed_cents,
            standard_cents=e.standard_cents + pad_standard,
            last_bill_turn=self.turn,
            writedown_bp=0,
        )
        return self.pay_from_funds(e, bill)

    def padding(self, v: MatterBillingView, wip: int, fee: int) -> tuple[int, int]:
        """(standard, fee) of time a padding lead adds that was never worked."""
        if v.lead_id is None or v.lead_id in self.found or wip <= 0:
            return 0, 0
        lead = next((p for p in self.state.people if p.id == v.lead_id), None)
        if lead is None or PADDER_TAG not in lead.tags:
            return 0, 0
        standard = times(wip, self.cfg.padding_share)
        if standard <= 0:
            return 0, 0
        self.books.move(bk.WIP_POSTED, WIP, FEES, standard, v.practice, self.office(v.client_id))
        return standard, round_half_even(standard * fee, wip)

    def padding_found(self, bill: Bill) -> Bill:
        """A disputed padded bill brings the padding to light: the padded time is credited,
        the client is angry, and the firm learns the lead's tag."""
        v = self.views.get(bill.matter_id) if bill.matter_id is not None else None
        lead = v.lead_id if v is not None else None
        amount = min(bill.padding_cents, bill.outstanding_cents)
        self.books.move(
            bk.CREDIT_NOTES, FEES, RECEIVABLES, amount, bill.practice, self.office(bill.client_id)
        )
        self.add("credited_cents", amount)
        self.point(bill.client_id, self.cfg.padding_points)
        if lead is not None:
            self.found.add(lead)
            self.reveal_padder(lead)
        disputed = bill.dispute
        rest = None
        if disputed is not None:
            left = max(0, disputed.amount_cents - amount)
            rest = replace(disputed, amount_cents=left, padded=False) if left > 0 else None
        out = replace(
            bill,
            credited_cents=bill.credited_cents + amount,
            padding_cents=0,
            dispute=rest,
            status="disputed" if rest is not None else "open",
        )
        self.logs.append(
            inbox_item(
                self.turn,
                self.firm_id,
                "padding_found",
                link_kind="person" if lead is not None else "finance",
                link_id=lead if lead is not None else bill.id,
                client=self.client(bill.client_id).name,
                amount_cents=amount,
            )
        )
        return out

    def reveal_padder(self, person_id: int) -> None:
        reveal = self.state.reveal(self.firm_id, person_id)
        if reveal is None or any(t == PADDER_TAG for t, _ in reveal.revealed_tags):
            return
        updated = replace(reveal, revealed_tags=(*reveal.revealed_tags, (PADDER_TAG, self.turn)))
        self.state = with_reveals(self.state, [updated])

    def cycle_bills(self) -> None:
        for mid in sorted(self.eng):
            e = self.eng[mid]
            v = self.views.get(mid)
            if v is None or e.closed:
                continue
            if e.model in ("hourly", "blended", "capped", "success"):
                due = e.last_bill_turn is None or self.turn - e.last_bill_turn >= e.cycle_months
                if due and e.wip_cents > 0:
                    self.eng[mid] = self.fees_bill(e, v, final=False)
            elif e.model == "fixed":
                amount = fx.fixed_due(e, v.done_share)
                if amount > 0:
                    self.eng[mid] = self.fixed_bill(e, amount, final=False)
        for key in sorted(self.flows):
            f = self.flows[key]
            if f.wip_cents <= 0:
                continue
            disc = self.discount_bp(f.client_id)  # PT-M7b: flow is new work each month
            fee = fx.after_discount(f.wip_cents, disc)
            fee -= self.crisis_writedown(
                f.client_id,
                (CRISIS_FLOW + self.data.practice_keys.index(f.practice), f.client_id),
                fee,
            )
            fee -= self.ai_cut(fee, self.data.market.flow_tasks)  # PT-M14
            bill = self.issue(
                client_id=f.client_id,
                matter_id=None,
                practice=f.practice,
                model="hourly",
                kind="fees",
                standard=f.wip_cents,
                fee=fee,
                memo=bk.BILLS,
            )
            self.realised(f.wip_cents, bill.billed_cents)
            self.flows[key] = replace(f, wip_cents=0, wip_tenths=0, last_bill_turn=self.turn)

    def fixed_bill(self, e: Engagement, amount: int, *, final: bool) -> Engagement:
        bill = self.issue(
            client_id=e.client_id,
            matter_id=e.matter_id,
            practice=e.practice,
            model="fixed",
            kind="final" if final else "fees",
            standard=e.wip_cents,
            fee=amount,
            memo=bk.CLOSINGS if final else bk.BILLS,
            rejectable=False,
        )
        self.realised(e.wip_cents, amount)
        e = replace(
            e,
            wip_cents=0,
            wip_tenths=0,
            billed_cents=e.billed_cents + amount,
            last_bill_turn=self.turn,
        )
        return self.pay_from_funds(e, bill)

    # --- 4. WIP -----------------------------------------------------------------------------

    def post_wip(self) -> None:
        # PT-M13 (T12): the month's records are summed per ledger line, engagement and flow
        # account first (integer sums, keys in first-seen order), then posted once each;
        # identical results to posting record by record
        wip: dict[tuple[str, int | None], int] = {}
        to_eng: dict[int, list[int]] = {}
        to_flow: dict[tuple[int, str], list[int]] = {}
        worked = billable = 0
        seen = False
        for r in month_hours(self.state, self.firm_id):
            if r.value_cents == 0 and r.tenths == 0:
                continue
            seen = True
            worked += r.value_cents
            billable += r.tenths
            e = self.eng.get(r.matter_id) if r.matter_id is not None else None
            if e is None or e.model != "contingency":
                # PT-M12 (ADR PT-0018): a contingency case's WIP posts no fee until its
                # recovery (its funder's advance is posted per case below)
                line = (r.practice, self.office(r.client_id))
                wip[line] = wip.get(line, 0) + r.value_cents
            if e is not None:
                acc = to_eng.setdefault(e.matter_id, [0, 0])
            else:
                acc = to_flow.setdefault((r.client_id, r.practice), [0, 0])
            acc[0] += r.value_cents
            acc[1] += r.tenths
        for (practice, office), cents in wip.items():
            self.books.move(bk.WIP_POSTED, WIP, FEES, cents, practice, office)
        if seen:
            self.add("worked_cents", worked)
            self.add("billable_tenths", billable)
        for mid, (cents, tenths) in to_eng.items():
            e = self.eng[mid]
            if e.model == "contingency":
                # a funder advances its share of the case's month of WIP (2800)
                advance = funding.advance_cents(cents, e.funded_bp)
                office = self.office(e.client_id)
                self.books.move(bk.FUNDING, CASH, FUNDER_ADVANCES, advance, e.practice, office)
                e = replace(e, advances_cents=e.advances_cents + advance)
            self.eng[mid] = replace(
                e,
                wip_cents=e.wip_cents + cents,
                wip_tenths=e.wip_tenths + tenths,
                standard_cents=e.standard_cents + cents,
            )
        for key, (cents, tenths) in to_flow.items():
            f = self.flows.get(key) or FlowAccount(
                client_id=key[0], practice=key[1], firm_id=self.firm_id
            )
            self.flows[key] = replace(
                f, wip_cents=f.wip_cents + cents, wip_tenths=f.wip_tenths + tenths
            )
        self.add(
            "capacity_tenths",
            fee_earner_capacity_tenths(self.state, self.firm_id, self.data, self.balance),
        )

    # --- 5. retainers -----------------------------------------------------------------------

    def retainers(self) -> None:
        for mid in sorted(self.eng):
            e = self.eng[mid]
            v = self.views.get(mid)
            if e.model != "retainer" or v is None:
                continue
            fee = e.price_cents
            if e.advance_turn == self.turn:  # an advance bill covered this month: earn it
                self.books.move(
                    bk.RETAINERS,
                    DEFERRED_FEES,
                    WIP,
                    e.wip_cents,
                    e.practice,
                    self.office(e.client_id),
                )
                self.books.move(
                    bk.RETAINERS,
                    DEFERRED_FEES,
                    FEES,
                    fee - e.wip_cents,
                    e.practice,
                    self.office(e.client_id),
                )
                self.deferred -= fee
            else:  # the first month: billed as it is earned
                bill = self.issue(
                    client_id=e.client_id,
                    matter_id=mid,
                    practice=e.practice,
                    model="retainer",
                    kind="fees",
                    standard=e.wip_cents,
                    fee=fee,
                    memo=bk.RETAINERS,
                    rejectable=False,
                )
                e = self.pay_from_funds(e, bill)
            self.realised(e.wip_cents, fee)
            e = replace(
                e,
                wip_cents=0,
                wip_tenths=0,
                billed_cents=e.billed_cents + fee,
                last_bill_turn=self.turn,
                months_billed=e.months_billed + 1,
            )
            if e.months_billed >= e.term_months:  # the term is over: the rest bills hourly
                self.eng[mid] = replace(e, model="hourly", advance_turn=None)
                continue
            if v.status == "open":  # next month, in advance: debit receivables, credit 2200
                bill = self.issue(
                    client_id=e.client_id,
                    matter_id=mid,
                    practice=e.practice,
                    model="retainer",
                    kind="retainer_advance",
                    standard=0,
                    fee=fee,
                    memo=bk.RETAINERS,
                    disputable=False,
                    rejectable=False,
                    revenue=DEFERRED_FEES,
                )
                self.deferred += fee
                e = self.pay_from_funds(replace(e, advance_turn=self.turn + 1), bill)
            self.eng[mid] = e

    # --- 6. closings ------------------------------------------------------------------------

    def closings(self) -> None:
        for mid in sorted(self.eng):
            e = self.eng[mid]
            v = self.views.get(mid)
            if v is None or v.status != "closed" or e.closed:
                continue
            if v.outcome == "disqualified" and e.model == "contingency":
                e = self.contingency(e, v, recovered=False)
            elif v.outcome == "disqualified":
                self.books.move(
                    bk.CLOSINGS, FEES, WIP, e.wip_cents, e.practice, self.office(e.client_id)
                )
                self.realised(e.wip_cents, 0)
                e = replace(e, wip_cents=0, wip_tenths=0)
            elif e.model == "contingency":
                e = self.contingency(e, v)
            elif e.model == "fixed":
                share = 1.0 if v.outcome in DONE_OUTCOMES else v.progress
                amount = fx.fixed_due(e, share)
                if amount > 0 or e.wip_cents > 0:
                    e = self.fixed_bill(e, amount, final=True)
            elif e.model != "retainer":
                e = self.fees_bill(e, v, final=True)
            if e.model == "success" and v.outcome in WIN_OUTCOMES and e.bonus_cents > 0:
                bill = self.issue(
                    client_id=e.client_id,
                    matter_id=mid,
                    practice=e.practice,
                    model="success",
                    kind="success",
                    standard=0,
                    fee=e.bonus_cents,
                    memo=bk.CLOSINGS,
                    rejectable=False,
                    revenue=SUCCESS_FEES,
                )
                self.realised(0, e.bonus_cents)
                e = self.pay_from_funds(
                    replace(e, billed_cents=e.billed_cents + e.bonus_cents), bill
                )
            if e.funds_cents > 0:
                refund = min(e.funds_cents, self.funds.get((self.firm_id, e.client_id), 0))
                self.client_book.pay_out(bk.REFUNDS, e.client_id, refund)
                self.hold_funds(e.client_id, -refund)
                e = replace(e, funds_cents=0)
            self.eng[mid] = replace(e, closed=True, closed_turn=self.turn)

    def contingency(
        self, e: Engagement, v: MatterBillingView, *, recovered: bool = True
    ) -> Engagement:
        """A contingency case's fee is a share of the recovery, which arrives in the client
        account; the fee is transferred to the firm and the rest paid out to the client.
        PT-M12 (ADR PT-0018): its WIP never posted a fee, so a loss reverses nothing; a funded
        case pays the funder first from the fee, and the advances a loss leaves are the
        funder's (released to 4400)."""
        cfg = self.cfg
        if not recovered:
            recovery = 0
        elif v.outcome == "won":
            recovery = pct_of(v.stakes_cents, cfg.recovery_bp)
        elif v.outcome == "settled":
            recovery = pct_of(
                v.stakes_cents, e.offer_bp if e.offer_bp is not None else cfg.settlement_fallback_bp
            )
        else:
            recovery = 0
        fee = pct_of(recovery, e.share_bp)
        if fee <= 0:
            self.realised(e.wip_cents, 0)
            self.settle_funding(e, 0)
            return replace(e, wip_cents=0, wip_tenths=0, advances_cents=0)
        self.client_book.receive(bk.RECOVERIES, e.client_id, recovery)
        self.hold_funds(e.client_id, recovery)
        bill = self.issue(
            client_id=e.client_id,
            matter_id=e.matter_id,
            practice=e.practice,
            model="contingency",
            kind="contingency",
            standard=0,  # PT-M12: the WIP was never posted (ADR PT-0018)
            fee=fee,
            memo=bk.CLOSINGS,
            disputable=False,
            rejectable=False,
            revenue=SUCCESS_FEES,
        )
        self.realised(e.wip_cents, fee)
        self.transfer(bill, bill.outstanding_cents)
        self.client_book.pay_out(bk.REFUNDS, e.client_id, recovery - fee)
        self.hold_funds(e.client_id, -(recovery - fee))
        self.settle_funding(e, fee)
        return replace(
            e, wip_cents=0, wip_tenths=0, billed_cents=e.billed_cents + fee, advances_cents=0
        )

    def settle_funding(self, e: Engagement, fee: int) -> None:
        """PT-M12: the funder's waterfall at a funded case's close (ADR PT-0018)."""
        close = funding.close_funding(e.advances_cents, fee, e.funder_return_bp)
        office = self.office(e.client_id)
        self.books.move(bk.FUNDING, FUNDER_ADVANCES, CASH, close.repaid_cents, e.practice, office)
        self.books.move(bk.FUNDING, FUNDING_COSTS, CASH, close.cost_cents, e.practice, office)
        self.books.move(
            bk.FUNDING, FUNDER_ADVANCES, FUNDED_FEES, close.released_cents, e.practice, office
        )
        self.add("funder_paid_cents", close.paid_cents)
        self.add("funded_released_cents", close.released_cents)

    # --- 7. disputes ------------------------------------------------------------------------

    def expire_disputes(self) -> None:
        for bid in sorted(self.bills):
            bill = self.bills[bid]
            if bill.dispute is None or self.turn < bill.dispute.expires_turn:
                continue
            u = fx.billing_draws(self.rng, self.turn, fx.DISPUTE, bid)
            rel = relationship_score(self.state, bill.client_id, self.firm_id)
            bill, credit, points = resolve_dispute(
                bill, "negotiate", u[0], rel, self.turn, self.cfg
            )
            self.books.move(
                bk.CREDIT_NOTES,
                FEES,
                RECEIVABLES,
                credit,
                bill.practice,
                self.office(bill.client_id),
            )
            self.add("credited_cents", credit)
            self.point(bill.client_id, points)
            self.bills[bid] = bill

    # --- 8. provisions ----------------------------------------------------------------------

    def provisions(self) -> None:
        target = 0
        for mid, e in self.eng.items():
            if e.closed:
                continue
            if e.model == "contingency":
                continue  # PT-M12: its WIP is not on the books (ADR PT-0018)
            v = self.views.get(mid)
            target += e.wip_cents - fx.expected_value(e, v.progress if v else 0.0, self.cfg)
        for f in self.flows.values():
            if f.wip_cents > 0:
                disc = self.discount_bp(f.client_id)
                target += f.wip_cents - fx.after_discount(f.wip_cents, disc)
        self.books.move(bk.PROVISIONS, FEES, WIP_PROVISION, target - self.wip_provision)
        self.wip_provision = target
        bad = sum(
            pct_of(b.outstanding_cents, fx.provision_bp(self.turn - b.issued_turn, self.cfg))
            for b in self.bills.values()
            if b.is_open
        )
        self.books.move(
            bk.PROVISIONS, WRITE_OFFS, BAD_DEBT_PROVISION, bad - self.bad_debt_provision
        )
        self.bad_debt_provision = bad

    # --- result -----------------------------------------------------------------------------

    def run(self) -> BillingMonth:
        self.sync()
        self.collect()
        self.cycle_bills()
        self.post_wip()
        self.retainers()
        self.closings()
        self.expire_disputes()
        self.provisions()
        return self.finish()

    def finish(self) -> BillingMonth:
        fees = -self.books.total(FEES, SUCCESS_FEES, FUNDED_FEES)
        resolved = [b for b in self.bills.values() if b.closed_turn == self.turn]
        month = MonthTotals(
            turn=self.turn,
            firm_id=self.firm_id,
            fees_cents=fees,
            premium_cents=-self.books.total(SUCCESS_FEES),
            resolved_billed_cents=sum(b.billed_cents for b in resolved),
            resolved_paid_cents=sum(b.paid_cents for b in resolved),
            **self.totals,
        )
        old = self.state.billing
        mine = [m for m in old.months if m.firm_id == self.firm_id and m.turn < self.turn]
        others = [m for m in old.months if m.firm_id != self.firm_id]
        months = tuple(
            sorted((*others, *[*mine, month][-TRAILING:]), key=lambda m: (m.firm_id, m.turn))
        )
        engagements = sorted((*self.other_eng, *self.eng.values()), key=lambda e: e.matter_id)
        flows = sorted((*self.other_flows, *(f for f in self.flows.values())), key=lambda f: f.key)
        funds = tuple(
            ClientFunds(client_id=c, firm_id=f, owed_cents=v)
            for (f, c), v in sorted(self.funds.items())
            if v != 0
        )
        billing = replace(
            old,
            engagements=tuple(engagements),
            flows=tuple(flows),
            bills=tuple(sorted(self.bills.values(), key=lambda b: b.id)),
            funds=funds,
            months=months,
            next_bill_id=self.next_bill_id,
            wip_provision_cents=self.wip_provision,
            bad_debt_provision_cents=self.bad_debt_provision,
            deferred_cents=self.deferred,
            padding_found=tuple(sorted(self.found)),
        )
        state = replace(self.state, billing=billing)
        if self.audits:  # PT-M15: the month's audits, for the Risk screen
            state = replace(state, risk=keep_audits(state.risk, self.audits, self.turn))
        for cid in sorted(self.points):
            state = bump_relationship(state, cid, self.firm_id, self.points[cid])
        return BillingMonth(
            state=state,
            entries=self.books.entries(),
            book=self.client_book.entries(),
            log=tuple(self.logs),
        )


def _pick_model(mix: Mapping[str, float], u: float) -> BillingModel:
    acc = 0.0
    last: BillingModel = "hourly"
    for model in BILLING_MODELS:
        w = mix.get(model, 0.0)
        if w <= 0:
            continue
        acc += w
        last = model
        if u < acc:
            return model
    return last


def resolve_dispute(
    bill: Bill, choice: DisputeChoice, u: float, relationship: float, turn: int, cfg: BillingBalance
) -> tuple[Bill, int, float]:
    """Answer a dispute: (the bill, the credit note, relationship points). Concede credits the
    disputed amount; negotiate credits `negotiate_share` of it; holding firm is paid in full
    with the hold chance, else the client is credited in full and the relationship suffers."""
    d = bill.dispute
    if d is None:
        return bill, 0, 0.0
    if choice == "concede":
        credit, points = d.amount_cents, cfg.concede_points
    elif choice == "negotiate":
        credit, points = times(d.amount_cents, cfg.negotiate_share), 0.0
    elif u < fx.hold_chance(relationship, cfg):
        credit, points = 0, 0.0
    else:
        credit, points = d.amount_cents, cfg.hold_fail_points
    credit = min(credit, bill.outstanding_cents)
    out = replace(
        bill,
        credited_cents=bill.credited_cents + credit,
        dispute=None,
        status="open",
        due_turn=max(bill.due_turn, turn + 1),
    )
    if out.outstanding_cents <= 0:
        out = replace(out, status="paid", closed_turn=turn)
    return out, credit, points


def billing_month(
    state: GameState, rng: RngFactory, data: GameData, balance: Balance
) -> BillingMonth:
    """The player's firm's billing month (phase 5, after PT-M3a's work)."""
    if not state.market.clients:
        return BillingMonth(state=state, entries=(), book=(), log=())
    return _Run(state, state.player.id, rng, data, balance).run()
