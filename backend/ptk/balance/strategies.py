"""docs/balance-targets.md's strategies as scripts (PT-M7). Each is called once a month before
the turn and acts through `ptk.balance.moves`. The do-nothing script does nothing; the others
hire (a campus class each year and laterals by rule), use the delegates where the strategy
says so, set rates each January (in December, before January's rise) and answer December's
votes.

Two variants serve single targets: `lateral_rocket_heeded` (T9: the rocket with the CFO's
warnings heeded) and `restructuring` (T8: steady with a restructuring practice from the start).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Final

from ptk.balance import moves as mv
from ptk.balance.automated import steady_automated
from ptk.balance.game import Game, is_associate
from ptk.balance.tech import TECH_VARIANTS
from ptk.sim.data_models import Balance

type Script = Callable[[Game], None]

PYRAMID_HOURS: Final = (
    175  # hours a month planned for each associate: 2,100 a year (docs/balance-targets.md)
)
# PT-M7b: pyramid's hours policy, a firm-wide billable target (the brief's 2,300-2,400)
PYRAMID_POLICY_HOURS: Final = 2300
# PT-M10 (Reece, 2026-11-22): a pyramid lays off associates while utilisation stays low
PYRAMID_LAYOFF_BELOW: Final = 0.75  # three months' utilisation under this: lay off
PYRAMID_LAYOFF_TARGET: Final = 0.85  # ... enough associates to bring it back toward this
PYRAMID_LAYOFF_MAX: Final = 0.10  # at most this share of the associates in a month
# PT-M7c (client tiers; CLAUDE.md 9 rule 2): a pyramid billing mid-market clients at below the
# market's rates pays below the top New York scale, as mid-size firms do (65-72% of the scale,
# docs/research/firm-economics.md s5); at the full scale it dissolved on 13 of seeds 11-40
PYRAMID_PAY_BP: Final = 8000
# PT-M7c (client tiers; CLAUDE.md 9 rule 2): steady lays off associates while utilisation stays
# low (more patient than the pyramid); without it every easy-difficulty death came in 2009 (a
# loss year zeroes the partners' allocations and flight takes them): T5 easy 40%, standard 30%
STEADY_LAYOFF_BELOW: Final = 0.70  # three months' utilisation under this: lay off
STEADY_LAYOFF_TARGET: Final = 0.80  # ... enough associates to bring it back toward this
STEADY_LAYOFF_MAX: Final = 0.10  # at most this share of the associates in a month
CORPORATE: Final = "corporate_ma"
LITIGATION: Final = "commercial_litigation"
# The order steady adds practices in (one at each 30 lawyers): cross-sell from M&A first.
STEADY_ADDS: Final = (
    "private_equity",
    "banking_finance",
    "restructuring",
    "capital_markets",
    "white_collar",
    "ip",
    "employment",
    "real_estate",
)


def _cfg(g: Game) -> Balance:
    return g.balance


def do_nothing(g: Game) -> None:
    """Founders only, flow work only, no BD, no revolver use, no votes."""


def _campus_split(g: Game, practices: list[str], total: int, delegated: bool) -> None:
    """A class of `total` a year split over the practices held (largest share first); a
    practice whose group has a leader hires through a campus plan when `delegated`."""
    if not practices or total <= 0:
        return
    base, extra = divmod(total, len(practices))
    for i, practice in enumerate(practices):
        n = base + (1 if i < extra else 0)
        if n <= 0:
            continue
        if delegated and g.ym[1] == mv.CAMPUS_OPEN and mv.delegate(g, practice, n):
            continue
        if not (
            delegated and mv.unit_of(g, practice) is not None and _has_campus_plan(g, practice)
        ):
            mv.campus(g, practice, n)


def _has_campus_plan(g: Game, practice: str) -> bool:
    unit = mv.unit_of(g, practice)
    return any(
        pl.status == "active" and pl.unit_id == unit and pl.campus for pl in g.state.org.plans
    )


def _busiest(g: Game, practices: list[str]) -> list[str]:
    """Practices by associates per partner, fewest first (where a hire helps most)."""

    def ratio(p: str) -> float:
        staff = [x for x in g.lawyers() if mv.practice_of(g, x.id) == p]
        partners = sum(1 for x in staff if x.level in ("equity_partner", "income_partner"))
        return sum(1 for x in staff if is_associate(x.level)) / max(1, partners)

    return sorted(practices, key=lambda p: (ratio(p), p))


def _per_equity(g: Game) -> float:
    staff = g.lawyers()
    return len(staff) / max(1, sum(1 for p in staff if p.level == "equity_partner"))


def _admissions(g: Game, lawyers_per_equity: float) -> int:
    """December's business case: equity admissions that bring the firm to one equity partner
    per `lawyers_per_equity` lawyers."""
    staff = g.lawyers()
    equity = sum(1 for p in staff if p.level == "equity_partner")
    return max(0, round(len(staff) / lawyers_per_equity) - equity)


def _grow(g: Game, practices: list[str], n: int, channel: str = "job_post") -> None:
    """Hire about `n` lateral associates this month across the practices that need them most:
    a practice group's leader through a hiring plan, otherwise the founder."""
    order = _busiest(g, practices)
    for i in range(n):
        practice = order[i % len(order)] if order else None
        if practice is None:
            return
        if not mv.delegate(g, practice, 2, channel):
            mv.lateral_associates(g, practice, 1, channel)


