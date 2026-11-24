"""Money limits, commitments and one-offs (spec 9.4; TST formulas.md 40.2).

Ported from backend/tst/sim/automation/limits.py @ 80a38079 (Tech Startup Tycoon); changed:
Partner Track's actions. A decision's commitment is its cash cost over the next
`automation.commitment_months` plus every fixed obligation it creates, from what the firm can
see (the salary scale and bands, its own WIP, an offer's terms):

- a hiring plan: its hires x the plan level's firm salary for a year (campus: a first-year's;
  a lateral plan with no level: a mid-level associate's);
- a write-down: the share of the matter's unbilled time written off;
- a lateral partner's offer: a year of the comp offered, plus every guaranteed year;
- a pro bono credit rise: the extra credited hours across the firm at its average standard
  rate (time not billed);
- a repayment of the revolver: its amount (cash out);
- PT-M14: an AI subscription (lawyers x its subscription x coverage over the months; an era's
  first investment, which buys its platform, is a one-off) and a training programme's rise;
- setting rates, a waiver request, an RFP pitch, an introduction, a sponsor, the conflict
  checks, a search or diligence, answering an event: nothing.

Spec 9.4's one-offs (`config.SPEC_ONE_OFFS`) are always proposals, whatever their size.
"""

from __future__ import annotations

from typing import Any

from ptk.sim.automation.config import ONE_OFF_KINDS
from ptk.sim.calendar import turn_to_ym
from ptk.sim.data_models import Balance, GameData
from ptk.sim.matters.intake import key_clients
from ptk.sim.money import BP_DENOMINATOR
from ptk.sim.state import GameState

MONTHS_PER_YEAR = 12  # tunable-exempt: calendar
CAMPUS_LEVEL = "associate_1"  # tunable-exempt: a campus hire's first level
PLAN_LEVEL = "associate_3"  # tunable-exempt: a lateral plan with no level is costed here
BS_LEVEL = "staff"  # tunable-exempt: a business-services plan with no level
TENTHS = 10  # tunable-exempt: hours are tenths


def _f(action: object, name: str) -> Any:
    """A field of an action of any system (its kind decides which fields it has)."""
    return getattr(action, name)


def _salary(state: GameState, level: str, data: GameData, b: Balance) -> int:
    from ptk.sim.hiring.pay import firm_pay_cents

    firm = state.player
    ym = turn_to_ym(state.turn, state.save_meta.start_ym)
    return firm_pay_cents(data, b, level, ym, firm.home_city, firm.pay_policy)


def commitment(state: GameState, action: object, b: Balance, data: GameData) -> int:
    """Cents committed by one action (TST 40.2)."""
    kind = str(getattr(action, "kind", ""))
    months = b.automation.commitment_months
    if kind == "create_plan":
        role = data.role(str(_f(action, "role")))
        channel = str(_f(action, "channel"))
        level = getattr(action, "level", None)
        if level is None:
            level = (
                CAMPUS_LEVEL
                if channel == "campus"
                else (PLAN_LEVEL if role.kind == "lawyer" else BS_LEVEL)
            )
        yearly = _salary(state, str(level), data, b)
        return int(_f(action, "target")) * yearly * months // MONTHS_PER_YEAR
    if kind == "write_down_matter":
        e = state.billing.engagement(int(_f(action, "matter_id")))
        wip = e.wip_cents if e is not None else 0
        return wip * int(_f(action, "writedown_bp")) // BP_DENOMINATOR
    if kind == "lateral_offer":
        comp = int(_f(action, "comp_cents"))
        return comp * months // MONTHS_PER_YEAR + comp * int(_f(action, "guarantee_years"))
    if kind == "repay_revolver":
        return int(_f(action, "amount_cents"))
    if kind == "invest_in_era":  # PT-M14: the subscription over the months, at the new coverage
        era = data.legal_eras.era(str(_f(action, "era")))
        lawyers = _lawyers(state, data)
        return (
            era.subscription_cents
            * lawyers
            * int(_f(action, "subscription_bp"))
            * months
            // (BP_DENOMINATOR)
        )
    if kind == "set_training_programme":  # PT-M14: the extra programme hours' cost
        from ptk.sim.tech.efficiency import trainee_ids

        firm = state.tech.firm(state.player.id)
        before = 0 if firm is None else firm.training_hours
        extra = max(0, int(_f(action, "hours")) - before)
        people = len(trainee_ids(state, state.player.id, b))
        cost = b.tech.training.cost_cents_per_hour
        return extra * people * cost * months // MONTHS_PER_YEAR
    if kind == "set_pro_bono_credit":
        now = state.player.pro_bono_credit_hours
        before = b.pro_bono.credit_hours if now is None else now
        extra = max(0, int(_f(action, "hours")) - before)
        lawyers = sum(
            1
            for e in state.staff(state.player.id)
            if data.role(state.person(e.person_id).role).kind == "lawyer"
        )
        rate = _average_rate(state, data)
        return extra * lawyers * rate * months // MONTHS_PER_YEAR
    return 0


def _lawyers(state: GameState, data: GameData) -> int:
    return sum(
        1
        for e in state.staff(state.player.id)
        if data.role(state.person(e.person_id).role).kind == "lawyer"
    )


def _average_rate(state: GameState, data: GameData) -> int:
    """The firm's standard value an hour last month (its hours' value over its hours)."""
    staff = set(state.staff_ids(state.player.id))
    hours = [r for r in state.market.hours if r.person_id in staff]
    tenths = sum(r.tenths for r in hours)
    value = sum(r.value_cents for r in hours)
    return value * TENTHS // tenths if tenths > 0 else 0


def is_one_off(state: GameState, action: object, b: Balance) -> bool:
    """Spec 9.4's list (TST 40.2): always a proposal, whoever owns the area."""
    kind = str(getattr(action, "kind", ""))
    if kind in ONE_OFF_KINDS:
        return True
    if kind == "propose_partner":  # partnership admissions (a second look is not one)
        return str(_f(action, "track")) in ("equity", "income")
    if kind == "lateral_offer":  # every hire with a guarantee
        return int(getattr(action, "guarantee_years", 0)) > 0
    if kind == "counter":  # a counter-offer's guarantee
        return int(getattr(action, "guarantee_years", 0)) > 0
    if kind == "invest_in_era":  # PT-M14: an era's first investment buys its platform
        firm = state.tech.firm(state.player.id)
        era = None if firm is None else firm.era(str(_f(action, "era")))
        return era is None or not era.platform
    if kind == "set_pay_policy":  # a salary-scale change above the market
        return str(getattr(action, "mode", "match")) == "lead"
    if kind == "seek_waiver":  # a matter adverse to a key client, with a waiver
        m = state.market.matter(int(_f(action, "matter_id")))
        adverse = None if m is None else m.adverse_client_id
        return adverse is not None and adverse in key_clients(state.market, m.firm_id, b)  # type: ignore[union-attr]
    return False
