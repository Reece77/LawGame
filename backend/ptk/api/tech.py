"""Technology endpoints and schemas (PT-M14; spec 13, 16; ADR PT-0011).

The Technology screen reads one view: each era (its strength now, the market's adoption, the
firm's adoption, what it costs, the rollout's state), each task (its exposure, the firm's and
the market's efficiency, what clients cut from an hourly bill's hours on it), the training
programme, client expectations (cuts on hourly bills over the trailing months, RFPs' AI
question from 2023) and the firm's fixed-fee products with the kinds it could offer.

Never in a schema: partners' adaptability or technology (their buy-in is seen only in a
vote's count), a seat holder's true score or the CKO's effect, or the seeded paths' targets
beyond this month. Every write is one player action (ADR-0014), logged to `decision_log`, and
returns the fresh view.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from ptk import loader
from ptk.config import get_settings
from ptk.db import saves
from ptk.sim.actions import Action
from ptk.sim.calendar import format_turn, ym_to_turn
from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import NotFoundError
from ptk.sim.interfaces import kind_task_mix, tech_billing, tech_hours, tech_rfp_gap
from ptk.sim.matters.models import Matter
from ptk.sim.state import GameState
from ptk.sim.tech import efficiency as ef
from ptk.sim.tech.actions import (
    InvestInEra,
    LaunchProduct,
    RetireProduct,
    RolloutEra,
    SetTrainingProgramme,
)
from ptk.sim.tech.adoption import lawyer_count

BP = 10000  # tunable-exempt


class EraOut(BaseModel):
    key: str
    label: str
    start_label: str
    available: bool
    strength_pct: int  # the era's strength this month, 0-100
    market_pct: int  # the market's average adoption, 0-100
    adoption_pct: int  # the firm's adoption, 0-100
    full: bool
    platform: bool
    platform_cents: int
    subscription_cents: int  # a lawyer a month at full coverage
    subscription_bp: int  # the firm's coverage
    monthly_cents: int  # what the firm pays a month at its coverage
    rolled_out: bool
    can_rollout: bool
    vote_label: str | None  # the last rollout vote's month
    tasks: dict[str, int]  # task -> the era's strength on it now, 0-100


class TaskOut(BaseModel):
    key: str
    exposure_pct: int
    efficiency_pct: int  # hours the firm needs per 100 base hours
    full_pct: int  # hours a fully adopted firm needs
    market_pct: int  # hours clients expect (the market, lagged)
    client_cut_bp: int  # realisation clients cut on hourly bills for the task


class TrainingOut(BaseModel):
    hours: int
    lo: int
    hi: int
    default: int
    full_hours: int
    trainees: int
    monthly_cents: int


class ClientsOut(BaseModel):
    pressure: bool  # clients press hourly bills now
    pressure_from_label: str
    cut_12m_cents: int  # clients' AI cuts on bills over the trailing months
    case_cut_bp: int  # a typical case's hourly-bill cut now
    deal_cut_bp: int
    flow_cut_bp: int
    rfp_asks: bool  # RFPs ask for AI and efficiency (from rfp_from_year)
    rfp_standing: str | None  # ahead, level or behind the market
    rfp_from_year: int


class ProductOut(BaseModel):
    id: int
    practice: str
    kind_key: str
    label: str
    price_bp: int
    price_pct_of_standard: int  # price as a share of the matter's fees at standard hours
    launched_label: str
    active: bool
    matters: int
    billed_cents: int
    standard_cents: int  # the same matters' hours at standard value


class KindOut(BaseModel):
    practice: str
    kind_key: str
    label: str
    exposed_pct: int  # share of the kind's hours on exposed tasks
    market_cost_pct: int  # what the market expects the work to cost, of standard
    hours_pct: int  # the firm's hours on the kind, of base


class TechOut(BaseModel):
    month_label: str
    stage: int
    lawyers: int
    eras: list[EraOut]
    tasks: list[TaskOut]
    training: TrainingOut
    clients: ClientsOut
    products: list[ProductOut]
    kinds: list[KindOut]
    can_launch: bool
    product_stage: int
    price_lo: int
    price_hi: int
    price_default: int
    max_products: int


class InvestIn(BaseModel):
    era: str
    subscription_bp: int


class RolloutIn(BaseModel):
    era: str


class TrainingIn(BaseModel):
    hours: int


class ProductIn(BaseModel):
    practice: str
    kind_key: str
    price_bp: int


def _pct(x: float) -> int:
    return round(100 * x)


def _standing(gap: float | None) -> str | None:
    if gap is None:
        return None
    if gap > 0.05:  # tunable-exempt: display band
        return "ahead"
    if gap < -0.05:  # tunable-exempt: display band
        return "behind"
    return "level"


def tech_out(state: GameState, data: GameData, balance: Balance) -> TechOut:
    firm_id = state.player.id
    start = state.save_meta.start_ym
    ym = ef.ym_of(state)
    world = ef.world(state, data)
    firm = state.tech.firm(firm_id)
    lawyers = lawyer_count(state, firm_id, data)
    cfg = balance.tech
    eras = []
    strengths = world.task_strengths(ym)
    for i, d in enumerate(data.legal_eras.eras):
        mine = None if firm is None else firm.era(d.key)
        sub_bp = 0 if mine is None else mine.subscription_bp
        a = 0.0 if mine is None else mine.adoption
        wait = cfg.adoption.retry_months
        eras.append(
            EraOut(
                key=d.key,
                label=d.label,
                start_label=format_turn(ym_to_turn(d.start[0], d.start[1], start), start),
                available=ym >= d.start,
                strength_pct=_pct(world.strength(i, ym)),
                market_pct=_pct(world.market(i, ym)),
                adoption_pct=_pct(a),
                full=a >= cfg.adoption.full_from,
                platform=mine is not None and mine.platform,
                platform_cents=d.platform_cents,
                subscription_cents=d.subscription_cents,
                subscription_bp=sub_bp,
                monthly_cents=lawyers * d.subscription_cents * sub_bp // BP,
                rolled_out=mine is not None and mine.rolled_out,
                can_rollout=mine is not None
                and sub_bp > 0
                and not mine.rolled_out
                and (mine.vote_turn is None or state.turn - mine.vote_turn >= wait),
                vote_label=None
                if mine is None or mine.vote_turn is None
                else format_turn(mine.vote_turn, start),
                tasks={t: _pct(v) for t, v in strengths[i].items()},
            )
        )
    mine_eff = ef.firm_efficiency(state, firm_id, data)
    full = ef.full_efficiency(state, data, ym)
    market = ef.market_efficiency(state, data, balance)
    cuts = ef.task_cuts(mine_eff, market, balance) if ef.pressure_on(state, balance) else {}
    tasks = [
        TaskOut(
            key=t.key,
            exposure_pct=_pct(t.ai_exposure),
            efficiency_pct=_pct(mine_eff[t.key]),
            full_pct=_pct(full[t.key]),
            market_pct=_pct(market[t.key]),
            client_cut_bp=round(BP * cuts.get(t.key, 0.0)),
        )
        for t in data.market.tasks
    ]
    trainees = len(ef.trainee_ids(state, firm_id, balance))
    tenths = ef.monthly_training_tenths(firm)
    tcfg = cfg.training
    training = TrainingOut(
        hours=0 if firm is None else firm.training_hours,
        lo=tcfg.hours.lo,
        hi=tcfg.hours.hi,
        default=tcfg.hours.default,
        full_hours=tcfg.full_hours,
        trainees=trainees,
        monthly_cents=trainees * tenths * tcfg.cost_cents_per_hour // ef.TENTHS,
    )
    billing = tech_billing(state, firm_id, data, balance)
    pf = cfg.clients.pressure_from
    clients = ClientsOut(
        pressure=ef.pressure_on(state, balance),
        pressure_from_label=format_turn(ym_to_turn(pf[0], pf[1], start), start),
        cut_12m_cents=sum(m.ai_cut_cents for m in state.billing.months if m.firm_id == firm_id),
        case_cut_bp=billing.cut_bp(kind_task_mix("case", data)),
        deal_cut_bp=billing.cut_bp(kind_task_mix("deal", data)),
        flow_cut_bp=billing.cut_bp(data.market.flow_tasks),
        rfp_asks=ym[0] >= cfg.clients.rfp_from_year,
        rfp_standing=_standing(tech_rfp_gap(state, firm_id, data, balance)),
        rfp_from_year=cfg.clients.rfp_from_year,
    )
    exposed = {t.key for t in data.market.tasks if t.ai_exposure >= cfg.exposed_min}
    view = tech_hours(state, firm_id, data, balance)
    labels: dict[str, str] = {}
    kinds = []
    for p in data.practices:
        for mk in p.matter_kinds:
            labels[mk.key] = mk.label
            mix = kind_task_mix(mk.kind, data)
            total = sum(mix.values())
            kinds.append(
                KindOut(
                    practice=p.key,
                    kind_key=mk.key,
                    label=mk.label,
                    exposed_pct=_pct(sum(w for t, w in mix.items() if t in exposed) / total),
                    market_cost_pct=_pct(ef.mix_efficiency(market, mix)),
                    hours_pct=_pct(view.factor(mix)),
                )
            )
    products = []
    for prod in () if firm is None else firm.products:
        engs = [
            e
            for e in state.billing.engagements
            if e.firm_id == firm_id
            and e.model == "fixed"
            and e.opened_turn >= prod.launched_turn
            and (prod.retired_turn is None or e.opened_turn < prod.retired_turn)
            and (m := state.market.matter(e.matter_id)) is not None
            and m.kind_key == prod.kind_key
        ]
        kind = next(k for k in kinds if k.kind_key == prod.kind_key)
        products.append(
            ProductOut(
                id=prod.id,
                practice=prod.practice,
                kind_key=prod.kind_key,
                label=labels[prod.kind_key],
                price_bp=prod.price_bp,
                price_pct_of_standard=round(kind.market_cost_pct * prod.price_bp / BP),
                launched_label=format_turn(prod.launched_turn, start),
                active=prod.active,
                matters=len(engs),
                billed_cents=sum(e.billed_cents for e in engs),
                standard_cents=sum(e.standard_cents for e in engs),
            )
        )
    pc = cfg.products
    return TechOut(
        month_label=format_turn(state.turn, start),
        stage=state.player.stage,
        lawyers=lawyers,
        eras=eras,
        tasks=tasks,
        training=training,
        clients=clients,
        products=products,
        kinds=kinds,
        can_launch=state.player.stage >= pc.stage,
        product_stage=pc.stage,
        price_lo=pc.price_bp.lo,
        price_hi=pc.price_bp.hi,
        price_default=pc.price_bp.default,
        max_products=pc.max_products,
    )


def matter_ai_fields(
    state: GameState, m: Matter, data: GameData, balance: Balance
) -> dict[str, Any]:
    """The matter page's AI fields (PT-M14): the hours the current phase needs per 100 base
    hours, the kind's exposed share, clients' cut on an hourly bill, and whether a product
    prices it."""
    kind = data.market.kinds[m.kind]
    phase = kind.phases[min(m.phase_index, len(kind.phases) - 1)]
    mix = kind_task_mix(m.kind, data)
    exposed = {t.key for t in data.market.tasks if t.ai_exposure >= balance.tech.exposed_min}
    billing = tech_billing(state, m.firm_id, data, balance)
    e = state.billing.engagement(m.id)
    return {
        "ai_hours_pct": _pct(tech_hours(state, m.firm_id, data, balance).factor(phase.tasks)),
        "ai_exposed_pct": _pct(sum(w for t, w in mix.items() if t in exposed) / sum(mix.values())),
        "ai_client_cut_bp": billing.cut_bp(mix),
        "ai_product": m.kind_key in billing.products
        or (e is not None and e.model == "fixed" and m.kind_key in _product_kinds(state, m)),
    }


def _product_kinds(state: GameState, m: Matter) -> set[str]:
    firm = state.tech.firm(m.firm_id)
    if firm is None:
        return set()
    return {
        p.kind_key
        for p in firm.products
        if p.launched_turn <= m.opened_turn
        and (p.retired_turn is None or m.opened_turn < p.retired_turn)
    }


def practice_ai_cut_bp(state: GameState, practice: str, data: GameData, balance: Balance) -> int:
    """The pricing screen's AI column (PT-M14): clients' cut on the practice's hourly bills,
    over its matter kinds by weight."""
    billing = tech_billing(state, state.player.id, data, balance)
    if not billing.cuts:
        return 0
    kinds = data.practice(practice).matter_kinds
    total = sum(k.weight for k in kinds)
    return round(sum(k.weight * billing.cut_bp(kind_task_mix(k.kind, data)) for k in kinds) / total)


# --- Router -------------------------------------------------------------------------------------


def _path(slug: str) -> Path:
    return saves.open_save(get_settings().resolved_save_dir(), slug)


def _view(path: Path) -> TechOut:
    state = saves.read_state(path)[0]
    return tech_out(state, loader.game_data(), loader.balance())


def _act(slug: str, build: Any) -> TechOut:
    path = _path(slug)
    state = saves.read_state(path)[0]
    actor = state.founder_of(state.player.id)
    if actor is None:
        raise NotFoundError("the firm has no founding partner to act")
    action: Action = build(actor)
    saves.run_action(path, action, loader.balance(), loader.game_data())
    return _view(path)


def make_tech_router(errors: dict[int | str, dict[str, Any]]) -> APIRouter:
    router = APIRouter()
    base = "/api/saves/{slug}/tech"
    kw: dict[str, Any] = {"response_model": TechOut, "responses": errors}

    @router.get(base, operation_id="getTech", **kw)
    def get_tech(slug: str) -> TechOut:
        return _view(_path(slug))

    @router.post(f"{base}/invest", operation_id="investInEra", **kw)
    def invest(slug: str, body: InvestIn) -> TechOut:
        return _act(slug, lambda a: InvestInEra(a, body.era, body.subscription_bp))

    @router.post(f"{base}/rollout", operation_id="rolloutEra", **kw)
    def rollout(slug: str, body: RolloutIn) -> TechOut:
        return _act(slug, lambda a: RolloutEra(a, body.era))

    @router.post(f"{base}/training", operation_id="setTrainingProgramme", **kw)
    def training(slug: str, body: TrainingIn) -> TechOut:
        return _act(slug, lambda a: SetTrainingProgramme(a, body.hours))

    @router.post(f"{base}/products", operation_id="launchProduct", **kw)
    def launch(slug: str, body: ProductIn) -> TechOut:
        return _act(slug, lambda a: LaunchProduct(a, body.practice, body.kind_key, body.price_bp))

    @router.post(f"{base}/products/{{product_id}}/retire", operation_id="retireProduct", **kw)
    def retire(slug: str, product_id: int) -> TechOut:
        return _act(slug, lambda a: RetireProduct(a, product_id))

    return router
