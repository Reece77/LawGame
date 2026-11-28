"""PT-M3b: billing models, bills, write-downs, collections, disputes, padding, client money."""

from __future__ import annotations

from collections import Counter
from dataclasses import replace

import pytest

from ptk.sim.billing import formulas as fx
from ptk.sim.billing.actions import RespondDispute, WriteDownMatter
from ptk.sim.billing.models import Bill, BillingState, Dispute, Engagement
from ptk.sim.billing.phase import _pick_model, billing_month, resolve_dispute
from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import BillingActionError, UnknownBillError
from ptk.sim.interfaces import ClientBillingView
from ptk.sim.ledger import CASH, CLIENT_BANK, DEFERRED_FEES, OWED_TO_CLIENTS, SUCCESS_FEES
from ptk.sim.state import GameState
from ptk.sim.streams import RngFactory
from tests.billing_support import played


def _client(ps: float = 10.0, size: str = "large", temperament: float = 10.0) -> ClientBillingView:
    return ClientBillingView(
        client_id=1,
        name="C",
        real=False,
        size_class=size,
        price_sensitivity=ps,
        gc_temperament=temperament,
        gc_integrity=10.0,
    )


def _eng(model: str = "hourly", **kw: int) -> Engagement:
    return Engagement(
        matter_id=1,
        firm_id=1,
        client_id=1,
        practice="corporate_ma",
        model=model,  # type: ignore[arg-type]
        opened_turn=0,
        **kw,
    )


# --- formulas --------------------------------------------------------------------------------


def test_fees_by_model(balance: Balance) -> None:
    wip, tenths = 1_000_000, 200  # $10,000 for 20 hours
    assert fx.hourly_fee(_eng(discount_bp=1000), wip, tenths) == 900_000
    assert fx.hourly_fee(_eng("success", discount_bp=0, share_bp=8000), wip, tenths) == 800_000
    # blended: 20 hours x $400 less 10%
    assert (
        fx.hourly_fee(_eng("blended", rate_cents=40_000, discount_bp=1000), wip, tenths) == 720_000
    )
    # capped: never past the cap
    capped = _eng("capped", price_cents=1_500_000, billed_cents=1_200_000)
    assert fx.hourly_fee(capped, wip, tenths) == 300_000
    # fixed: the completed share of the price, less what is billed
    fixed = _eng("fixed", price_cents=2_000_000, billed_cents=500_000)
    assert fx.fixed_due(fixed, 0.5) == 500_000
    assert fx.fixed_due(fixed, 0.2) == 0


def test_client_discount_and_chances_follow_price_sensitivity(balance: Balance) -> None:
    cfg = balance.billing
    low, mid, high = (fx.client_discount_bp(_client(ps), cfg) for ps in (4, 10, 20))
    assert low < mid == cfg.discount_base_bp < high <= cfg.discount_max_bp
    assert fx.bp_chance(1500, 150, 20) > fx.bp_chance(1500, 150, 10) > fx.bp_chance(1500, 150, 1)
    assert fx.dispute_chance(_client(temperament=4), False, cfg) > fx.dispute_chance(
        _client(temperament=16), False, cfg
    )
    assert fx.dispute_chance(_client(), True, cfg) == pytest.approx(
        fx.dispute_chance(_client(), False, cfg) * cfg.dispute_padding_mult
    )


def test_overrun_is_written_down_by_the_default_rule(balance: Balance) -> None:
    cfg = balance.billing
    # expected $100k; $130k worked so far, $40k of it on this bill: $20k is past 110%
    e = _eng(standard_cents=13_000_000)
    wd = fx.overrun_writedown(e, 10_000_000, 4_000_000, 3_600_000, cfg)
    assert wd == round(2_000_000 * cfg.overrun_writedown * 3_600_000 / 4_000_000)
    assert (
        fx.overrun_writedown(_eng(standard_cents=9_000_000), 10_000_000, 4_000_000, 3_600_000, cfg)
        == 0
    )


def test_days_to_pay_and_provisions(balance: Balance) -> None:
    cfg = balance.billing
    assert fx.days_to_pay(_client(20), 0.5, cfg) > fx.days_to_pay(_client(10), 0.5, cfg)
    assert fx.days_to_pay(_client(10, "mid"), 0.5, cfg) < fx.days_to_pay(_client(10), 0.5, cfg)
    assert fx.due_turn(5, 1.0, cfg) == 6  # never paid in the month billed
    ages = [fx.provision_bp(a, cfg) for a in (0, 2, 3, 6, 12, 40)]
    assert ages == sorted(ages) and ages[0] == cfg.provision_bp[0].value


