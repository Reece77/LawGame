"""Rivals merging with each other after history (PT-M13; ADR PT-0008 2, PT-0015, PT-0016 7).

Before 2026 rivals merge only as history did (`ptk.sim.rivals.history`). From January 2026, in
each quarter's first month, one uniform (stream `rival_merger`, key (1,)) below
`mergers.rival.free_rate_bp` brings one merger: the buyer is drawn among active rivals of the
buying personalities weighted by revenue, the target is the active rival at most
`free_max_ratio` of its lawyers (PT-M18, T15: and of its last 12 months' fees, so no deal makes a
firm more than 1.5 times its size) whose practices complement it most (ties by id). The target's
pools, demand and key people join the buyer; its key leaves every panel for the buyer's. A
member of the player's verein, or a firm in talks with the player, is never a target.
"""

from __future__ import annotations

from collections.abc import Sequence
from collections.abc import Set as AbstractSet
from dataclasses import replace

from simcore.kernel.calendar import turn_to_ym

from ptk.sim.data_models import Balance
from ptk.sim.mergers import streams
from ptk.sim.rivals.history import _add_pools, _move, record, replace_panel_key, with_firm
from ptk.sim.rivals.models import RivalFirm, RivalMove
from ptk.sim.state import GameState
from ptk.sim.streams import RngFactory

FREE_FROM_YEAR = 2026  # tunable-exempt: ADR PT-0008 2's pin ends in December 2025
QUARTER_MONTHS = (1, 4, 7, 10)  # tunable-exempt: calendar


def _complement(buyer: RivalFirm, target: RivalFirm) -> float:
    have = {p.practice for p in buyer.pools if p.lawyers >= 2.0}  # tunable-exempt: as profile
    total = max(target.lawyers, 1e-9)
    return sum(p.lawyers for p in target.pools if p.practice not in have) / total


def free_targets(
    buyer: RivalFirm, active: Sequence[RivalFirm], busy: AbstractSet[str], ratio: float
) -> list[RivalFirm]:
    """The firms a free-play buyer may take: at most `ratio` of its lawyers and (PT-M18, T15)
    of its last 12 months' fees, neither in the player's verein nor in talks with the player."""
    return [
        f
        for f in active
        if f.id != buyer.id
        and f.key not in busy
        and f.lawyers <= ratio * buyer.lawyers
        and f.revenue_12m <= ratio * buyer.revenue_12m
    ]


def free_play(
    state: GameState, rng: RngFactory, balance: Balance
) -> tuple[GameState, tuple[RivalMove, ...]]:
    ym = turn_to_ym(state.turn, state.save_meta.start_ym)
    if ym[0] < FREE_FROM_YEAR or ym[1] not in QUARTER_MONTHS:
        return state, ()
    cfg = balance.mergers.rival
    gen = streams.rival_merger(rng, state.turn, 1)
    if float(gen.random()) * 10_000 >= cfg.free_rate_bp:
        return state, ()
    rivals = state.rivals
    busy = state.mergers.member_keys() | {d.rival_key for d in state.mergers.open_deals()}
    buyers = [
        f for f in rivals.active if f.personality in cfg.free_personalities and f.key not in busy
    ]
    weights = [max(f.revenue_12m, 1) for f in buyers]
    if not buyers:
        return state, ()
    u = float(gen.random()) * sum(weights)
    buyer = buyers[-1]
    for f, w in zip(buyers, weights, strict=True):
        if u < w:
            buyer = f
            break
        u -= w
    targets = free_targets(buyer, rivals.active, busy, cfg.free_max_ratio)
    if not targets:
        return state, ()
    target = max(targets, key=lambda f: (_complement(buyer, f), -f.id))
    grown = _add_pools(buyer, target, 1.0)
    grown = replace(
        grown,
        demand_cents=buyer.demand_cents + target.demand_cents,
        offices=buyer.offices + target.offices,
        base_offices=buyer.base_offices + target.offices,
        revenue=tuple(x + y for x, y in zip(buyer.revenue, target.revenue, strict=False)),
        profit=tuple(x + y for x, y in zip(buyer.profit, target.profit, strict=False)),
    )
    rivals = with_firm(rivals, grown)
    rivals = with_firm(
        rivals, replace(target, status="merged", ended_turn=state.turn, successor=buyer.key)
    )
    for m in rivals.members_of(target.id):
        rivals = _move(rivals, m.person_id, buyer.id, state.turn)
    rivals, move = record(
        rivals,
        target,
        state.turn,
        "merged",
        f"{target.name} merges into {buyer.name}",
        other=buyer.id,
    )
    market = replace_panel_key(state.market, target.key, buyer.key)
    return replace(state, rivals=rivals, market=market), (move,)
