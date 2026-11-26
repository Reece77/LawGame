"""Rival decisions (spec 10.2; TST formulas.md 15.3's utility AI): one or two actions a month.

Each active rival, in id order, draws from its own generator (stream `rival_firm`, key
`(*rival_key,)`) in this order: the demand shock (economy.update_demand), one N(0, 0.1) per
action in RIVAL_ACTIONS order, then the draws of the actions it takes, in the order taken.
U(a) = need(a) x weight(personality, a) + noise; actions on cooldown or with no need are not
candidates; the best runs, and the second best too if its U is at least
`rivals.second_action_min`. Every action is a `RivalMove` (news, cooldowns, the decision log);
replay recomputes them from the state (ADR-0015 section 5).

While pinned, actions steer toward the path: hiring and layoffs move headcount toward the
path's lawyers, rate moves toward its revenue per lawyer. Laterals between rivals, team
lifts and new offices move demand only in free play (the path already holds history's).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ptk.sim.fastcopy import replace
from ptk.sim.rivals import formulas as f
from ptk.sim.rivals.data import RIVAL_ACTIONS
from ptk.sim.rivals.economy import Month, rate_gap, target_lawyers
from ptk.sim.rivals.models import Pool, RivalFirm

NEWSLESS = frozenset({"hire_associates"})  # tunable-exempt: routine actions, not market news


@dataclass(frozen=True, slots=True)
class Choice:
    action: str
    utility: float
    need: float


def needs(firm: RivalFirm, month: Month, approach_target: bool) -> dict[str, float]:
    rb = month.balance.rivals
    pinned = month.pinned(firm)
    lawyers = max(firm.lawyers, 1.0)
    gap = (target_lawyers(firm, month) - lawyers) / lawyers
    rg = rate_gap(firm, month)
    margin = firm.profit_12m / firm.revenue_12m if firm.revenue_12m > 0 else 0.0
    last = firm.history[-1] if firm.history else None
    pep_now = firm.profit_12m / max(firm.equity_partners, 1.0)
    pep_falling = (
        last is not None and last.pep_cents > 0 and pep_now < rb.de_equitise_pep * last.pep_cents
    )
    out = {
        "raise_rates": f.need_gap(rg, rb.rate_need_span),
        "cut_rates": f.need_gap(-rg, rb.rate_need_span),
        "hire_associates": f.need_gap(gap, rb.hire_span),
        "hire_lateral": 0.5 * f.need_gap(gap, rb.hire_span),
        "lift_team": 0.0 if pinned else (0.6 if gap > rb.hire_span else 0.0),
        "approach_player": rb.approach_need if approach_target else 0.0,
        "open_office": 0.0
        if pinned
        else (
            0.3 if lawyers / max(firm.offices, 1) > 150 else 0.0
        ),  # tunable-exempt: lawyers an office holds [A]
        "cut_costs": max(
            f.need_gap(-gap, rb.hire_span), 0.6 if margin < rb.cut_costs_margin else 0.0
        ),
        "de_equitise": 0.7 if pep_falling else 0.0,
    }
    return out


def choose(
    firm: RivalFirm, month: Month, gen: np.random.Generator, approach_target: bool
) -> list[Choice]:
    rb = month.balance.rivals
    weights = month.personality(firm).weights
    need = needs(firm, month, approach_target)
    scored: list[Choice] = []
    for action in RIVAL_ACTIONS:  # one noise draw per action, always, in this order
        noise = float(gen.normal(0.0, rb.noise_sd))
        n = need[action]
        if n <= 0.0 or firm.cooldown(action) > month.turn:
            continue
        scored.append(Choice(action, f.utility(n, weights.get(action, 0.0), noise), n))
    scored.sort(key=lambda c: (-c.utility, RIVAL_ACTIONS.index(c.action)))
    picked = scored[:1]
    if len(scored) > 1 and rb.actions_per_month > 1 and scored[1].utility >= rb.second_action_min:
        picked.append(scored[1])
    return [c for c in picked if c.utility > 0]


def with_cooldown(firm: RivalFirm, action: str, month: Month) -> RivalFirm:
    months = month.balance.rivals.cooldown_months.get(action, 0)
    rest = tuple((a, t) for a, t in firm.cooldowns if a != action)
    return replace(firm, cooldowns=tuple(sorted((*rest, (action, month.turn + months)))))


# --- Pools ------------------------------------------------------------------------------------


def grow(firm: RivalFirm, n: float, month: Month) -> RivalFirm:
    """Add n lawyers in the personality's shape (laterals and promotions keep it), spread
    over practices by current size."""
    pdef = month.personality(firm)
    total = firm.lawyers or 1.0
    pools = tuple(
        Pool(
            practice=p.practice,
            equity=p.equity + n * pdef.equity_share * p.lawyers / total,
            partners=p.partners + n * (pdef.partner_share - pdef.equity_share) * p.lawyers / total,
            associates=p.associates + n * (1 - pdef.partner_share) * p.lawyers / total,
        )
        for p in firm.pools
    )
    return replace(firm, pools=pools)


def shrink(firm: RivalFirm, n: float) -> RivalFirm:
    """Lay off n lawyers, associates first (counsel and partners when associates run out)."""
    total_assoc = sum(p.associates for p in firm.pools)
    take_assoc = min(n, total_assoc * 0.9)  # tunable-exempt: keep a tenth of associates
    rest = n - take_assoc
    total_partners = sum(p.partners for p in firm.pools) or 1.0
    pools = tuple(
        Pool(
            practice=p.practice,
            equity=p.equity,
            partners=max(0.0, p.partners - rest * p.partners / total_partners),
            associates=max(
                0.0,
                p.associates - (take_assoc * p.associates / total_assoc if total_assoc else 0.0),
            ),
        )
        for p in firm.pools
    )
    return replace(firm, pools=pools)


def add_partner(firm: RivalFirm, practice: str, equity: bool = True, n: float = 1.0) -> RivalFirm:
    pools = tuple(
        replace(p, equity=p.equity + n)
        if p.practice == practice and equity
        else replace(p, partners=p.partners + n)
        if p.practice == practice
        else p
        for p in firm.pools
    )
    return replace(firm, pools=pools)


def remove_lawyer(firm: RivalFirm, practice: str, partner: bool) -> RivalFirm:
    """One lawyer leaves a practice pool (a key person moving or retiring)."""
    pools = []
    for p in firm.pools:
        if p.practice != practice:
            pools.append(p)
        elif partner and p.equity >= 1.0:
            pools.append(replace(p, equity=p.equity - 1.0))
        elif partner and p.partners >= 1.0:
            pools.append(replace(p, partners=p.partners - 1.0))
        else:
            pools.append(replace(p, associates=max(0.0, p.associates - 1.0)))
    return replace(firm, pools=tuple(pools))


def strongest_practice(firm: RivalFirm) -> str:
    return max(firm.pools, key=lambda p: (p.lawyers, p.practice)).practice


# --- Actions (each returns the firm and the news words) ---------------------------------------


def apply_simple(firm: RivalFirm, action: str, month: Month) -> tuple[RivalFirm, str]:
    """The actions that touch only the firm itself."""
    rb = month.balance.rivals
    lawyers = max(firm.lawyers, 1.0)
    if action == "raise_rates":
        step = min(rb.rate_step, max(0.0, rate_gap(firm, month)))
        return replace(
            firm, rate_index=firm.rate_index * (1 + step)
        ), f"raised its rates {step:.0%}"
    if action == "cut_rates":
        step = min(rb.rate_step, max(0.0, -rate_gap(firm, month)))
        return replace(firm, rate_index=firm.rate_index * (1 - step)), f"cut its rates {step:.0%}"
    if action == "hire_associates":
        n = min(target_lawyers(firm, month) - lawyers, rb.hire_max_monthly * lawyers)
        return grow(firm, max(0.0, n), month), f"hired {round(max(0.0, n))} lawyers"
    if action == "cut_costs":
        n = min(max(0.0, lawyers - target_lawyers(firm, month)), rb.cut_max_monthly * lawyers)
        firm = shrink(firm, n)
        return firm, f"laid off {round(n)} lawyers" if n >= 1 else "cut costs"
    if action == "de_equitise":
        moved = 0.0
        pools = []
        for p in firm.pools:
            d = p.equity * 0.05  # tunable-exempt: a de-equitisation round moves 5%
            moved += d
            pools.append(replace(p, equity=p.equity - d, partners=p.partners + d))
        return replace(firm, pools=tuple(pools)), f"de-equitised {round(moved)} partners"
    if action == "open_office":
        demand = firm.demand_cents
        if not month.pinned(firm):
            demand *= 1 + rb.office_demand
        return replace(firm, offices=firm.offices + 1, demand_cents=demand), "opened an office"
    if action == "hire_lateral":
        practice = strongest_practice(firm)
        firm = add_partner(firm, practice)
        if not month.pinned(firm):
            firm = replace(
                firm,
                demand_cents=firm.demand_cents + rb.lateral_book_cents * rb.lateral_portability,
            )
        label = month.data.practice(practice).label
        return firm, f"hired a lateral {label.lower()} partner"
    raise ValueError(action)
