"""PT-M16 sub-tasks 1-2: reputation by (firm, practice, region), prestige, and reputation that
gates the card and the appeal (spec 12.1, 7.1)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from ptk.sim import interfaces
from ptk.sim.data_models import Balance, GameData
from ptk.sim.matters.market import firm_reputation
from ptk.sim.matters.rates import card_target_bp, start_card_bp
from ptk.sim.money import BP_DENOMINATOR
from ptk.sim.rankings import lists
from ptk.sim.reputation import formulas as fx
from ptk.sim.reputation import phase
from ptk.sim.reputation.models import PublicOutcome
from ptk.sim.state import GameState
from tests.matters_support import game, play


@pytest.fixture(scope="module")
def start(data: GameData, balance: Balance) -> GameState:
    return game(data, balance)


def _rival(state: GameState, key: str) -> int:
    firm = state.rivals.by_key(key)
    assert firm is not None
    return firm.id


def test_a_new_firm_starts_low_and_rivals_at_their_standing(
    start: GameState, data: GameData, balance: Balance
) -> None:
    rb = balance.reputation
    pid = start.player.id
    founders = fx.founders_practices(start, pid)
    assert founders
    for p in data.practice_keys:
        want = rb.start_founders if p in founders else rb.start_other
        assert fx.reputation(start, pid, p, balance) == want
    # every active rival is seeded in every practice, at its long-run mean
    seeded = {e.firm_id for e in start.standing.reputation.entries}
    assert {f.id for f in start.rivals.active} <= seeded
    for e in start.standing.reputation.entries:
        if e.firm_id != pid:
            assert e.value == pytest.approx(e.mean)
    assert fx.reputation(start, _rival(start, "wachtell"), "corporate_ma", balance) > 75


def test_the_2005_bands_put_historys_leaders_in_band_1(
    start: GameState, data: GameData, balance: Balance
) -> None:
    """Acceptance: Wachtell in M&A, Cravath in corporate, Skadden in M&A and litigation, and at
    least 80% of the dossier's strengths (firms.yaml `strong`) in band 1."""
    rivals = lists.rivals_now(start, data)
    bands = lists.bands(start, 2005, rivals, data, balance)
    band = {(b.firm_id, b.practice): b.band for b in bands}
    for key, practice in (
        ("wachtell", "corporate_ma"),
        ("cravath", "corporate_ma"),
        ("skadden", "corporate_ma"),
        ("skadden", "commercial_litigation"),
    ):
        assert band.get((_rival(start, key), practice)) == 1, (key, practice)
    pairs = [
        (_rival(start, f.key), p)
        for f in data.rivals.firms.firms
        if start.rivals.by_key(f.key) is not None and start.rivals.by_key(f.key).active  # type: ignore[union-attr]
        for p in f.strong
    ]
    agreement = sum(1 for pair in pairs if band.get(pair) == 1) / len(pairs)
    assert agreement >= 0.8
    # and a new firm is far from band 1 anywhere
    pid = start.player.id
    assert all(b.band > 1 for b in bands if b.firm_id == pid)


def test_a_month_moves_reputation_toward_the_long_run_mean(
    start: GameState, data: GameData, balance: Balance
) -> None:
    pid = start.player.id
    before = {e.practice: e for e in start.standing.reputation.of(pid)}
    after = phase.month(start, data, balance)
    for e in after.standing.reputation.of(pid):
        old = before[e.practice]
        step = balance.reputation.speed * (e.mean - old.value)
        assert e.value == pytest.approx(fx.clamp_rep(old.value + step))
    assert after.standing.reputation.prestige_of(pid) is not None


def test_public_outcomes_pulse_and_build_the_record(
    start: GameState, data: GameData, balance: Balance
) -> None:
    rb = balance.reputation
    pid = start.player.id
    rep = start.standing.reputation
    outcomes = tuple(
        PublicOutcome(start.turn, "corporate_ma", 1000 + i, "closed", 1.0) for i in range(10)
    )
    richer = replace(
        start, standing=replace(start.standing, reputation=replace(rep, outcomes=outcomes))
    )
    plain = fx.means(start, data, balance)[(pid, "corporate_ma")]
    record = fx.means(richer, data, balance)[(pid, "corporate_ma")]
    assert record == pytest.approx(plain + rb.mean.record * 10 / rb.record_full)


def test_a_pulse_is_clamped_and_its_cause_kept(start: GameState, balance: Balance) -> None:
    pid = start.player.id
    up = fx.apply_pulse(start, pid, 500.0, "a test", balance, "corporate_ma")
    assert fx.reputation(up, pid, "corporate_ma", balance) == 100.0
    down = fx.apply_pulse(up, pid, -500.0, "a test", balance)
    assert all(e.value == 0.0 for e in down.standing.reputation.of(pid))
    assert down.standing.reputation.causes[-1].cause == "a test"
    # the events' hook moves every practice
    moved = interfaces.reputation_change(start, pid, 2.0, balance)
    for a, b in zip(
        start.standing.reputation.of(pid), moved.standing.reputation.of(pid), strict=True
    ):
        assert b.value == pytest.approx(a.value + 2.0)


def test_the_appeal_reads_reputation_above_a_floor(start: GameState, balance: Balance) -> None:
    pid = start.player.id
    floor = balance.reputation.appeal_floor
    low = fx.apply_pulse(start, pid, -100.0, "t", balance)
    high = fx.apply_pulse(start, pid, 100.0, "t", balance)
    assert firm_reputation(low, pid, "corporate_ma", balance) == pytest.approx(floor)
    assert firm_reputation(high, pid, "corporate_ma", balance) == pytest.approx(1.0)
    mid = firm_reputation(start, pid, "corporate_ma", balance)
    assert floor < mid < 1.0


def test_the_card_reaches_the_top_only_near_the_top_of_the_market(
    start: GameState, data: GameData, balance: Balance
) -> None:
    pid = start.player.id
    base = start_card_bp("standard", data, balance)
    progress = fx.card_progress(start, pid, "corporate_ma", balance)
    assert progress < 0.5
    assert card_target_bp(progress, base, balance) < BP_DENOMINATOR
    top = fx.market_quantile(start, "corporate_ma", balance.reputation.card.top_quantile)
    near = fx.apply_pulse(start, pid, top, "t", balance, "corporate_ma")
    assert fx.card_progress(near, pid, "corporate_ma", balance) == 1.0


def test_prestige_feeds_offer_scores(start: GameState, balance: Balance) -> None:
    from ptk.sim.hiring.rules import prestige

    pid = start.player.id
    value = start.standing.reputation.prestige_of(pid)
    assert value is not None and 0 <= value <= 100
    assert fx.prestige_term(start, pid, balance) == pytest.approx(
        balance.reputation.prestige.offer_weight * value / 100
    )
    assert prestige(start, pid, balance) >= fx.prestige_term(start, pid, balance)


def test_a_year_of_play_keeps_reputation_in_range_and_seeded(
    data: GameData, balance: Balance
) -> None:
    state, _ = play(game(data, balance), data, balance, 12)
    entries = state.standing.reputation.entries
    assert entries and all(0.0 <= e.value <= 100.0 for e in entries)
    active = {f.id for f in state.rivals.active} | {state.player.id}
    assert {e.firm_id for e in entries} == active
