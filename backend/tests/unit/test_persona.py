"""PT-M17 sub-tasks 2-3: persona (spec 2.3; TST 32.4), the foundation (TST 32.3), bar
politics (TST 32.5) and legacy (TST 32.6), in Partner Track's units."""

from __future__ import annotations

from dataclasses import replace

import pytest

from ptk.sim import dmath
from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import FounderLifeError
from ptk.sim.founder import foundation, influence, legacy, persona
from ptk.sim.founder.actions import (
    BarCommittee,
    CreateFoundation,
    GiveToFoundation,
    StandForOffice,
)
from ptk.sim.founder.config import SOURCES, TRAITS
from ptk.sim.founder.models import ENDOWMENT, with_life
from ptk.sim.interfaces import founder_recruiting_term, founder_resign_mult
from ptk.sim.rng import RngFactory
from tests.founder_support import start_life


def test_every_source_raises_its_trait_by_its_points(balance: Balance) -> None:
    pb = balance.founder_life.persona
    for source, trait in SOURCES.items():
        life = persona.new_life(1, 0, balance)
        life = persona.apply_source(life, source, 0, balance)
        assert life.trait(trait) == pytest.approx(pb.start + pb.sources[source])
        for other in TRAITS:
            if other != trait:
                assert life.trait(other) == pb.start
        assert life.causes[-1][1] == trait


def test_spec_2_3_sources_map_to_their_traits() -> None:
    """Ruthless by de-equitisations, hostile laterals, layoffs; Beloved by pro bono, raises,
    comp fairness; Visionary by new practices (and v2's regions, AI); Reckless by guarantees,
    revolver leverage, broken public claims."""
    assert {s for s, t in SOURCES.items() if t == "ruthless"} == {
        "deequitisation",
        "hostile_lateral",
        "layoffs",
    }
    assert {s for s, t in SOURCES.items() if t == "beloved"} == {
        "pro_bono",
        "raises",
        "comp_fairness",
    }
    assert {"new_practice", "first_region", "early_ai"} == {
        s for s, t in SOURCES.items() if t == "visionary"
    }
    assert {"guarantee", "revolver_leverage", "broken_claim"} <= {
        s for s, t in SOURCES.items() if t == "reckless"
    }


def test_drift_returns_to_start_two_a_month(balance: Balance) -> None:
    life = replace(persona.new_life(1, 0, balance), ruthless=27.0, beloved=19.0)
    life = persona.drift(life, balance)
    assert life.ruthless == 25.0 and life.beloved == 20.0


def test_effects_only_at_the_line_in_pt_units(balance: Balance) -> None:
    """TST 32.4's effects at 60: Visionary +0.03 hiring appeal (an offer-score term);
    Beloved resignations x0.9; Ruthless and Reckless cost partner confidence, Beloved adds."""
    pb = balance.founder_life.persona
    life = persona.new_life(1, 0, balance)
    assert persona.recruiting_points(life, balance) == 0
    assert persona.resign_mult(life, balance) == 1
    assert persona.confidence_points(life, balance) == 0
    strong = replace(life, visionary=60.0, beloved=60.0, ruthless=60.0, reckless=59.9)
    assert persona.recruiting_points(strong, balance) == pytest.approx(0.03)
    assert persona.resign_mult(strong, balance) == pytest.approx(0.9)
    assert persona.confidence_points(strong, balance) == pytest.approx(
        pb.ruthless_confidence + pb.beloved_confidence
    )


def test_persona_reaches_hiring_through_the_interface(data: GameData, balance: Balance) -> None:
    g = start_life(data, balance)
    g.advance(1)
    you = g.founder
    firm = g.state.player.id
    assert founder_recruiting_term(g.state, firm, balance) == 0
    assert founder_resign_mult(g.state, firm, balance) == 1
    fl = g.state.founder_life
    life = fl.life(you)
    assert life is not None
    g.state = replace(
        g.state, founder_life=with_life(fl, replace(life, visionary=80.0, beloved=80.0))
    )
    assert founder_recruiting_term(g.state, firm, balance) == pytest.approx(0.03)
    assert founder_resign_mult(g.state, firm, balance) == pytest.approx(0.9)
    assert founder_recruiting_term(g.state, firm + 1, balance) == 0  # never a rival's


def test_a_deequitisation_makes_the_founder_ruthless(data: GameData, balance: Balance) -> None:
    from ptk.sim.partnership.models import Vote, with_firm_partnership, with_vote

    g = start_life(data, balance)
    g.advance(2)
    fp = g.fp
    other = next(p.person_id for p in fp.equity_partners if p.person_id != g.founder)
    vote = Vote(
        99,
        fp.firm_id,
        "deequity",
        other,
        (("mode", "income"),),
        g.state.turn,
        5000,
        status="passed",
        resolved_turn=g.state.turn,
    )
    g.state = replace(
        g.state, partnership=with_firm_partnership(g.state.partnership, with_vote(fp, vote))
    )
    before = g.state.founder_life.life(g.founder)
    assert before is not None
    g.advance(1)
    life = g.state.founder_life.life(g.founder)
    assert life is not None
    pb = balance.founder_life.persona
    assert life.ruthless == pytest.approx(
        max(pb.start, before.ruthless + pb.sources["deequitisation"] - pb.drift)
    )
    assert any(c[3] == persona.SOURCE_WORDS["deequitisation"] for c in life.causes)