def test_model_mix_is_seeded_and_follows_the_kind(balance: Balance) -> None:
    rng = RngFactory(5)
    mix = balance.billing.models["case"]
    picks = Counter(
        _pick_model(mix, fx.billing_draws(rng, 3, fx.TERMS, mid)[0]) for mid in range(1, 4001)
    )
    again = Counter(
        _pick_model(mix, fx.billing_draws(RngFactory(5), 3, fx.TERMS, mid)[0])
        for mid in range(1, 4001)
    )
    assert picks == again
    for model, w in mix.items():
        assert abs(picks[model] / 4000 - w) < 0.03  # tunable-exempt: sampling tolerance
    assert set(picks) == set(mix)


# --- the phase ---------------------------------------------------------------------------


def test_same_seed_same_books(data: GameData, balance: Balance) -> None:
    a = played(data, balance, 12, 8, seed=4)
    b = played(data, balance, 12, 8, seed=4)
    assert a.state.billing == b.state.billing
    assert a.entries == b.entries and a.book == b.book
    c = played(data, balance, 12, 8, seed=5)
    assert c.state.billing != a.state.billing


def _with_engagement(state: GameState, e: Engagement) -> GameState:
    rest = [x for x in state.billing.engagements if x.matter_id != e.matter_id]
    engagements = tuple(sorted([*rest, e], key=lambda x: x.matter_id))
    return replace(state, billing=replace(state.billing, engagements=engagements))


def _open_matter(state: GameState) -> int:
    return next(m.id for m in state.market.open_matters(1) if state.billing.engagement(m.id))


def _close(state: GameState, matter_id: int, outcome: str) -> GameState:
    from ptk.sim.matters.intake import with_matter

    m = state.market.matter(matter_id)
    assert m is not None
    closed = replace(m, status="closed", outcome=outcome, closed_turn=state.turn)  # type: ignore[arg-type]
    return replace(state, market=with_matter(state.market, closed))


def test_retainer_defers_income_then_bills_hourly_after_its_term(
    data: GameData, balance: Balance
) -> None:
    # PT-M7: seed 3 (seed 2's universe now holds a retainer of its own; this test needs none)
    game = played(data, balance, 24, 4, seed=3)
    assert game.state.billing.deferred_cents == 0  # no other retainer's deferred income
    mid = _open_matter(game.state)
    e = game.state.billing.engagement(mid)
    assert e is not None
    state = _with_engagement(
        game.state, replace(e, model="retainer", price_cents=500_000, term_months=2, wip_cents=0)
    )
    month = billing_month(state, RngFactory(3), data, balance)
    first = month.state.billing.engagement(mid)
    assert first is not None and first.advance_turn == state.turn + 1 and first.months_billed == 1
    deferred = sum(
        ln.amount for x in month.entries for ln in x.lines if ln.account == DEFERRED_FEES
    )
    assert deferred == -500_000  # next month billed in advance, not yet earned
    assert month.state.billing.deferred_cents == 500_000
    nxt = replace(month.state, turn=state.turn + 1)
    second = billing_month(nxt, RngFactory(3), data, balance)
    earned = sum(ln.amount for x in second.entries for ln in x.lines if ln.account == DEFERRED_FEES)
    after = second.state.billing.engagement(mid)
    assert earned == 500_000  # earned out of deferred income, and the term is over
    assert after is not None and after.model == "hourly" and after.months_billed == 2


def test_contingency_fee_comes_from_the_recovery_through_the_client_book(
    data: GameData, balance: Balance
) -> None:
    game = played(data, balance, 24, 4, seed=3)
    mid = _open_matter(game.state)
    e = game.state.billing.engagement(mid)
    assert e is not None
    m = game.state.market.matter(mid)
    assert m is not None
    from ptk.sim.matters.intake import with_matter

    state = replace(
        game.state, market=with_matter(game.state.market, replace(m, stakes_cents=10_000_000))
    )
    state = _with_engagement(
        state, replace(e, model="contingency", share_bp=3000, wip_cents=1_000_000)
    )
    month = billing_month(_close(state, mid, "won"), RngFactory(3), data, balance)
    recovery = 10_000_000 * balance.billing.recovery_bp // 10_000
    fee = recovery * 3000 // 10_000
    book = [ln for x in month.book for ln in x.lines if ln.client_id == m.client_id]
    bank = sum(ln.amount for ln in book if ln.account == CLIENT_BANK)
    owed = sum(ln.amount for ln in book if ln.account == OWED_TO_CLIENTS)
    assert bank == -owed == month.state.billing.funds_of(m.client_id, 1)
    received = sum(
        ln.amount for x in month.book for ln in x.lines if x.memo.startswith("Recoveries")
    )
    assert received == 0  # bank and owed move together
    transfers = [x for x in month.entries if x.memo.startswith("Bills paid from client money")]
    assert sum(ln.amount for x in transfers for ln in x.lines if ln.account == CASH) >= fee
    premium = -sum(ln.amount for x in month.entries for ln in x.lines if ln.account == SUCCESS_FEES)
    # PT-M12 (ADR PT-0018): a contingency case's WIP never posted a fee, so the whole fee is
    # the contingency fee (4100); PT-M3b's premium was the fee above the WIP posted to 4000
    assert premium == fee
    closed = month.state.billing.engagement(mid)
    assert closed is not None and closed.closed and closed.wip_cents == 0


