"""Mergers endpoints and schemas (PT-M13; spec 8.8; ADR PT-0016).

The Mergers screen reads one view: the target list with its fit (public figures only: revenue,
lawyers, PEP, practices, headquarters), the open and past deals (stage, diligence's exact books
and ranges, the terms, the other partnership's last count, the player's predicted vote, the
conflicts clearance found and how each ended), integrations in progress, the verein and the exit.

Never in a schema (CLAUDE.md section 10; ADR PT-0016 4): the other firm's annuity share and lease
years, its partners' true quality, the true conflict count before clearance (diligence shows a
range), a book client's adverse engagement before clearance, the answer's noise or bias, a
waiver's chance. Every write is one player action in its own transaction (ADR-0014).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel

from ptk import loader
from ptk.config import get_settings
from ptk.db import saves
from ptk.sim.calendar import format_turn
from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import NotFoundError
from ptk.sim.mergers.actions import (
    AnswerApproach,
    ApproachFirm,
    CommissionDiligence,
    PutTerms,
    WalkAway,
)
from ptk.sim.mergers.diligence import fee_cents, max_level, reveal
from ptk.sim.mergers.integration import partners_lost_share
from ptk.sim.mergers.models import Deal
from ptk.sim.mergers.profile import fit, player_side, rival_side
from ptk.sim.mergers.talks import eligible
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState


class MergerTargetOut(BaseModel):
    key: str
    name: str
    kind: str
    city: str  # headquarters (a label; "Elsewhere" outside the modelled cities)
    region: str
    lawyers: int
    equity_partners: int
    revenue_cents: int
    pep_cents: int
    practices: list[str]  # its largest practices, by lawyers
    complement_pct: int
    new_city: bool
    rate_pct: int  # its card as % of the player's
    pep_pct: int  # its PEP as % of the player's
    clash_pct: int
    fair_share_pct: int  # the player's share of the two profit pools
    integrable: bool
    reason: str  # why it cannot be integrated, if not
    merger_blocked: str  # why it cannot be approached for a merger now ('' when it can)
    verein_blocked: str


class MergerRangeOut(BaseModel):
    lo: int
    hi: int


class MergerRevealOut(BaseModel):
    level: int
    max_level: int
    exact: bool
    revenue_cents: int
    profit_cents: int
    pep_cents: int
    lawyers: int
    equity_partners: int
    wip_cents: int | None
    receivables_cents: int | None
    cash_cents: int | None
    revolver_cents: int | None
    partner_ability: MergerRangeOut  # the key partners' ability, a range
    annuities_cents: MergerRangeOut
    leases_cents: MergerRangeOut
    conflicts: MergerRangeOut
    book_clients: int
    next_fee_cents: int


class MergerTermsOut(BaseModel):
    our_share_pct: int
    name: str
    mp: str
    comp_system: str
    rates: str


class MergerConflictOut(BaseModel):
    our_client: str
    their_client: str
    matter_id: int | None
    outcome: str


class MergerPredictionOut(BaseModel):
    yes_lo: float
    yes_hi: float
    total: float
    needed: float


class MergerDealOut(BaseModel):
    id: int
    firm_key: str
    firm: str
    form: str
    initiator: str
    stage: str
    opened: str
    leaked: bool
    absorbed: bool
    diligence_running: bool
    diligence_fees_cents: int
    reveal: MergerRevealOut | None
    terms: MergerTermsOut | None
    counter_share_pct: int | None
    their_yes_pct: int | None
    prediction: MergerPredictionOut | None
    conflicts: list[MergerConflictOut]
    ended: str | None
    ended_reason: str


class MergerIntegrationOut(BaseModel):
    deal_id: int
    firm: str
    closed: str
    until: str
    months_left: int
    clash_pct: int
    lawyers_at_closing: int
    partners_at_closing: int
    partners_lost: int
    partners_lost_pct: int
    clients_lost: int
    card_rise_pct: int
    surrender_cents: int


class VereinMemberOut(BaseModel):
    key: str
    name: str
    city: str
    joined: str
    lawyers: int
    revenue_cents: int


class VereinOut(BaseModel):
    name: str
    formed: str
    members: list[VereinMemberOut]
    costs_cents: int


class MergerExitOut(BaseModel):
    turn: str
    firm: str
    capital_cents: int
    earnings_cents: int
    rank: int
    revenue_cents: int


class MergersOut(BaseModel):
    targets: list[MergerTargetOut]
    deals: list[MergerDealOut]
    integrations: list[MergerIntegrationOut]
    verein: VereinOut | None
    exit: MergerExitOut | None
    is_mp: bool
    energy: int
    costs: dict[str, int]  # energy costs of the merger actions
    absorbed_below_pct: int
    vote_pct: int
    max_lawyers: int
    comp_systems: list[str]


class MergerApproachIn(BaseModel):
    rival_key: str
    form: Literal["merger", "verein"] = "merger"


class MergerAnswerIn(BaseModel):
    accept: bool


class MergerTermsIn(BaseModel):
    our_share_bp: int = 5000
    name: Literal["ours", "theirs", "combined"] = "ours"
    mp: Literal["ours", "theirs"] = "ours"
    comp_system: str = "modified_lockstep"
    rates: Literal["ours", "theirs", "higher", "blend"] = "ours"


def _city(data: GameData, hq: str) -> str:
    key = data.geo.city_key(hq)
    return data.geo.city(key).label if key is not None else "Elsewhere"


def _prediction(
    state: GameState, deal: Deal, data: GameData, balance: Balance
) -> MergerPredictionOut | None:
    """The player's predicted vote on the terms put (a range, ADR PT-0007 2)."""
    from ptk.sim.partnership.governance import predicted, threshold_for
    from ptk.sim.partnership.models import Vote

    fp = state.partnership.of(state.player.id)
    if fp is None or deal.terms is None or not deal.is_open:
        return None
    params: dict[str, str | int | float | bool] = {
        "deal_id": deal.id,
        "threshold_bp": balance.mergers.vote_bp,
        "form": deal.form,
    }
    vote = Vote(
        id=0,
        firm_id=fp.firm_id,
        kind="merger",
        subject_id=None,
        params=tuple(sorted(params.items())),
        opened_turn=state.turn,
        threshold_bp=threshold_for(fp, "merger", params),
    )
    p = predicted(state, fp, vote, balance, data)
    return MergerPredictionOut(yes_lo=p.yes_lo, yes_hi=p.yes_hi, total=p.total, needed=p.needed)


