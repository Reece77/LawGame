"""PT-M12 sub-task 4: clients' wallets in the v2 practices (spec 7.1).

Real clients' sectors drive them (banks in financial regulation, insurers in insurance, energy
companies in energy); generated clients take theirs from their sector and size; individuals are
pooled clients per city that hold private client and mass torts; London's clients get the new
practices by cities.yaml's mix.
"""

from __future__ import annotations

from typing import Any

import pytest

from ptk.balance.game import start_game
from ptk.loader import load_balance, load_game_data
from ptk.sim.geo.markets import city_demand, make_city_clients
from ptk.sim.matters.market import wallets
from ptk.sim.streams import RngFactory
from tests.pt_m12_support import DATA


@pytest.fixture(scope="module")
def world() -> Any:
    data, balance = load_game_data(DATA), load_balance(DATA)
    g = start_game(data, balance, 1)
    return data, balance, g.state


def _top_sector(world: Any, practice: str) -> str:
    data, balance, state = world
    clients = [c for c in state.market.clients if c.city == ""]
    w = wallets(tuple(clients), data, balance)
    i = data.practice_keys.index(practice)
    by: dict[str, float] = {}
    for c in clients:
        by[c.sector] = by.get(c.sector, 0.0) + w.shares[c.id][i]
    return max(by, key=lambda k: by[k])


@pytest.mark.parametrize(
    ("practice", "sector"),
    [
        ("financial_regulation", "banking"),
        ("insurance", "insurance"),
        ("energy", "energy"),
        ("healthcare", "pharma_health"),
        ("technology_privacy", "technology"),
        ("private_client", "private_wealth"),
        ("mass_torts", "claimants"),
    ],
)
def test_sectors_drive_the_new_practices_wallets(world: Any, practice: str, sector: str) -> None:
    assert _top_sector(world, practice) == sector


def test_every_new_practice_has_a_wallet_that_sums_to_the_market(world: Any) -> None:
    data, balance, state = world
    clients = tuple(c for c in state.market.clients if c.city == "")
    w = wallets(clients, data, balance)
    for i in range(10, 20):
        assert sum(w.shares[c.id][i] for c in clients) == pytest.approx(1.0)


def test_generated_clients_take_wallets_from_their_sector(world: Any) -> None:
    data, balance, state = world
    clients = tuple(c for c in state.market.clients if c.city == "")
    w = wallets(clients, data, balance)
    tax = data.practice_keys.index("tax")
    generated = [c for c in clients if not c.real]
    assert generated and all(w.shares[c.id][tax] > 0 for c in generated)
    # a bigger client of the same sector has a bigger wallet
    same = sorted(
        (c for c in generated if c.sector == generated[0].sector), key=lambda c: c.revenue_bn
    )
    assert w.shares[same[-1].id][tax] > w.shares[same[0].id][tax]


def test_individuals_are_pooled_and_never_adverse(world: Any) -> None:
    data, _, state = world
    pooled = [c for c in state.market.clients if c.sector in data.clients.pooled_sectors]
    assert [c.name for c in pooled] == ["New York private clients", "New York claimants"]
    assert all(c.real and c.size_class == "mid" for c in pooled)  # no generated failure
    ids = {c.id for c in pooled}
    assert all(m.adverse_id not in ids for m in state.market.matters)


def test_london_clients_get_the_new_practices_by_mix(world: Any) -> None:
    data, balance, state = world
    rng = RngFactory(1)
    state = make_city_clients(state, "london", rng, data, balance)
    london = tuple(c for c in state.market.clients if c.city == "london")
    assert {"London private clients", "London claimants"} <= {c.name for c in london}
    demand = city_demand(rng, 0, state, "london", data, balance)
    i_arb = data.practice_keys.index("international_arbitration")
    i_torts = data.practice_keys.index("mass_torts")
    ny = data.practices
    # London's arbitration market is a larger share of New York's than its mass torts (2.5 vs 0.2)
    assert demand[i_arb] / ny[i_arb].demand_cents > demand[i_torts] / ny[i_torts].demand_cents
    w = wallets(london, data, balance)
    assert sum(w.shares[c.id][i_arb] for c in london) == pytest.approx(1.0)
