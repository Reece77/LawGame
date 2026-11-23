"""Rivals on client panels (spec 7.1's appeal logit): each active rival's appeal by practice.

A_f,p = base + strength + price + capacity + people, where base is the firm's NY panel appeal
(firms.yaml `panel_base`, which is clients.yaml's for the static panel firms; others by size:
`appeal_size_base` + `appeal_size_slope` x log10(revenue / $100M), clamped; the curve passes
through the static panel firms' appeals for their sizes), strength is `appeal.rival_strong` in its
strong practices (for generated firms and boutiques, their two largest), price is
`rivals.appeal_price_weight` x (1 - rate index / the rivals' mean rate index), capacity is
minus `rivals.appeal_capacity_weight` x max(0, utilisation - 0.95), and people is
`rivals.appeal_rep_weight` x 20 x (key partners / its target - 1): a firm that loses its key
partners loses its clients' favour. Computed in phase 2; intake reads it (PT-M3a's
`player_share`), and so do RFP awards.
"""

from __future__ import annotations

import math
from dataclasses import replace

from ptk.sim.data_models import Balance, GameData
from ptk.sim.rivals.models import RivalFirm, RivalsState

FULL_CAPACITY = 0.95  # tunable-exempt: utilisation above which a firm turns work away
REP_SCALE = 20.0  # tunable-exempt: the attribute scale's span, converting a share to points


def base_appeal(firm: RivalFirm, data: GameData, balance: Balance) -> float:
    defs = {f.key: f for f in data.rivals.firms.firms}
    fdef = defs.get(firm.key)
    if fdef is not None and fdef.panel_base is not None:
        return fdef.panel_base
    revenue = max(firm.revenue_12m, 1)
    rb = balance.rivals
    size = rb.appeal_size_base + rb.appeal_size_slope * math.log10(revenue / 10_000_000_000)
    return min(rb.appeal_size_max, max(rb.appeal_size_min, size))


def strong_practices(firm: RivalFirm, data: GameData) -> frozenset[str]:
    defs = {f.key: f for f in data.rivals.firms.firms}
    fdef = defs.get(firm.key)
    if fdef is not None:
        return frozenset(fdef.strong)
    top = sorted(firm.pools, key=lambda p: (-p.lawyers, p.practice))[:2]
    return frozenset(p.practice for p in top)


def appeal_table(rivals: RivalsState, data: GameData, balance: Balance) -> RivalsState:
    from ptk.sim.geo.cities import rival_region

    rb = balance.rivals
    active = rivals.active
    # PT-M11: a firm's price against its own region's firms (v1: every firm is a US firm)
    region = {f.id: rival_region(data, f.hq) for f in active}
    sums: dict[str, list[float]] = {}
    for f in active:
        acc = sums.setdefault(region[f.id], [0.0, 0.0])
        acc[0] += f.rate_index
        acc[1] += 1.0
    means = {r: (v[0] / v[1] if v[1] else 1.0) for r, v in sums.items()}
    partners: dict[int, int] = {}
    for m in rivals.members:
        if m.kind == "partner":
            partners[m.firm_id] = partners.get(m.firm_id, 0) + 1
    out = []
    for f in active:
        base = base_appeal(f, data, balance)
        price = rb.appeal_price_weight * (1.0 - f.rate_index / means[region[f.id]])
        capacity = -rb.appeal_capacity_weight * max(0.0, f.utilisation - FULL_CAPACITY)
        people = 0.0
        if f.key_target > 0:
            people = rb.appeal_rep_weight * REP_SCALE * (partners.get(f.id, 0) / f.key_target - 1.0)
        strong = strong_practices(f, data)
        values = tuple(
            base + price + capacity + people + (balance.appeal.rival_strong if p in strong else 0.0)
            for p in data.practice_keys
        )
        out.append((f.key, values))
    return replace(rivals, appeals=tuple(sorted(out)))
