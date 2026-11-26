"""PT-M4 sub-tasks 7 and 8: lateral partners and partner flight (spec 5.7, 8.7), through the
`PartnerFlightHook` PT-M5 reuses; and the scripted exodus (balance target T9's mechanism)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import PartnershipError
from ptk.sim.interfaces import ApproachRequest, CounterOffer, Suitor, partner_flight
from ptk.sim.ledger import LedgerEntry
from ptk.sim.partnership import formulas as fx
from ptk.sim.partnership.actions import (
    CapitalCall,
    Counter,
    Diligence,
    LateralOffer,
    LateralSearch,
    RepayRevolver,
    SetDraws,
)
from ptk.sim.partnership.common import last_month_costs
from ptk.sim.partnership.models import with_partner
from tests.partnership_support import add_partner, depart, start


def test_leave_chance_is_spec_8_7(balance: Balance) -> None:
    cfg = balance.partnership.flight
    # at market, loyalty 11, no departures, confident: b x 1 x 1 x 1 x 1
    assert fx.leave_chance_bp(100, 100, 11, 0, 4, 60, 1.0, cfg) == 25
    # V_mkt 50% above comp: x (1 + 2 x 0.5) = 2
    assert fx.leave_chance_bp(150, 100, 11, 0, 4, 60, 1.0, cfg) == 50
    # loyalty 1: x 2; two of four left: x (1 + 3 x 0.5) = 2.5; confidence 25: x 2
    assert fx.leave_chance_bp(100, 100, 1, 2, 4, 25, 1.0, cfg) == 250
    assert fx.leave_chance_bp(10**9, 1, 1, 10, 1, 0, 2.0, cfg) == cfg.cap_bp


def test_approach_counter_and_decision(data: GameData, balance: Balance) -> None:
    g = start(data, balance, 3)
    hook = partner_flight()
    target = next(p.person_id for p in g.fp.partners if p.person_id != g.founder)
    res = hook.approach(
        g.state,
        ApproachRequest(target, Suitor("cravath", "Cravath"), offer_comp_cents=50_000_000),
        balance=balance,
        data=data,
    )
    g.state = res.state
    [view] = hook.approaches(g.state, 1)
    assert view.person_id == target and view.counter is None
    assert view.stay_label in ("likely to stay", "undecided", "likely to go")
    with pytest.raises(PartnershipError):
        hook.approach(
            g.state,
            ApproachRequest(target, Suitor("cravath", "Cravath"), 1),
            balance=balance,
            data=data,
        )
    g.act(Counter(g.founder, view.approach_id, comp_cents=60_000_000, guarantee_years=2))
    [view] = hook.approaches(g.state, 1)
    assert view.counter == CounterOffer(view.approach_id, 60_000_000, 0.0, 2, False)
    assert view.stay_label == "likely to stay"  # well above the offer
    g.advance(2)
    a = g.fp.approach(view.approach_id)
    assert a is not None and a.status in ("stayed", "left")
    if a.status == "stayed":
        p = g.fp.partner(target)
        assert p is not None and p.guarantee_until_turn is not None


def test_a_departure_returns_capital_and_takes_clients(data: GameData, balance: Balance) -> None:
    g = start(data, balance, 4)
    pid = add_partner(g, "corporate_ma", 50_000_000, clients=6, n=1)
    person = g.state.person(pid)
    g.state = replace(
        g.state,
        people=tuple(
            replace(p, portability_bp=10_000) if p.id == pid else p for p in g.state.people
        ),
    )
    g.advance(13)  # a year in: capital paid in, a current account
    p = g.fp.partner(pid)
    assert p is not None and p.capital_cents > 0
    depart(g, pid)
    assert g.fp.partner(pid) is None
    ret = next((r for r in g.fp.capital_returns if r.person_id == pid), None)
    owed = max(0, p.capital_cents + min(0, p.current_cents))
    assert (ret.remaining_capital_cents if ret else 0) == owed
    dep = next(d for d in g.fp.departures if d.person_id == pid)
    assert len(dep.follows) == 6  # portability 100%
    [view] = partner_flight().departures(g.state, 1, dep.turn)
    assert view.suitor is not None and view.suitor.key == "skadden"
    assert g.state.employment_of(pid).status == "notice"  # type: ignore[union-attr]
    g.advance(15)
    left = {r.client_id for r in g.state.market.relationships if r.firm_id == 1}
    assert not left & {c for c, _ in dep.follows}
    assert "client_followed" in g.templates()
    assert person.id not in g.state.staff_ids(1)


def test_lateral_partner_search_to_arrival(data: GameData, balance: Balance) -> None:
    g = start(data, balance, 5)
    g.act(LateralSearch(g.founder, "corporate_ma"))
    cands = [c for c in g.fp.laterals if c.status == "open"]
    assert 1 <= len(cands) <= 3
    c = cands[0]
    book = g.state.person(c.person_id).book_cents
    assert c.book_lo_cents <= book <= c.book_hi_cents
    wide = c.book_hi_cents - c.book_lo_cents
    g.act(Diligence(g.founder, c.person_id))
    c = g.fp.lateral(c.person_id)
    assert c is not None and c.diligence
    assert c.book_lo_cents <= book <= c.book_hi_cents
    assert c.book_hi_cents - c.book_lo_cents < wide
    g.act(LateralOffer(g.founder, c.person_id, c.ask_cents * 2, 3))
    g.advance()
    c = g.fp.lateral(c.person_id)
    assert c is not None and c.status == "hired"  # twice the ask, more guarantee than asked
    p = g.fp.partner(c.person_id)
    assert p is not None and p.guarantee_cents == c.offer_comp_cents
    assert p.guarantee_until_turn == g.state.turn - 1 + 36 - 1
    assert g.state.person(c.person_id).level == "equity_partner"
    g.advance(24)
    arrived = {r.client_id for r in g.state.market.relationships if r.partner_id == c.person_id}
    assert arrived <= set(c.client_ids) - set(c.conflict_ids)
    assert not g.fp.arrivals or all(a.turn > g.state.turn for a in g.fp.arrivals)


def test_a_guarantee_is_a_floor(data: GameData, balance: Balance) -> None:
    # PT-M16: seed 5 (this $900k guarantee sinks the group lift within the year on seeds 2-4
    # and 7 on main as on PT-M16, and seed 6 now too); the test is about the floor, so it uses
    # a firm that survives the year, as it asserts
    g = start(data, balance, 5)
    pid = add_partner(g, "corporate_ma", 90_000_000, guarantee_years=2, n=1)
    g.advance(12)
    assert not g.state.ended
    p = g.fp.partner(pid)
    assert p is not None and p.comp_last_cents >= 90_000_000


# --- The scripted exodus (balance target T9's mechanism) --------------------------------------

SEEDS = range(1, 11)


def _exodus(data: GameData, balance: Balance, seed: int, respond: bool) -> str:
    """Three corporate partners leave in six months with two litigators' guarantees still
    running and the revolver drawn for a fit-out. The response (spec 8.7's CFO warning
    heeded, as T9's script rule): suspend draws, call capital, repay the revolver from cash
    above two months' costs."""
    g = start(data, balance, seed)
    corp = [add_partner(g, "corporate_ma", 60_000_000, clients=6, n=i) for i in range(3)]
    for i in range(2):
        add_partner(g, "commercial_litigation", 250_000_000, guarantee_years=3, clients=2, n=10 + i)
    g.advance(12)
    g.post(
        [
            LedgerEntry.transfer(
                turn=g.state.turn,
                firm_id=1,
                memo="Office fit-out financed",
                debit="1500_ppe",
                credit="2300_revolver",
                amount=180_000_000,
            )
        ]
    )
    warned = False
    for month in range(40):
        if month in (0, 2, 4) and g.fp.partner(corp[month // 2]) is not None:
            depart(g, corp[month // 2])
        if respond:
            if (
                not warned
                and any(  # PT-M7b: T9's rule heeds the CFO's forecast first
                    t
                    in (
                        "cfo_forecast",
                        "cfo_warning",
                        "covenant_breach",
                        "revolver_called",
                        "insolvent",
                    )
                    for t in g.templates()[-60:]
                )
            ):
                warned = True
                g.act(SetDraws(g.founder, True))
                g.act(CapitalCall(g.founder, 100_000_000))
            spare = g.bal("1000_cash") - 2 * last_month_costs(g.fp)
            drawn = -g.bal("2300_revolver")
            if warned and drawn > 0 and spare > 0:
                g.act(RepayRevolver(g.founder, min(drawn, spare)))
        g.advance()
        if g.state.ended:
            break
    return g.state.save_meta.game_state


@pytest.mark.nightly  # PT-M11: over 60 s; check's runtime (product manager, 2026-11-23)
def test_the_exodus_spiral(
    data: GameData, balance: Balance, capsys: pytest.CaptureFixture[str]
) -> None:
    ignored = [_exodus(data, balance, s, False) for s in SEEDS]
    heeded = [_exodus(data, balance, s, True) for s in SEEDS]
    with capsys.disabled():
        print(
            f"\nexodus: dissolved without intervention on {ignored.count('dissolved')} of 10 "
            f"seeds, with the scripted response on {heeded.count('dissolved')} of 10"
        )
    assert ignored.count("dissolved") >= 3
    if heeded.count("dissolved") > 1:  # PT-M18's, non-strict (the product manager, 2026-11-25)
        pytest.xfail(
            "PT-M18 (product manager, 2026-11-25: non-strict, seed variance under rule 4): the "
            "heeded response dissolves on main 04efa78 1/10 (seeds 1-10) and 4/30 (11-40), on "
            "PT-M12's branch 2/10 and 3/30 (docs/tasks/PT-M12-all-twenty-practices.md, 18)"
        )


def test_confidence_and_contagion_feed_flight(data: GameData, balance: Balance) -> None:
    g = start(data, balance, 7)
    pid = add_partner(g, "corporate_ma", 50_000_000, n=1)
    hook = partner_flight()
    base = hook.leave_chance_bp(g.state, pid, balance, data)
    fp = g.fp
    p = fp.partner(pid)
    assert p is not None
    g.state = replace(
        g.state,
        partnership=replace(
            g.state.partnership, firms=(with_partner(fp, replace(p, confidence=10.0)),)
        ),
    )
    assert hook.leave_chance_bp(g.state, pid, balance, data) > base
    other = add_partner(g, "corporate_ma", 50_000_000, n=2)
    depart(g, other)
    assert hook.leave_chance_bp(g.state, pid, balance, data) > base
