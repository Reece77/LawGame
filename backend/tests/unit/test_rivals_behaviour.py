"""Rival decisions, panels and RFPs, poaching both ways, boutiques and history (PT-M5).
Seeded: every draw comes from the rivals' own streams."""

from __future__ import annotations

from dataclasses import replace

import pytest

from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import InvalidActionError
from ptk.sim.rivals import poaching, rfp
from ptk.sim.rivals.actions import ApproachRival, CounterApproach, PitchRfp, apply_rival_action
from ptk.sim.rivals.decisions import choose
from ptk.sim.rivals.economy import Month
from ptk.sim.rivals.models import PLAYER_PANEL_KEY, Approach, Rfp
from ptk.sim.rng import RngFactory
from tests.rivals_support import hire_away, play_until, start, turn_of


def test_a_month_of_decisions_is_seeded_and_respects_cooldowns(
    data: GameData, balance: Balance
) -> None:
    state = start(data, balance, 1)
    firm = state.rivals.by_key("latham")
    assert firm is not None
    month = Month(turn=0, start=state.save_meta.start_ym, data=data, balance=balance)
    a = choose(firm, month, RngFactory(1).stream(0, "misc", 1), False)
    b = choose(firm, month, RngFactory(1).stream(0, "misc", 1), False)
    assert a == b
    cooled = replace(firm, cooldowns=tuple((c.action, 99) for c in a))
    again = choose(cooled, month, RngFactory(1).stream(0, "misc", 1), False)
    assert not {c.action for c in again} & {c.action for c in a}
    assert len(a) <= balance.rivals.actions_per_month


def test_history_happens_on_its_dates_without_the_player(data: GameData, balance: Balance) -> None:
    state = start(data, balance, 7)
    # PT-M10: history's dated events run to 2025 (the pin's end), so play past the last one
    last = max(e.ym for e in data.rivals.firms.events)
    state, results = play_until(state, data, balance, turn_of(state, last[0] + 1, 1), 7)
    status = {f.key: (f.status, f.ended_turn) for f in state.rivals.firms}
    for e in data.rivals.firms.events:
        when = turn_of(state, *e.ym)
        done = state.rivals.done(e.key)
        assert done is not None and done.outcome == "happened", e.key
        assert done.turn == when, e.key
        if e.kind == "collapse":
            assert status[e.firm] == ("collapsed", when)
        if e.kind == "merger":
            successor = state.rivals.by_key(e.into or "")
            assert status[e.firm][0] == "merged" and successor is not None
            assert successor.founded_turn == when
    names = {f.key: f.name for f in state.rivals.firms}
    assert names["kl_gates"] == "K&L Gates" and names["hogan_hartson"] == "Hogan Lovells"
    assert names["baker_mckenzie"] == "Baker McKenzie" and names["shearman"] == "A&O Shearman"
    # every month's rival ledger entries balance (ADR-0003) and post to rival firms only
    rival_ids = {f.id for f in state.rivals.firms}
    for r in results:
        for e in r.ledger_entries:
            assert sum(ln.amount for ln in e.lines) == 0
            assert e.firm_id == state.player.id or e.firm_id in rival_ids


def test_hiring_a_third_of_a_collapsing_firms_partners_brings_its_collapse_forward(
    data: GameData, balance: Balance
) -> None:
    """The brief's conditional-history criterion on one seed (balance/test_t11 has 10)."""
    seed = 3
    state = start(data, balance, seed)
    state, _ = play_until(state, data, balance, turn_of(state, 2010, 3), seed)
    state = hire_away(state, "howrey", 1 / 3, data, balance)
    state, _ = play_until(state, data, balance, turn_of(state, 2011, 3), seed)
    howrey = state.rivals.by_key("howrey")
    assert howrey is not None and howrey.status == "collapsed"
    assert howrey.ended_turn is not None and howrey.ended_turn < turn_of(state, 2011, 3)
    done = state.rivals.done("howrey_dissolution")
    assert done is not None and done.outcome == "forward"