def boutique(g: Game) -> None:
    """25 lawyers, leverage at most 2, the founders' two practices, high rates (market + 1
    point), premium clients (RFPs pitched), pure lockstep, one partner admitted every two
    years, conservative money. It grows whenever its people are busy: associates while
    leverage is under 2, a lateral partner with a $2M book when it reaches 2."""
    mv.answer_election(g)
    mv.comp_system(g, "lockstep")
    mv.set_rates(g, _market_bp(g) + 100)
    mv.december_votes(g, 1 if g.ym[0] % 2 == 1 else 0)  # one partner every two years
    mv.comp_round(g)  # PT-M7b: December's comp round (pure lockstep: no lever)
    practices = [CORPORATE, LITIGATION]
    lawyers = len(g.lawyers())
    leverage = mv.associates_per_partner(g)
    busy = mv.utilisation(g) >= 0.80
    if lawyers < 25:
        _campus_split(g, practices, 2 if leverage < 2.0 else 0, delegated=False)
        if busy and leverage < 2.0:
            mv.lateral_associates(g, _busiest(g, practices)[0], 1, "recruiter")
        elif busy and mv.bank_quiet(g):  # a partner to keep leverage at 2 (a premium book)
            mv.lateral_partner(g, _busiest(g, practices)[-1], mv.LateralRule(200_000_000))
    mv.revolver_cap(g, 0)
    mv.pitch_rfps(g, 2, team_size=3)


