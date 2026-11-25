"""PT-M15 sub-tasks 4-6: discipline, regulators' inquiries, trust accounts, audits and fee
arbitration (spec 11.4, 11.6; ADR PT-0003 7, PT-0013)."""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from ptk.sim.billing.models import ClientFunds
from ptk.sim.data_models import Balance
from ptk.sim.interfaces import ClientBillingView, suspended
from ptk.sim.risk import discipline as dc
from ptk.sim.risk import inquiries as iq
from ptk.sim.risk import trust
from ptk.sim.risk.arbitration import after_hold, awards_month
from ptk.sim.risk.common import Books, lawyers
from ptk.sim.risk.models import EMPTY_RISK
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState
from tests.risk_support import busy_firm, loaded


def _risky(balance: Balance, **changes: object) -> Balance:
    """The balance with the risk section's sub-models updated (e.g. discipline=...)."""
    return balance.model_copy(update={"risk": balance.risk.model_copy(update=changes)})


def _always(balance: Balance) -> Balance:
    d = balance.risk.discipline
    causes = d.causes.model_copy(update={"court": 10_000, "neglect": 10_000})
    return _risky(balance, discipline=d.model_copy(update={"causes": causes}))


def _clean() -> GameState:
    return replace(busy_firm(), risk=EMPTY_RISK)


def _books(state: GameState, cash: int = 10**12) -> Books:
    return Books(state.player.id, state.turn, cash)


def test_cases_open_from_the_month_rolls_and_never_for_real_people() -> None:
    data, balance = loaded()
    hot = _always(balance)
    state = _clean()
    books = _books(state)
    out = dc.new_cases(state, state, np.random.default_rng(1), books, hot, data, [])  # noqa: NPY002
    staff = lawyers(state, state.player.id, data)
    assert {c.person_id for c in out.risk.cases} == {p.id for p in staff if not p.real}
    real = replace(state, people=tuple(replace(p, real=True) for p in state.people))
    none = dc.new_cases(real, real, np.random.default_rng(1), _books(real), hot, data, [])  # noqa: NPY002
    assert none.risk.cases == ()


def _run_case(state: GameState, balance: Balance, months: int = 30) -> GameState:
    data, _ = loaded()
    for _ in range(months):
        books = _books(state)
        state = dc.cases_month(state, RngFactory(5), books, balance, data, {})
        state = replace(state, turn=state.turn + 1)
    return state


def test_a_case_runs_its_stages_to_a_sanction_and_a_suspension_stops_billing() -> None:
    data, balance = loaded()
    d = balance.risk.discipline
    only_suspension = d.model_copy(
        update={"outcomes": (d.outcomes[0].model_copy(update={"key": "suspension", "min": 0.0}),)}
    )
    b = _risky(balance, discipline=only_suspension)
    state = _clean()
    pid = next(p.id for p in lawyers(state, state.player.id, data) if not p.is_founder)
    state = dc.open_case(state, pid, "neglect", np.random.default_rng(2), _books(state), b, data)  # noqa: NPY002
    case = state.risk.cases[0]
    state = replace(state, risk=replace(state.risk, cases=(replace(case, culpability=1.0),)))
    state = _run_case(state, b)
    closed = state.risk.cases[0]
    assert closed.stage == "closed" and closed.outcome == "suspension"
    assert closed.suspended_until is not None and closed.choice == "cooperate"
    during = replace(state, turn=closed.closed_turn or 0)
    assert suspended(during, pid)
    assert not suspended(replace(state, turn=closed.suspended_until), pid)


def test_disbarment_ends_an_associates_time_at_the_firm() -> None:
    data, balance = loaded()
    d = balance.risk.discipline
    only = d.model_copy(
        update={"outcomes": (d.outcomes[0].model_copy(update={"key": "disbarment", "min": 0.0}),)}
    )
    b = _risky(balance, discipline=only)
    state = _clean()
    pid = next(
        p.id for p in lawyers(state, state.player.id, data) if p.level.startswith("associate")
    )
    state = dc.open_case(state, pid, "court", np.random.default_rng(2), _books(state), b, data)  # noqa: NPY002
    case = replace(state.risk.cases[0], culpability=1.0)
    state = _run_case(replace(state, risk=replace(state.risk, cases=(case,))), b)
    e = state.employment_of(pid)
    assert state.risk.cases[0].outcome == "disbarment"
    assert e is not None and e.status in ("notice", "ended") and e.end_reason == "fired"


def _with_funds(state: GameState, cents: int) -> GameState:
    client = state.market.clients[0].id
    funds = (ClientFunds(client_id=client, firm_id=state.player.id, owed_cents=cents),)
    return replace(state, billing=replace(state.billing, funds=funds))


