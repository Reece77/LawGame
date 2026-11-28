"""Regulators' inquiries into the firm (spec 11.4; ADR PT-0017 4; TST 48.3's settle or contest).

A regulator that sanctions firms (bar_rules.yaml `discipline.firm_sanctions`: the SRA for
England and Wales, New York's grievance committees) may open an inquiry where the firm's systems
failed: a client-account shortfall (`trust_bp`), `cases_12m` disciplinary cases opened in a
year (`cases_bp`), or a conflict that surfaced with the checks off (`conflict_bp`) (stream
`regulator`, (1, firm_id)). One open inquiry a regulator at a time, and none within
`cooldown_months` of the last one's close.

The inquiry shows the fine a finding would bring as a range: `fine_share_bp` of the firm's
year of fees, capped by the regulator's cap at the date (0 where it cannot fine: a finding is
then a public censure only). Within `window` months the firm settles (the fine's middle x
`settle_share_bp`, posted to 6970 at once, half the reputation cost) or contests (the firm's
lawyers' costs to 6600; at the inquiry's end a finding with chance `found_bp` + `found_per_
failure_bp` per failure it counts, the fine at the range's top and the reputation cost in every
practice). Unanswered at the window's end, the firm settles.
"""

from __future__ import annotations

from dataclasses import replace

from simcore.kernel.calendar import turn_to_ym

from ptk.sim.data_models import Balance, GameData
from ptk.sim.risk import draws as dr
from ptk.sim.risk import formulas as fx
from ptk.sim.risk.common import FINES, PROFESSIONAL_FEES, Books, with_risk
from ptk.sim.risk.models import Inquiry, InquiryChoice, take_id, with_firm, with_inquiry
from ptk.sim.state import GameState
from ptk.sim.streams import RngFactory

MONTHS = 12  # tunable-exempt: a year


def _fees_12m(state: GameState, firm_id: int) -> int:
    return sum(m.fees_cents for m in state.billing.months if m.firm_id == firm_id)


def regulator_label(data: GameData, jurisdiction: str) -> str:
    rules = data.geo.rules(jurisdiction)
    return rules.regulator if rules is not None else jurisdiction


def failures(state: GameState, firm_id: int) -> int:
    since = state.turn - MONTHS
    risk = state.risk
    return sum(1 for c in risk.cases if c.firm_id == firm_id and c.opened_turn > since) + sum(
        1
        for r in risk.reconciliations
        if r.firm_id == firm_id and r.turn > since and r.shortfall_cents
    )


