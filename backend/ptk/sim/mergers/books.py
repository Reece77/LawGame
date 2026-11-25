"""The other firm's books (ADR PT-0016 2): its fixed hidden values, its client book (drawn when
talks open) and its closing balance sheet (from its run-rates in the month it is read).

Every sheet balances by construction: capital is the figure that makes assets equal
liabilities plus capital. The book is fixed for a deal; its shares sum to 1.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np

from ptk.sim.data_models import Balance, GameData
from ptk.sim.matters.market import client_weight
from ptk.sim.matters.models import Client
from ptk.sim.mergers import streams
from ptk.sim.mergers.models import BookClient, Sheet
from ptk.sim.mergers.profile import annualised, round_pools
from ptk.sim.rivals.models import RivalFirm
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState

DAYS = 365  # tunable-exempt: days in a year
MONTHS = 12  # tunable-exempt: months in a year
RANGES = 4  # tunable-exempt: quality, annuities, leases, conflicts (the offsets' order)


@dataclass(frozen=True, slots=True)
class Hidden:
    """A firm's fixed hidden values (stream `merger_target` at turn 0): never shown."""

    annuity_share: float
    lease_years: float
    offsets: tuple[float, ...]  # each range's offset in [-1, 1], times offset_share x h


def hidden(rng: RngFactory, firm: RivalFirm, balance: Balance) -> Hidden:
    cfg = balance.mergers.books
    gen = streams.target(rng, firm.rival_key)
    annuity = float(gen.uniform(cfg.annuity_share.lo, cfg.annuity_share.hi))
    lease = float(gen.uniform(cfg.lease_years.lo, cfg.lease_years.hi))
    offsets = tuple(float(gen.uniform(-1.0, 1.0)) for _ in range(RANGES))
    return Hidden(annuity, lease, offsets)


def lease_months(h: Hidden) -> int:
    return max(1, round(h.lease_years * MONTHS))


def market_city(state: GameState, city: str | None) -> str | None:
    """The `Client.city` of a modelled city's market ("" is the home market)."""
    if city is None:
        return None
    return "" if city == state.player.home_city else city


def monthly_costs(firm: RivalFirm, balance: Balance) -> int:
    extra = max(0, firm.offices - firm.base_offices)
    return round(
        (firm.lawyers * firm.cost_per_lawyer_cents + extra * balance.rivals.office_cost_cents)
        / MONTHS
    )


def monthly_rent(firm: RivalFirm, data: GameData, balance: Balance) -> int:
    lawyers = sum(e + q + a for _, e, q, a in round_pools(firm))
    city = data.geo.city_key(firm.hq)
    per_seat = (
        data.geo.city(city).rent_per_seat_cents
        if city is not None
        else balance.mergers.books.rent_per_seat_cents
    )
    return lawyers * per_seat


def sheet(firm: RivalFirm, rng: RngFactory, data: GameData, balance: Balance) -> Sheet:
    """The closing sheet now (ADR PT-0016 2's table)."""
    cfg = balance.mergers.books
    h = hidden(rng, firm, balance)
    revenue = annualised(firm.revenue)
    wip = revenue * cfg.wip_days // DAYS
    ar = revenue * cfg.ar_days // DAYS
    cash = round(cfg.cash_months * monthly_costs(firm, balance))
    leases = monthly_rent(firm, data, balance) * lease_months(h)
    annuities = round(h.annuity_share * (wip + ar))
    revolver = round(cfg.debt_share * (wip + ar))
    capital = wip + ar + cash - annuities - revolver
    if capital < 0:  # a firm whose claims exceed its assets borrows the rest
        revolver += capital
        capital = 0
    return Sheet(
        cash=cash,
        wip=wip,
        receivables=ar,
        right_of_use=leases,
        leases=leases,
        annuities=annuities,
        revolver=max(0, revolver),
        capital=capital,
    )


def _practices(
    client: Client, weights: dict[str, float], k: int, data: GameData, balance: Balance
) -> tuple[str, ...]:
    scored = sorted(
        (
            (-(weights.get(p, 0.0) * client_weight(client, p, data, balance)), p)
            for p in data.practice_keys
        ),
    )
    keep = {p for s, p in scored[:k] if s < 0}
    return tuple(p for p in data.practice_keys if p in keep)


def draw_book(
    state: GameState,
    deal_id: int,
    firm: RivalFirm,
    rng: RngFactory,
    data: GameData,
    balance: Balance,
) -> tuple[BookClient, ...]:
    """The clients whose panels carry its key first, then its city's market by wallet in its
    practices, until the book holds revenue / `book.client_cents` clients. With probability
    `book.adverse_p` each has an engagement adverse to another client of the market (the
    player's clients weigh `adverse_player_bias` times as much: firms in one market meet)."""
    cfg = balance.mergers.book
    gen = streams.book(rng, state.turn, deal_id)
    revenue = annualised(firm.revenue)
    k = max(3, min(cfg.max_clients, round(revenue / cfg.client_cents)))  # tunable-exempt: 3
    city = market_city(state, data.geo.city_key(firm.hq))
    clients = state.market.clients
    mix = {p.practice: p.lawyers for p in firm.pools}
    panel = [c for c in clients if firm.key in c.panel][:k]
    chosen = {c.id for c in panel}
    pool = [c for c in clients if c.id not in chosen and (city is None or c.city == city)]
    if city is None:  # outside the modelled cities: the home market stands in
        pool = [c for c in pool if c.city == ""]
    weights = np.array(
        [sum(mix.get(p, 0.0) * client_weight(c, p, data, balance) for p in mix) for c in pool]
    )
    extra = min(k - len(panel), int((weights > 0).sum()))
    picked: list[Client] = list(panel)
    if extra > 0 and weights.sum() > 0:
        idx = gen.choice(len(pool), size=extra, replace=False, p=weights / weights.sum())
        picked += [pool[int(j)] for j in sorted(idx)]
    picked.sort(key=lambda c: c.id)
    ours = {r.client_id for r in state.market.relationships if r.firm_id == state.player.id}
    book_ids = {c.id for c in picked}
    others = [c for c in clients if c.id not in book_ids and c.id != 0]
    adverse_w = np.array([cfg.adverse_player_bias if c.id in ours else 1.0 for c in others])
    out: list[BookClient] = []
    sizes: list[float] = []
    for c in picked:
        practices = _practices(c, mix, cfg.practices_per_client, data, balance)
        score = float(gen.uniform(cfg.relationship.lo, cfg.relationship.hi))
        adverse = None
        if float(gen.random()) < cfg.adverse_p and others:
            adverse = others[int(gen.choice(len(others), p=adverse_w / adverse_w.sum()))].id
        size = sum(client_weight(c, p, data, balance) for p in practices) or 1e-9
        sizes.append(size)
        out.append(BookClient(c.id, score, practices, 0.0, adverse))
    kept = [(b, s) for b, s in zip(out, sizes, strict=True) if b.practices]
    total = sum(s for _, s in kept) or 1.0
    return tuple(replace(b, share=s / total) for b, s in kept)


def split_exact(total: int, shares: list[float]) -> list[int]:
    """`total` split by `shares` in whole cents, the remainder to the largest parts (exact)."""
    if not shares:
        return []
    s = sum(shares) or 1.0
    raw = [total * x / s for x in shares]
    out = [int(v) for v in raw]
    left = total - sum(out)
    order = sorted(range(len(raw)), key=lambda i: (-(raw[i] - out[i]), i))
    for i in order[: max(0, left)]:
        out[i] += 1
    return out
