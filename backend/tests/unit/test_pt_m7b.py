"""PT-M7b: a new firm's card by practice, difficulty teeth, crisis discounts and collapsing
deals, the CFO's forecast warning, the hours policy and the scripts' December comp round."""

from __future__ import annotations

from dataclasses import replace

import pytest

from ptk.sim.billing.phase import billing_month
from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import MatterActionError
from ptk.sim.macro import crisis_factor, crisis_stress, driver_shortfall, sector_shortfall
from ptk.sim.matters import formulas as mfx
from ptk.sim.matters.actions import SetHoursPolicy
from ptk.sim.matters.rates import (
    card_bp,
    card_moved,
    card_target_bp,
    practice_index,
    price_term,
    start_card_bp,
    yearly_rise,
)
from ptk.sim.matters.staffing import FeeEarner, fee_earners, policy_fill
from ptk.sim.money import BP_DENOMINATOR
from ptk.sim.partnership import formulas as pfx
from ptk.sim.partnership.models import PnlPoint
from ptk.sim.rng import STREAM_IDS, RngFactory
from ptk.sim.setup import new_game
from ptk.sim.state import GameState, with_firm
from tests.hiring_helpers import start
from tests.matters_support import game, play

START = (2005, 1)


def _new(data: GameData, balance: Balance, difficulty: str, seed: int = 1) -> GameState:
    return new_game(
        name="t",
        firm_name="Founders LLP",
        master_seed=seed,
        scenario_id="biglaw_spinout",
        difficulty=difficulty,
        data=data,
        balance=balance,
    ).state


def _turn(ym: tuple[int, int]) -> int:
    return (ym[0] - START[0]) * 12 + ym[1] - START[1]


# --- 1. a new firm's card ------------------------------------------------------------------


def test_a_new_firm_starts_every_practice_at_the_start_share(
    data: GameData, balance: Balance
) -> None:
    state = game(data, balance)
    start_bp = balance.rates.card.start_bp
    assert dict(state.player.rate_card) == dict.fromkeys(data.practice_keys, start_bp)
    for p in data.practice_keys:
        assert practice_index(state.player, p) == pytest.approx(start_bp / BP_DENOMINATOR)
        # the price term reads the practice's card against the market's (1.0 at turn 0)
        assert price_term(state, state.player.id, data, balance, p) == pytest.approx(
            1 - start_bp / BP_DENOMINATOR
        )
    # a firm with no card (a save from before PT-M7b) bills at the full card
    legacy = replace(state.player, rate_card=())
    assert card_bp(legacy, "corporate_ma") == BP_DENOMINATOR
    assert practice_index(legacy, "corporate_ma") == 1.0


def test_the_target_rises_with_reputation_to_the_full_card(balance: Balance) -> None:
    """PT-M16: the target reads card progress (0-1, reputation against the market's top)."""
    start_bp = balance.rates.card.start_bp
    assert card_target_bp(0.0, start_bp, balance) == start_bp
    assert card_target_bp(1.0, start_bp, balance) == BP_DENOMINATOR
    assert card_target_bp(2.0, start_bp, balance) == BP_DENOMINATOR
    values = [card_target_bp(r / 20, start_bp, balance) for r in range(21)]
    assert values == sorted(values)


def test_january_moves_the_card_at_most_a_step(data: GameData, balance: Balance) -> None:
    state = game(data, balance)
    moved = dict(card_moved(state, state.player, data, balance))
    step = balance.rates.card.step_bp
    start_bp = balance.rates.card.start_bp
    for bp in moved.values():
        assert start_bp - step <= bp <= start_bp + step
    # PT-M16: a new firm's reputation is far below the market's top, so its card moves only a
    # little toward a target still below the full card
    assert start_bp <= moved["corporate_ma"] < BP_DENOMINATOR
    # January's rise moves it; other months do not
    state, _ = play(state, data, balance, 12)  # through December 2005
    assert dict(state.player.rate_card)["corporate_ma"] == start_bp
    state, _ = play(state, data, balance, 1)  # January 2006
    moved_bp = dict(state.player.rate_card)["corporate_ma"]
    assert start_bp - step <= moved_bp <= start_bp + step and moved_bp < BP_DENOMINATOR


