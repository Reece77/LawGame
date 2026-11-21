"""PT-M4 sub-tasks 1, 2 and 4: capital, draws, the December allocation and true-up, the
revolver and insolvency; PEP and spec 8.1's worked example."""

from __future__ import annotations

from dataclasses import replace

import pytest

from ptk.sim.data_models import Balance, GameData
from ptk.sim.ledger import LedgerEntry
from ptk.sim.partnership import formulas as fx
from ptk.sim.partnership.actions import RepayRevolver, SetDraws
from ptk.sim.partnership.books import monthly_draw_cents
from ptk.sim.partnership.models import Partner
from tests.partnership_support import Game, start


def subledgers_match(g: Game) -> None:
    fp = g.fp
    capital = sum(p.capital_cents for p in fp.partners) + sum(
        r.remaining_capital_cents for r in fp.capital_returns
    )
    current = sum(p.current_cents for p in fp.partners) + sum(
        r.remaining_current_cents for r in fp.capital_returns
    )
    assert capital == -g.bal("3000_partners_capital")
    assert current == -g.bal("2700_partner_current_accounts")


def test_spec_8_1_worked_example() -> None:
    """120 lawyers, 30 equity partners, 1,750 hours at $420, 88% and 96%: $74.5M revenue,
    RPL $621k, costs $45.0M, profit $29.5M, margin 39.6%, leverage 4.0, PEP $983k."""
    revenue = fx.revenue_from_hours(120, 1750, 42_000, 8800, 9600)
    assert revenue == 7_451_136_000  # $74,511,360
    ident = fx.PepIdentity(revenue, revenue - 4_500_000_000, 120, 30)
    assert ident.rpl_cents == 62_092_800  # $620,928: $621k
    assert ident.profit_cents == 2_951_136_000  # $29.5M
    assert ident.margin_bp == 3961  # 39.6%
    assert ident.leverage == 4.0
    assert ident.pep_cents == 98_371_200  # $983,712: $983k (the spec rounds down)
    rpl, margin, lev = ident.rpl_cents, ident.margin_bp / 10_000, ident.leverage
    assert rpl * margin * lev == pytest.approx(ident.pep_cents, rel=1e-3)


def test_founders_agreement(data: GameData, balance: Balance) -> None:
    g = start(data, balance, seed=1, scenario="biglaw_spinout")
    fp = g.fp
    assert fp.mp_id == g.founder
    assert len(fp.equity_partners) == 2
    assert all(p.points == balance.partnership.lockstep.founder_points for p in fp.partners)
    assert fp.agreement.comp_system == "modified_lockstep"
    subledgers_match(g)
    assert -g.bal("3000_partners_capital") == 60_000_000


def test_a_year_of_draws_allocation_and_true_up(data: GameData, balance: Balance) -> None:
    # PT-M7: seed 3 (with overhead per lawyer, seed 2's founders drew more than its first
    # year's cash profit: no true-up is owed, which is not what this test is about)
    g = start(data, balance, seed=3, scenario="biglaw_spinout")
    g.advance(11)  # January to November: draws only
    drawn = sum(p.drawn_ytd_cents for p in g.fp.partners)
    assert drawn > 0 and g.bal("3200_drawings") == drawn
    assert g.bal("2700_partner_current_accounts") == 0
    g.advance()  # December: the allocation
    fp = g.fp
    assert g.bal("3200_drawings") == 0  # drawings closed to the current accounts
    allocated = sum(p.comp_last_cents for p in fp.partners)
    assert allocated == fp.last_profit_cents  # retain_bp 0: everything is allocated
    assert g.bal("3100_undistributed_profit") == allocated
    subledgers_match(g)
    owed = -g.bal("2700_partner_current_accounts")
    assert owed > 0  # the precondition: the firm owes its partners a true-up
    draws = sum(
        ln.amount for e in g.entries if e.memo == "Partner draws" for ln in e.lines if ln.amount > 0
    )
    assert draws > drawn  # December's draw too
    assert owed == allocated - draws
    g.advance(4)  # January to April: the true-up as cash allows
    assert -g.bal("2700_partner_current_accounts") < owed
    subledgers_match(g)
    assert "profit_allocated" in g.templates()