def test_a_lost_contingency_case_writes_its_wip_off(data: GameData, balance: Balance) -> None:
    game = played(data, balance, 24, 4, seed=3)
    mid = _open_matter(game.state)
    e = game.state.billing.engagement(mid)
    assert e is not None
    state = _with_engagement(
        game.state, replace(e, model="contingency", share_bp=3000, wip_cents=800_000)
    )
    month = billing_month(_close(state, mid, "lost"), RngFactory(3), data, balance)
    assert not month.book or all(m.memo != "Recoveries received for clients" for m in month.book)
    totals = next(t for t in month.state.billing.months if t.turn == state.turn)
    assert totals.standard_cents >= 800_000


def test_success_bonus_on_a_closed_deal(data: GameData, balance: Balance) -> None:
    game = played(data, balance, 24, 4, seed=6)
    mid = _open_matter(game.state)
    e = game.state.billing.engagement(mid)
    assert e is not None
    state = _with_engagement(
        game.state, replace(e, model="success", share_bp=8000, bonus_cents=250_000)
    )
    month = billing_month(_close(state, mid, "closed"), RngFactory(6), data, balance)
    bonus = [b for b in month.state.billing.bills if b.kind == "success" and b.matter_id == mid]
    assert len(bonus) == 1 and bonus[0].billed_cents == 250_000 and bonus[0].standard_cents == 0


def test_partner_write_down_applies_to_the_next_bill(data: GameData, balance: Balance) -> None:
    from ptk.sim.actions import apply_action

    game = played(data, balance, 24, 4, seed=7)
    mid = _open_matter(game.state)
    hourly = game.state.billing.engagement(mid)
    assert hourly is not None
    state = _with_engagement(game.state, replace(hourly, model="hourly"))
    founder = state.founder_of(1)
    assert founder is not None
    out = apply_action(
        state,
        WriteDownMatter(founder, mid, 2000),
        seq=1,
        rng=RngFactory(7),
        balance=balance,
        data=data,
        ledger_balances={},
    )
    e = out.state.billing.engagement(mid)
    assert e is not None and e.writedown_bp == 2000
    with pytest.raises(BillingActionError):
        apply_action(
            state,
            WriteDownMatter(founder, mid, 9999),
            seq=2,
            rng=RngFactory(7),
            balance=balance,
            data=data,
            ledger_balances={},
        )
    # the next cycle bill carries it, and resets it
    e2 = replace(e, wip_cents=1_000_000, wip_tenths=20, last_bill_turn=None)
    s2 = _with_engagement(out.state, e2)
    month = billing_month(s2, RngFactory(7), data, balance)
    after = month.state.billing.engagement(mid)
    assert after is not None and after.writedown_bp == 0


def _disputed(bill_id: int = 9, amount: int = 200_000, padded: bool = False) -> Bill:
    return Bill(
        id=bill_id,
        firm_id=1,
        client_id=1,
        matter_id=None,
        practice="ip",
        model="hourly",
        kind="fees",
        issued_turn=3,
        due_turn=5,
        standard_cents=1_000_000,
        billed_cents=900_000,
        status="disputed",
        dispute=Dispute(amount_cents=amount, raised_turn=3, expires_turn=5, padded=padded),
    )


