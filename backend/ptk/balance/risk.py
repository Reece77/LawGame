"""PT-M15's balance strategy (brief sub-task 8): `cowboy`, steady with its corners cut.

- **Lax supervision** from the first month (`SetSupervision`): partners' non-billable hours are
  freed for billing, and claims, bar complaints and client-money misuse come more often.
- **No general counsel:** the seat is left vacant (PT-M8's fill-seats step appoints one each
  month; the script vacates it before the turn, so the turn runs without a GC), and the conflict
  checks are switched off.
- **Rule-bending laterals:** whenever steady would hire a lateral partner, the cowboy takes the
  candidate with the biggest claimed book (the top of its range) and offers their ask at once,
  without diligence (steady diligences every lateral and goes by the bottom of the range).

Otherwise it is steady (`ptk.balance.strategies.steady`). Registered in
`ptk.balance.strategies.VARIANTS` in one line (lane A owns the runner). It acts only through
the player's actions and reads only what the player can see.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Final

from ptk.balance import moves as mv
from ptk.balance.game import Game, start_game
from ptk.sim.matters.actions import SetConflictChecks
from ptk.sim.org.seats import AppointSeat
from ptk.sim.partnership.actions import LateralOffer, LateralSearch
from ptk.sim.risk.actions import SetSupervision

GC: Final = "general_counsel"
FIRST_YEAR: Final = 2006  # T14 reads claims from the first full year (2005 has no history)


def _cut_corners(g: Game) -> None:
    me = g.founder_id
    if g.state.risk.firm(g.state.player.id).supervision != "lax":
        g.act(SetSupervision(me, "lax"))
    if g.state.player.conflict_checks:
        g.act(SetConflictChecks(me, False))
    for h in [h for h in g.state.leadership.holders if h.seat == GC]:
        g.act(AppointSeat(me, GC, h.slot, None))


def _unvetted(g: Game, practice: str, rule: mv.LateralRule) -> bool:
    """Steady's lateral step without diligence: the candidate with the biggest claimed book
    (the top of its range) is offered their ask as soon as the top reaches the rule's floor."""
    fp = g.state.partnership.of(g.state.player.id)
    if fp is None:
        return False
    open_ = [c for c in fp.laterals if c.status == "open" and c.practice == practice]
    if not open_:
        return g.act(LateralSearch(g.founder_id, practice))
    best = max(open_, key=lambda c: (c.book_hi_cents, -c.person_id))
    if best.book_hi_cents < rule.min_book_cents:
        return False
    return g.act(LateralOffer(g.founder_id, best.person_id, best.ask_cents, rule.guarantee_years))


def cowboy(g: Game) -> None:
    from ptk.balance.strategies import steady  # strategies imports this module

    _cut_corners(g)
    vetted = mv.lateral_partner
    mv.lateral_partner = _unvetted  # steady's cadence, without diligence (restored below)
    try:
        steady(g)
    finally:
        mv.lateral_partner = vetted


RISK_VARIANTS: Final[dict[str, Callable[[Game], None]]] = {"cowboy": cowboy}


# --- PT-M15's readings (tests/balance/test_pt_m15.py) -------------------------------------


@dataclass(frozen=True, slots=True)
class RiskRun:
    """What one run's risk readings need, 2005-2015 (picklable for worker processes)."""

    strategy: str
    seed: int
    claims: int  # claims noticed
    cases: int  # disciplinary cases opened
    lawyer_years: float  # lawyers on the books, summed over months / 12, 2006-2015
    claims_0615: int  # claims noticed 2006-2015 (T14's window)
    pep_cents: int  # PEP (trailing 12 months) in December 2015; 0 if dissolved
    premium_per_lawyer_cents: int  # the policy in force in December 2015, a lawyer
    dissolved: bool


def risk_run(strategy: str, seed: int, turns: int = 132, data_dir: str = "data") -> RiskRun:
    from simcore.kernel.calendar import turn_to_ym

    from ptk.balance.report import SCENARIO, _loaded
    from ptk.balance.seats import fill_seats
    from ptk.balance.strategies import PLAYABLE

    data, balance = _loaded(data_dir)
    g = start_game(data, balance, seed, SCENARIO, "standard")
    script = PLAYABLE[strategy]
    months = 0.0
    for _ in range(turns):
        if g.state.ended:
            break
        fill_seats(g)
        script(g)
        g.turn()
        if g.ym[0] >= FIRST_YEAR:
            months += len(g.lawyers())
    state = g.state
    start = state.save_meta.start_ym

    def year(t: int) -> int:
        return turn_to_ym(t, start)[0]

    noticed = [c for c in state.risk.claims if c.noticed_turn is not None]
    policy = state.risk.policy(state.player.id, state.turn - 1)
    last = g.months[-1] if g.months else None
    lawyers = max(1, len(g.lawyers()))
    return RiskRun(
        strategy=strategy,
        seed=seed,
        claims=len(noticed),
        cases=len(state.risk.cases),
        lawyer_years=months / 12,
        claims_0615=sum(1 for c in noticed if year(c.noticed_turn or 0) >= FIRST_YEAR),
        pep_cents=0 if state.ended or last is None else (last.pep_cents or 0),
        premium_per_lawyer_cents=0 if policy is None else policy.premium_cents // lawyers,
        dissolved=state.ended,
    )
