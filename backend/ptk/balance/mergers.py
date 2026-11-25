"""PT-M13's strategies (registered in `ptk.balance.strategies.VARIANTS` with one line).

Both play steady and decline every rival's approach:

- `merger`: from January 2010 to December 2012, while it has not merged, approaches the
  integrable firm (at most `MAX_RATIO` times its lawyers, at least `MIN_SHARE` of the merged pool
  for the player's partners) whose practices complement it most; commissions one level of
  diligence, then puts terms at the fair share of the two profit pools, a combined name, its own
  managing partner and comp system, and a blended card; accepts a counter that leaves it at
  least `MIN_SHARE`, else walks away and tries the next firm.
- `verein`: from January 2010, until it has one, approaches the London firm most open to a
  verein and puts terms (a verein's terms carry no points ratio).
"""

from __future__ import annotations

from typing import Final

from ptk.balance.game import Game
from ptk.sim.mergers.actions import (
    AnswerApproach,
    ApproachFirm,
    CommissionDiligence,
    PutTerms,
    WalkAway,
)
from ptk.sim.mergers.models import Deal
from ptk.sim.mergers.profile import fit, rival_side
from ptk.sim.mergers.talks import bias, eligible

FROM_YM: Final = (2010, 1)
UNTIL_YM: Final = (2012, 12)
MAX_RATIO: Final = 6.0  # the other firm's lawyers at most this many times the player's
MIN_SHARE: Final = 2000  # bp of the merged pool the player's partners keep at least
MIN_COMPLEMENT: Final = 0.25  # share of its lawyers in practices the player lacks
LONDON: Final = "london"


def _decline_others(g: Game, keep: str | None) -> None:
    for d in g.state.mergers.open_deals():
        if d.initiator == "rival" and d.stage == "approached" and d.rival_key != keep:
            g.act(AnswerApproach(actor_id=g.founder_id, deal_id=d.id, accept=False))


def _ours(g: Game, form: str) -> Deal | None:
    return next(
        (d for d in g.state.mergers.open_deals() if d.initiator == "player" and d.form == form),
        None,
    )


def _pick_target(g: Game) -> str | None:
    me = len(g.lawyers())
    best: tuple[float, int, str] | None = None
    for f in g.state.rivals.active:
        if bias(f, "merger", g.balance) is None:
            continue
        if eligible(g.state, f, "merger", g.balance):
            continue
        ft = fit(g.state, f, g.data, g.balance)
        side = rival_side(f, g.data)
        if not ft.integrable or side.lawyers > MAX_RATIO * max(me, 1):
            continue
        if ft.fair_share_bp < MIN_SHARE or ft.complement < MIN_COMPLEMENT:
            continue
        score = ft.complement - abs(ft.rate_ratio - 1.0)
        if best is None or (score, -f.id) > (best[0], best[1]):
            best = (score, -f.id, f.key)
    return best[2] if best else None


def _terms(g: Game, deal: Deal, share: int) -> bool:
    fp = g.state.partnership.of(1)
    system = fp.agreement.comp_system if fp is not None else "modified_lockstep"
    return g.act(
        PutTerms(
            actor_id=g.founder_id,
            deal_id=deal.id,
            our_share_bp=share,
            name="combined",
            mp="ours",
            comp_system=system,
            rates="blend",
        )
    )


def merger_moves(g: Game) -> None:
    deal = _ours(g, "merger")
    _decline_others(g, deal.rival_key if deal else None)
    if g.state.mergers.integrations or not FROM_YM <= g.ym <= UNTIL_YM:
        return
    mp = g.founder_id
    if deal is None:
        key = _pick_target(g)
        if key is not None:
            g.act(ApproachFirm(actor_id=mp, rival_key=key, form="merger"))
        return
    firm = g.state.rivals.firm(deal.rival_id)
    if firm is None:
        return
    if deal.stage == "talks" and deal.diligence_level == 0 and deal.diligence_due_turn is None:
        g.act(CommissionDiligence(actor_id=mp, deal_id=deal.id))
    elif deal.stage == "talks" and deal.diligence_due_turn is None:
        _terms(g, deal, fit(g.state, firm, g.data, g.balance).fair_share_bp)
    elif deal.stage == "countered":
        counter = deal.counter_share_bp or 0
        if counter >= MIN_SHARE:
            _terms(g, deal, counter)
        else:
            g.act(WalkAway(actor_id=mp, deal_id=deal.id))


def verein_moves(g: Game) -> None:
    deal = _ours(g, "verein")
    _decline_others(g, deal.rival_key if deal else None)
    if g.state.mergers.vereins or g.ym < FROM_YM:
        return
    mp = g.founder_id
    if deal is None:
        london = [
            f
            for f in g.state.rivals.active
            if g.data.geo.city_key(f.hq) == LONDON
            and bias(f, "verein", g.balance) is not None
            and not eligible(g.state, f, "verein", g.balance)
        ]
        london.sort(key=lambda f: (-(bias(f, "verein", g.balance) or 0.0), f.id))
        if london:
            g.act(ApproachFirm(actor_id=mp, rival_key=london[0].key, form="verein"))
        return
    if deal.stage in ("talks", "countered"):
        _terms(g, deal, 5000)  # tunable-exempt: a verein's terms carry no points ratio


def merger(g: Game) -> None:
    from ptk.balance.strategies import steady  # registered there (no import cycle)

    merger_moves(g)  # before steady's moves spend the month's energy
    steady(g)


def verein(g: Game) -> None:
    from ptk.balance.strategies import steady

    verein_moves(g)
    steady(g)


MERGER_VARIANTS: Final = {"merger": merger, "verein": verein}
