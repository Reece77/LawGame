"""PT-M17 sub-task 4: the family (spec 2.4; TST 45.1-45.3, 45.6). Life events apply only
to the player's own generated family, never to a person flagged real (ADR PT-0013)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import FamilyError
from ptk.sim.family import estate
from ptk.sim.family.models import CHILD, PARTNER, FamilyState
from ptk.sim.family.phase import family_month, head_active
from ptk.sim.family.setup import FamilySpec, start_family
from ptk.sim.founder.actions import ChooseEducation, JoinFirm, SetFamilyTime
from ptk.sim.founder.models import INVESTMENTS, PERSONAL_CASH, PersonalBook, PersonalEntry
from ptk.sim.state import with_people
from ptk.sim.streams import RngFactory
from tests.founder_support import set_age, start_life

KIDS = FamilySpec("children", (11, 17, 24))


def test_family_none_changes_nothing(data: GameData, balance: Balance) -> None:
    a = start_life(data, balance, seed=4)
    b = start_life(data, balance, seed=4, family=FamilySpec())
    a.advance(6)
    b.advance(6)
    assert a.state == b.state


def test_a_family_of_generated_people(data: GameData, balance: Balance) -> None:
    g = start_life(data, balance, family=KIDS, age=50)
    fs = g.state.family
    assert fs.family is not None and fs.family.head_id == g.founder
    assert [m.relation for m in fs.members].count(PARTNER) == 1
    kids = [m for m in fs.members if m.relation == CHILD]
    assert sorted(g.state.person(m.person_id).age(0) for m in kids) == [11, 17, 24]
    for m in fs.members:
        p = g.state.person(m.person_id)
        assert not p.real
        assert g.state.employment_of(p.id) is None
        assert g.state.reveal(1, p.id) is not None  # the player sees ranges
    assert g.state.founder_of(1) == g.founder  # the family's people are not the player


def test_family_time_eases_strain_and_holds_the_relationship(
    data: GameData, balance: Balance
) -> None:
    def play(time: int) -> tuple[float, float]:
        g = start_life(data, balance, family=KIDS, age=50, seed=6)
        g.act(SetFamilyTime(g.founder, time))
        g.advance(12)
        fam = g.state.family.family
        assert fam is not None
        return fam.relationship, g.state.person(g.founder).strain

    rel_hi, strain_hi = play(20)
    rel_lo, strain_lo = play(0)
    assert rel_hi > rel_lo
    assert strain_hi <= strain_lo
    g = start_life(data, balance, family=KIDS, age=50)
    with pytest.raises(FamilyError):
        g.act(SetFamilyTime(g.founder, balance.family.max_time + 1))


def test_children_grow_and_their_potential_stays_hidden(data: GameData, balance: Balance) -> None:
    g = start_life(data, balance, family=FamilySpec("children", (8,)), age=45)
    child = next(m.person_id for m in g.state.family.members if m.relation == CHILD)
    before = sum(v for _, v in g.state.person(child).skills.items)
    g.advance(24)
    after = sum(v for _, v in g.state.person(child).skills.items)
    assert after > before
    rv = g.state.reveal(1, child)
    assert rv is not None
    assert rv.record("potential_ability").hw >= balance.family.pa_hw_floor - 1e-9


def test_education_and_joining_the_firm(data: GameData, balance: Balance) -> None:
    g = start_life(data, balance, family=FamilySpec("children", (12, 18)), age=52)
    young, older = sorted(
        (m.person_id for m in g.state.family.members if m.relation == CHILD),
        key=lambda pid: -g.state.person(pid).birth_turn,
    )
    you = g.founder
    g.act(ChooseEducation(you, young, "school", "standard"))
    with pytest.raises(FamilyError):
        g.act(ChooseEducation(you, young, "law_school", "top"))  # not yet 18
    g.act(ChooseEducation(you, older, "law_school", "standard"))
    book = g.state.founder_life.book(you)
    assert (
        book is not None
        and book.bal("9330_education") == balance.family.education.cents["law_standard"]
    )
    with pytest.raises(FamilyError):
        g.act(JoinFirm(you, older))  # not qualified yet
    g.state = set_age(g.state, older, balance.family.education.qualify_age)
    g.act(JoinFirm(you, older))
    e = g.state.employment_of(older)
    assert e is not None and e.firm_id == 1 and g.state.person(older).level == "associate_1"
    assert "family_joined_firm" in [i.kind for i in g.log]
    g.advance(2)  # an associate now: phase 8 grows them, the partnership watches promotions


def test_life_events_only_for_the_players_generated_family(
    data: GameData, balance: Balance
) -> None:
    """ADR PT-0013: no family or life event ever selects a person flagged real. Over years of
    play every member born, met or divorced is generated; a real head runs no family."""
    g = start_life(data, balance, family=FamilySpec("partner"), age=34, seed=9)
    young = balance.family.child_parent_age_max - 15
    for m in g.state.family.members:
        g.state = set_age(g.state, m.person_id, young)
    g.advance(60)
    members = g.state.family.members
    assert len(members) >= 2  # a partner and at least one child born in five years
    for m in members:
        assert not g.state.person(m.person_id).real
    # a real head: nothing runs, no member is chosen, nothing changes
    head = replace(g.state.person(g.founder), real=True)
    state = with_people(g.state, [head])
    assert not head_active(state)
    after, entries, logs = family_month(state, RngFactory(1), balance, data)
    assert after == state and entries == () and logs == ()
    with pytest.raises(FamilyError):
        start_family(state, FamilySpec("partner"), RngFactory(1), balance, data)


def test_divorce_takes_half_the_liquid_assets(data: GameData, balance: Balance) -> None:
    g = start_life(data, balance, family=FamilySpec("partner"), age=40)
    g.advance(1)
    you = g.founder
    g.act(SetFamilyTime(you, 0))
    fam = g.state.family.family
    assert fam is not None
    g.state = replace(
        g.state,
        family=replace(
            g.state.family,
            family=replace(fam, relationship=5.0, low_months=balance.family.divorce_months),
        ),
    )
    book = g.state.founder_life.book(you)
    assert book is not None
    cash = book.cash
    g.advance(1)
    rel = [m.relation for m in g.state.family.members]
    assert "ex_partner" in rel and "partner" not in rel
    book = g.state.founder_life.book(you)
    assert book is not None
    assert book.bal("9360_divorce_settlement") > 0
    assert book.cash < cash


def test_estate_tax_quote_follows_the_us_history(balance: Balance) -> None:
    assert estate.rule_for(2005, balance).rate == 0.47
    assert estate.rule_for(2008, balance).exemption_cents == 200_000_000
    assert estate.rule_for(2030, balance).exemption_cents == 1_500_000_000
    book = PersonalBook(1, 0).posted(
        (
            PersonalEntry.transfer(0, 1, "t", "t", PERSONAL_CASH, "9900_opening_net_worth", 10**9),
            PersonalEntry.transfer(0, 1, "t", "t", INVESTMENTS, "9900_opening_net_worth", 10**9),
        )
    )
    from ptk.sim.family.models import Family

    fs = FamilyState(Family(1, "partner", 1, 0))
    q = estate.quote(book, fs, 12 * 20, (2005, 1), balance)  # 2025: $13.99M at 40%
    assert q.estate_cents == 2 * 10**9
    assert q.tax_cents == round((2 * 10**9 - 1_399_000_000) * 0.40)
    paid, fs2, _entries = estate.pay_estate_tax(book, fs, 12 * 20, (2005, 1), balance)
    assert paid.bal("9340_estate_tax") == q.tax_cents
    assert sum(v for _, v in paid.balances) == 0
    assert fs2.family is not None and fs2.family.estate_tax_cents == q.tax_cents
    # gifts above the exemption pay gift tax; a trust moves assets outside the estate
    gave, _fs3, _ = estate.gift_to_heir(
        book, _with_child(fs), 2, 500_000_000, 0, (2005, 1), balance
    )
    assert gave.bal("9340_estate_tax") == round((500_000_000 - 150_000_000) * 0.47)
    trusted, _, _ = estate.set_up_trust(book, fs, 500_000_000, 0, balance)
    assert estate.estate_cents(trusted) < estate.estate_cents(book)


def _with_child(fs: FamilyState) -> FamilyState:
    from ptk.sim.family.models import FamilyMember, with_member

    return with_member(fs, FamilyMember(2, CHILD, 1, 1, 0, parent_ids=(1,)))
