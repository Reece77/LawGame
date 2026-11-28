"""Legal demand, client wallets and wallet shares (spec 6 demand, 7.1 wallet share).

Each month the New York market's demand by practice (spec 6: D0 x G x (1 + beta (I - 1)) x eps,
with G and I from the macro history, PT-M7) is split over every client by its wallet weight (size x
sector intensity x the sector's practice mix), so the wallets always sum to the market. A
client splits its wallet in a practice between the firms on its panel by the appeal logit
(TST 11.6's pattern): the player's firm, where it is instructed in the practice, and the
client's static panel firms, whose appeal is fixed in PT-M3a.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from typing import Final

from simcore.kernel import dmath
from simcore.kernel.calendar import turn_to_ym

from ptk.sim.data_models import AppealWeights, Balance, GameData
from ptk.sim.macro import demand_factor, wallet_factors
from ptk.sim.matters.models import Client, Relationship
from ptk.sim.state import GameState
from ptk.sim.streams import RngFactory

REGION_NEW_YORK: Final = 0  # v1's one region (stream `demand` key)
MONTHS: Final = 12  # tunable-exempt: months in a year


def monthly_demand(
    rng: RngFactory, turn: int, state: GameState, data: GameData, balance: Balance
) -> tuple[int, ...]:
    """Demand in standard-value cents this month, by practice (practices.yaml order), driven
    by the macro history (PT-M7, `ptk.sim.macro.demand_factor`)."""
    ym = turn_to_ym(turn, state.save_meta.start_ym)
    out = []
    for index, practice in enumerate(data.practices):
        z = float(rng.stream(turn, "demand", REGION_NEW_YORK, index).standard_normal())
        eps = dmath.exp(practice.sigma * z)
        base = practice.demand_cents / MONTHS * practice.seasonality[ym[1] - 1]
        out.append(round(base * demand_factor(practice, ym, data, balance) * eps))
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


def wallets(
    clients: Sequence[Client],
    data: GameData,
    balance: Balance,
    turn: int | None = None,
    start: tuple[int, int] | None = None,
) -> Wallets:
    """Each client's share of the market by practice; given the month, real clients that
    history fails (PT-M7: `macro.wallet_factors`) shrink to their estate's or end."""
    sectors = tuple(
        (x.key, x.intensity, tuple(sorted(x.mix.items()))) for x in data.clients.sectors
    )
    key = tuple((c.id, c.sector, c.revenue_bn, c.city) for c in clients)
    failed: tuple[tuple[int, tuple[float, ...]], ...] = ()
    if turn is not None and start is not None:
        failed = tuple(
            (c.id, f)
            for c in clients
            if c.real and (f := wallet_factors(c, turn, data, balance, start)) is not None
        )
    return _wallets(key, sectors, data.practice_keys, balance.clients.size_exponent, failed)


@lru_cache(maxsize=32)
def _wallets(
    clients: tuple[tuple[int, str, float, str], ...],
    sectors: tuple[tuple[str, float, tuple[tuple[str, float], ...]], ...],
    keys: tuple[str, ...],
    exponent: float,
    failed: tuple[tuple[int, tuple[float, ...]], ...] = (),
) -> Wallets:
    """Memoised: the universe and its weights change only with the data and history's
    failures (clients are fixed in PT-M3a; real failures are dated, PT-M7)."""
    table = {k: (intensity, dict(mix)) for k, intensity, mix in sectors}
    factors = dict(failed)
    raw: dict[int, tuple[float, ...]] = {}
    city_of: dict[int, str] = {}
    for cid, sector, revenue, city in clients:
        intensity, mix = table[sector]
        size = dmath.pow(revenue, exponent) * intensity
        row = tuple(size * mix.get(p, 0.0) for p in keys)
        if cid in factors:
            row = tuple(w * f for w, f in zip(row, factors[cid], strict=True))
        raw[cid] = row
        city_of[cid] = city
    # PT-M11: each city's clients split that city's market (v1: one market, city "")
    totals: dict[str, list[float]] = {}
    for cid, w in raw.items():
        t = totals.setdefault(city_of[cid], [0.0] * len(keys))
        for i in range(len(keys)):
            t[i] += w[i]
    return Wallets(
        shares={
            cid: tuple(
                w[i] / tot[i] if (tot := totals[city_of[cid]])[i] > 0 else 0.0
                for i in range(len(keys))
            )
            for cid, w in raw.items()
        }
    )


def appeal_weights(client: Client, balance: Balance) -> AppealWeights:
    return balance.appeal.large if client.size_class == "large" else balance.appeal.mid


def rival_appeal(firm_key: str, practice: str, data: GameData, balance: Balance) -> float:
    firm = data.clients.panel_firm(firm_key)
    return firm.base + (balance.appeal.rival_strong if practice in firm.strong else 0.0)


def firm_reputation(state: GameState, firm_id: int, practice: str, balance: Balance) -> float:
    """The appeal's Rep 0-1 in a practice (spec 7.1): PT-M16's public reputation
    (`reputation.formulas.appeal_rep`), which replaced PT-M3a's stand-in (the best partner's
    familiarity)."""
    from ptk.sim.reputation.formulas import appeal_rep

    return appeal_rep(state, firm_id, practice, balance)


def player_appeal(
    client: Client,
    rel: Relationship,
    reputation: float,
    conflicted: bool,
    balance: Balance,
    price_term: float = 0.0,
    reach: float = 0.0,
) -> float:
    """A_f = w_rel R + w_rep Rep + w_price (1 - rate/ref) + w_cap Cap - w_conf Conflict
    - reach (PT-M11: `geo.reach_penalty` for a client's work in a city where the firm has no
    office; 0 in the home market).

    The price term (PT-M7a) is 1 - the firm's rate index / the market's (`rates.price_term`):
    0 for a firm whose card rises with the market; Cap is minus last month's unserved share
    of the client's flow; Conflict is 1 while the firm is adverse to the client on an open
    matter."""
    w = appeal_weights(client, balance)
    return (
        w.relationship * rel.score / 100.0
        + w.reputation * reputation
        + w.price * price_term
        - w.capacity * rel.lost_share
        - w.conflict * (1.0 if conflicted else 0.0)
        - reach
    )


def player_share(
    client: Client,
    rel: Relationship,
    practice: str,
    reputation: float,
    conflicted: bool,
    data: GameData,
    balance: Balance,
    appeals: Mapping[str, tuple[float, ...]] | None = None,
    price_term: float = 0.0,
    reach: float = 0.0,
) -> float:
    """s_f = e^A_f / Σ_g e^A_g over the client's panel (spec 7.1). `appeals` (PT-M5): the
    rival firms' live appeal by practice (`RivalsState.appeals`); the static panel appeal
    stands in for a key it does not hold. `price_term` (PT-M7a): `rates.price_term`."""
    if practice not in rel.practices:
        return 0.0
    mine = dmath.exp(player_appeal(client, rel, reputation, conflicted, balance, price_term, reach))
    index = data.practice_keys.index(practice)
    rivals = 0.0
    for k in client.panel:
        live = appeals.get(k) if appeals is not None else None
        rivals += dmath.exp(
            live[index] if live is not None else rival_appeal(k, practice, data, balance)
        )
    return mine / (mine + rivals)
