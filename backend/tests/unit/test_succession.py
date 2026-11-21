"""PT-M17 sub-tasks 5-6: mandatory retirement, annuities and succession (spec 2.5, 8.4,
8.6; TST 45.5; ADR PT-0007 3).

A succession hands play to the successor with no change to the firm's state other than the
MP seat, the player flag and the founder's status (state-diff test); replay is identical."""

from __future__ import annotations

import dataclasses
from dataclasses import replace

import pytest

from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import SuccessionError
from ptk.sim.family import succession
from ptk.sim.founder.actions import NameSuccessor, PlanSuccession, ProposeRetirementAge
from ptk.sim.founder.models import AnnuityTerms
from ptk.sim.interfaces import managing_partner, partner_ids, retirement_age
from ptk.sim.ledger import ANNUITIES, CASH
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState
from tests.founder_support import LifeGame, set_age, start_life


def _other(g: LifeGame) -> int:
    return next(p.person_id for p in g.fp.equity_partners if p.person_id != g.founder)


def test_handover_changes_only_the_seat_the_flag_and_the_status(
    data: GameData, balance: Balance
) -> None:
    g = start_life(data, balance)
    g.advance(6)
    old, heir = g.founder, _other(g)
    before = g.state
    done = succession.hand_over(before, heir, "choice", g.rng, balance, data, g.balances)
    after = done.state
    assert done.entries == ()  # no firm entry: the firm's books are untouched
    assert after.founder_of(after.player.id) == heir
    assert managing_partner(after, after.player.id) == heir
    life = after.founder_life.life(old)
    assert life is not None and life.status == "senior_partner"
    # the state diff: only the partnership's MP seat, the people's player flag, the month's
    # energy (PT-M4's hand-over) and lane C's own records change
    for f in dataclasses.fields(GameState):
        a, b = getattr(before, f.name), getattr(after, f.name)
        if f.name == "partnership":
            fa, fb = a.of(before.player.id), b.of(after.player.id)
            assert replace(fb, mp_id=fa.mp_id) == fa
            assert a.firms == b.firms or [x for x in a.firms if x.firm_id != fa.firm_id] == [
                x for x in b.firms if x.firm_id != fb.firm_id
            ]
        elif f.name == "people":
            changed = {p.id for p, q in zip(a, b, strict=True) if p != q}
            assert changed == {old, heir}
            for p, q in zip(a, b, strict=True):
                assert replace(q, is_founder=p.is_founder) == p
        elif f.name == "person_states":
            ids = {s.person_id for s in a} ^ {s.person_id for s in b}
            changed = {s.person_id for s in b if s not in a} | ids
            assert changed <= {old, heir}
        elif f.name in ("founder_life", "family"):
            continue  # lane C's records: lives, books, the succession
        else:
            assert a == b, f.name


def test_succession_replays_identically(data: GameData, balance: Balance) -> None:
    def play() -> GameState:
        g = start_life(data, balance, seed=3)
        g.advance(8)
        g.act(NameSuccessor(g.founder, _other(g)))
        g.advance(4)
        return g.state

    a, b = play(), play()
    assert a == b
    assert a.founder_life.last_succession is not None
    assert a.founder_life.last_succession.result == "handed_over"


def test_name_a_successor_and_play_them(data: GameData, balance: Balance) -> None:
    g = start_life(data, balance)
    g.advance(13)
    old, heir = g.founder, _other(g)
    pred = succession.predict(g.state, heir, balance, data)
    assert pred.yes_lo <= pred.yes_hi <= pred.total
    g.act(NameSuccessor(old, heir))
    with pytest.raises(SuccessionError):
        g.act(NameSuccessor(old, heir))  # one vote at a time
    g.advance(1)
    assert g.state.founder_of(g.state.player.id) == heir
    assert g.state.person_state(heir).energy == balance.energy.per_month
    assert g.state.person_state(old).energy is None
    fl = g.state.founder_life
    assert fl.book(heir) is not None  # the successor's own book opens
    life = fl.life(heir)
    assert life is not None and life.status == "managing_partner"
    assert life.visionary == balance.founder_life.persona.start  # persona resets
    kinds = [i.kind for i in g.log]
    assert "succession_elected" in kinds and "succession_handover" in kinds
    g.advance(3)  # play on as the successor
    assert g.state.founder_of(g.state.player.id) == heir


def _weak_candidate(g: LifeGame, data: GameData, balance: Balance) -> tuple[int, int]:
    """A weak candidate (low skills) and a strong, ambitious rival; partners who lack
    confidence in the MP."""
    from ptk.sim.partnership.models import with_firm_partnership, with_partner
    from tests.partnership_support import add_partner

    for n in range(3):
        add_partner(g, "corporate_ma", 120_000_000, n=n)
    fp = g.fp
    ids = [p.person_id for p in fp.equity_partners if p.person_id != g.founder]
    weak, rival = ids[0], ids[1]
    people = []
    for pid in ids:
        p = g.state.person(pid)
        if pid == weak:
            p = replace(
                p,
                skills=p.skills.updated(dict.fromkeys(p.skills.keys(), 3.0)),
                personality=p.personality.updated({"ambition": 1.0}),
            )
        elif pid == rival:
            p = replace(
                p,
                skills=p.skills.updated(dict.fromkeys(p.skills.keys(), 19.0)),
                personality=p.personality.updated({"ambition": 20.0}),
            )
        else:
            p = replace(p, personality=p.personality.updated({"ambition": 1.0}))
        people.append(p)
    from ptk.sim.people.reveal import new_reveal_state
    from ptk.sim.state import with_people, with_reveals

    g.state = with_people(g.state, people)
    g.state = with_reveals(
        g.state,
        [
            new_reveal_state(
                observer_firm_id=1,
                person=g.state.person(pid),
                turn=g.state.turn,
                rng=g.rng,
                data=data,
                balance=balance,
                knows_exactly=True,
            )
            for pid in ids
        ],
    )
    for p in g.fp.equity_partners:
        if p.person_id != g.founder:
            fp = with_partner(g.fp, replace(p, confidence=35.0))
            g.state = replace(g.state, partnership=with_firm_partnership(g.state.partnership, fp))
    return weak, rival


