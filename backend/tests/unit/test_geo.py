"""PT-M11: cities, offices and leases, local markets, bar admissions and the UK path."""

from __future__ import annotations

from dataclasses import replace

import pytest

from ptk.sim.actions import apply_action
from ptk.sim.data_models import Balance, GameData
from ptk.sim.decisions import Decisions
from ptk.sim.errors import SimError
from ptk.sim.geo import formulas as gf
from ptk.sim.geo.actions import CloseOffice, MoveLawyer, OfferTrainingContracts, SeekAdmission
from ptk.sim.geo.admissions import may_lead
from ptk.sim.geo.cities import client_office_id, person_office_id
from ptk.sim.geo.markets import city_demand
from ptk.sim.geo.models import Office
from ptk.sim.geo.offices import (
    closing_entries,
    month_entries,
    office_pnl,
    renewed,
    signing_entries,
)
from ptk.sim.hiring.pay import london_pay_cents, market_pay_cents
from ptk.sim.ledger import (
    CASH,
    DEPRECIATION,
    LEASES,
    PPE,
    RENT,
    RIGHT_OF_USE,
    LedgerEntry,
    apply_entries,
)
from ptk.sim.streams import RngFactory
from ptk.sim.turn import advance_turn
from tests.geo_support import london_game, open_london
from tests.matters_support import game, solvent

OFFICE = Office(
    id=1,
    firm_id=1,
    city="london",
    seats=10,
    opened_turn=24,
    how="team_lift",
    term_months=120,
    rent_cents=5_000_000,
    fit_out_cents=25_000_007,  # odd cents: amortisation must still clear exactly
    lease_start_turn=24,
)


def _sum(entries: list[LedgerEntry]) -> dict[tuple[int, str], int]:
    return dict(apply_entries({}, entries))


def test_a_lease_posts_and_amortises_to_nothing_over_its_term() -> None:
    entries = list(signing_entries(OFFICE, 24))
    for t in range(24, 24 + OFFICE.term_months):
        entries += month_entries(OFFICE, t)
    b = _sum(entries)
    assert b.get((1, LEASES), 0) == 0  # every month's rent paid the liability down
    assert b.get((1, RIGHT_OF_USE), 0) == 0  # ... and expensed the asset
    assert b.get((1, PPE), 0) == 0  # the fit-out is fully amortised
    assert b[(1, RENT)] == OFFICE.rent_cents * OFFICE.term_months
    assert b[(1, DEPRECIATION)] == OFFICE.fit_out_cents
    assert b[(1, CASH)] == -(OFFICE.rent_cents * OFFICE.term_months + OFFICE.fit_out_cents)
    assert all(line.office_id == 1 for e in entries for line in e.lines)


def test_signing_recognises_the_term_and_a_lease_renews_at_its_end() -> None:
    b = _sum(list(signing_entries(OFFICE, 24)))
    assert b[(1, LEASES)] == -OFFICE.rent_cents * 120
    assert b[(1, RIGHT_OF_USE)] == OFFICE.rent_cents * 120
    same, none = renewed(OFFICE, 24 + 119)
    assert same is OFFICE and none == ()
    new, renewal = renewed(OFFICE, 24 + 120)
    assert new.lease_start_turn == 144 and len(renewal) == 1
    assert _sum(list(renewal))[(1, LEASES)] == -OFFICE.rent_cents * 120
    # a renewed term has no fit-out of its own
    assert not any(ln.account == DEPRECIATION for ln in month_entries(new, 150)[0].lines)


def test_closing_a_lease_clears_it_and_charges_the_penalty(balance: Balance) -> None:
    entries = list(signing_entries(OFFICE, 24))
    for t in range(24, 24 + 30):
        entries += month_entries(OFFICE, t)
    entries += closing_entries(OFFICE, 54, balance)
    b = _sum(entries)
    assert b.get((1, LEASES), 0) == 0 and b.get((1, RIGHT_OF_USE), 0) == 0
    assert b.get((1, PPE), 0) == 0
    penalty = gf.close_penalty_cents(OFFICE.rent_cents, balance.geo)
    assert b[(1, RENT)] == OFFICE.rent_cents * 30 + penalty


