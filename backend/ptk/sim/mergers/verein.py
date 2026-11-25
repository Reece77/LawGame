"""The verein (TST formulas.md 31, re-cast; spec 8.8; ADR PT-0016 5).

Member firms share a brand and keep their own books, partners and profit pools. Each month the
verein's costs, `verein.cost_base_cents` + `verein.cost_bp` x the members' monthly revenue, are
split by revenue share: the player's share posts to its own ledger (6900 against cash), a rival
member's to its own (6900 against its drawings, so its cash stays zero and its profit, its PEP,
falls by its share). No entry carries two members.

Shared: referrals (every `referral_months` a member introduces the player's firm to one of its
panel clients, stream `verein`, at a score in `referral_score`), reach (no reach penalty in a
member's city; `appeal_share` points per member there instead: a London member opens London
without an office) and conflicts (a member's panel clients are checked as the firm's own).
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from ptk.sim.data_models import Balance, GameData
from ptk.sim.ledger import CASH, DRAWINGS, GENERAL_ADMIN, LedgerEntry
from ptk.sim.log import LogItem, inbox_item
from ptk.sim.matters.market import client_weight
from ptk.sim.mergers import streams
from ptk.sim.mergers.models import Deal, Verein, with_deal, with_verein
from ptk.sim.mergers.profile import annualised
from ptk.sim.mergers.talks import put_mergers
from ptk.sim.money import BP_DENOMINATOR
from ptk.sim.rivals.models import RivalFirm
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState

MONTHS = 12  # tunable-exempt
_CLIENTS: dict[int, tuple[object, frozenset[str], frozenset[int]]] = {}
_KEEP = 8  # tunable-exempt: memoised (a cache, not a rule)


def members(state: GameState) -> tuple[RivalFirm, ...]:
    keys = state.mergers.member_keys()
    return tuple(f for f in state.rivals.active if f.key in keys)


def verein_clients(state: GameState, firm_id: int) -> frozenset[int]:
    """The members' panel clients (the player's firm's conflicts check them as its own)."""
    if firm_id != state.player.id or not state.mergers.vereins:
        return frozenset()
    keys = frozenset(f.key for f in members(state))
    clients = state.market.clients
    hit = _CLIENTS.get(firm_id)
    if hit is not None and hit[0] is clients and hit[1] == keys:
        return hit[2]
    out = frozenset(c.id for c in clients if keys.intersection(c.panel))
    if len(_CLIENTS) >= _KEEP:
        _CLIENTS.clear()
    _CLIENTS[firm_id] = (clients, keys, out)
    return out


def member_city_counts(state: GameState, firm_id: int, data: GameData) -> dict[str, int]:
    if firm_id != state.player.id or not state.mergers.vereins:
        return {}
    out: dict[str, int] = {}
    for f in members(state):
        city = data.geo.city_key(f.hq)
        if city is not None:
            out[city] = out.get(city, 0) + 1
    return out


def join(
    state: GameState, deal: Deal, rng: RngFactory, data: GameData, balance: Balance
) -> tuple[GameState, tuple[LogItem, ...]]:
    """Closing a verein deal: the member joins (the verein is formed with the first)."""
    from ptk.sim.geo.markets import make_city_clients
    from ptk.sim.mergers.clearance import clear

    firm = state.rivals.firm(deal.rival_id)
    assert firm is not None
    state, deal, logs = clear(state, deal, rng, balance)
    ms = state.mergers
    v = ms.verein
    if v is None:
        short = state.player.name.split()[0]
        v = Verein(
            id=len(ms.vereins) + 1, name=f"{short} {firm.short}", formed_turn=state.turn, members=()
        )
    v = replace(v, members=tuple(sorted((*v.members, (firm.key, state.turn)))))
    ms = with_verein(ms, v)
    deal = replace(deal, stage="closed", stage_turn=state.turn, ended_turn=state.turn)
    state = put_mergers(state, with_deal(ms, deal))
    city = data.geo.city_key(firm.hq)
    if city is not None and city != state.player.home_city:
        state = make_city_clients(state, city, rng, data, balance)
    log = inbox_item(
        state.turn,
        state.player.id,
        "verein_joined",
        link_kind="mergers",
        link_id=deal.id,
        firm=firm.name,
        verein=v.name,
    )
    return state, (*logs, log)


