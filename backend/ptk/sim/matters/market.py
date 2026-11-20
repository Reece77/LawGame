"""Legal demand, client wallets and wallet shares (spec 6 demand, 7.1 wallet share).

Each month the New York market's demand by practice (spec 6: D0 x G x (1 + beta (I - 1)) x eps,
with G and I at 1.0 until PT-M7) is split over every client by its wallet weight (size x
sector intensity x the sector's practice mix), so the wallets always sum to the market. A
client splits its wallet in a practice between the firms on its panel by the appeal logit
(TST 11.6's pattern): the player's firm, where it is instructed in the practice, and the
client's static panel firms, whose appeal is fixed in PT-M3a.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from typing import Final

from ptk.sim import dmath
from ptk.sim.calendar import turn_to_ym
from ptk.sim.data_models import AppealWeights, Balance, GameData
from ptk.sim.matters.models import Client, Relationship
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState

REGION_NEW_YORK: Final = 0  # v1's one region (stream `demand` key)
MONTHS: Final = 12  # tunable-exempt: months in a year


def monthly_demand(rng: RngFactory, turn: int, state: GameState, data: GameData) -> tuple[int, ...]:
    """Demand in standard-value cents this month, by practice (practices.yaml order)."""
    month = turn_to_ym(turn, state.save_meta.start_ym)[1]
    out = []
    for index, practice in enumerate(data.practices):
        z = float(rng.stream(turn, "demand", REGION_NEW_YORK, index).standard_normal())
        eps = dmath.exp(practice.sigma * z)
        base = practice.demand_cents / MONTHS * practice.seasonality[month - 1]
        out.append(round(base * eps))
    return tuple(out)


def base_monthly_demand(data: GameData) -> tuple[int, ...]:
    """The demand base without noise or season: D0 / 12."""
    return tuple(round(p.demand_cents / MONTHS) for p in data.practices)


def client_weight(client: Client, practice: str, data: GameData, balance: Balance) -> float:
    sector = data.clients.sector(client.sector)
    size = dmath.pow(client.revenue_bn, balance.clients.size_exponent)
    return size * sector.intensity * sector.mix.get(practice, 0.0)


@dataclass(frozen=True, slots=True)
class Wallets:
    """Each client's share of the market in each practice (weights normalised per practice)."""

    shares: dict[int, tuple[float, ...]]  # client id -> share of the market by practice

    def wallet(self, client_id: int, practice_index: int, demand: Sequence[int]) -> float:
        return self.shares[client_id][practice_index] * demand[practice_index]


def wallets(clients: Sequence[Client], data: GameData, balance: Balance) -> Wallets:
    sectors = tuple(
        (x.key, x.intensity, tuple(sorted(x.mix.items()))) for x in data.clients.sectors
    )
    key = tuple((c.id, c.sector, c.revenue_bn) for c in clients)
    return _wallets(key, sectors, data.practice_keys, balance.clients.size_exponent)


@lru_cache(maxsize=8)
def _wallets(
    clients: tuple[tuple[int, str, float], ...],
    sectors: tuple[tuple[str, float, tuple[tuple[str, float], ...]], ...],
    keys: tuple[str, ...],
    exponent: float,
) -> Wallets:
    """Memoised: the universe and its weights change only with the data (clients are fixed
    in PT-M3a)."""
    table = {k: (intensity, dict(mix)) for k, intensity, mix in sectors}
    raw: dict[int, tuple[float, ...]] = {}
    for cid, sector, revenue in clients:
        intensity, mix = table[sector]
        size = dmath.pow(revenue, exponent) * intensity
        raw[cid] = tuple(size * mix.get(p, 0.0) for p in keys)
    totals = [sum(w[i] for w in raw.values()) for i in range(len(keys))]
    return Wallets(
        shares={
            cid: tuple(w[i] / totals[i] if totals[i] > 0 else 0.0 for i in range(len(keys)))
            for cid, w in raw.items()
        }
    )


def appeal_weights(client: Client, balance: Balance) -> AppealWeights:
    return balance.appeal.large if client.size_class == "large" else balance.appeal.mid


def rival_appeal(firm_key: str, practice: str, data: GameData, balance: Balance) -> float:
    firm = data.clients.panel_firm(firm_key)
    return firm.base + (balance.appeal.rival_strong if practice in firm.strong else 0.0)


def firm_reputation(state: GameState, firm_id: int, practice: str) -> float:
    """0-1 reputation in a practice: the best partner's familiarity, (f - 1) / 19. A stand-in
    until reputation and rankings (spec 12) arrive."""
    from ptk.sim.data_models import PARTNER_LEVELS

    staff = set(state.staff_ids(firm_id))
    best = 0.0
    for person in state.people:
        if person.id in staff and person.level in PARTNER_LEVELS:
            best = max(best, (person.familiarity[practice] - 1.0) / 19.0)
    return best


def player_appeal(
    client: Client,
    rel: Relationship,
    reputation: float,
    conflicted: bool,
    balance: Balance,
) -> float:
    """A_f = w_rel R + w_rep Rep + w_price (1 - rate/ref) + w_cap Cap - w_conf Conflict.

    The player's firm charges the practice's card in PT-M3a, so the price term is 0 until
    rates are set (PT-M7); Cap is minus last month's unserved share of the client's flow;
    Conflict is 1 while the firm is adverse to the client on an open matter."""
    w = appeal_weights(client, balance)
    price_term = 0.0
    return (
        w.relationship * rel.score / 100.0
        + w.reputation * reputation
        + w.price * price_term
        - w.capacity * rel.lost_share
        - w.conflict * (1.0 if conflicted else 0.0)
    )


def player_share(
    client: Client,
    rel: Relationship,
    practice: str,
    reputation: float,
    conflicted: bool,
    data: GameData,
    balance: Balance,
) -> float:
    """s_f = e^A_f / Σ_g e^A_g over the client's panel (spec 7.1)."""
    if practice not in rel.practices:
        return 0.0
    mine = dmath.exp(player_appeal(client, rel, reputation, conflicted, balance))
    rivals = sum(dmath.exp(rival_appeal(k, practice, data, balance)) for k in client.panel)
    return mine / (mine + rivals)