def test_hours_are_valued_on_the_practice_card(data: GameData, balance: Balance) -> None:
    full = game(data, balance)
    full = with_firm(full, replace(full.player, rate_card=()))
    low = game(data, balance)
    a, _ = play(full, data, balance, 1)
    b, _ = play(low, data, balance, 1)

    def rate(s: GameState) -> float:
        rows = [r for r in s.market.hours if r.value_cents and r.practice == "corporate_ma"]
        return sum(r.value_cents for r in rows) / sum(r.tenths for r in rows)

    assert rate(b) == pytest.approx(rate(a) * balance.rates.card.start_bp / BP_DENOMINATOR, 0.05)


def test_the_rise_keeps_the_card(data: GameData, balance: Balance) -> None:
    state = game(data, balance)
    state, _ = play(state, data, balance, 12)
    state = replace(state, turn=12)
    risen, _ = yearly_rise(state, data, balance)
    assert risen.player.rate_index > 1.0
    assert risen.player.rate_card != ()


# --- 2. difficulty teeth -------------------------------------------------------------------


def test_hard_and_easy_scale_books_revolver_loyalty_and_card(
    data: GameData, balance: Balance
) -> None:
    std, hard, easy = (_new(data, balance, d) for d in ("standard", "hard", "easy"))
    lv = {d.id: d for d in data.difficulties}

    def books(s: GameState) -> dict[int, int]:
        return {p.id: p.book_cents for p in s.people if p.founding_partner}

    for s, d in ((hard, "hard"), (easy, "easy")):
        for pid, cents in books(std).items():
            assert books(s)[pid] == round(cents * lv[d].books_mult_bp / BP_DENOMINATOR)
        fp, fp0 = s.partnership.firms[0], std.partnership.firms[0]
        assert fp.facility_cents == round(fp0.facility_cents * lv[d].revolver_mult_bp / 10000)
        card = start_card_bp(d, data, balance)
        assert card == min(10000, round(balance.rates.card.start_bp * lv[d].card_mult_bp / 10000))
        assert dict(s.player.rate_card)["ip"] == card
    assert lv["standard"].books_mult_bp == lv["standard"].revolver_mult_bp == 10000
    assert lv["standard"].loyalty_points == 0 and lv["standard"].card_mult_bp == 10000
    # starting relationships carry the difficulty's loyalty points: each is drawn in the
    # books' range and shifted (the books' size changes which clients are drawn)
    lo, hi = balance.books.start_relationship.lo, balance.books.start_relationship.hi
    for s, d in ((std, "standard"), (hard, "hard"), (easy, "easy")):
        pts = lv[d].loyalty_points
        scores = [r.score for r in s.market.relationships]
        assert scores
        assert all(lo + pts - 1e-9 <= x <= hi + pts + 1e-9 for x in scores)
    assert lv["hard"].loyalty_points < 0 < lv["easy"].loyalty_points


def test_difficulty_fields_are_validated_at_load() -> None:
    from pydantic import ValidationError

    from ptk.sim.data_models import Difficulty

    with pytest.raises(ValidationError):
        Difficulty(id="x", name="X", capital_mult_bp=10000, books_mult_bp=0)
    with pytest.raises(ValidationError):
        Difficulty(id="x", name="X", capital_mult_bp=10000, loyalty_points=99)


# --- 3. the crisis -------------------------------------------------------------------------


def test_crisis_stress_peaks_in_2009_and_eases(data: GameData, balance: Balance) -> None:
    def stress(ym: tuple[int, int]) -> float:
        return crisis_stress(_turn(ym), START, data, balance)

    assert stress((2006, 7)) == 0.0
    assert stress((2007, 7)) == 0.0
    assert 0 < stress((2008, 10)) < 1
    assert stress((2009, 4)) == pytest.approx(1.0)
    assert stress((2010, 7)) < stress((2009, 7))
    assert stress((2012, 7)) == 0.0