def test_draws_follow_budget_and_guarantees(balance: Balance) -> None:
    from ptk.sim.partnership.models import Agreement, FirmPartnership

    fp = FirmPartnership(firm_id=1, agreement=Agreement.of(balance.partnership.agreement), mp_id=1)
    p = Partner(1, 1, "equity", 0, budget_cents=1_200_000_00)
    assert monthly_draw_cents(p, fp, 5) == 7_000_000  # 70% of $1.2M / 12
    assert monthly_draw_cents(p, replace(fp, draws_suspended=True), 5) == 0
    g = replace(p, guarantee_cents=2_400_000_00, guarantee_until_turn=30)
    assert monthly_draw_cents(g, replace(fp, draws_suspended=True), 5) == 20_000_000
    assert monthly_draw_cents(replace(p, admitted_turn=6), fp, 5) == 0  # admitted from next month


def test_suspending_draws(data: GameData, balance: Balance) -> None:
    g = start(data, balance, seed=3, scenario="biglaw_spinout")
    g.act(SetDraws(g.founder, True))
    g.advance(2)
    assert all(p.drawn_ytd_cents == 0 for p in g.fp.partners)


def test_revolver_draws_when_short_and_repays(data: GameData, balance: Balance) -> None:
    g = start(data, balance, seed=4)
    g.advance(3)
    # the firm spends more cash than it has: the revolver covers what the borrowing base allows
    g.post(
        [
            LedgerEntry.transfer(
                turn=g.state.turn,
                firm_id=1,
                memo="Fit-out",
                debit="1500_ppe",
                credit="1000_cash",
                amount=g.bal("1000_cash") + 5_000_000,
            )
        ]
    )
    g.advance()
    drawn = -g.bal("2300_revolver")
    assert drawn > 0 and g.bal("1000_cash") >= 0
    assert g.bal("6800_interest") == 0 or g.bal("6800_interest") > 0
    g.advance()
    assert g.bal("6800_interest") > 0  # interest on the opening balance
    g.post(
        [
            LedgerEntry.transfer(
                turn=g.state.turn,
                firm_id=1,
                memo="Partner loan",
                debit="1000_cash",
                credit="3000_partners_capital",
                amount=drawn * 2,
            )
        ]
    )
    g.act(RepayRevolver(g.founder, 10**12))
    assert g.bal("2300_revolver") == 0


def test_three_months_below_zero_dissolve_the_firm(data: GameData, balance: Balance) -> None:
    g = start(data, balance, seed=5)
    fp = replace(g.fp, facility_cents=0)
    g.state = replace(g.state, partnership=replace(g.state.partnership, firms=(fp,)))
    g.post(
        [
            LedgerEntry.transfer(
                turn=0,
                firm_id=1,
                memo="Lost",
                debit="6900_general_admin",
                credit="1000_cash",
                amount=g.bal("1000_cash") + 500_000_000,
            )
        ]
    )
    for _ in range(balance.partnership.insolvency_months):
        assert not g.state.ended
        g.advance()
    assert g.state.save_meta.game_state == "dissolved"
    assert "firm_dissolved" in g.templates()


def test_covenants() -> None:
    from ptk.sim.data_models import RevolverBalance

    cfg = RevolverBalance(
        receivables_bp=7000,
        wip_bp=4000,
        unsecured_bp=5000,
        facility_of_revenue_bp=2500,
        rate_bp=650,
        leverage_max_bp=3000,
        min_capital_bp=5000,
        departures_max_bp=2000,
        cure_months=3,
        call_months=3,
        warning_headroom_bp=2000,
        forecast_months=6,  # PT-M7b: the CFO's forecast (not read by the covenants)
        forecast_window=6,
    )
    assert fx.covenants(0, 10, 0, 0, cfg) == ()
    lev, cap, dep = fx.covenants(1_000, 10_000, 600, 1_000, cfg)
    assert lev.holds and cap.holds and dep.holds
    assert not fx.covenants(4_000, 10_000, 600, 1_000, cfg)[0].holds
    assert not fx.covenants(1_000, 10_000, 400, 1_000, cfg)[1].holds
    assert not fx.covenants(1_000, 10_000, 600, 3_000, cfg)[2].holds
    assert fx.borrowing_base_cents(1_000, 1_000, cfg) == 1_100
    assert fx.monthly_interest_cents(1_200_000, cfg) == 6_500


def test_pep_in_the_snapshot(data: GameData, balance: Balance) -> None:
    g = start(data, balance, seed=6, scenario="biglaw_spinout")
    result = g.advance(13)
    assert result is not None
    snap = result.snapshot.firms[0]
    assert snap.equity_partners == 2
    assert snap.pep_cents is not None and snap.pep_cents > 0
    assert snap.margin_bp is not None and snap.leverage_bp is not None
