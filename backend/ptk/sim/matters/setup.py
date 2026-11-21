"""The client universe, judges and the founding partners' books at game creation (PT-M3a).

- Clients: clients.yaml's real 2005 clients (ids 1..n in file order), then
  `clients.generated_count` generated ones. Each draws, from stream `client_gen` keyed by its
  index: (generated only) sector, revenue and name; then its panel, price sensitivity,
  loyalty and general counsel.
- Judges: courts.yaml order, `judges` per court, from stream `judge_gen` keyed
  (court_index, n): a name and procedural traits.
- Books (spec 7.1): each founding partner with a book brings the clients it came from, from
  stream `book` keyed by founder index: clients drawn by their expected fees to the firm in
  the partner's practices, none above `books.max_client_share` of the book, until the
  expected fees reach the book. The firm joins those clients' panels with the partner as
  relationship partner.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final

import numpy as np

from ptk.sim import dmath
from ptk.sim.calendar import MONTHS_PER_YEAR
from ptk.sim.data_models import Balance, GameData
from ptk.sim.matters.market import base_monthly_demand, firm_reputation, player_share, wallets
from ptk.sim.matters.models import (
    Client,
    GeneralCounsel,
    Judge,
    JudgeTraits,
    MarketState,
    Relationship,
    SizeClass,
)
from ptk.sim.people.models import Person, Personality
from ptk.sim.rng import RngFactory
from ptk.sim.scale import ATTR_MAX, ATTR_MIN
from ptk.sim.state import GameState

SETUP_TURN: Final = 0
TRAIT_MEAN: Final = 10.0  # tunable-exempt: the 1-20 scale's centre
TRAIT_SD: Final = 3.5  # tunable-exempt: generated traits' spread, as people's personality
UNIQUE_TRIES: Final = 8  # tunable-exempt: name redraws before a numeral is added


def _clamp(v: float) -> float:
    return min(ATTR_MAX, max(ATTR_MIN, v))


def _pick(gen: np.random.Generator, items: Sequence[str]) -> str:
    return items[int(gen.integers(len(items)))]


def _weighted(gen: np.random.Generator, weights: dict[str, float]) -> str:
    keys = list(weights)
    total = sum(weights.values())
    u = float(gen.random()) * total
    acc = 0.0
    for k in keys:
        acc += weights[k]
        if u < acc:
            return k
    return keys[-1]


def client_gen_stream(rng: RngFactory, index: int) -> np.random.Generator:
    return rng.stream(SETUP_TURN, "client_gen", index)


def generate_clients(rng: RngFactory, data: GameData, balance: Balance) -> tuple[Client, ...]:
    cfg = balance.clients
    pool = data.names["us"]
    firms = [f.key for f in data.clients.panel_firms]
    taken: set[str] = {c.name for c in data.clients.real_clients}
    out: list[Client] = []
    n_real = len(data.clients.real_clients)
    for index in range(n_real + cfg.generated_count):
        gen = client_gen_stream(rng, index)
        if index < n_real:
            real = data.clients.real_clients[index]
            name, sector, revenue, country = real.name, real.sector, real.revenue_bn, real.country
        else:
            sector = _weighted(gen, data.clients.generated_sector_weights)
            span = cfg.generated_revenue_bn
            z = float(gen.standard_normal())
            revenue = min(span.max, max(span.min, span.median * dmath.exp(span.sigma * z)))
            revenue = round(revenue, 3)
            suffixes = data.clients.sector(sector).suffixes
            name = f"{_pick(gen, pool.last)} {_pick(gen, suffixes)}"
            tries = 0
            while name in taken and tries < UNIQUE_TRIES:
                name = f"{_pick(gen, pool.last)} {_pick(gen, suffixes)}"
                tries += 1
            if name in taken:
                name = f"{name} {index}"
            country = "us"
        taken.add(name)
        size_class: SizeClass = "large" if revenue >= cfg.large_revenue_bn else "mid"
        lo, hi = cfg.panel_large if size_class == "large" else cfg.panel_mid
        n_panel = int(gen.integers(lo, hi + 1))
        panel = tuple(sorted(str(k) for k in gen.choice(firms, size=n_panel, replace=False)))
        price = float(gen.uniform(cfg.price_sensitivity.lo, cfg.price_sensitivity.hi))
        loyalty = float(gen.uniform(cfg.loyalty.lo, cfg.loyalty.hi))
        age = int(gen.integers(cfg.gc_age[0], cfg.gc_age[1] + 1))
        gc = GeneralCounsel(
            first_name=_pick(gen, pool.first),
            last_name=_pick(gen, pool.last),
            birth_turn=SETUP_TURN - age * MONTHS_PER_YEAR - int(gen.integers(MONTHS_PER_YEAR)),
            personality=Personality.build(
                data.personality_keys,
                {
                    k: _clamp(TRAIT_MEAN + TRAIT_SD * float(gen.standard_normal()))
                    for k in data.personality_keys
                },
            ),
        )
        out.append(
            Client(
                id=index + 1,
                name=name,
                sector=sector,
                country=country,
                real=index < n_real,
                revenue_bn=revenue,
                size_class=size_class,
                price_sensitivity=price,
                loyalty=loyalty,
                gc=gc,
                panel=panel,
            )
        )
    return tuple(out)


def generate_judges(rng: RngFactory, data: GameData) -> tuple[Judge, ...]:
    pool = data.names["us"]
    keys = tuple(t.key for t in data.courts.judge_traits)
    out: list[Judge] = []
    for ci, court in enumerate(data.courts.courts):
        for n in range(court.judges):
            gen = rng.stream(SETUP_TURN, "judge_gen", ci, n)
            first, last = _pick(gen, pool.first), _pick(gen, pool.last)
            traits = {k: _clamp(TRAIT_MEAN + TRAIT_SD * float(gen.standard_normal())) for k in keys}
            out.append(
                Judge(
                    id=len(out) + 1,
                    court=court.key,
                    first_name=first,
                    last_name=last,
                    traits=JudgeTraits.build(keys, traits),
                )
            )
    return tuple(out)


def _book_practices(person: Person, data: GameData) -> tuple[str, ...]:
    background = data.background(person.background) if person.background else None
    chosen = set(background.familiar_practices) if background else {data.role(person.role).practice}
    return tuple(p for p in data.practice_keys if p in chosen)


def founders_books(
    state: GameState,
    clients: tuple[Client, ...],
    firm_id: int,
    rng: RngFactory,
    data: GameData,
    balance: Balance,
) -> tuple[Relationship, ...]:
    """Relationships for the clients the founding partners' books came from (spec 7.1)."""
    cfg = balance.books
    demand = base_monthly_demand(data)
    shares = wallets(clients, data, balance)
    keys = data.practice_keys
    staff = set(state.staff_ids(firm_id))
    founders = [p for p in state.people if p.founding_partner and p.id in staff]
    chosen: dict[int, Relationship] = {}
    mid_score = (cfg.start_relationship.lo + cfg.start_relationship.hi) / 2
    level = data.difficulty(state.save_meta.difficulty)
    loyalty = level.loyalty_points if level is not None else 0.0  # PT-M7b: difficulty
    for founder_index, person in enumerate(founders):
        if person.book_cents <= 0:
            continue
        practices = _book_practices(person, data)
        gen = rng.stream(SETUP_TURN, "book", founder_index)
        cap = cfg.max_client_share * person.book_cents
        reps = {p: firm_reputation(state, firm_id, p) for p in practices}
        expected: dict[int, float] = {}
        for client in clients:
            if client.id in chosen:
                continue
            probe = Relationship(
                client_id=client.id,
                firm_id=firm_id,
                score=mid_score,
                partner_id=person.id,
                practices=practices,
                since_turn=SETUP_TURN,
            )
            fees = 0.0
            for p in practices:
                i = keys.index(p)
                s = player_share(client, probe, p, reps[p], False, data, balance)
                fees += shares.wallet(client.id, i, demand) * MONTHS_PER_YEAR * s
            if 0 < fees <= cap:
                expected[client.id] = fees
        total = 0.0
        for _ in range(cfg.max_clients):
            if total >= person.book_cents or not expected:
                break
            pick = int(_weighted(gen, {str(cid): f for cid, f in expected.items()}))
            score = float(gen.uniform(cfg.start_relationship.lo, cfg.start_relationship.hi))
            score = min(100.0, max(0.0, score + loyalty))  # tunable-exempt: the 0-100 scale
            chosen[pick] = Relationship(
                client_id=pick,
                firm_id=firm_id,
                score=score,
                partner_id=person.id,
                practices=practices,
                since_turn=SETUP_TURN,
                last_instructed_turn=SETUP_TURN,
            )
            total += expected.pop(pick)
    return tuple(sorted(chosen.values(), key=lambda r: (r.client_id, r.firm_id)))


def new_market(
    state: GameState, firm_id: int, rng: RngFactory, data: GameData, balance: Balance
) -> MarketState:
    clients = generate_clients(rng, data, balance)
    return MarketState(
        clients=clients,
        relationships=founders_books(state, clients, firm_id, rng, data, balance),
        judges=generate_judges(rng, data),
        demand_cents=base_monthly_demand(data),
    )