def test_a_shortfall_is_made_good_and_raises_a_critical_event() -> None:
    data, balance = loaded()
    t = balance.risk.trust.model_copy(update={"error_bp": 10_000})
    b = _risky(balance, trust=t)
    state = _with_funds(_clean(), 50_000_000)
    books = _books(state)
    out, book, rec = trust.reconcile(state, RngFactory(1), books, b, data)
    assert (
        rec is not None and rec.shortfall_cents > 0 and rec.made_good_cents == rec.shortfall_cents
    )
    assert rec.bank_cents == rec.owed_cents - rec.shortfall_cents
    bank = sum(line.amount for e in book for line in e.lines if line.account == "C1000_client_bank")
    assert bank == 0  # made good the same month: the bank equals what is owed at month end
    assert all(sum(line.amount for line in e.lines) == 0 for e in book)
    assert sum(e.lines[0].amount for e in books.entries) == rec.shortfall_cents
    assert any(q.template_id == "trust_shortfall" for q in out.events.queued)


def test_no_money_held_no_reconciliation_and_no_misuse_by_real_partners() -> None:
    data, balance = loaded()
    t = balance.risk.trust.model_copy(update={"error_bp": 0, "misuse_bp": 10_000})
    b = _risky(balance, trust=t)
    state = _clean()
    assert trust.reconcile(state, RngFactory(1), _books(state), b, data)[2] is None
    real = replace(
        _with_funds(state, 10**8), people=tuple(replace(p, real=True) for p in state.people)
    )
    rec = trust.reconcile(real, RngFactory(1), _books(real), b, data)[2]
    assert rec is not None and rec.shortfall_cents == 0


def test_an_inquiry_settles_with_a_fine_or_is_contested() -> None:
    data, balance = loaded()
    state = _clean()
    books = _books(state)
    state = iq.open_inquiry(state, "ew", "trust", [0.5, 0.0], books, balance, data)
    inquiry = state.risk.inquiries[0]
    assert inquiry.fine_hi_cents <= data.geo.rules("ew").discipline.fine_cap((2006, 1))  # type: ignore[union-attr]
    settled = iq.respond(state, inquiry, "settle", books, balance)
    assert settled.risk.inquiries[0].outcome == "settled"
    assert settled.risk.firm(state.player.id).inquiry_cooldown_until > state.turn
    again = iq.open_inquiry(settled, "ew", "trust", [0.5, 0.0], books, balance, data)
    assert len(again.risk.inquiries) == 1  # the regulator waits after closing one
    # New York cannot fine a firm: its finding is a censure
    fresh = _clean()
    ny = iq.open_inquiry(fresh, "us_ny", "cases", [0.5, 0.0], _books(fresh), balance, data)
    assert ny.risk.inquiries[0].fine_hi_cents == 0


def test_a_held_dispute_in_range_goes_to_fee_arbitration() -> None:
    data, balance = loaded()
    state = _clean()
    bill = next(b for b in state.billing.bills) if state.billing.bills else None
    assert bill is not None
    out, logs = after_hold(state, bill, 2_000_000, 0.0, 0.5, balance, data)
    assert len(out.risk.arbitrations) == 1 and logs
    arb = out.risk.arbitrations[0]
    a = balance.risk.audits.model_copy(update={"award_fee_bp": 10_000})
    b = _risky(balance, audits=a)
    later = replace(out, turn=arb.decide_turn)
    books = _books(later)
    decided = awards_month(later, RngFactory(3), books, b)
    assert decided.risk.arbitrations[0].decided and decided.risk.arbitrations[0].award_cents > 0
    assert all(sum(line.amount for line in e.lines) == 0 for e in books.entries)
    outside, _ = after_hold(state, bill, 10_000_000, 0.0, 0.5, balance, data)  # $100k: no Part 137
    assert outside.risk.arbitrations == ()


def test_a_large_clients_audit_cuts_a_bill() -> None:
    from ptk.sim.billing.audits import audit

    data, balance = loaded()
    a = balance.risk.audits.model_copy(update={"audit_bp": 10_000})
    b = _risky(balance, audits=a)
    state = replace(_clean(), turn=24)
    big = ClientBillingView(1, "Big Co", True, "large", 10.0, 10.0, 10.0)
    mid = replace(big, size_class="mid")
    cut = audit(state, RngFactory(1), 77, big, 1_000_000, 50_000, b)
    assert cut is not None and 0 < cut.cut_cents <= 50_000 and cut.finds_padding
    assert audit(state, RngFactory(1), 77, mid, 1_000_000, 0, b) is None