def open_inquiry(
    state: GameState,
    jurisdiction: str,
    reason: str,
    u: list[float],
    books: Books,
    balance: Balance,
    data: GameData,
) -> GameState:
    cfg = balance.risk.regulator
    rules = data.geo.rules(jurisdiction)
    if rules is None or not rules.discipline.firm_sanctions:
        return state
    firm = state.risk.firm(books.firm_id)
    if books.turn < firm.inquiry_cooldown_until or any(
        i.is_open and i.firm_id == books.firm_id and i.jurisdiction == jurisdiction
        for i in state.risk.inquiries
    ):
        return state
    cap = rules.discipline.fine_cap(turn_to_ym(books.turn, state.save_meta.start_ym))
    hi = min(cap, _fees_12m(state, books.firm_id) * cfg.fine_share_bp // fx.BP)
    risk, iid = take_id(state.risk)
    inquiry = Inquiry(
        id=iid,
        firm_id=books.firm_id,
        jurisdiction=jurisdiction,
        reason=reason,
        opened_turn=books.turn,
        failures=failures(state, books.firm_id),
        fine_lo_cents=hi // 2,
        fine_hi_cents=hi,
        stage_until=books.turn + fx.span(u[0], cfg.months),
    )
    books.inbox(
        "inquiry_opened",
        iid,
        regulator=regulator_label(data, jurisdiction),
        reason=reason,
        fine_hi_cents=hi,
    )
    return with_risk(state, with_inquiry(risk, inquiry))


def new_inquiries(
    state: GameState,
    rng: RngFactory,
    books: Books,
    balance: Balance,
    data: GameData,
    triggers: list[tuple[str, str]],
) -> GameState:
    """`triggers`: (jurisdiction, reason) of the month's failures, in order."""
    cfg = balance.risk.regulator
    since = books.turn - MONTHS
    cases = [c for c in state.risk.cases if c.firm_id == books.firm_id and c.opened_turn > since]
    if len(cases) >= cfg.cases_12m and any(c.opened_turn == books.turn for c in cases):
        triggers = [*triggers, (cases[-1].jurisdiction, "cases")]
    if not triggers:
        return state
    gen = dr.regulator_draws(rng, books.turn, dr.OPENED, books.firm_id)
    chance = {"trust": cfg.trust_bp, "cases": cfg.cases_bp, "conflicts": cfg.conflict_bp}
    for jurisdiction, reason in triggers:
        u = [float(x) for x in gen.random(2)]
        if u[1] < chance[reason] / fx.BP:
            state = open_inquiry(state, jurisdiction, reason, u, books, balance, data)
    return state


def respond(
    state: GameState, inquiry: Inquiry, choice: InquiryChoice, books: Books, balance: Balance
) -> GameState:
    """Settle (pay now, close) or contest (pay the costs, await the end)."""
    from ptk.sim.reputation.formulas import apply_pulse

    cfg = balance.risk.regulator
    if choice == "settle":
        fine = (inquiry.fine_lo_cents + inquiry.fine_hi_cents) // 2 * cfg.settle_share_bp // fx.BP
        books.pay(FINES, fine, f"Inquiry {inquiry.id}: settlement with the regulator")
        state = apply_pulse(
            state, books.firm_id, cfg.public_points / 2, "a regulator's settlement", balance
        )
        state = _close(
            state,
            replace(inquiry, choice=choice, outcome="settled", fine_cents=fine),
            books,
            balance,
        )
        return state
    books.pay(PROFESSIONAL_FEES, cfg.contest_cents, f"Inquiry {inquiry.id}: the firm's defence")
    return with_risk(state, with_inquiry(state.risk, replace(inquiry, choice=choice)))


def _close(state: GameState, inquiry: Inquiry, books: Books, balance: Balance) -> GameState:
    inquiry = replace(inquiry, stage="closed", stage_until=None, closed_turn=books.turn)
    risk = with_inquiry(state.risk, inquiry)
    firm = risk.firm(books.firm_id)
    risk = with_firm(
        risk,
        replace(firm, inquiry_cooldown_until=books.turn + balance.risk.regulator.cooldown_months),
    )
    books.inbox(
        "inquiry_closed",
        inquiry.id,
        outcome=inquiry.outcome or "dismissed",
        fine_cents=inquiry.fine_cents,
    )
    return with_risk(state, risk)


def inquiries_month(state: GameState, rng: RngFactory, books: Books, balance: Balance) -> GameState:
    from ptk.sim.reputation.formulas import apply_pulse

    cfg = balance.risk.regulator
    for inquiry in [i for i in state.risk.inquiries if i.firm_id == books.firm_id and i.is_open]:
        if inquiry.choice is None and books.turn >= inquiry.opened_turn + cfg.window:
            state = respond(state, inquiry, "settle", books, balance)
            continue
        if (
            inquiry.stage_until is None
            or books.turn < inquiry.stage_until
            or inquiry.choice is None
        ):
            continue
        u = float(dr.regulator_draws(rng, books.turn, dr.MONTH, inquiry.id).random())
        p = (cfg.found_bp + cfg.found_per_failure_bp * inquiry.failures) / fx.BP
        if u < p:
            books.pay(FINES, inquiry.fine_hi_cents, f"Inquiry {inquiry.id}: the regulator's fine")
            state = apply_pulse(
                state, books.firm_id, cfg.public_points, "a regulator's finding", balance
            )
            state = _close(
                state,
                replace(inquiry, outcome="fined", fine_cents=inquiry.fine_hi_cents),
                books,
                balance,
            )
        else:
            state = _close(state, replace(inquiry, outcome="dismissed"), books, balance)
    return state