def test_straight_line_months_sum_exactly() -> None:
    for total, months in ((1, 3), (25_000_007, 120), (999, 7)):
        parts = [gf.straight_line(total, months, k) for k in range(months)]
        assert sum(parts) == total and min(parts) >= 0


def test_opening_an_office_by_team_lift(data: GameData, balance: Balance) -> None:
    out = london_game(data, balance, partners=2, associates=4)
    state = out.state
    office = state.geo.firm_offices(1)[0]
    assert office.city == "london" and office.seats == 10
    team = [p for p in state.people if p.city == "london" and p.id in state.staff_ids(1)]
    assert len(team) == 6
    assert all("ew" in p.bar_admissions for p in team)  # local solicitors
    assert all(person_office_id(state, 1, p) == office.id for p in team)
    clients = [c for c in state.market.clients if c.city == "london"]
    assert clients and all(set(c.panel) <= {f.key for f in state.rivals.active} for c in clients)
    assert any(c.real for c in clients)  # London's real clients (FTSE names)
    assert any(e.memo.startswith("Office lease signed") for e in out.entries)
    assert state.partnership.of(1) is not None
    assert state.partnership.of(1).arrivals  # the lifted partners' clients follow
    assert any(i.kind == "office_opened" for i in out.log)


def test_opening_needs_a_known_city_a_size_and_room(data: GameData, balance: Balance) -> None:
    state = game(data, balance)
    with pytest.raises(SimError):
        open_london(state, data, balance, city="paris")
    with pytest.raises(SimError):
        open_london(state, data, balance, city="new_york")  # the home city
    with pytest.raises(SimError):
        open_london(state, data, balance, seats=7)  # not a lease size
    with pytest.raises(SimError):
        open_london(state, data, balance, partners=3, associates=9, seats=10)
    with pytest.raises(SimError):
        open_london(state, data, balance, rival="skadden")  # not a London firm
    state = open_london(state, data, balance).state
    with pytest.raises(SimError):
        open_london(state, data, balance)  # already open


def test_an_organic_start_moves_a_partner_who_registers(data: GameData, balance: Balance) -> None:
    out = london_game(data, balance, how="organic", seats=5)
    movers = [p for p in out.state.people if p.city == "london"]
    assert len(movers) == 1
    assert "ew_rfl" in movers[0].bar_admissions  # a registered foreign lawyer
    london = {c.id for c in out.state.market.clients if c.city == "london"}
    rels = [r for r in out.state.market.relationships if r.client_id in london]
    assert len(rels) == balance.geo.organic_clients


def test_closing_moves_people_home_and_posts_a_one_off(data: GameData, balance: Balance) -> None:
    state = london_game(data, balance).state
    founder = state.founder_of(1)
    assert founder is not None
    out = apply_action(
        state,
        CloseOffice(actor_id=founder, office_id=1),
        seq=2,
        rng=RngFactory(1),
        balance=balance,
        data=data,
        ledger_balances={},
    )
    assert not out.state.geo.firm_offices(1)
    assert not any(p.city == "london" for p in out.state.people if p.id in out.state.staff_ids(1))
    assert any(e.memo.startswith("Office closed") for e in out.entries)


def test_the_office_pnls_sum_to_the_firms_each_month(data: GameData, balance: Balance) -> None:
    state = london_game(data, balance).state
    bal = solvent(balance)
    types = {a.code: a.type for a in data.accounts}
    london_lines = 0
    for _ in range(14):
        result = advance_turn(state, Decisions(), RngFactory(1), bal, data, {})
        entries = [e for e in result.ledger_entries if e.firm_id == 1]
        pnl = office_pnl(entries, 1, data)
        firm = -sum(
            ln.amount
            for e in entries
            for ln in e.lines
            if types[ln.account] in ("income", "expense")
        )
        assert sum(pnl.values()) == firm
        london_lines += sum(1 for e in entries for ln in e.lines if ln.office_id == 1)
        state = result.new_state
    assert london_lines > 0
    # fees, salaries and the lease all reached London's P&L
    accounts = {ln.account for e in result.ledger_entries for ln in e.lines if ln.office_id == 1}
    assert {RENT, "5000_associate_salaries"} <= accounts