def test_the_player_approaches_a_rivals_people_and_hires_one(
    data: GameData, balance: Balance
) -> None:
    state = start(data, balance, 4)
    founder = state.founder_of(1)
    assert founder is not None
    firm = state.rivals.by_key("skadden")
    assert firm is not None
    draws = lambda: RngFactory(4).stream(0, "actions", 1)  # noqa: E731
    out = apply_rival_action(state, ApproachRival(founder, firm.id), draws, balance, data)
    # partners become PT-M4's lateral candidates (a book range, clients, a guarantee ask);
    # associates would be hiring candidates
    fp = out.state.partnership.of(1)
    assert fp is not None
    laterals = [c for c in fp.laterals if c.status == "open"]
    cands = [c.person_id for c in out.state.candidates if c.status == "open"]
    found = [c.person_id for c in laterals] + cands
    lo, hi = balance.rivals.poach.candidates.lo, balance.rivals.poach.candidates.hi
    assert lo <= len(found) <= hi
    for c in laterals:
        assert c.book_lo_cents <= out.state.person(c.person_id).book_cents <= c.book_hi_cents
        assert c.client_ids and c.ask_cents > 0
    for pid in found:
        member = out.state.rivals.member(pid)
        assert member is not None and member.outside and member.firm_id == firm.id
        assert out.state.reveal(1, pid) is not None  # the firm can scout them
    # a hire takes them off the rival, with its book, at the next phase 8
    state = hire_away(out.state, "skadden", 0.0, data, balance)
    person = found[0]
    from ptk.sim.people.models import Employment

    state = replace(
        state,
        employments=(
            *state.employments,
            Employment(id=state.next_id("employment"), person_id=person, firm_id=1, start_turn=0),
        ),
    )
    lost_before = firm.lost_to_player
    state, lost = poaching.hired_by_player(state, 0)
    assert [m.person_id for _, m in lost] == [person]
    after = state.rivals.firm(firm.id)
    assert after is not None and after.lost_to_player == lost_before + 1
    assert after.offset_cents < firm.offset_cents
    assert state.rivals.member(person) is None


def test_a_rival_approach_can_be_countered(data: GameData, balance: Balance) -> None:
    state = start(data, balance, 5, real_people=True)
    founder = state.founder_of(1)
    assert founder is not None
    target = next(e.person_id for e in state.staff(1) if e.person_id != founder)
    approach = Approach(id=1, firm_id=state.rivals.firms[0].id, person_id=target,
                        offer_cents=40_000_000, made_turn=0)  # fmt: skip
    state = replace(state, rivals=replace(state.rivals, approaches=(approach,), next_approach_id=2))
    draws = lambda: RngFactory(5).stream(0, "actions", 1)  # noqa: E731
    out = apply_rival_action(state, CounterApproach(founder, 1), draws, balance, data)
    assert out.state.rivals.approaches[0].status == "countered"
    with pytest.raises(InvalidActionError):
        apply_rival_action(out.state, CounterApproach(founder, 1), draws, balance, data)


def test_pitches_and_awards(data: GameData, balance: Balance) -> None:
    state = start(data, balance, 6)
    founder = state.founder_of(1)
    assert founder is not None
    client = next(c for c in state.market.clients if c.size_class == "large" and c.panel)
    r = Rfp(id=1, client_id=client.id, kind="panel", practices=("corporate_ma",), opened_turn=0,
            award_turn=0, seats=len(client.panel), incumbents=client.panel, bidders=(),
            player_invited=True)  # fmt: skip
    state = replace(state, rivals=replace(state.rivals, rfps=(r,), next_rfp_id=2))
    draws = lambda: RngFactory(6).stream(0, "actions", 1)  # noqa: E731
    with pytest.raises(InvalidActionError):
        apply_rival_action(state, PitchRfp(founder, 1, (), ()), draws, balance, data)
    with pytest.raises(InvalidActionError):
        apply_rival_action(
            state, PitchRfp(founder, 1, (founder,), ("bribes",)), draws, balance, data
        )
    out = apply_rival_action(
        state, PitchRfp(founder, 1, (founder,), ("references",)), draws, balance, data
    )
    pitched = out.state.rivals.rfp(1)
    assert pitched is not None and pitched.pitch is not None
    assert not rfp.substantiated(out.state, pitched, "references", (founder,))  # no history yet
    awarded, _ = rfp.award_due(out.state, RngFactory(6), data, balance)
    done = awarded.rivals.rfp(1)
    assert done is not None and done.status == "awarded" and len(done.winners) == r.seats
    winners = set(done.winners) - {PLAYER_PANEL_KEY}
    assert set(awarded.market.client(client.id).panel) == winners
    if PLAYER_PANEL_KEY in done.winners:
        rel = awarded.market.relationship(client.id, 1)
        assert rel is not None and "corporate_ma" in rel.practices


def test_boutiques_and_free_agents_appear_over_a_decade(data: GameData, balance: Balance) -> None:
    founded = agents = 0
    for seed in (1, 2):
        state = start(data, balance, seed)
        state, _ = play_until(state, data, balance, 120, seed)
        founded += state.rivals.boutiques_founded
        agents += sum(1 for m in state.rivals.moves if m.action == "founded")
        boutiques = [f for f in state.rivals.firms if f.kind == "boutique"]
        for b in boutiques:
            assert b.personality in ("litigation_boutique", "elite_lockstep")
    assert founded >= 1
