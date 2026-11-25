"""Both sides of a combination in one shape (spec 8.8): lawyers by practice, revenue, profit,
equity partners, PEP, comp system, region and rate card; and the target list's fit view.

The player's figures are its partnership's trailing twelve months (PT-M4's P&L points); a
rival's are its run-rates (PT-M5's economy). The fit view reads only what the player may see:
public figures (revenue, lawyers, PEP, offices, practices), never hidden values.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ptk.sim.data_models import Balance, GameData
from ptk.sim.rivals.models import RivalFirm
from ptk.sim.state import GameState

MONTHS = 12  # tunable-exempt: months in a year
# A rival's comp system from its personality (firms.yaml's comp texts are [A] labels; spec 8.5)
COMP_OF: dict[str, str] = {
    "elite_lockstep": "lockstep",
    "performance_machine": "eat_what_you_kill",
    "global_verein": "committee",
    "regional_champion": "modified_lockstep",
    "volume_mid_market": "modified_lockstep",
    "litigation_boutique": "eat_what_you_kill",
    "tech_coast": "modified_lockstep",
    "big_four_legal": "committee",
}


@dataclass(frozen=True, slots=True)
class Side:
    lawyers: int
    equity: int
    revenue_cents: int  # a year
    profit_cents: int  # a year
    practices: tuple[tuple[str, int], ...]  # (practice, lawyers), practices.yaml order
    comp_system: str
    region: str
    city: str | None  # a modelled city key (None: not modelled)
    rate_index: float

    @property
    def pep_cents(self) -> int:
        return self.profit_cents // max(1, self.equity)

    def practice_lawyers(self, practice: str) -> int:
        return next((n for p, n in self.practices if p == practice), 0)


def annualised(values: tuple[int, ...]) -> int:
    if not values:
        return 0
    return round(sum(values) * MONTHS / len(values))


def round_pools(firm: RivalFirm) -> tuple[tuple[str, int, int, int], ...]:
    """(practice, equity, other partners, associates) as whole lawyers: each pool rounded, at
    least one lawyer in a pool that holds one."""
    out = []
    for p in firm.pools:
        e, q, a = (max(0, round(x)) for x in (p.equity, p.partners, p.associates))
        if e + q + a == 0 and p.lawyers >= 0.5:  # tunable-exempt: half a lawyer rounds up
            a = 1
        out.append((p.practice, e, q, a))
    return tuple(out)


def rival_side(firm: RivalFirm, data: GameData) -> Side:
    from ptk.sim.geo.cities import rival_region

    pools = round_pools(firm)
    lawyers = sum(e + q + a for _, e, q, a in pools)
    equity = max(1, sum(e for _, e, _, _ in pools))
    return Side(
        lawyers=lawyers,
        equity=equity,
        revenue_cents=annualised(firm.revenue),
        profit_cents=annualised(firm.profit),
        practices=tuple((p, e + q + a) for p, e, q, a in pools),
        comp_system=COMP_OF.get(firm.personality, "modified_lockstep"),
        region=rival_region(data, firm.hq),
        city=data.geo.city_key(firm.hq),
        rate_index=firm.rate_index,
    )


def player_side(state: GameState, data: GameData, balance: Balance) -> Side:
    from ptk.sim.geo.cities import region_of_city
    from ptk.sim.partnership.common import home_practice, profit_12m, revenue_12m

    firm = state.player
    fp = state.partnership.of(firm.id)
    levels = balance.people.levels
    counts: dict[str, int] = {}
    for pid in state.staff_ids(firm.id):
        person = state.person(pid)
        if levels[person.level].kind != "lawyer":
            continue
        key = home_practice(person, data)
        counts[key] = counts.get(key, 0) + 1
    practices = tuple((k, counts[k]) for k in data.practice_keys if counts.get(k))
    return Side(
        lawyers=sum(counts.values()),
        equity=max(1, len(fp.equity_partners)) if fp is not None else 1,
        revenue_cents=revenue_12m(fp) if fp is not None else 0,
        profit_cents=profit_12m(fp) if fp is not None else 0,
        practices=practices,
        comp_system=fp.agreement.comp_system if fp is not None else "modified_lockstep",
        region=region_of_city(data, firm.home_city),
        city=firm.home_city,
        rate_index=firm.rate_index,
    )


def comp_distance(a: str, b: str, balance: Balance) -> float:
    if a == b:
        return 0.0
    table = balance.mergers.integration.clash_comp
    return table.get(a, {}).get(b, table.get(b, {}).get(a, 0.0))


def clash(ours: Side, theirs: Side, balance: Balance) -> float:
    """Culture distance 0-1: the comp systems' distance, plus `personality_distance` times the
    rate cards' gap (a premium firm and a volume firm are different places to work)."""
    cfg = balance.mergers.integration
    ratio = max(ours.rate_index, 1e-6) / max(theirs.rate_index, 1e-6)
    gap = min(1.0, abs(math.log(ratio)) * 5.0)  # tunable-exempt: a 20% card gap is the full term
    return min(
        1.0,
        comp_distance(ours.comp_system, theirs.comp_system, balance)
        + cfg.personality_distance * gap,
    )


def complement(ours: Side, theirs: Side) -> float:
    """Share of their lawyers in practices where ours has fewer than two."""
    if theirs.lawyers <= 0:
        return 0.0
    new = sum(n for p, n in theirs.practices if ours.practice_lawyers(p) < 2)  # tunable-exempt
    return new / theirs.lawyers


@dataclass(frozen=True, slots=True)
class Fit:
    complement: float  # share of their lawyers in practices the player lacks
    new_city: bool  # their headquarters is a city the player has no office in
    rate_ratio: float  # their card over the player's
    pep_ratio: float  # their PEP over the player's
    clash: float
    fair_share_bp: int  # the player's share of the two profit pools
    integrable: bool  # an integrated merger is possible (size, city)
    reason: str  # why not, when not


def fit(
    state: GameState, firm: RivalFirm, data: GameData, balance: Balance, ours: Side | None = None
) -> Fit:
    ours = ours or player_side(state, data, balance)
    theirs = rival_side(firm, data)
    total = max(ours.profit_cents, 0) + max(theirs.profit_cents, 0)
    fair = round(10_000 * max(ours.profit_cents, 0) / total) if total > 0 else 5_000
    reason = ""
    if theirs.lawyers > balance.mergers.max_lawyers:
        reason = f"more than {balance.mergers.max_lawyers} lawyers: a verein, not a merger"
    elif theirs.city is None:
        reason = "headquartered outside the cities the game models: a verein, not a merger"
    offices = {o.city for o in state.geo.firm_offices(state.player.id)}
    return Fit(
        complement=complement(ours, theirs),
        new_city=theirs.city is not None
        and theirs.city != state.player.home_city
        and theirs.city not in offices,
        rate_ratio=theirs.rate_index / max(ours.rate_index, 1e-6),
        pep_ratio=theirs.pep_cents / max(ours.pep_cents, 1),
        clash=clash(ours, theirs, balance),
        fair_share_bp=fair,
        integrable=not reason,
        reason=reason,
    )
