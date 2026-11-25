"""PT-M12 sub-task 7: a firm enters a practice by a lateral partner (PT-M4's search), a
lateral team, or a partner retraining (slow familiarity, ADR PT-0006); a new practice group
follows PT-M2's rules; the scenario's starting practices are unchanged."""

from __future__ import annotations

from typing import Any

import pytest

from ptk.balance.game import start_game
from ptk.loader import load_balance, load_game_data
from ptk.sim.org.practices import EnterPractice, firm_practices
from ptk.sim.people.formulas import familiarity_after
from tests.pt_m12_support import DATA

ARB = "international_arbitration"


@pytest.fixture
def g() -> Any:
    data, balance = load_game_data(DATA), load_balance(DATA)
    return start_game(data, balance, 1)


def test_the_scenario_starts_in_v1_practices_only(g: Any) -> None:
    assert set(firm_practices(g.state, 1, g.data)) <= set(g.data.practice_keys[:10])


def test_a_lateral_partner_search_opens_in_the_new_practice(g: Any) -> None:
    assert g.act(EnterPractice(g.founder_id, ARB, "lateral"))
    fp = g.state.partnership.firms[0]
    candidates = [c for c in fp.laterals if c.practice == ARB]
    assert candidates and all(c.status == "open" for c in candidates)
    assert ARB not in firm_practices(g.state, 1, g.data)  # the practice is the firm's on arrival


def test_a_lateral_team_brings_partners_associates_and_clients(g: Any) -> None:
    before = len(g.lawyers())
    assert g.act(EnterPractice(g.founder_id, "tax", "team"))
    cfg = g.balance.org.enter
    tax = [p for p in g.lawyers() if p.role == "tax"]
    assert len(g.lawyers()) == before + cfg.team_partners + cfg.team_associates
    assert sum(1 for p in tax if p.level == "equity_partner") == cfg.team_partners
    assert "tax" in firm_practices(g.state, 1, g.data)
    # the partners' books bring clients instructing the firm in tax (PT-M4's arrivals)
    coming = [x for x in g.state.partnership.firms[0].arrivals if x.practice == "tax"]
    assert coming
    with pytest.raises(AssertionError):
        assert g.act(EnterPractice(g.founder_id, "tax", "team"))  # already practised


def test_a_retrained_partner_takes_the_practice_with_slow_familiarity(g: Any) -> None:
    partner = next(p for p in g.lawyers() if p.level == "equity_partner")
    fam = partner.familiarity[ARB]
    assert g.act(EnterPractice(g.founder_id, ARB, "retrain", person_id=partner.id))
    after = g.state.person(partner.id)
    assert after.role == ARB and after.familiarity[ARB] == fam
    assert ARB in firm_practices(g.state, 1, g.data)
    # a year of full-time work in it moves familiarity a few points, not to the home range
    cfg = g.balance.familiarity
    value = fam
    for _ in range(12):
        value = familiarity_after(value, value, 1500, cfg)
    assert fam < value < 15


def test_an_associate_cannot_retrain_into_a_practice(g: Any) -> None:
    assoc = next(p for p in g.lawyers() if p.level.startswith("associate"))
    assert not g.act(EnterPractice(g.founder_id, ARB, "retrain", person_id=assoc.id))


def test_a_group_opens_by_pt_m2s_rules(g: Any) -> None:
    """At or above the unlock, a team entering a practice opens its group (PT-M2)."""
    data, balance = g.data, g.balance
    unlock = balance.org.practice_group_unlock_lawyers
    low = balance.model_copy(
        update={"org": balance.org.model_copy(update={"practice_group_unlock_lawyers": 1})}
    )
    g.balance = low
    assert unlock > 1
    assert g.act(EnterPractice(g.founder_id, "energy", "team"))
    groups = [u for u in g.state.org.firm_units(1) if u.practice == "energy"]
    assert len(groups) == 1 and groups[0].kind == "practice_group"
    _ = data


def test_a_team_entering_a_practice_wins_work_in_it(g: Any) -> None:
    from tests.matters_support import solvent

    g.balance = solvent(g.balance)  # a six-lawyer team at once is beyond a new firm's cash
    assert g.act(EnterPractice(g.founder_id, "tax", "team"))
    hours = 0
    for _ in range(18):
        g.turn()
        hours += sum(r.tenths for r in g.state.market.hours if r.practice == "tax")
    rels = [r for r in g.state.market.relationships if r.firm_id == 1 and "tax" in r.practices]
    assert rels and hours > 0
