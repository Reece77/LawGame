"""Efficiency by task, client expectations and the two hooks' views (ADR PT-0011 3-5).

- **The firm's efficiency** on task t = 1 - exposure_t x (strength x adoption)_t, where the
  combined strength x adoption compounds the eras (`eras.combined`). Hours on each task scale
  by it (`interfaces.tech_hours`, read where matters compute hours).
- **The market's efficiency** is the same with the market's average adoption of each era
  `tech.clients.lag_months` earlier: what clients expect the work to take.
- **Client expectations** (from `tech.clients.pressure_from`): on an hourly bill, a task's
  realisation falls by `pass_through` x max(0, 1 - E_market / E_firm) (clients refuse to pay
  for hours the market no longer needs) plus `discount` x (1 - E_market) (they ask adopters to
  share the saving too), at most `max_cut`; a bill's cut weights its task mix by the hours the
  firm actually spends on each task (`interfaces.tech_billing`).
- **Products**: a matter kind's fixed price = its expected fees at standard hours x the
  market's efficiency on the kind's task mix x the product's `price_bp`.
- **Learning** (ADR PT-0006 4): a person's substantive share falls by `training.learn_loss` x
  the share of their task mix's hours that AI removes, of which training buys back
  `training.restore` x the programme's coverage (hours / `training.full_hours`, at most 1).
"""

from __future__ import annotations

from collections.abc import Mapping

from ptk.sim.calendar import turn_to_ym
from ptk.sim.data_models import PARTNER_LEVELS, Balance, GameData
from ptk.sim.state import GameState
from ptk.sim.tech.eras import EraWorld, efficiencies, era_world
from ptk.sim.tech.models import FirmTech

MONTHS = 12  # tunable-exempt
TENTHS = 10  # tunable-exempt


def world(state: GameState, data: GameData) -> EraWorld:
    return era_world(data.legal_eras, state.save_meta.master_seed)


def ym_of(state: GameState, turn: int | None = None) -> tuple[int, int]:
    return turn_to_ym(state.turn if turn is None else turn, state.save_meta.start_ym)


def _lagged(ym: tuple[int, int], months: int) -> tuple[int, int]:
    m = ym[0] * MONTHS + ym[1] - 1 - months
    return (m // MONTHS, m % MONTHS + 1)


def exposure(data: GameData) -> dict[str, float]:
    return {t.key: t.ai_exposure for t in data.market.tasks}


def firm_adoption(firm: FirmTech | None, data: GameData) -> tuple[float, ...]:
    if firm is None:
        return tuple(0.0 for _ in data.legal_eras.eras)
    return tuple(
        (e.adoption if (e := firm.era(key)) is not None else 0.0) for key in data.legal_eras.keys
    )


def firm_efficiency(state: GameState, firm_id: int, data: GameData) -> dict[str, float]:
    """Task -> the firm's efficiency this month (1.0: AI saves nothing)."""
    w = world(state, data)
    adoption = firm_adoption(state.tech.firm(firm_id), data)
    return efficiencies(exposure(data), w.task_strengths(ym_of(state)), adoption)


def full_efficiency(state: GameState, data: GameData, ym: tuple[int, int]) -> dict[str, float]:
    """Task -> a fully adopted firm's efficiency (every era's adoption 1)."""
    w = world(state, data)
    ones = tuple(1.0 for _ in data.legal_eras.eras)
    return efficiencies(exposure(data), w.task_strengths(ym), ones)


def market_efficiency(
    state: GameState, data: GameData, balance: Balance, ym: tuple[int, int] | None = None
) -> dict[str, float]:
    """Task -> what clients expect: the market's efficiency `lag_months` ago."""
    w = world(state, data)
    at = _lagged(ym or ym_of(state), balance.tech.clients.lag_months)
    return efficiencies(exposure(data), w.task_strengths(at), w.market_adoption(at))


def mix_efficiency(eff: Mapping[str, float], tasks: Mapping[str, float]) -> float:
    total = sum(tasks.values())
    if total <= 0:
        return 1.0
    return sum(w * eff.get(t, 1.0) for t, w in tasks.items()) / total


def pressure_on(state: GameState, balance: Balance) -> bool:
    start = balance.tech.clients.pressure_from
    return ym_of(state) >= (start[0], start[1])


def task_cuts(
    firm_eff: Mapping[str, float], market_eff: Mapping[str, float], balance: Balance
) -> dict[str, float]:
    cfg = balance.tech.clients
    out: dict[str, float] = {}
    for t, ef in firm_eff.items():
        em = market_eff.get(t, 1.0)
        excess = max(0.0, 1.0 - em / ef) if ef > 0 else 0.0
        cut = cfg.pass_through * excess + cfg.discount * (1.0 - em)
        out[t] = min(cfg.max_cut, max(0.0, cut))
    return out


def training_cover(firm: FirmTech | None, balance: Balance) -> float:
    if firm is None or firm.training_hours <= 0:
        return 0.0
    return min(1.0, firm.training_hours / balance.tech.training.full_hours)


def trainee_ids(state: GameState, firm_id: int, balance: Balance) -> tuple[int, ...]:
    """People the programme trains: the firm's lawyers at `training.levels`, by id."""
    levels = set(balance.tech.training.levels)
    staff = set(state.staff_ids(firm_id))
    return tuple(p.id for p in state.people if p.id in staff and p.level in levels)


def monthly_training_tenths(firm: FirmTech | None) -> int:
    if firm is None or firm.training_hours <= 0:
        return 0
    return round(firm.training_hours * TENTHS / MONTHS)


def is_partner(level: str) -> bool:
    return level in PARTNER_LEVELS