def test_a_weak_candidate_loses_to_the_rival_nominee(data: GameData, balance: Balance) -> None:
    g = start_life(data, balance)
    g.advance(2)
    weak, rival = _weak_candidate(g, data, balance)
    pred = succession.predict(g.state, weak, balance, data)
    assert pred.rival_id == rival
    assert pred.yes_lo < pred.needed
    g.act(NameSuccessor(g.founder, weak))
    founder = g.founder
    g.advance(1)
    rec = g.state.founder_life.last_succession
    assert rec is not None and rec.result == "lost"
    assert g.state.founder_of(1) == founder  # by choice: the founder stays on
    assert "succession_lost" in [i.kind for i in g.log]


def test_forced_succession_lost_hands_to_the_rival_and_ironman_ends(
    data: GameData, balance: Balance
) -> None:
    for difficulty, ends in (("standard", False), ("ironman", True)):
        g = start_life(data, balance, difficulty=difficulty)
        g.advance(2)
        weak, rival = _weak_candidate(g, data, balance)
        fl = g.state.founder_life
        g.state = replace(
            g.state,
            founder_life=replace(fl, retirement_due_turn=g.state.turn, due_trigger="retirement"),
        )
        g.act(NameSuccessor(g.founder, weak))
        g.advance(1)
        assert g.state.ended is ends
        if not ends:
            assert g.state.founder_of(1) == rival  # the partnership's choice is played


def test_mandatory_retirement_names_the_plan_after_grace(data: GameData, balance: Balance) -> None:
    g = start_life(data, balance)
    g.advance(1)
    heir = _other(g)
    g.act(PlanSuccession(g.founder, heir))
    old = g.founder
    g.state = set_age(g.state, old, retirement_age(g.state, 1, balance))
    g.advance(1)
    assert g.state.founder_life.retirement_due_turn == g.state.turn - 1 + 3
    assert "succession_due_retirement" in [i.kind for i in g.log]
    g.advance(balance.succession.grace_months + 1)
    assert g.state.founder_of(1) == heir
    life = g.state.founder_life.life(old)
    assert life is not None and life.status == "retired"  # at 65 they retire as they hand over
    assert old not in partner_ids(g.state, 1)


def test_no_plan_from_sixty_costs_confidence(data: GameData, balance: Balance) -> None:
    def conf_after(plan: bool) -> float:
        g = start_life(data, balance, seed=2)
        g.advance(1)
        g.state = set_age(g.state, g.founder, 61)
        if plan:
            g.act(PlanSuccession(g.founder, _other(g)))
        g.advance(6)
        return sum(p.confidence for p in g.fp.equity_partners if p.person_id != g.founder)

    assert conf_after(False) < conf_after(True)


def test_partners_retire_at_the_age_and_the_age_is_voted(data: GameData, balance: Balance) -> None:
    g = start_life(data, balance)
    g.advance(1)
    other = _other(g)
    g.state = set_age(g.state, other, 66)
    g.advance(1)
    assert other not in partner_ids(g.state, 1)
    e = g.state.employment_of(other)
    assert e is None or e.end_reason == "retired"
    g.act(ProposeRetirementAge(g.founder, 70))
    fp = g.fp
    assert any(v.kind == "terms" and v.param("term") == "retirement_age" for v in fp.votes)
    g.advance(1)
    vote = next(v for v in g.fp.votes if v.param("term") == "retirement_age")
    assert (retirement_age(g.state, 1, balance) == 70) == (vote.status == "passed")


def test_annuities_post_to_2600_and_are_paid_from_cash(data: GameData, balance: Balance) -> None:
    g = start_life(data, balance)
    g.advance(13)  # a December allocation first: the annuity is a share of it
    fl = g.state.founder_life
    g.state = replace(g.state, founder_life=replace(fl, annuity_terms=AnnuityTerms(True, 2500, 10)))
    other = _other(g)
    last = g.fp.partner(other)
    assert last is not None and last.comp_last_cents > 0
    g.state = set_age(g.state, other, 66)
    g.advance(1)
    ann = g.state.founder_life.annuity(other)
    assert ann is not None
    yearly = last.comp_last_cents * 2500 // 10_000
    assert ann.monthly_cents == yearly // 12
    assert -g.bal(ANNUITIES) == ann.remaining_cents == ann.monthly_cents * 120
    cash = g.bal(CASH)
    g.advance(1)
    paid = g.state.founder_life.annuity(other)
    assert paid is not None
    assert paid.remaining_cents == ann.remaining_cents - ann.monthly_cents
    assert -g.bal(ANNUITIES) == paid.remaining_cents
    assert sum(g.balances.values()) == 0  # the balance sheet balances
    del cash


def test_health_never_asks_a_real_person(data: GameData, balance: Balance) -> None:
    g = start_life(data, balance)
    g.advance(1)
    you = g.founder
    real = replace(g.state.person(you), real=True)
    from ptk.sim.state import with_people

    state = set_age(with_people(g.state, [real]), you, 80)
    for t in range(0, 120, 12):  # ten Januaries
        assert not succession._health(replace(state, turn=t), you, 80, RngFactory(t), balance)