def costs(
    state: GameState, player_revenue_cents: int, balance: Balance
) -> tuple[GameState, tuple[LedgerEntry, ...]]:
    """Phase 6: each member pays its share of the month's shared costs from its own books."""
    v = state.mergers.verein
    mem = members(state)
    if v is None or not mem:
        return state, ()
    cfg = balance.mergers.verein
    revenues = [(state.player.id, max(0, player_revenue_cents // MONTHS))] + [
        (f.id, max(0, annualised(f.revenue) // MONTHS)) for f in mem
    ]
    total = sum(r for _, r in revenues)
    cost = cfg.cost_base_cents + total * cfg.cost_bp // BP_DENOMINATOR
    if total <= 0 or cost <= 0:
        return state, ()
    from ptk.sim.mergers.books import split_exact

    shares = split_exact(cost, [r / total for _, r in revenues])
    entries: list[LedgerEntry] = []
    rivals = state.rivals
    for (fid, _), amount in zip(revenues, shares, strict=True):
        if amount <= 0:
            continue
        if fid == state.player.id:
            entries.append(
                LedgerEntry.transfer(
                    turn=state.turn,
                    firm_id=fid,
                    memo=f"{v.name}: the verein's shared costs",
                    debit=GENERAL_ADMIN,
                    credit=CASH,
                    amount=amount,
                )
            )
            v = replace(v, costs_cents=v.costs_cents + amount)
        else:
            entries.append(
                LedgerEntry.transfer(
                    turn=state.turn,
                    firm_id=fid,
                    memo=f"{v.name}: the verein's shared costs",
                    debit=GENERAL_ADMIN,
                    credit=DRAWINGS,
                    amount=amount,
                )
            )
            f = rivals.firm(fid)
            if f is not None and f.profit:
                f = replace(f, profit=(*f.profit[:-1], f.profit[-1] - amount))
                rivals = replace(rivals, firms=tuple(f if x.id == fid else x for x in rivals.firms))
    state = replace(state, rivals=rivals)
    return put_mergers(state, with_verein(state.mergers, v)), tuple(entries)


def referrals(
    state: GameState, rng: RngFactory, data: GameData, balance: Balance
) -> tuple[GameState, tuple[LogItem, ...]]:
    """Phase 9: each member, every `referral_months` since joining, introduces a client."""
    from ptk.sim.matters.intake import with_relationship
    from ptk.sim.matters.models import Relationship
    from ptk.sim.mergers.profile import player_side

    v = state.mergers.verein
    if v is None:
        return state, ()
    cfg = balance.mergers.verein
    pid = state.player.id
    held = [p for p, _ in player_side(state, data, balance).practices]
    if not held:
        return state, ()
    joined = dict(v.members)
    logs: list[LogItem] = []
    for f in members(state):
        since = state.turn - joined[f.key]
        if since <= 0 or since % cfg.referral_months != 0:
            continue
        ours = {r.client_id for r in state.market.relationships if r.firm_id == pid}
        pool = [c for c in state.market.clients if f.key in c.panel and c.id not in ours]
        if not pool:
            continue
        gen = streams.verein(rng, state.turn, v.id, f.id)
        weights = np.array([sum(client_weight(c, p, data, balance) for p in held) for c in pool])
        if weights.sum() <= 0:
            continue
        client = pool[int(gen.choice(len(pool), p=weights / weights.sum()))]
        practice = max(held, key=lambda p: (client_weight(client, p, data, balance), p))
        rel = Relationship(
            client_id=client.id,
            firm_id=pid,
            score=float(gen.uniform(cfg.referral_score.lo, cfg.referral_score.hi)),
            partner_id=state.founder_of(pid),
            practices=(practice,),
            since_turn=state.turn,
        )
        state = replace(state, market=with_relationship(state.market, rel))
        logs.append(
            inbox_item(
                state.turn,
                pid,
                "verein_referral",
                link_kind="client",
                link_id=client.id,
                firm=f.name,
                client=client.name,
            )
        )
    return state, tuple(logs)
