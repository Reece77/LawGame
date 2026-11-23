"""The bodies of `interfaces.tech_hours`, `tech_billing` and `tech_rfp_gap` (PT-M14).

Views are memoised on the identity of what they read (the immutable tech state, people,
employments, data and balance) for the turn, so the many readers of a month pay once.
"""

from __future__ import annotations

from collections import OrderedDict

from ptk.sim.data_models import Balance, GameData
from ptk.sim.interfaces import (
    NO_TECH_BILLING,
    NO_TECH_HOURS,
    TechBillingView,
    TechHoursView,
)
from ptk.sim.matters import formulas as mfx
from ptk.sim.state import GameState
from ptk.sim.tech import efficiency as ef

KEEP = 16  # tunable-exempt: memoised views

_HOURS: OrderedDict[tuple[int, int, int], tuple[tuple[object, ...], TechHoursView]] = OrderedDict()
_BILLING: OrderedDict[tuple[int, int, int], tuple[tuple[object, ...], TechBillingView]] = (
    OrderedDict()
)


def _remember[V](
    cache: OrderedDict[tuple[int, int, int], tuple[tuple[object, ...], V]],
    key: tuple[int, int, int],
    deps: tuple[object, ...],
    value: V,
) -> V:
    cache[key] = (deps, value)
    while len(cache) > KEEP:
        cache.popitem(last=False)
    return value


def _hit[V](
    cache: OrderedDict[tuple[int, int, int], tuple[tuple[object, ...], V]],
    key: tuple[int, int, int],
    deps: tuple[object, ...],
) -> V | None:
    hit = cache.get(key)
    if hit is not None and all(a is b for a, b in zip(hit[0], deps, strict=True)):
        return hit[1]
    return None


def hours_view(state: GameState, firm_id: int, data: GameData, balance: Balance) -> TechHoursView:
    firm = state.tech.firm(firm_id)
    if firm is None or firm.idle:
        return NO_TECH_HOURS
    key = (firm_id, state.turn, state.save_meta.master_seed)
    deps = (state.tech, state.people, state.employments, data, balance)
    if (hit := _hit(_HOURS, key, deps)) is not None:
        return hit
    eff = ef.firm_efficiency(state, firm_id, data)
    if all(v == 1.0 for v in eff.values()):
        eff = {}
    cfg = balance.tech.training
    cover = ef.training_cover(firm, balance)
    tenths = ef.monthly_training_tenths(firm)
    trainees = ef.trainee_ids(state, firm_id, balance) if tenths > 0 else ()
    view = TechHoursView(
        efficiency=eff,
        learning_loss=cfg.learn_loss * (1.0 - cfg.restore * cover),
        training_tenths={pid: tenths for pid in trainees},
    )
    return _remember(_HOURS, key, deps, view)


def billing_view(
    state: GameState, firm_id: int, data: GameData, balance: Balance
) -> TechBillingView:
    firm = state.tech.firm(firm_id)
    pressure = ef.pressure_on(state, balance)
    products = tuple(p for p in firm.products if p.active) if firm is not None else ()
    if not pressure and not products:
        return NO_TECH_BILLING
    key = (firm_id, state.turn, state.save_meta.master_seed)
    deps = (state.tech, data, balance)
    if (hit := _hit(_BILLING, key, deps)) is not None:
        return hit
    firm_eff = ef.firm_efficiency(state, firm_id, data)
    market_eff = ef.market_efficiency(state, data, balance)
    cuts = ef.task_cuts(firm_eff, market_eff, balance) if pressure else {}
    if all(v == 0.0 for v in cuts.values()):
        cuts = {}
    priced: dict[str, float] = {}
    for p in products:
        kind = data.market.kinds[_kind_of(p.practice, p.kind_key, data)]
        market_cost = ef.mix_efficiency(market_eff, mfx.kind_tasks(kind))
        priced[p.kind_key] = market_cost * p.price_bp / 10000  # tunable-exempt: bp
    view = TechBillingView(cuts=cuts, efficiency=firm_eff, products=priced)
    return _remember(_BILLING, key, deps, view)


def _kind_of(practice: str, kind_key: str, data: GameData) -> str:
    for mk in data.practice(practice).matter_kinds:
        if mk.key == kind_key:
            return mk.kind
    raise KeyError(f"no matter kind {kind_key!r} in {practice}")


def ai_score(adoption: tuple[float, ...], weights: tuple[float, ...]) -> float:
    total = sum(weights)
    if total <= 0:
        return 0.0
    return sum(a * w for a, w in zip(adoption, weights, strict=True)) / total


def era_weights(state: GameState, data: GameData, balance: Balance) -> tuple[float, ...]:
    """Each era's weight in the AI score: its strength this month on the exposed tasks."""
    w = ef.world(state, data)
    ym = ef.ym_of(state)
    exposed = {t.key for t in data.market.tasks if t.ai_exposure >= balance.tech.exposed_min}
    out = []
    for i, era in enumerate(data.legal_eras.eras):
        s = w.strength(i, ym)
        out.append(s * sum(v for t, v in era.tasks.items() if t in exposed))
    return tuple(out)


def rfp_gap(state: GameState, firm_id: int, data: GameData, balance: Balance) -> float | None:
    if ef.ym_of(state)[0] < balance.tech.clients.rfp_from_year:
        return None
    weights = era_weights(state, data, balance)
    mine = ai_score(ef.firm_adoption(state.tech.firm(firm_id), data), weights)
    market = ai_score(ef.world(state, data).market_adoption(ef.ym_of(state)), weights)
    return max(-1.0, min(1.0, mine - market))