def test_a_firm_without_offices_posts_no_office_lines(data: GameData, balance: Balance) -> None:
    state = game(data, balance)
    for _ in range(3):
        result = advance_turn(state, Decisions(), RngFactory(1), solvent(balance), data, {})
        assert all(ln.office_id is None for e in result.ledger_entries for ln in e.lines)
        state = result.new_state
    assert state.geo.demand == ()


def test_london_pays_the_london_scale(data: GameData, balance: Balance) -> None:
    ny = market_pay_cents(data, balance, "associate_1", (2006, 1), "new_york")
    ldn = market_pay_cents(data, balance, "associate_1", (2006, 1), "london")
    assert ldn < ny  # an NQ in London earns less than a New York first-year in 2006
    assert london_pay_cents(data, "trainee", (2006, 1), "london") is not None
    assert london_pay_cents(data, "associate_1", (2006, 1), "chicago") is None


def test_city_demand_is_seeded_and_sized(data: GameData, balance: Balance) -> None:
    state = game(data, balance)
    a = city_demand(RngFactory(5), 30, state, "london", data, balance)
    b = city_demand(RngFactory(5), 30, state, "london", data, balance)
    c = city_demand(RngFactory(6), 30, state, "london", data, balance)
    assert a == b and a != c
    houston = city_demand(RngFactory(5), 30, state, "houston", data, balance)
    assert sum(houston) < sum(a)


def test_leads_must_be_admitted_where_the_matter_is(data: GameData, balance: Balance) -> None:
    state = london_game(data, balance).state
    london = next(c for c in state.market.clients if c.city == "london")
    assert client_office_id(state, 1, london) == 1
    founder = state.person(state.founder_of(1) or 0)
    lifted = next(p for p in state.people if p.city == "london" and p.level == "equity_partner")
    from ptk.sim.matters.models import Matter

    deal = Matter(
        id=999,
        firm_id=1,
        client_id=london.id,
        practice="corporate_ma",
        kind_key="ma_deal",
        kind="deal",
        name="x",
        opened_turn=0,
        planned_months=6,
        expected_fees_cents=1,
        hours_needed_tenths=10,
    )
    case = replace(deal, kind="case", court="ew_commercial")
    assert may_lead(state, lifted, deal, data) and may_lead(state, lifted, case, data)
    assert not may_lead(state, founder, deal, data)  # a New York lawyer is not a solicitor
    rfl = replace(founder, bar_admissions=(*founder.bar_admissions, "ew_rfl"))
    assert may_lead(state, rfl, deal, data)  # a registered foreign lawyer: non-contentious
    assert not may_lead(state, rfl, case, data)  # ... but not a case in the English courts
    ny_client = state.market.client(1)
    delaware = replace(deal, client_id=ny_client.id, kind="case", court="ddel")
    assert may_lead(state, founder, delaware, data)  # pro hac vice is offered in Delaware
    assert not may_lead(state, lifted, delaware, data)  # not admitted in New York