def mergers_out(state: GameState, data: GameData, balance: Balance) -> MergersOut:
    rng = RngFactory(state.save_meta.master_seed)
    start = state.save_meta.start_ym
    pid = state.player.id
    ours = player_side(state, data, balance)
    targets = []
    for f in state.rivals.active:
        if f.kind == "boutique":
            continue
        side = rival_side(f, data)
        ft = fit(state, f, data, balance, ours)
        top = sorted(side.practices, key=lambda pn: (-pn[1], pn[0]))[:3]
        targets.append(
            MergerTargetOut(
                key=f.key,
                name=f.name,
                kind=f.kind,
                city=_city(data, f.hq),
                region=side.region,
                lawyers=side.lawyers,
                equity_partners=side.equity,
                revenue_cents=side.revenue_cents,
                pep_cents=side.pep_cents,
                practices=[p for p, _ in top],
                complement_pct=round(ft.complement * 100),
                new_city=ft.new_city,
                rate_pct=round(ft.rate_ratio * 100),
                pep_pct=round(ft.pep_ratio * 100),
                clash_pct=round(ft.clash * 100),
                fair_share_pct=round(ft.fair_share_bp / 100),
                integrable=ft.integrable,
                reason=ft.reason,
                merger_blocked=eligible(state, f, "merger", balance) or ft.reason,
                verein_blocked=eligible(state, f, "verein", balance),
            )
        )
    targets.sort(key=lambda t: (-t.complement_pct, t.key))
    deals = []
    for d in sorted(state.mergers.deals, key=lambda d: -d.id):
        firm = state.rivals.firm(d.rival_id)
        rev = None
        if firm is not None and firm.active and d.is_open:
            r = reveal(state, d, firm, rng, data, balance)
            rev = MergerRevealOut(
                level=r.level,
                max_level=max_level(balance),
                exact=r.exact,
                revenue_cents=r.revenue_cents,
                profit_cents=r.profit_cents,
                pep_cents=r.pep_cents,
                lawyers=r.lawyers,
                equity_partners=r.equity_partners,
                wip_cents=r.wip_cents,
                receivables_cents=r.receivables_cents,
                cash_cents=r.cash_cents,
                revolver_cents=r.revolver_cents,
                partner_ability=MergerRangeOut(lo=r.quality[0], hi=r.quality[1]),
                annuities_cents=MergerRangeOut(lo=r.annuities_cents[0], hi=r.annuities_cents[1]),
                leases_cents=MergerRangeOut(lo=r.leases_cents[0], hi=r.leases_cents[1]),
                conflicts=MergerRangeOut(lo=r.conflicts[0], hi=r.conflicts[1]),
                book_clients=r.book_clients,
                next_fee_cents=fee_cents(firm, balance),
            )
        t = d.terms
        deals.append(
            MergerDealOut(
                id=d.id,
                firm_key=d.rival_key,
                firm=firm.name if firm is not None else d.rival_key,
                form=d.form,
                initiator=d.initiator,
                stage=d.stage,
                opened=format_turn(d.opened_turn, start),
                leaked=d.leaked,
                absorbed=d.absorbed,
                diligence_running=d.diligence_due_turn is not None,
                diligence_fees_cents=d.diligence_fees_cents,
                reveal=rev,
                terms=MergerTermsOut(
                    our_share_pct=t.our_share_bp // 100,
                    name=t.name,
                    mp=t.mp,
                    comp_system=t.comp_system,
                    rates=t.rates,
                )
                if t is not None
                else None,
                counter_share_pct=d.counter_share_bp // 100 if d.counter_share_bp else None,
                their_yes_pct=d.their_yes_bp // 100 if d.their_yes_bp is not None else None,
                prediction=_prediction(state, d, data, balance),
                conflicts=[
                    MergerConflictOut(
                        our_client=state.market.client(c.our_client_id).name,
                        their_client=state.market.client(c.their_client_id).name,
                        matter_id=c.matter_id,
                        outcome=c.outcome,
                    )
                    for c in d.conflicts
                ],
                ended=format_turn(d.ended_turn, start) if d.ended_turn is not None else None,
                ended_reason=d.ended_reason,
            )
        )
    integrations = [
        MergerIntegrationOut(
            deal_id=i.deal_id,
            firm=i.name,
            closed=format_turn(i.closed_turn, start),
            until=format_turn(i.until_turn, start),
            months_left=max(0, i.until_turn - state.turn + 1),
            clash_pct=round(i.clash * 100),
            lawyers_at_closing=i.lawyers_at_closing,
            partners_at_closing=i.partners_at_closing,
            partners_lost=len(i.lost_partners),
            partners_lost_pct=round(
                100 * partners_lost_share(i, balance.mergers.integration.months)
            ),
            clients_lost=len(i.lost_clients),
            card_rise_pct=round(i.card_rise * 100),
            surrender_cents=i.surrender_cents,
        )
        for i in state.mergers.integrations
    ]
    v = state.mergers.verein
    verein = None
    if v is not None:
        members = []
        for key, joined in v.members:
            member = state.rivals.by_key(key)
            if member is None:
                continue
            side = rival_side(member, data)
            members.append(
                VereinMemberOut(
                    key=key,
                    name=member.name,
                    city=_city(data, member.hq),
                    joined=format_turn(joined, start),
                    lawyers=side.lawyers,
                    revenue_cents=side.revenue_cents,
                )
            )
        verein = VereinOut(
            name=v.name,
            formed=format_turn(v.formed_turn, start),
            members=members,
            costs_cents=v.costs_cents,
        )
    e = state.mergers.exit
    fp = state.partnership.of(pid)
    founder = state.founder_of(pid)
    energy = state.person_state(founder).energy if founder is not None else None
    costs = balance.energy.cost
    return MergersOut(
        targets=targets,
        deals=deals,
        integrations=integrations,
        verein=verein,
        exit=MergerExitOut(
            turn=format_turn(e.turn, start),
            firm=e.firm_name,
            capital_cents=e.capital_cents,
            earnings_cents=e.earnings_cents,
            rank=e.rank,
            revenue_cents=e.revenue_cents,
        )
        if e is not None
        else None,
        is_mp=fp is not None and founder is not None and fp.mp_id == founder,
        energy=energy or 0,
        costs={k: costs[k] for k in ("merger_approach", "merger_diligence", "merger_terms")},
        absorbed_below_pct=balance.mergers.absorbed_below_bp // 100,
        vote_pct=round(balance.mergers.vote_bp / 100),
        max_lawyers=balance.mergers.max_lawyers,
        comp_systems=["lockstep", "modified_lockstep", "eat_what_you_kill", "committee"],
    )