def test_foundation_beloved_and_tst_example(balance: Balance) -> None:
    """TST 32.3: Beloved +min(10, 2 log10(g / $100k)); TST 32.7 target 5's $10M a year raises
    hiring appeal by at most 0.03."""
    assert foundation.beloved_from(10_000_000_00, balance) == pytest.approx(2 * dmath.log10(100))
    assert foundation.beloved_from(10**15, balance) == balance.founder_life.foundation.beloved_cap
    assert foundation.beloved_from(5_000_000, balance) == 0
    f = foundation.Foundation(
        1, "F", "education", 0, last_grant_cents=10_000_000_00, last_grant_turn=11
    )
    assert foundation.recruiting_points(f, 12, balance) == pytest.approx(0.03)
    assert foundation.recruiting_points(f, 11 + 12, balance) == 0  # the effect has lapsed


def test_foundation_needs_cash_and_grants_each_december(data: GameData, balance: Balance) -> None:
    g = start_life(data, balance)
    g.advance(1)
    you = g.founder
    with pytest.raises(FounderLifeError):
        g.act(CreateFoundation(you, "access_to_justice"))  # $1M of personal cash needed
    fl = g.state.founder_life
    book = fl.book(you)
    assert book is not None
    from ptk.sim.founder.models import PERSONAL_CASH, PersonalEntry, with_book

    windfall = PersonalEntry.transfer(
        g.state.turn, you, "t", "t", PERSONAL_CASH, "9900_opening_net_worth", 200_000_000
    )
    g.state = replace(g.state, founder_life=with_book(fl, book.posted((windfall,))))
    g.personal.append(windfall)
    g.act(CreateFoundation(you, "access_to_justice"))
    g.act(GiveToFoundation(you, 100_000_000))
    book = g.state.founder_life.book(you)
    assert book is not None and book.bal(ENDOWMENT) == 100_000_000
    while g.state.turn % 12 != 0 or g.state.turn == 1:
        g.advance(1)
    f = g.state.founder_life.foundation(you)
    assert f is not None
    assert f.grants_cents == round(100_000_000 * balance.founder_life.foundation.payout)
    assert "foundation_grants" in [i.kind for i in g.log]


def test_bar_politics_rise_decay_and_office(data: GameData, balance: Balance) -> None:
    ib = balance.founder_life.influence
    life = persona.new_life(1, 0, balance)
    life = replace(life, committee=True)
    for _ in range(12):
        life = influence.month(life, 0, balance)
    assert 0 < life.influence < ib.cap
    life = replace(life, committee=False, influence=80.0, standing=True)
    won, result = influence.election(life, 5, (2005, 1), RngFactory(1), balance)  # June
    assert result is True and won.office_until_turn == 5 + 12 * ib.office_years
    assert influence.recruiting_points(won, balance) == pytest.approx(ib.recruiting * 0.8)
    low = replace(life, influence=10.0, standing=True)
    assert influence.election(low, 5, (2005, 1), RngFactory(1), balance)[1] is False


def test_bar_actions_and_energy(data: GameData, balance: Balance) -> None:
    g = start_life(data, balance)
    g.advance(1)
    you = g.founder
    with pytest.raises(FounderLifeError):
        g.act(StandForOffice(you))
    g.act(BarCommittee(you, True))
    energy = g.state.person_state(you).energy
    g.advance(1)
    assert g.state.person_state(you).energy == (
        balance.energy.per_month - balance.founder_life.energy.committee
    )
    assert energy is not None
    life = g.state.founder_life.life(you)
    assert life is not None and life.influence > 0


def test_legacy_has_its_parts(data: GameData, balance: Balance) -> None:
    g = start_life(data, balance)
    g.advance(13)
    you = g.founder
    lg = legacy.legacy_of(g.state, you, balance)
    start = balance.founder_life.persona.start
    assert lg.persona == pytest.approx(2 * (2 * start) - 2 * start, abs=10)
    assert lg.firm > 0  # the firm had a year's revenue
    assert lg.total == round(
        lg.firm + lg.name_on_door + lg.giving + lg.persona + lg.family + lg.bar
    )
    named = replace(g.state.player, name=f"{g.state.person(you).last_name} & Partners LLP")
    from ptk.sim.state import with_firm

    lg2 = legacy.legacy_of(with_firm(g.state, named), you, balance)
    assert lg2.name_on_door == balance.founder_life.legacy.name_points