def test_pro_hac_vice_posts_once_per_case_and_lead(data: GameData, balance: Balance) -> None:
    from ptk.sim.geo.admissions import pro_hac_vice_month
    from ptk.sim.matters.intake import with_matter
    from ptk.sim.matters.models import Matter

    state = game(data, balance)
    founder = state.founder_of(1)
    m = Matter(
        id=500,
        firm_id=1,
        client_id=1,
        practice="commercial_litigation",
        kind_key="x",
        kind="case",
        name="A v B",
        opened_turn=0,
        planned_months=6,
        expected_fees_cents=1,
        hours_needed_tenths=10,
        court="ddel",
        lead_id=founder,
    )
    state = replace(state, market=with_matter(state.market, m))
    state, entries, _ = pro_hac_vice_month(state, data)
    rules = data.geo.rules("us_de")
    assert rules is not None and len(entries) == 1
    assert entries[0].lines[0].amount == rules.pro_hac_vice_cents
    _, again, _ = pro_hac_vice_month(state, data)
    assert again == ()


def test_an_exam_result_is_seeded_and_a_motion_is_granted(data: GameData, balance: Balance) -> None:
    state = london_game(data, balance).state
    founder = state.founder_of(1) or 0
    act = lambda s, a: apply_action(  # noqa: E731
        s, a, seq=3, rng=RngFactory(1), balance=balance, data=data, ledger_balances={}
    )
    out = act(
        state,
        SeekAdmission(actor_id=founder, person_id=founder, jurisdiction="us_dc", route="motion"),
    )
    exam = out.state.geo.exams[0]
    assert exam.kind == "motion" and out.entries
    with pytest.raises(SimError):  # California has no admission on motion
        act(
            state,
            SeekAdmission(
                actor_id=founder, person_id=founder, jurisdiction="us_ca", route="motion"
            ),
        )
    from ptk.sim.geo.admissions import exams_month

    later = replace(out.state, turn=exam.result_turn)
    done, logs = exams_month(later, RngFactory(1), data)
    assert "us_dc" in done.person(founder).bar_admissions and logs
    assert not done.geo.exams


def test_moving_a_lawyer_changes_their_office(data: GameData, balance: Balance) -> None:
    state = london_game(data, balance).state
    founder = state.founder_of(1) or 0
    assoc = next(
        p
        for p in state.people
        if p.level.startswith("associate_") and p.city == "new_york" and p.id in state.staff_ids(1)
    )
    out = apply_action(
        state,
        MoveLawyer(actor_id=founder, person_id=assoc.id, office_id=1),
        seq=4,
        rng=RngFactory(1),
        balance=balance,
        data=data,
        ledger_balances={},
    )
    assert person_office_id(out.state, 1, out.state.person(assoc.id)) == 1


def test_training_contracts_bring_trainees_who_qualify(data: GameData, balance: Balance) -> None:
    from ptk.sim.geo.uk import trainees_join, trainees_month

    state = london_game(data, balance).state
    founder = state.founder_of(1) or 0
    out = apply_action(
        state,
        OfferTrainingContracts(actor_id=founder, office_id=1, count=3),
        seq=5,
        rng=RngFactory(1),
        balance=balance,
        data=data,
        ledger_balances={},
    )
    contract = out.state.geo.contracts[0]
    assert out.entries and contract.count == 3
    joined, logs = trainees_join(
        replace(out.state, turn=contract.start_turn), RngFactory(1), balance, data
    )
    trainees = [p for p in joined.people if p.level == "trainee"]
    assert len(trainees) == 3 and logs
    assert all(not p.bar_admissions for p in trainees)
    t = joined.geo.trainees[0]
    mid, _ = trainees_month(replace(joined, turn=t.started_turn + 7), balance, data)
    assert mid.person(t.person_id).role == data.practice_role(t.seats[1]).key  # the second seat
    done, logs = trainees_month(replace(joined, turn=t.qualify_turn), balance, data)
    nq = done.person(t.person_id)
    assert nq.level == "associate_1" and "ew" in nq.bar_admissions
    assert any(i.kind == "trainee_qualified" for i in logs)
    with pytest.raises(SimError):  # only once a year an office
        apply_action(
            out.state,
            OfferTrainingContracts(actor_id=founder, office_id=1, count=1),
            seq=6,
            rng=RngFactory(1),
            balance=balance,
            data=data,
            ledger_balances={},
        )