def test_dispute_answers(balance: Balance) -> None:
    cfg = balance.billing
    bill = _disputed()
    conceded, credit, pts = resolve_dispute(bill, "concede", 0.0, 50, 4, cfg)
    assert credit == 200_000 and pts == cfg.concede_points and conceded.dispute is None
    _, credit, pts = resolve_dispute(bill, "negotiate", 0.0, 50, 4, cfg)
    assert credit == 100_000 and pts == 0
    held, credit, _ = resolve_dispute(bill, "hold", 0.0, 90, 4, cfg)  # strong relationship
    assert credit == 0 and held.status == "open" and held.due_turn == 5
    _, credit, pts = resolve_dispute(bill, "hold", 0.999, 10, 4, cfg)
    assert credit == 200_000 and pts == cfg.hold_fail_points
    assert fx.hold_chance(90, cfg) > fx.hold_chance(50, cfg) > fx.hold_chance(10, cfg)


def test_respond_dispute_action_posts_a_credit_note(data: GameData, balance: Balance) -> None:
    from ptk.sim.actions import apply_action

    game = played(data, balance, 12, 2, seed=8)
    founder = game.state.founder_of(1)
    assert founder is not None
    bill = replace(_disputed(bill_id=9999), client_id=game.state.market.relationships[0].client_id)
    state = replace(
        game.state, billing=replace(game.state.billing, bills=(*game.state.billing.bills, bill))
    )
    out = apply_action(
        state,
        RespondDispute(founder, 9999, "concede"),
        seq=1,
        rng=RngFactory(8),
        balance=balance,
        data=data,
        ledger_balances={},
    )
    assert out.entries and sum(ln.amount for ln in out.entries[0].lines) == 0
    after = out.state.billing.bill(9999)
    assert after is not None and after.dispute is None and after.credited_cents == 200_000
    with pytest.raises(UnknownBillError):
        apply_action(
            state,
            RespondDispute(founder, 12345, "concede"),
            seq=2,
            rng=RngFactory(8),
            balance=balance,
            data=data,
            ledger_balances={},
        )


def test_unanswered_disputes_are_negotiated_when_their_window_closes(
    data: GameData, balance: Balance
) -> None:
    game = played(data, balance, 12, 2, seed=8)
    bill = replace(_disputed(bill_id=9999), client_id=game.state.market.relationships[0].client_id)
    state = replace(game.state, turn=5, billing=replace(game.state.billing, bills=(bill,)))
    month = billing_month(state, RngFactory(8), data, balance)
    after = month.state.billing.bill(9999)
    assert after is not None and after.dispute is None and after.credited_cents == 100_000


def test_padding_comes_to_light_in_a_dispute(data: GameData, balance: Balance) -> None:
    game = played(data, balance, 24, 4, seed=9)
    mid = _open_matter(game.state)
    hourly = game.state.billing.engagement(mid)
    assert hourly is not None
    state = _with_engagement(game.state, replace(hourly, model="hourly"))
    m = state.market.matter(mid)
    assert m is not None and m.lead_id is not None
    lead = state.person(m.lead_id)
    from ptk.sim.state import with_person

    state = with_person(state, replace(lead, tags=("rule_bender",)))
    e = state.billing.engagement(mid)
    assert e is not None
    state = _with_engagement(
        state, replace(e, wip_cents=2_000_000, wip_tenths=40, last_bill_turn=None)
    )
    certain = balance.model_copy(
        update={"billing": balance.billing.model_copy(update={"dispute_bp": 10_000})}
    )
    month = billing_month(state, RngFactory(9), data, certain)
    assert m.lead_id in month.state.billing.padding_found
    if state.reveal(1, m.lead_id) is not None:  # the firm learns the lead's tag
        reveal = month.state.reveal(1, m.lead_id)
        assert reveal is not None and "rule_bender" in {t for t, _ in reveal.revealed_tags}
    assert any(x.kind == "padding_found" for x in month.log)
    rel_before = state.market.relationship(m.client_id, 1)
    rel_after = month.state.market.relationship(m.client_id, 1)
    assert rel_before is not None and rel_after is not None and rel_after.score < rel_before.score


def test_bankruptcy_never_strikes_a_real_company(data: GameData, balance: Balance) -> None:
    game = played(data, balance, 24, 4, seed=10)
    doom = balance.model_copy(
        update={
            "billing": balance.billing.model_copy(
                update={"bankruptcy_bp": {"large": 10_000, "mid": 10_000}}
            )
        }
    )
    state = game.state
    month = billing_month(state, RngFactory(10), data, doom)
    real = {c.id for c in state.market.clients if c.real}
    for b in month.state.billing.bills:
        if b.status == "written_off" and b.closed_turn == state.turn:
            assert b.client_id not in real
    assert all(b.status != "written_off" for b in month.state.billing.bills if b.client_id in real)


def test_empty_state_has_no_billing() -> None:
    assert BillingState().next_bill_id == 1
