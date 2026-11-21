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
from ptk.balance.game import Game, is_associate
from ptk.sim.data_models import Balance

type Script = Callable[[Game], None]

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
    """25 lawyers, leverage at most 2, the founders' two practices, high rates (market + 2
    points), pure lockstep, one partner admitted every two years, conservative money."""
    mv.comp_system(g, "lockstep")
    mv.set_rates(g, _market_bp(g) + 200)
    practices = [CORPORATE, LITIGATION]
    lawyers = len(g.lawyers())
    room = lawyers < 25 and mv.associates_per_partner(g) < 2.0
    if room:
        _campus_split(g, practices, 2, delegated=False)
        if mv.utilisation(g) >= 0.85:
            mv.lateral_associates(g, _busiest(g, practices)[0], 1, "recruiter")
    if g.ym[0] % 2 == 1:
        mv.december_votes(g, 1)
    else:
        mv.december_votes(g, 0)
    mv.revolver_cap(g, 0)
    mv.pitch_rfps(g, 1, team_size=3)


def steady(g: Game, adds: tuple[str, ...] = STEADY_ADDS) -> None:
    """Grow while utilisation is at least 80%; a campus class each year (10% of lawyers,
    through the groups' delegates once they exist); a practice added at each 30 lawyers by a
    lateral partner; the revolver at most a month's fees; modified lockstep; partners admitted
    by business case (leverage above 3 associates a partner)."""
    mv.comp_system(g, "modified_lockstep")
    mv.set_rates(g, None)
    held = mv.practices_held(g)
    lawyers = len(g.lawyers())
    mv.practice_groups(g)
    _campus_split(g, held, max(2, lawyers // 10), delegated=True)
    if mv.utilisation(g) >= 0.80:
        _grow(g, held, max(2, lawyers // 8))
    wanted = 2 + lawyers // 30  # practices the firm should hold
    missing = [p for p in adds if p not in held]
    leverage = mv.associates_per_partner(g)
    if len(held) < wanted and missing:
        mv.lateral_partner(g, missing[0], mv.LateralRule(min_book_cents=100_000_000))
    elif leverage > 4.0 and mv.utilisation(g) >= 0.80:  # partners for supervision and books
        mv.lateral_partner(g, _busiest(g, held)[-1], mv.LateralRule(min_book_cents=100_000_000))
    mv.december_votes(g, max(0, round((leverage - 3.0) * 2)) if leverage > 3.0 else 0)
    fees = g.months[-1].revenue_cents if g.months else 0
    mv.revolver_cap(g, fees)
    mv.pitch_rfps(g)
    mv.cross_sell(g, 1)


def restructuring(g: Game) -> None:
    """T8's restructuring-heavy firm: steady, adding restructuring first."""
    steady(g, ("restructuring", *[p for p in STEADY_ADDS if p != "restructuring"]))


def lateral_rocket(g: Game, heeded: bool = False) -> None:
    """Lateral partners whenever a book of $2M+ is available, with guarantees; associates in
    the laterals' practices when busy; the revolver to its covenant limit; eat what you kill.
    `heeded` (T9): when the CFO warns, stop guarantees and repay the revolver."""
    mv.comp_system(g, "eat_what_you_kill")
    mv.set_rates(g, None)
    warned = heeded and mv.heed_warning(g)
    if not warned:
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
    mv.december_votes(g, 1)
    mv.pitch_rfps(g, 1)


def lateral_rocket_heeded(g: Game) -> None:
    lateral_rocket(g, heeded=True)


def pyramid(g: Game) -> None:
    """Leverage 5+, associates hired only when utilisation reaches 88% (a 2,100-hour year),
    volume work at rates below the market (market - 2 points), two-tier with few equity
    admissions (income partners instead), a moderate revolver (two months' fees)."""
    mv.comp_system(g, "modified_lockstep", two_tier=True)
    mv.set_rates(g, max(0, _market_bp(g) - 200))
    held = mv.practices_held(g)
    lawyers = len(g.lawyers())
    mv.practice_groups(g)
    _campus_split(g, held, max(3, lawyers // 6), delegated=True)
    if mv.utilisation(g) >= 0.88 or mv.associates_per_partner(g) < 5.0:
        for practice in _busiest(g, held)[:2]:
            mv.lateral_associates(g, practice, 2, "job_post")
    if len(held) < 2 + lawyers // 40:
        missing = [p for p in STEADY_ADDS if p not in held]
        if missing:
            mv.lateral_partner(g, missing[0], mv.LateralRule(min_book_cents=100_000_000))
    admit = 1 if g.ym[0] % 3 == 0 else 0
    mv.december_votes(g, 2, track="income")
    if admit:
        mv.december_votes(g, 1, track="equity")
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
}
PLAYABLE: Final[dict[str, Script]] = {**STRATEGIES, **VARIANTS}
