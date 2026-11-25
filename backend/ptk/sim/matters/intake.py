"""Monthly intake (spec 7.4; ADR PT-0004): clients instruct the firms on their panels.

For each client whose panel the firm sits on (by client id), and each practice it is
instructed in: the firm's fees this month are the client's wallet x the firm's wallet share.
A practice's `flow_share` of them is flow work. The rest arrives as discrete matters of the
practice's kinds: for a kind with LogNormal size (median, sigma) and mean size m, matters
arrive at rate F_k / m a month; those of at least the named threshold (`matters.named_min_cents`,
or `key_named_min_cents` for a key client) are drawn individually (Poisson count, size from
the LogNormal's tail), and the smaller ones' expected fees join the flow. Draws come from
stream `intake` keyed by the client, in practices.yaml then matter-kind order.

A client the firm is adverse to on an open matter sends no work until that matter ends (its
flow is suspended and its new matters would be conflicts: ADR PT-0009).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Final

import numpy as np

from ptk.sim import dmath
from ptk.sim.data_models import Balance, GameData, MatterKindDef, PracticeDef
from ptk.sim.interfaces import practice_leader_effect
from ptk.sim.log import LogItem, inbox_item
from ptk.sim.matters import formulas as fx
from ptk.sim.matters.conflicts import ConflictIndex, adverse_to, affected_client, conflict_index
from ptk.sim.matters.market import Wallets, firm_reputation, player_share, wallets
from ptk.sim.matters.models import Client, MarketState, Matter, Relationship
from ptk.sim.matters.rates import client_indexes, market_index
from ptk.sim.matters.staffing import staff_matter
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState

GOVERNMENT_PRACTICES: Final = frozenset({"white_collar"})
LONDON_COURT: Final = "ew_commercial"  # PT-M11: courts.yaml
OMP: Final = "office_managing_partner"  # PT-M11: seats.yaml
LONDON_ARBITRATION: Final = "lcia"
CASE_KINDS: Final = frozenset({"case", "investigation"})


@dataclass(frozen=True, slots=True)
class IntakeResult:
    state: GameState
    flow_tenths: dict[tuple[int, str], int]  # (client, practice) -> tenths of flow demanded
    flow_fees: dict[tuple[int, str], float]
    log: tuple[LogItem, ...]


def key_clients(market: MarketState, firm_id: int, balance: Balance) -> frozenset[int]:
    """Top `matters.key_clients` clients by trailing-12-month fees (ADR PT-0004 1)."""
    ranked = sorted(
        (r for r in market.relationships if r.firm_id == firm_id and r.fees_12m > 0),
        key=lambda r: (-r.fees_12m, r.client_id),
    )
    return frozenset(r.client_id for r in ranked[: balance.matters.key_clients])


def _pick_client(gen: np.random.Generator, clients: tuple[Client, ...], exclude: int) -> Client:
    """An adverse company drawn by size from the client universe."""
    weights = [0.0 if c.id == exclude else c.revenue_bn for c in clients]
    total = sum(weights)
    u = float(gen.random()) * total
    acc = 0.0
    for c, w in zip(clients, weights, strict=True):
        acc += w
        if u < acc:
            return c
    return clients[-1] if clients[-1].id != exclude else clients[0]


def _forum(gen: np.random.Generator, kind: MatterKindDef) -> str | None:
    if not kind.forums:
        float(gen.random())  # keep one draw per matter regardless of kind
        return None
    total = sum(kind.forums.values())
    u = float(gen.random()) * total
    acc = 0.0
    for key, w in kind.forums.items():
        acc += w
        if u < acc:
            return key
    return next(reversed(kind.forums))


def new_matter(
    matter_id: int,
    firm_id: int,
    client: Client,
    rel: Relationship,
    practice: PracticeDef,
    kind: MatterKindDef,
    size_cents: int,
    gen: np.random.Generator,
    market: MarketState,
    turn: int,
    data: GameData,
    balance: Balance,
    rate_index: float = 1.0,
    region: str = "us",
) -> Matter:
    """A named matter's intake draws, in a fixed order: months, critical, adverse, merits,
    opposing counsel, stakes, forum."""
    out = balance.outcomes
    months = int(gen.integers(kind.months[0], kind.months[1] + 1))
    critical = float(gen.random()) < kind.critical_bp / 10000
    adverse_roll = float(gen.random())
    adverse = _pick_client(gen, market.clients, client.id)
    merits = out.merits_sd * float(gen.standard_normal())
    opposing = min(
        20.0, max(1.0, out.opposing_mean + out.opposing_sd * float(gen.standard_normal()))
    )
    stakes_mult = float(gen.uniform(out.stakes_mult.lo, out.stakes_mult.hi))
    court = _forum(gen, kind)
    if court is not None and region == "uk":  # PT-M11: a London case's forum is London's
        arbitration = data.courts.court(court).kind == "arbitration"
        court = LONDON_ARBITRATION if arbitration else LONDON_COURT
    is_adverse_client = adverse_roll < practice.conflict_bp / 10000
    if is_adverse_client:
        adverse_name, adverse_id = adverse.name, adverse.id
    else:
        adverse_name = (
            "the government" if practice.key in GOVERNMENT_PRACTICES else "a non-client party"
        )
        adverse_id = None
    kind_def = data.market.kinds[kind.kind]
    rate = fx.blended_rate(practice, fx.kind_tasks(kind_def), data)
    hours = max(fx.TENTHS, round(size_cents * fx.TENTHS / rate))
    if court is not None:
        months = max(1, round(months * data.courts.court(court).pace))
    against = adverse_id is not None and kind.kind in CASE_KINDS
    label = f"{kind.label}, {adverse_name}" if against else kind.label
    return Matter(
        id=matter_id,
        firm_id=firm_id,
        client_id=client.id,
        practice=practice.key,
        kind_key=kind.key,
        kind=kind.kind,
        name=f"{client.name}: {label}",
        opened_turn=turn,
        planned_months=months,
        expected_fees_cents=size_cents if rate_index == 1.0 else round(size_cents * rate_index),
        hours_needed_tenths=hours,
        adverse_client_id=adverse_id,
        adverse_name=adverse_name,
        critical=critical,
        originator_id=rel.partner_id,
        court=court,
        stakes_cents=round(size_cents * stakes_mult) if kind.kind in CASE_KINDS else 0,
        merits=merits if kind_def.outcome == "case" else 0.0,
        opposing_quality=opposing if kind_def.outcome == "case" else 0.0,
    )


def _with_matter(market: MarketState, matter: Matter) -> MarketState:
    rest = [m for m in market.matters if m.id != matter.id]
    return replace(market, matters=tuple(sorted([*rest, matter], key=lambda m: m.id)))


def with_relationship(market: MarketState, rel: Relationship) -> MarketState:
    rest = [
        r for r in market.relationships if (r.client_id, r.firm_id) != (rel.client_id, rel.firm_id)
    ]
    merged = sorted([*rest, rel], key=lambda r: (r.client_id, r.firm_id))
    return replace(market, relationships=tuple(merged))


def bump(market: MarketState, client_id: int, firm_id: int, points: float) -> MarketState:
    rel = market.relationship(client_id, firm_id)
    if rel is None or points == 0:
        return market
    return with_relationship(market, replace(rel, score=min(100.0, max(0.0, rel.score + points))))


def open_checked(
    state: GameState,
    matter: Matter,
    index: ConflictIndex,
    data: GameData,
    balance: Balance,
    key: frozenset[int],
) -> tuple[GameState, tuple[LogItem, ...]]:
    """Run the conflicts check (ADR PT-0009) and open, hold or hide the matter."""
    firm = state.firm(matter.firm_id)
    market = state.market
    affected = affected_client(matter, index)
    logs: list[LogItem] = []
    if not firm.conflict_checks:
        matter = replace(matter, checked=False, hidden_conflict=affected is not None)
    elif affected is not None:
        matter = replace(matter, status="conflicted")
        market = bump(market, matter.client_id, firm.id, balance.relationships.conflict_refused)
        logs.append(
            inbox_item(
                state.turn,
                firm.id,
                "matter_conflicted",
                link_kind="matter",
                link_id=matter.id,
                matter=matter.name,
                affected=market.client(affected).name,
            )
        )
        return replace(state, market=_with_matter(market, matter)), tuple(logs)
    client = market.client(matter.client_id)
    for other in sorted(key):  # positional conflicts (ADR PT-0009 3)
        rival = market.client(other)
        if (
            other != client.id
            and rival.sector == client.sector
            and rival.size_class == "large" == client.size_class
        ):
            market = bump(market, other, firm.id, balance.relationships.positional)
    state = replace(state, market=_with_matter(market, matter))
    staffed = staff_matter(state, matter, data, balance)
    logs.append(
        inbox_item(
            state.turn,
            firm.id,
            "matter_opened",
            link_kind="matter",
            link_id=matter.id,
            matter=matter.name,
            fees_cents=matter.expected_fees_cents,
        )
    )
    return replace(state, market=_with_matter(state.market, staffed)), tuple(logs)


def intake(
    state: GameState,
    firm_id: int,
    rng: RngFactory,
    demand: tuple[int, ...],
    data: GameData,
    balance: Balance,
) -> IntakeResult:
    turn = state.turn
    market = state.market
    shares: Wallets = wallets(market.clients, data, balance, turn, state.save_meta.start_ym)
    key = key_clients(market, firm_id, balance)
    keys = data.practice_keys
    reps = {p: firm_reputation(state, firm_id, p, balance) for p in keys}
    appeals = dict(state.rivals.appeals) or None  # PT-M5: rival firms' live appeal
    from ptk.sim.mergers.verein import verein_clients

    shared = verein_clients(state, firm_id)  # PT-M13: conflicts across the verein
    flow_fees: dict[tuple[int, str], float] = {}
    logs: list[LogItem] = []
    named_min = balance.matters.named_min_cents
    # PT-M8 (spec 9.1): a practice group leader keeps the group's diary full
    k_pgl = balance.seats.effects.pgl_flow
    diary = {
        p: 1.0 + k_pgl * practice_leader_effect(state, firm_id, p, balance, data) for p in keys
    }
    # PT-M7a: the firm's card against the market's; PT-M7b: each practice's card
    # PT-M7c: each client's card by its tier, against what the market charges that tier
    tiers = client_indexes(state, state.firm(firm_id), balance)
    market_idx = market_index(turn, state.save_meta.start_ym, data, balance)

    def price(p: str, client: Client) -> float:
        return 1.0 - tiers(p, client.id) / (market_idx * tiers.reference(client.id))

    local = local_terms(state, firm_id, data, balance)  # PT-M11: each city's market
    for rel in [r for r in market.relationships if r.firm_id == firm_id]:
        client = state.market.client(rel.client_id)
        if adverse_to(state.market, firm_id, client.id):
            continue
        market_demand, reach, rate_f, region = (
            local(client.city) if client.city else (demand, 0.0, 1.0, "us")
        )
        gen = rng.stream(turn, "intake", client.id)
        threshold = balance.matters.key_named_min_cents if client.id in key else named_min
        instructed = False
        for p in rel.practices:
            practice = data.practice(p)
            fees = shares.wallet(client.id, keys.index(p), market_demand) * player_share(
                client, rel, p, reps[p], False, data, balance, appeals, price(p, client), reach
            )
            if fees <= 0:
                continue
            instructed = True
            flow = fees * practice.flow_share
            discrete = fees - flow
            total_w = sum(k.weight for k in practice.matter_kinds)
            for kind in practice.matter_kinds:
                f_k = discrete * kind.weight / total_w
                rate = f_k / fx.lognormal_mean(kind.median_cents, kind.sigma)
                p_tail, fee_tail, cdf = fx.tail_split(kind.median_cents, kind.sigma, threshold)
                flow += f_k * (1.0 - fee_tail)
                count = fx.poisson_from_uniform(rate * p_tail, float(gen.random()))
                for _ in range(count):
                    u = float(gen.uniform(cdf, 1.0))
                    z = dmath.normal_inv_cdf(min(max(u, 1e-12), 1 - 1e-12))
                    size = round(kind.median_cents * dmath.exp(kind.sigma * z))
                    matter = new_matter(
                        state.market.next_matter_id,
                        firm_id,
                        client,
                        rel,
                        practice,
                        kind,
                        size,
                        gen,
                        state.market,
                        turn,
                        data,
                        balance,
                        # PT-M7a: fees on the firm's card; PT-M7b: the practice's card;
                        # PT-M11: the city's card
                        tiers(p, client.id) * rate_f,
                        region,
                    )
                    index = conflict_index(state.market, firm_id, turn, balance, shared)
                    state, items = open_checked(state, matter, index, data, balance, key)
                    logs.extend(items)
            flow *= diary[p]
            flow_fees[(client.id, p)] = flow_fees.get((client.id, p), 0.0) + flow
        if instructed:
            current = state.market.relationship(client.id, firm_id)
            assert current is not None
            state = replace(
                state,
                market=with_relationship(state.market, replace(current, last_instructed_turn=turn)),
            )
    flow_tenths = {
        (cid, p): round(
            f * fx.TENTHS / fx.blended_rate(data.practice(p), data.market.flow_tasks, data)
        )
        for (cid, p), f in flow_fees.items()
    }
    return IntakeResult(state=state, flow_tenths=flow_tenths, flow_fees=flow_fees, log=tuple(logs))


type LocalTerms = tuple[tuple[int, ...], float, float, str]


def local_terms(
    state: GameState, firm_id: int, data: GameData, balance: Balance
) -> Callable[[str], LocalTerms]:
    """PT-M11: a city's (demand, reach penalty, rate factor, region) for its clients' work."""
    from ptk.sim.geo.cities import office_in
    from ptk.sim.geo.formulas import rate_factor
    from ptk.sim.mergers.verein import member_city_counts
    from ptk.sim.org.seats import effect as seat_effect

    zeros = tuple(0 for _ in data.practices)
    cache: dict[str, LocalTerms] = {}
    member_cities = member_city_counts(state, firm_id, data)

    def terms(city: str) -> LocalTerms:
        if city not in cache:
            cdef = data.geo.city(city)
            office = office_in(state, firm_id, city)
            members = member_cities.get(city, 0)  # PT-M13: a verein member's city
            if office is None and members:
                reach = -balance.mergers.verein.appeal_share * members
            elif office is None:
                reach = balance.geo.reach_penalty
            else:  # spec 9.1: the office managing partner's local business development
                e = seat_effect(state, firm_id, OMP, balance, data, office.id)
                reach = -balance.geo.omp_appeal * e
            cache[city] = (
                state.geo.city_demand(city) or zeros,
                reach,
                rate_factor(cdef),
                cdef.region,
            )
        return cache[city]

    return terms


def expire_conflicted(
    state: GameState, firm_id: int, balance: Balance
) -> tuple[GameState, tuple[LogItem, ...]]:
    """Conflicted instructions with no waiver in time are declined."""
    window = balance.matters.conflicted_window_turns
    logs = []
    market = state.market
    for m in market.matters:
        if (
            m.firm_id == firm_id
            and m.status == "conflicted"
            and state.turn - m.opened_turn >= window
        ):
            market = _with_matter(market, replace(m, status="declined", closed_turn=state.turn))
            logs.append(
                inbox_item(
                    state.turn,
                    firm_id,
                    "matter_declined",
                    link_kind="matter",
                    link_id=m.id,
                    matter=m.name,
                )
            )
    return replace(state, market=market), tuple(logs)


def with_matter(market: MarketState, matter: Matter) -> MarketState:
    return _with_matter(market, matter)
