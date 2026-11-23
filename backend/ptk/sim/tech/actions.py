"""Technology actions (ADR-0014: they take effect at once; PT-M14).

- `InvestInEra`: subscribe to an era's tools at a coverage (bp of the per-lawyer subscription;
  0 stops it). The first investment in an era with a platform buys it (capex to 1500, amortised
  to 6100 over `tech.adoption.platform_months`). Not before the era's start.
- `RolloutEra`: put a firm-wide rollout of an era to the equity partners (a vote; stream
  `tech_vote`); without one, adoption stays at most `tech.adoption.pilot_cap`. At most once in
  `retry_months` for an era.
- `SetTrainingProgramme`: the programme's non-billable hours a lawyer a year
  (`tech.training.hours`), for the levels in `tech.training.levels`.
- `LaunchProduct` / `RetireProduct`: a fixed-price product for a matter kind (spec 13, from
  stage `tech.products.stage`): new matters of the kind take a fixed price of `price_bp` of
  what the market expects the work to cost (billing reads it through `interfaces`).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Any, Literal

import numpy as np

from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import TechActionError
from ptk.sim.hiring.actions import Outcome, acting_firm
from ptk.sim.ledger import CASH, LedgerEntry
from ptk.sim.log import inbox_item
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState
from ptk.sim.tech import efficiency as ef
from ptk.sim.tech.adoption import BP, PPE, rollout_vote
from ptk.sim.tech.models import EraAdoption, FirmTech, Product, with_era, with_firm


@dataclass(frozen=True, slots=True)
class InvestInEra:
    actor_id: int
    era: str
    subscription_bp: int  # 0-10000 of the era's per-lawyer subscription
    kind: Literal["invest_in_era"] = "invest_in_era"


@dataclass(frozen=True, slots=True)
class RolloutEra:
    actor_id: int
    era: str
    kind: Literal["rollout_era"] = "rollout_era"


@dataclass(frozen=True, slots=True)
class SetTrainingProgramme:
    actor_id: int
    hours: int  # a lawyer a year
    kind: Literal["set_training_programme"] = "set_training_programme"


@dataclass(frozen=True, slots=True)
class LaunchProduct:
    actor_id: int
    practice: str
    kind_key: str
    price_bp: int
    kind: Literal["launch_product"] = "launch_product"


@dataclass(frozen=True, slots=True)
class RetireProduct:
    actor_id: int
    product_id: int
    kind: Literal["retire_product"] = "retire_product"


type TechAction = InvestInEra | RolloutEra | SetTrainingProgramme | LaunchProduct | RetireProduct

TECH_ACTION_TYPES: dict[str, type[Any]] = {
    "invest_in_era": InvestInEra,
    "rollout_era": RolloutEra,
    "set_training_programme": SetTrainingProgramme,
    "launch_product": LaunchProduct,
    "retire_product": RetireProduct,
}


def _firm(state: GameState, firm_id: int) -> FirmTech:
    return state.tech.firm(firm_id) or FirmTech(firm_id=firm_id)


def _era_def(data: GameData, key: str, state: GameState) -> Any:
    try:
        d = data.legal_eras.era(key)
    except KeyError as exc:
        raise TechActionError(f"no era {key!r}") from exc
    if ef.ym_of(state) < d.start:
        raise TechActionError(f"{d.label} is not available until {d.start[0]}-{d.start[1]:02d}")
    return d


def invest(state: GameState, a: InvestInEra, data: GameData, balance: Balance) -> Outcome:
    firm_id = acting_firm(state, a.actor_id)
    d = _era_def(data, a.era, state)
    if not 0 <= a.subscription_bp <= BP:
        raise TechActionError(f"coverage is 0 to {BP} bp, got {a.subscription_bp}")
    firm = _firm(state, firm_id)
    era = firm.era(a.era) or EraAdoption(era=a.era)
    entries: tuple[LedgerEntry, ...] = ()
    if a.subscription_bp > 0 and not era.platform:
        months = balance.tech.adoption.platform_months
        era = replace(
            era,
            platform=True,
            platform_turn=state.turn,
            capex_left_cents=d.platform_cents,
            amortise_cents=-(-d.platform_cents // months),
        )
        if d.platform_cents > 0:
            entries = (
                LedgerEntry.transfer(
                    turn=state.turn,
                    firm_id=firm_id,
                    memo=f"AI: {d.label} platform",
                    debit=PPE,
                    credit=CASH,
                    amount=d.platform_cents,
                ),
            )
    era = replace(era, subscription_bp=a.subscription_bp)
    firm = with_era(firm, era, data.legal_eras.keys)
    return Outcome(state=replace(state, tech=with_firm(state.tech, firm)), entries=entries)


def rollout(
    state: GameState, a: RolloutEra, rng: RngFactory, data: GameData, balance: Balance
) -> Outcome:
    firm_id = acting_firm(state, a.actor_id)
    d = _era_def(data, a.era, state)
    era = _firm(state, firm_id).era(a.era)
    if era is None or era.subscription_bp <= 0:
        raise TechActionError(f"invest in {d.label} before rolling it out")
    if era.rolled_out:
        raise TechActionError(f"{d.label} is already rolled out firm-wide")
    wait = balance.tech.adoption.retry_months
    if era.vote_turn is not None and state.turn - era.vote_turn < wait:
        raise TechActionError(f"the partners voted on {d.label} less than {wait} months ago")
    state, _passed, _s, _n, item = rollout_vote(state, firm_id, a.era, rng, data, balance)
    return Outcome(state=state, log=(item,))


def set_training(state: GameState, a: SetTrainingProgramme, balance: Balance) -> Outcome:
    firm_id = acting_firm(state, a.actor_id)
    band = balance.tech.training.hours
    if not band.lo <= a.hours <= band.hi:
        raise TechActionError(f"the programme is {band.lo} to {band.hi} hours, got {a.hours}")
    firm = replace(_firm(state, firm_id), training_hours=a.hours)
    return Outcome(state=replace(state, tech=with_firm(state.tech, firm)))


def launch(state: GameState, a: LaunchProduct, data: GameData, balance: Balance) -> Outcome:
    firm_id = acting_firm(state, a.actor_id)
    cfg = balance.tech.products
    if state.firm(firm_id).stage < cfg.stage:
        raise TechActionError(f"products open at stage {cfg.stage}")
    if a.practice not in data.practice_keys:
        raise TechActionError(f"no practice {a.practice!r}")
    kinds = {mk.key: mk for mk in data.practice(a.practice).matter_kinds}
    if a.kind_key not in kinds:
        raise TechActionError(f"no matter kind {a.kind_key!r} in {a.practice}")
    if not cfg.price_bp.lo <= a.price_bp <= cfg.price_bp.hi:
        raise TechActionError(
            f"a product's price is {cfg.price_bp.lo} to {cfg.price_bp.hi} bp, got {a.price_bp}"
        )
    firm = _firm(state, firm_id)
    active = [p for p in firm.products if p.active]
    if any(p.kind_key == a.kind_key for p in active):
        raise TechActionError(f"{kinds[a.kind_key].label} already has a product")
    if len(active) >= cfg.max_products:
        raise TechActionError(f"at most {cfg.max_products} products at once")
    product = Product(
        id=firm.next_product_id,
        kind_key=a.kind_key,
        practice=a.practice,
        price_bp=a.price_bp,
        launched_turn=state.turn,
    )
    firm = replace(
        firm, products=(*firm.products, product), next_product_id=firm.next_product_id + 1
    )
    item = inbox_item(
        state.turn,
        firm_id,
        "product_launched",
        link_kind="tech",
        link_id=product.id,
        kind=kinds[a.kind_key].label,
        price_pct=round(a.price_bp / 100),
    )
    return Outcome(state=replace(state, tech=with_firm(state.tech, firm)), log=(item,))


def retire(state: GameState, a: RetireProduct, data: GameData) -> Outcome:
    firm_id = acting_firm(state, a.actor_id)
    firm = _firm(state, firm_id)
    found = next((p for p in firm.products if p.id == a.product_id and p.active), None)
    if found is None:
        raise TechActionError(f"no active product {a.product_id}")
    products = tuple(
        replace(p, retired_turn=state.turn) if p.id == found.id else p for p in firm.products
    )
    label = next(
        mk.label for mk in data.practice(found.practice).matter_kinds if mk.key == found.kind_key
    )
    item = inbox_item(
        state.turn, firm_id, "product_retired", link_kind="tech", link_id=found.id, kind=label
    )
    firm = replace(firm, products=products)
    return Outcome(state=replace(state, tech=with_firm(state.tech, firm)), log=(item,))


def apply_tech_action(
    state: GameState,
    action: TechAction,
    draws: Callable[[], np.random.Generator],
    rng: RngFactory,
    data: GameData,
    balance: Balance,
) -> Outcome:
    del draws  # the rollout vote draws from its own stream
    if isinstance(action, InvestInEra):
        return invest(state, action, data, balance)
    if isinstance(action, RolloutEra):
        return rollout(state, action, rng, data, balance)
    if isinstance(action, SetTrainingProgramme):
        return set_training(state, action, balance)
    if isinstance(action, LaunchProduct):
        return launch(state, action, data, balance)
    return retire(state, action, data)