def test_sensitive_clients_and_stressed_sectors_ask_more(data: GameData, balance: Balance) -> None:
    ym = (2009, 4)
    banking = sector_shortfall("banking", ym, data)
    assert banking > 0
    assert sector_shortfall("banking", (2006, 7), data) < 0.02  # enforcement dipped in 2006
    assert crisis_factor(15, "banking", ym, data, balance) > crisis_factor(
        8, "banking", ym, data, balance
    )
    # restructuring is counter-cyclical: no shortfall for its deals
    assert driver_shortfall(data.practice("restructuring"), ym, data) == 0.0
    assert driver_shortfall(data.practice("corporate_ma"), ym, data) > 0.2


def test_the_crisis_lowers_a_deals_chance_to_close(balance: Balance) -> None:
    out = balance.outcomes
    assert mfx.p_close(10.0, False, out, 0.5) < mfx.p_close(10.0, False, out)


def _crisis_month(data: GameData, balance: Balance, seed: int, crisis: bool) -> tuple[int, int]:
    """(fees billed, crisis write-downs) of one billing month of a grown firm, its turn moved
    to April 2009 (stress 1) or kept in 2005."""
    state = game(data, balance, seed)
    state, _ = play(state, data, balance, 4, seed)
    if crisis:
        state = replace(state, turn=_turn((2009, 4)))
    month = billing_month(state, RngFactory(seed), data, balance)
    totals = next(m for m in month.state.billing.months if m.turn == state.turn)
    return totals.billed_cents, totals.crisis_writedown_cents


def test_crisis_write_downs_are_seeded_and_only_in_the_crisis(
    data: GameData, balance: Balance
) -> None:
    hits = []
    for seed in (1, 2, 3):
        assert _crisis_month(data, balance, seed, crisis=False)[1] == 0
        hit = _crisis_month(data, balance, seed, crisis=True)
        assert hit == _crisis_month(data, balance, seed, crisis=True)  # same seed, same draws
        assert 0 <= hit[1] <= hit[0] + hit[1]
        hits.append(hit[1])
    assert any(h > 0 for h in hits)


def test_new_streams_are_registered() -> None:
    assert STREAM_IDS["crisis"] == 42
    assert STREAM_IDS["deal_collapse"] == 43


def test_deals_collapse_in_progress_in_the_crisis(data: GameData, balance: Balance) -> None:
    """A two-year run through the crash: open deals collapse in progress (no relationship
    loss), and the same seed collapses the same deals."""
    from ptk.sim.matters.progress import matter_month

    state = game(data, balance, 5)  # seed 5 has five open deals by November 2005
    state, _ = play(state, data, balance, 10, 5)
    deals = [
        m
        for m in state.market.open_matters(state.player.id)
        if data.market.kinds[m.kind].outcome == "deal" and m.team
    ]
    assert deals
    crashed = replace(state, turn=_turn((2009, 4)))
    ym = (2009, 4)
    collapsed = 0
    for m in deals:
        before = crashed.market.relationship(m.client_id, m.firm_id)
        market, _ = matter_month(crashed, m, [], {}, RngFactory(5), data, balance)
        again, _ = matter_month(crashed, m, [], {}, RngFactory(5), data, balance)
        assert market.matter(m.id) == again.matter(m.id)
        hazard = (
            balance.macro.crisis.collapse_month_bp
            / 10000
            * driver_shortfall(data.practice(m.practice), ym, data)
        )
        draw = float(RngFactory(5).stream(crashed.turn, "deal_collapse", m.id).random())
        after_m = market.matter(m.id)
        assert after_m is not None
        if draw < hazard:
            collapsed += 1
            assert after_m.outcome == "collapsed"
            after = market.relationship(m.client_id, m.firm_id)
            assert before is not None and after is not None
            assert after.score == pytest.approx(before.score)  # a pulled deal: no blame
        else:
            assert after_m.outcome != "collapsed" or after_m.closed_turn == crashed.turn
    # outside the crisis the hazard is nil
    calm = replace(state, turn=_turn((2006, 7)))
    for m in deals:
        market, _ = matter_month(calm, m, [], {}, RngFactory(5), data, balance)
        assert driver_shortfall(data.practice(m.practice), (2006, 7), data) == 0.0


# --- 4. the CFO's forecast -----------------------------------------------------------------