def steady(g: Game, adds: tuple[str, ...] = STEADY_ADDS) -> None:
    """Grow while utilisation is at least 80%; a campus class each year (10% of lawyers,
    through the groups' delegates once they exist); a practice added at each 30 lawyers by a
    lateral partner; the revolver at most a month's fees; modified lockstep; partners admitted
    by business case (leverage above 3 associates a partner); PT-M7c: associates laid off while
    utilisation stays below 70%."""
    mv.answer_election(g)
    mv.comp_system(g, "modified_lockstep")
    mv.set_rates(g, None)
    mv.december_votes(g, _admissions(g, 4.0))  # December's vote first (its energy)
    mv.comp_round(g)  # PT-M7b: December's comp round, the partners it would keep
    held = mv.practices_held(g)
    lawyers = len(g.lawyers())
    mv.practice_groups(g)
    _campus_split(g, held, max(2, lawyers // 10), delegated=True)
    # PT-M7c (rule 2): associates laid off while utilisation stays low, as 2009's firms did
    mv.lay_off_idle(g, STEADY_LAYOFF_BELOW, STEADY_LAYOFF_TARGET, STEADY_LAYOFF_MAX)
    if mv.utilisation(g) >= 0.80:
        _grow(g, held, max(2, lawyers // 8))
    wanted = 2 + lawyers // 30  # practices the firm should hold
    missing = [p for p in adds if p not in held]
    leverage = mv.associates_per_partner(g)
    if len(held) < wanted and missing:
        mv.lateral_partner(g, missing[0], mv.LateralRule(min_book_cents=100_000_000))
    elif (
        (leverage > 4.0 or _per_equity(g) > 5.0) and mv.utilisation(g) >= 0.80 and mv.bank_quiet(g)
    ):
        # partners for supervision, books and the equity (a steady firm keeps about one equity
        # partner to four or five lawyers)
        mv.lateral_partner(g, _busiest(g, held)[-1], mv.LateralRule(min_book_cents=100_000_000))
    fees = g.months[-1].revenue_cents if g.months else 0
    mv.revolver_cap(g, fees)
    mv.pitch_rfps(g)
    mv.cross_sell(g, 1)


def restructuring(g: Game) -> None:
    """T8's restructuring-heavy firm: steady, with a restructuring lateral partner from 2005
    (two until it holds them) and restructuring first among the practices it adds."""
    held = mv.practices_held(g)
    partners = sum(
        1
        for p in g.lawyers()
        if mv.practice_of(g, p.id) == "restructuring"
        and p.level in ("equity_partner", "income_partner")
    )
    if partners < 2 and mv.bank_quiet(g):
        mv.lateral_partner(g, "restructuring", mv.LateralRule(min_book_cents=100_000_000))
    del held
    steady(g, ("restructuring", *[p for p in STEADY_ADDS if p != "restructuring"]))


def lateral_rocket(g: Game, heeded: bool = False) -> None:
    """Lateral partners whenever a book of $2M+ is available, with guarantees; associates in
    the laterals' practices when busy; the revolver to its covenant limit; eat what you kill.
    `heeded` (T9): when the CFO warns, stop guarantees and repay the revolver; PT-M10: before a
    guaranteed lateral, ask the CFO's forecast and take none until it shows headroom."""
    mv.answer_election(g)
    mv.comp_system(g, "eat_what_you_kill")
    mv.set_rates(g, None)
    mv.december_votes(g, 1)
    mv.comp_round(g)  # PT-M7b (eat what you kill: no lever)
    warned = heeded and mv.heed_warning(g)
    # PT-M10 (Reece, 2026-11-22): the heeded rocket asks the CFO's forecast before a guaranteed
    # lateral and takes none until six months of trend show headroom
    asked = not heeded or mv.cfo_clear(g)
    if not warned and asked and mv.bank_quiet(g):
        for practice in [CORPORATE, LITIGATION, *STEADY_ADDS][: 2 + len(g.lawyers()) // 15]:
            if mv.lateral_partner(
                g, practice, mv.LateralRule(min_book_cents=200_000_000, guarantee_years=3)
            ):
                break
    held = mv.practices_held(g)
    mv.practice_groups(g)
    if mv.utilisation(g) >= 0.80:
        for practice in _busiest(g, held)[:2]:
            mv.lateral_associates(g, practice, 1, "recruiter")
    _campus_split(g, held, max(1, len(g.lawyers()) // 15), delegated=True)
    mv.pitch_rfps(g, 1)


def lateral_rocket_heeded(g: Game) -> None:
    lateral_rocket(g, heeded=True)


def pyramid(g: Game) -> None:
    """Leverage 5+, associates hired only when utilisation reaches 88% (a 2,100-hour year),
    volume work at rates below the market (market - 2 points), two-tier with few equity
    admissions (income partners instead), a moderate revolver (two months' fees); PT-M10:
    associates laid off while utilisation stays below 75%; PT-M7c: pays 80% of the scale."""
    mv.answer_election(g)
    mv.comp_system(g, "modified_lockstep", two_tier=True)
    mv.pay_policy(g, PYRAMID_PAY_BP)  # PT-M7c: mid-market rates, mid-market pay
    mv.set_rates(g, max(0, _market_bp(g) - 200))
    held = mv.practices_held(g)
    lawyers = len(g.lawyers())
    mv.december_votes(g, max(1, lawyers // 15), track="income")
    mv.comp_round(g)  # PT-M7b: December's comp round, the partners it would keep
    mv.practice_groups(g)
    _campus_split(g, held, max(3, lawyers // 6), delegated=True)
    mv.hours_policy(g, PYRAMID_POLICY_HOURS)  # PT-M7b: the staffing rule plans toward it
    mv.push_hours(g, PYRAMID_HOURS)  # a 2,100-hour year's plan for every associate
    # PT-M10 (Reece, 2026-11-22): associates laid off while utilisation stays low
    mv.lay_off_idle(g, PYRAMID_LAYOFF_BELOW, PYRAMID_LAYOFF_TARGET, PYRAMID_LAYOFF_MAX)
    if mv.utilisation(g) >= 0.90 and mv.bank_quiet(g, cash_months=1.0):
        _grow(g, held, max(2, lawyers // 6))
    if len(held) < 2 + lawyers // 40 and mv.bank_quiet(g):
        missing = [p for p in STEADY_ADDS if p not in held]
        if missing:
            mv.lateral_partner(g, missing[0], mv.LateralRule(min_book_cents=100_000_000))
    fees = g.months[-1].revenue_cents if g.months else 0
    mv.revolver_cap(g, 2 * fees)
    mv.pitch_rfps(g)
    mv.cross_sell(g, 1)


def _market_bp(g: Game) -> int:
    from ptk.sim.matters.rates import market_rise_bp

    return market_rise_bp(g.ym[0] + 1, g.data, g.balance)


STRATEGIES: Final[dict[str, Script]] = {
    "do-nothing": do_nothing,
    "boutique": boutique,
    "steady": steady,
    "lateral-rocket": lateral_rocket,
    "pyramid": pyramid,
}
VARIANTS: Final[dict[str, Script]] = {
    "lateral-rocket-heeded": lateral_rocket_heeded,  # T9
    "restructuring": restructuring,  # T8
    "steady-30y": steady,  # PT-M10: steady to December 2034 (T11 at 2020 and 2025, 2020's shock)
    "steady-automated": steady_automated,  # PT-M9 (ptk/balance/automated.py)
    **TECH_VARIANTS,  # PT-M14: ai-hourly, ai-fixed, never (ptk/balance/tech.py)
    **__import__("ptk.balance.offices").balance.offices.OFFICE_VARIANTS,  # PT-M11 (offices.py)
    **__import__("ptk.balance.mergers").balance.mergers.MERGER_VARIANTS,  # PT-M13 (mergers.py)
}
PLAYABLE: Final[dict[str, Script]] = {**STRATEGIES, **VARIANTS}
