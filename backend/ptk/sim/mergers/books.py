"""The other firm's books (ADR PT-0016 2): its fixed hidden values, its client book (drawn when
talks open) and its closing balance sheet (from its run-rates in the month it is read).

Every sheet balances by construction: capital is the figure that makes assets equal
liabilities plus capital. The book is fixed for a deal; its shares sum to 1.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np

from ptk.sim.data_models import Balance, GameData
from ptk.sim.matters.market import Wallets, client_weight, wallets
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


def expected_fees(
    state: GameState,
    client: Client,
    practices: tuple[str, ...],
    score: float,
    without: str,
    data: GameData,
    balance: Balance,
    shares: Wallets | None = None,
) -> float:
    """A year of work the player's firm can expect from a client it would hold at `score` in
    `practices`, the other firm (`without`) gone from its panel: the client's wallet x the
    firm's logit share (PT-M3a's intake, at last month's demand, no conflicts, the firm's card at
    the market's)."""
    from ptk.sim.matters.market import base_monthly_demand, firm_reputation, player_share
    from ptk.sim.matters.models import Relationship

    demand = state.market.demand_cents or base_monthly_demand(data)
    if client.city:
        demand = state.geo.city_demand(client.city) or demand
    shares = shares or wallets(state.market.clients, data, balance)
    appeals = dict(state.rivals.appeals) or None
    solo = replace(client, panel=tuple(k for k in client.panel if k != without))
    rel = Relationship(
        client_id=client.id,
        firm_id=state.player.id,
        score=score,
        partner_id=None,
        practices=practices,
        since_turn=state.turn,
    )
    keys = data.practice_keys
    total = 0.0
    for p in practices:
        rep = firm_reputation(state, state.player.id, p, balance)
        share = player_share(solo, rel, p, rep, False, data, balance, appeals)
        total += shares.wallet(client.id, keys.index(p), demand) * MONTHS * share
    return total


def draw_book(
    state: GameState,
    deal_id: int,
    firm: RivalFirm,
    rng: RngFactory,
    data: GameData,
    balance: Balance,
) -> tuple[BookClient, ...]:
    """The clients whose panels carry its key first, then its city's market drawn by wallet in
    its practices, until the work the merged firm can expect from them (`expected_fees`)
    reaches `book.coverage` x its revenue (at most `book.max_clients`). With probability
    `book.adverse_p` each has an engagement adverse to another client of the market (the
    player's clients weigh `adverse_player_bias` times as much: firms in one market meet)."""
    cfg = balance.mergers.book
    gen = streams.book(rng, state.turn, deal_id)
    target = annualised(firm.revenue) * cfg.coverage
    city = market_city(state, data.geo.city_key(firm.hq))
    clients = state.market.clients
    mix = {p.practice: p.lawyers for p in firm.pools}
    panel = [c for c in clients if firm.key in c.panel]
    chosen = {c.id for c in panel}
    pool = [c for c in clients if c.id not in chosen and (city is None or c.city == city)]
    if city is None:  # outside the modelled cities: the home market stands in
        pool = [c for c in pool if c.city == ""]
    weights = np.array(
        [sum(mix.get(p, 0.0) * client_weight(c, p, data, balance) for p in mix) for c in pool]
    )
    order: list[Client] = list(panel)
    live = int((weights > 0).sum())
    if live > 0:
        idx = gen.choice(len(pool), size=live, replace=False, p=weights / weights.sum())
        order += [pool[int(j)] for j in idx]
    ours = {r.client_id for r in state.market.relationships if r.firm_id == state.player.id}
    shares = wallets(clients, data, balance)
    lawyers = sum(mix.values()) or 1.0
    # each practice's work is sized to its share of the firm's lawyers (the book is the work
    # its people do)
    left = {p: target * n / lawyers for p, n in mix.items() if n > 0}
    picked: list[tuple[Client, tuple[str, ...], float, float]] = []
    for c in order:
        if len(picked) >= cfg.max_clients or all(v <= 0 for v in left.values()):
            break
        open_ = [p for p in data.practice_keys if left.get(p, 0.0) > 0]
        practices = tuple(
            p
            for p in sorted(
                open_, key=lambda p: (-(left[p] * client_weight(c, p, data, balance)), p)
            )[: cfg.practices_per_client]
            if client_weight(c, p, data, balance) > 0
        )
        if not practices:
            continue
        practices = tuple(p for p in data.practice_keys if p in practices)
        score = float(gen.uniform(cfg.relationship.lo, cfg.relationship.hi))
        fees = expected_fees(state, c, practices, score, firm.key, data, balance, shares)
        if fees <= 0:
            continue
        picked.append((c, practices, score, fees))
        for p in practices:
            left[p] -= fees / len(practices)
    picked.sort(key=lambda x: x[0].id)
    book_ids = {c.id for c, _, _, _ in picked}
    others = [c for c in clients if c.id not in book_ids]
    adverse_w = np.array([cfg.adverse_player_bias if c.id in ours else 1.0 for c in others])
    total = sum(f for _, _, _, f in picked) or 1.0
    out: list[BookClient] = []
    for c, practices, score, fees in picked:
        adverse = None
        if float(gen.random()) < cfg.adverse_p and others:
            adverse = others[int(gen.choice(len(others), p=adverse_w / adverse_w.sum()))].id
        out.append(BookClient(c.id, score, practices, fees / total, adverse))
    return tuple(out)


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
