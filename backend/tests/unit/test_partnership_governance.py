"""PT-M4 sub-tasks 5, 6 and 9: confidence (TST 14.6's rule, ported), votes, the agreement,
the December vote and up or out, and the MP election (ADR PT-0007)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from ptk.sim.calendar import turn_to_ym
from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import NotManagingPartnerError, PartnershipError
from ptk.sim.partnership import formulas as fx
from ptk.sim.partnership.actions import (
    CapitalCall,
    ElectionChoice,
    Lobby,
    ProposePartner,
    ProposeTerms,
    SetDraws,
)
from ptk.sim.partnership.governance import predicted
from ptk.sim.partnership.models import FirmPartnership, with_partner
from ptk.sim.state import with_firm, with_people
from tests.matters_support import solvent
from tests.partnership_support import Game, add_partner, start


def _put(g: Game, fp: FirmPartnership) -> None:
    g.state = replace(g.state, partnership=replace(g.state.partnership, firms=(fp,)))


def _confidence(g: Game, value: float) -> None:
    fp = g.fp
    for p in fp.partners:
        fp = with_partner(fp, replace(p, confidence=value))
    _put(g, fp)


def _to_month(g: Game, month: int) -> None:
    while turn_to_ym(g.state.turn, g.state.save_meta.start_ym)[1] != month:
        g.advance()


# --- Confidence -------------------------------------------------------------------------------


def test_confidence_rule_is_tsts(balance: Balance) -> None:
    cfg = balance.partnership.confidence
    assert fx.next_confidence(50, 80, cfg) == pytest.approx(56)  # B + 0.2 (T - B)
    assert fx.next_confidence(95, 200, cfg) == 100
    assert fx.next_confidence(5, -50, cfg) == 0
    base = fx.confidence_target(0, 0, 10, False, False, 0, cfg)
    assert base == cfg.target_base
    assert fx.confidence_target(0, 0, 10, True, True, 2, cfg) == pytest.approx(
        base + cfg.draws_suspended + cfg.bank_trouble + 2 * cfg.departure_hit
    )


def test_whip_count_is_ranges(balance: Balance) -> None:
    cfg = balance.partnership.confidence
    counts = fx.whip_range([90, 62, 50, 20], cfg)
    assert counts["supportive"] == (1, 2)  # 62 might be neutral
    assert counts["restless"] == (1, 1)
    assert sum(lo for lo, _ in counts.values()) <= 4 <= sum(hi for _, hi in counts.values())


def test_suspending_draws_lowers_confidence(data: GameData, balance: Balance) -> None:
    a, b = start(data, balance, 2), start(data, balance, 2)
    b.act(SetDraws(b.founder, True))
    a.advance(3)
    b.advance(3)
    others = [p.person_id for p in a.fp.partners if p.person_id != a.founder]
    for pid in others:
        assert b.fp.partner(pid).confidence < a.fp.partner(pid).confidence  # type: ignore[union-attr]


# --- Votes ------------------------------------------------------------------------------------


def test_votes_are_seeded_and_counted_in_phase_1(data: GameData, balance: Balance) -> None:
    runs = []
    for _ in range(2):
        g = start(data, balance, 5)
        g.act(CapitalCall(g.founder, 30_000_000))
        vote = g.fp.votes[0]
        assert vote.status == "open"
        g.advance()
        runs.append(g.fp.vote(vote.id))
    assert runs[0] == runs[1]
    assert runs[0] is not None and runs[0].status in ("passed", "failed")
    assert len(runs[0].ballots) == len(start(data, balance, 5).fp.equity_partners)


def test_a_passed_capital_call_pays_capital_in(data: GameData, balance: Balance) -> None:
    g = start(data, balance, 6)
    _confidence(g, 100.0)  # a confident partnership backs its MP
    before = -g.bal("3000_partners_capital")
    g.act(CapitalCall(g.founder, 30_000_000))
    g.advance()
    vote = g.fp.votes[0]
    assert vote.status == "passed"
    assert -g.bal("3000_partners_capital") >= before + 30_000_000


def test_prediction_brackets_lobbying(data: GameData, balance: Balance) -> None:
    g = start(data, balance, 7)
    _confidence(g, 50.0)
    g.act(ProposeTerms(g.founder, "retain_bp", 500))
    vote = g.fp.votes[0]
    before = predicted(g.state, g.fp, vote, balance, data)
    for p in g.fp.partners:
        if p.person_id != g.founder:
            g.act(Lobby(g.founder, p.person_id))
    after = predicted(g.state, g.fp, vote, balance, data)
    assert before.yes_lo <= after.yes_lo and before.yes_hi <= after.yes_hi
    assert after.total == len(g.fp.equity_partners)


def test_agreement_terms_change_by_vote(data: GameData, balance: Balance) -> None:
    g = start(data, balance, 8)
    _confidence(g, 100.0)
    g.act(ProposeTerms(g.founder, "two_tier", True))
    with pytest.raises(PartnershipError):
        g.act(ProposeTerms(g.founder, "two_tier", True))  # the same vote is open
    with pytest.raises(PartnershipError):
        g.act(ProposeTerms(g.founder, "comp_system", "auction"))
    g.advance()
    assert g.fp.agreement.two_tier
    assert "vote_result" in g.templates()


# --- The December vote and up or out -----------------------------------------------------------


def _eligible_associate(g: Game, level: str = "associate_8") -> int:
    staff = [e.person_id for e in g.state.staff(1)]
    pid = next(pid for pid in staff if g.state.person(pid).level.startswith("associate"))
    g.state = with_people(g.state, [replace(g.state.person(pid), level=level)])
    return pid


def test_admission_in_december(data: GameData, balance: Balance) -> None:
    g = start(data, balance, 9)
    pid = _eligible_associate(g)
    with pytest.raises(PartnershipError):
        g.act(ProposePartner(g.founder, pid, "equity"))  # only in December
    _to_month(g, 12)
    _confidence(g, 100.0)
    for p in g.fp.partners:
        if p.person_id != g.founder:
            g.act(Lobby(g.founder, p.person_id))
    g.act(ProposePartner(g.founder, pid, "equity"))
    g.advance()
    vote = next(v for v in g.fp.votes if v.subject_id == pid)
    if vote.status == "passed":
        partner = g.fp.partner(pid)
        assert partner is not None and partner.equity
        assert g.state.person(pid).level == "equity_partner"
        assert g.state.employment_of(pid).salary_cents == 0  # type: ignore[union-attr]
        assert not any(m.person_id == pid for m in g.fp.moving_on)
    else:
        assert any(m.person_id == pid for m in g.fp.moving_on)


def test_up_or_out(data: GameData, balance: Balance) -> None:
    g = start(data, balance, 10)
    pid = _eligible_associate(g)
    _to_month(g, 12)
    g.advance()  # not proposed: told to move on
    move = next(m for m in g.fp.moving_on if m.person_id == pid)
    assert "told_to_move_on" in g.templates()
    while g.state.turn <= move.leave_turn + 1:
        g.advance()
    e = g.state.employment_of(pid)
    assert e is None or e.status != "active"
    dep = next(d for d in g.fp.departures if d.person_id == pid)
    assert dep.reason == "up_or_out"


def test_counsel_escapes_up_or_out(data: GameData, balance: Balance) -> None:
    g = start(data, balance, 11)
    pid = _eligible_associate(g)
    _to_month(g, 12)
    g.act(ProposePartner(g.founder, pid, "counsel"))
    g.advance()
    assert g.state.person(pid).level == "counsel"
    assert not any(m.person_id == pid for m in g.fp.moving_on)


def test_sponsors_are_given_in_september(data: GameData, balance: Balance) -> None:
    g = start(data, balance, 12)
    pid = _eligible_associate(g, "associate_6")
    _to_month(g, 9)
    g.advance()
    assert g.fp.sponsor_of(pid) is not None


# --- The MP election ---------------------------------------------------------------------------


def _with_term(g: Game, *, ambition: float = 20.0, turns: int = 1) -> int:
    """Stage 2 and a term ending now; a co-founder ambitious enough to stand."""
    g.state = with_firm(g.state, replace(g.state.player, stage=2))
    rival = next(p.person_id for p in g.fp.partners if p.person_id != g.founder)
    person = g.state.person(rival)
    g.state = with_people(
        g.state, [replace(person, personality=person.personality.updated({"ambition": ambition}))]
    )
    _put(g, replace(g.fp, term_ends_turn=g.state.turn + turns - 1))
    return rival


def test_losing_an_election_never_ends_a_standard_game(data: GameData, balance: Balance) -> None:
    # PT-M7b: solvent, because it tests the election, not survival (an untouched group lift
    # at a new firm's card can dissolve within the year, Reece's decision 3 on PT-M7)
    g = start(data, solvent(balance), 13)
    for i in range(3):
        add_partner(g, "corporate_ma", 40_000_000, n=i)
    rival = _with_term(g)
    _confidence(g, 0.0)
    g.advance()
    assert g.fp.mp_id == rival
    assert not g.state.ended
    assert "election_lost" in g.templates()
    with pytest.raises(NotManagingPartnerError):
        g.act(CapitalCall(g.founder, 1_000_000))
    g.act(ElectionChoice(g.founder, "stay"))
    g.advance(12)
    assert not g.state.ended


def test_handing_over_plays_the_successor(data: GameData, balance: Balance) -> None:
    g = start(data, balance, 14)
    for i in range(3):
        add_partner(g, "corporate_ma", 40_000_000, n=i)
    rival = _with_term(g)
    _confidence(g, 0.0)
    g.advance()
    old = g.founder
    g.act(ElectionChoice(old, "hand_over", rival))
    assert g.founder == rival
    assert g.fp.mp_id == rival  # the player plays the new MP
    assert not g.state.person(old).is_founder
    g.act(CapitalCall(rival, 1_000_000))  # the MP's powers again


def test_ironman_makes_losing_final(data: GameData, balance: Balance) -> None:
    g = start(data, balance, 15)
    g.state = replace(g.state, save_meta=replace(g.state.save_meta, difficulty="ironman"))
    for i in range(3):
        add_partner(g, "corporate_ma", 40_000_000, n=i)
    _with_term(g)
    _confidence(g, 0.0)
    g.advance()
    assert g.state.save_meta.game_state == "election_lost"


def test_a_confident_partnership_re_elects(data: GameData, balance: Balance) -> None:
    g = start(data, balance, 16)
    _with_term(g)
    _confidence(g, 100.0)
    g.advance()
    assert g.fp.mp_id == g.founder
    assert g.fp.term_ends_turn is not None and g.fp.term_ends_turn > g.state.turn


def test_a_december_admission_keeps_its_budget(data: GameData, balance: Balance) -> None:
    """PT-M7c: a partner voted in December joins January's allocation; December's close of the
    year must not leave them a zero budget (flight read their comp as nothing and nearly every
    new partner left within the year)."""
    from ptk.sim.partnership.flight import firm_comp_cents

    g = start(data, balance, 10)
    pid = _eligible_associate(g)
    _to_month(g, 12)
    _confidence(g, 100.0)
    for p in g.fp.partners:
        if p.person_id != g.founder:
            g.act(Lobby(g.founder, p.person_id))
    g.act(ProposePartner(g.founder, pid, "equity"))
    g.advance()
    partner = g.fp.partner(pid)
    assert partner is not None and partner.equity, "the lobbied vote passes on seed 10"
    assert partner.comp_last_cents == 0  # no share of the year it was not a partner in
    assert partner.budget_cents > 0
    assert firm_comp_cents(partner) == partner.budget_cents