def _path(slug: str) -> Path:
    return saves.open_save(get_settings().resolved_save_dir(), slug)


def _view(path: Path) -> MergersOut:
    state = saves.read_state(path)[0]
    return mergers_out(state, loader.game_data(), loader.balance())


def _act(slug: str, make: Any) -> MergersOut:
    path = _path(slug)
    state = saves.read_state(path)[0]
    actor = state.founder_of(state.player.id)
    if actor is None:
        raise NotFoundError("the firm has no player partner")
    saves.run_action(path, make(actor), loader.balance(), loader.game_data())
    return _view(path)


def make_mergers_router(errors: dict[int | str, dict[str, Any]]) -> APIRouter:
    router = APIRouter()
    kw: dict[str, Any] = {"response_model": MergersOut, "responses": errors}
    base = "/api/saves/{slug}/mergers"

    @router.get(base, operation_id="getMergers", **kw)
    def get_mergers(slug: str) -> MergersOut:
        return _view(_path(slug))

    @router.post(f"{base}/approach", operation_id="approachFirm", **kw)
    def approach(slug: str, body: MergerApproachIn) -> MergersOut:
        return _act(
            slug, lambda a: ApproachFirm(actor_id=a, rival_key=body.rival_key, form=body.form)
        )

    @router.post(f"{base}/{{deal_id}}/answer", operation_id="answerApproach", **kw)
    def answer(slug: str, deal_id: int, body: MergerAnswerIn) -> MergersOut:
        return _act(slug, lambda a: AnswerApproach(actor_id=a, deal_id=deal_id, accept=body.accept))

    @router.post(f"{base}/{{deal_id}}/diligence", operation_id="commissionDiligence", **kw)
    def diligence(slug: str, deal_id: int) -> MergersOut:
        return _act(slug, lambda a: CommissionDiligence(actor_id=a, deal_id=deal_id))

    @router.post(f"{base}/{{deal_id}}/terms", operation_id="putTerms", **kw)
    def put_terms(slug: str, deal_id: int, body: MergerTermsIn) -> MergersOut:
        return _act(
            slug,
            lambda a: PutTerms(
                actor_id=a,
                deal_id=deal_id,
                our_share_bp=body.our_share_bp,
                name=body.name,
                mp=body.mp,
                comp_system=body.comp_system,
                rates=body.rates,
            ),
        )

    @router.post(f"{base}/{{deal_id}}/walk-away", operation_id="walkAway", **kw)
    def walk_away(slug: str, deal_id: int) -> MergersOut:
        return _act(slug, lambda a: WalkAway(actor_id=a, deal_id=deal_id))

    return router
