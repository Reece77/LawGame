"""The founders' agreement at game creation (spec 2.1, 8.6; ADR PT-0007 3): the founding
partners are the equity partners, at the plateau's points; the player's founding partner is
managing partner; the scenario's capital is each founder's capital account; the first year's
budget is the founders' books at the budget margin."""

from __future__ import annotations

from simcore.kernel.money import pct_of

from ptk.sim.data_models import Balance, GameData, Scenario
from ptk.sim.partnership import formulas as fx
from ptk.sim.partnership.models import Agreement, FirmPartnership, Partner, PartnershipState
from ptk.sim.state import GameState


def revolver_floor(difficulty: str, scenario: Scenario, data: GameData) -> int:
    """The scenario's revolver at this difficulty (PT-M7b's `revolver_mult_bp`): the facility
    at the start and its floor at each January's reset."""
    level = data.difficulty(difficulty)
    return pct_of(scenario.revolver_limit_cents, level.revolver_mult_bp if level else 10000)


def founding_partnership(
    state: GameState,
    firm_id: int,
    capital_cents: int,
    scenario: Scenario,
    balance: Balance,
    data: GameData | None = None,
) -> PartnershipState:
    cfg = balance.partnership
    staff = set(state.staff_ids(firm_id))
    founders = [p for p in state.people if p.founding_partner and p.id in staff]
    books = {p.id: float(max(p.book_cents, 1)) for p in founders}
    capital = fx.split_cents(capital_cents, books)
    budget_total = pct_of(sum(p.book_cents for p in founders), cfg.budget.first_year_margin_bp)
    budgets = fx.split_cents(budget_total, dict.fromkeys(books, cfg.lockstep.founder_points))
    partners = tuple(
        Partner(
            person_id=p.id,
            firm_id=firm_id,
            klass="equity",
            admitted_turn=0,
            points=cfg.lockstep.founder_points,
            capital_required_cents=capital[p.id],
            capital_cents=capital[p.id],
            budget_cents=budgets[p.id],
            confidence=cfg.confidence.start,
        )
        for p in sorted(founders, key=lambda p: p.id)
    )
    mp = state.founder_of(firm_id)
    fp = FirmPartnership(
        firm_id=firm_id,
        agreement=Agreement.of(cfg.agreement),
        mp_id=mp,
        partners=partners,
        facility_cents=(
            revolver_floor(state.save_meta.difficulty, scenario, data)
            if data is not None
            else scenario.revolver_limit_cents
        ),
    )
    return PartnershipState(firms=(fp,))