def _pnl(drawn: list[int], cash: list[int], fees: int = 100_000_00) -> tuple[PnlPoint, ...]:
    return tuple(
        PnlPoint(
            turn=i,
            revenue_cents=fees * i,
            costs_cents=0,
            equity_partners=2,
            lawyers=4,
            drawn_cents=d,
            capital_cents=600_000_00,
            cash_cents=c,
        )
        for i, (d, c) in enumerate(zip(drawn, cash, strict=True))
    )


def test_the_forecast_sees_a_rising_balance_before_it_breaks(balance: Balance) -> None:
    cfg = balance.partnership.revolver
    # fees $100k a month: leverage limit is 30% of $1.2M = $360k drawn
    rising = _pnl([0, 0, 0, 0, 0, 0, 50_000_00, 100_000_00, 150_000_00, 200_000_00, 250_000_00,
                   300_000_00, 320_000_00], [0] * 13)  # fmt: skip
    found = pfx.forecast_breach(rising, 0, cfg)
    assert found is not None and found.covenant == "leverage"
    assert 1 <= found.months <= cfg.forecast_months
    flat = _pnl([100_000_00] * 13, [0] * 13)
    assert pfx.forecast_breach(flat, 0, cfg) is None
    # breached now: the headroom warning's, not the forecast's
    over = _pnl([500_000_00] * 13, [0] * 13)
    assert pfx.forecast_breach(over, 0, cfg) is None
    # nothing drawn but cash running out: the firm will draw, and the forecast sees it
    burning = _pnl([0] * 13, [600_000_00 - 100_000_00 * i for i in range(13)])
    burn = pfx.forecast_breach(burning, 0, cfg)
    assert burn is not None and burn.covenant in ("leverage", "partner capital")


def test_the_forecast_arrives_in_the_inbox_once_a_cooldown(
    data: GameData, balance: Balance
) -> None:
    from ptk.sim.partnership.phase import cfo_forecast

    state = game(data, balance)
    fp = state.partnership.firms[0]
    rising = _pnl([0, 0, 0, 0, 0, 0, 50_000_00, 100_000_00, 150_000_00, 200_000_00, 250_000_00,
                   300_000_00, 320_000_00], [0] * 13)  # fmt: skip
    fp = replace(fp, pnl=rising)
    fp2, items = cfo_forecast(fp, 12, balance)
    assert [i.kind for i in items] == ["cfo_forecast"]
    assert fp2.last_forecast_turn == 12
    _fp3, again = cfo_forecast(fp2, 13, balance)
    assert again == ()


# --- 5. the hours policy -------------------------------------------------------------------


def test_the_policy_fill(data: GameData, balance: Balance) -> None:
    state = game(data, balance)
    e: FeeEarner = next(
        x for x in fee_earners(state, 1, data, balance) if x.person.level.startswith("associate")
    )
    base = balance.staffing.plan_fill
    assert policy_fill(e, base, None, balance) == base
    assert policy_fill(e, base, 1800, balance) == base  # below the default: no change
    high = policy_fill(e, base, 2400, balance)
    assert base < high <= balance.staffing.policy_fill_max
    assert policy_fill(e, base, 2600, balance) <= balance.staffing.policy_fill_max


def test_the_hours_policy_action_and_its_strain(data: GameData, balance: Balance) -> None:
    g = start(data, balance)
    with pytest.raises(MatterActionError):
        g.act(SetHoursPolicy(g.founder_id, balance.staffing.policy_max_hours + 1))
    g.act(SetHoursPolicy(g.founder_id, 2500))
    assert g.state.player.billable_target_hours == 2500
    g.act(SetHoursPolicy(g.founder_id, None))
    assert g.state.player.billable_target_hours is None


def test_a_high_policy_plans_and_works_more_hours(data: GameData, balance: Balance) -> None:
    base = game(data, balance, 4)
    pushed = with_firm(base, replace(base.player, billable_target_hours=2500))
    a, _ = play(base, data, balance, 6, 4)
    b, _ = play(pushed, data, balance, 6, 4)

    def hours(s: GameState) -> int:
        return sum(r.tenths for r in s.market.hours)

    assert hours(b) >= hours(a)
