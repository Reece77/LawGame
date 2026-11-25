"""Risk endpoints and schemas (PT-M15; spec 11.3-11.6, 16).

The Risk screen reads one view: the insurance policy in force (insurer, limit, deductible,
premium, what was paid, the experience modifier and the market's rate it was priced on, the
renewal month) with the terms asked for at the next renewal and the market's options; the
claims the firm has been notified of, each with its stage, the claimant's demand and open offer,
the general counsel's reading of its merit as a range, and the money paid by the firm (within
the deductible and above the limit) and by the insurer; disciplinary cases against the firm's
lawyers; regulators' inquiries with the fine's range; the client account's reconciliations;
clients' e-billing audits; fee arbitrations; the supervision policy.

Never in a schema (CLAUDE.md 10): a claim's merit or size, a claim not yet surfaced, a case's
culpability, any chance or draw. Every write is one player action (ADR-0014), logged to
`decision_log`, and returns the fresh view.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel

from ptk import loader
from ptk.config import get_settings
from ptk.db import saves
from ptk.sim.actions import Action
from ptk.sim.calendar import format_turn
from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import NotFoundError
from ptk.sim.risk.actions import (
    RespondCase,
    RespondClaim,
    RespondInquiry,
    SetPolicyTerms,
    SetSupervision,
)
from ptk.sim.risk.inquiries import regulator_label
from ptk.sim.risk.insurance import compulsory_limit_cents
from ptk.sim.state import GameState

MONTHS = 12  # tunable-exempt


class PolicyOut(BaseModel):
    id: int
    insurer: str
    insurer_kind: str
    start_label: str
    renews_label: str
    limit_cents: int
    deductible_cents: int
    premium_cents: int
    paid_cents: int
    premium_per_lawyer_cents: int
    mod: float  # the experience modifier it was priced with (1 = the market's average)
    rate_bp: int  # the market's premium rate that year, bp of fees
    exposure_cents: int


class OptionOut(BaseModel):
    cents: int
    factor: float


class InsurerOut(BaseModel):
    key: str
    label: str
    kind: str
    min_lawyers: int


class TermsOut(BaseModel):
    insurer: str | None
    limit_cents: int | None
    deductible_cents: int | None


class MalpracticeClaimOut(BaseModel):
    id: int
    matter_id: int
    matter: str
    client: str
    practice: str
    source: str
    stage: str
    stage_label: str  # the current stage's planned end, or ""
    noticed_label: str
    demand_cents: int
    merit_lo_pct: int  # the GC's reading of the claimant's chance at trial
    merit_hi_pct: int
    offer_cents: int
    offer_expires_label: str
    defence_cents: int
    indemnity_cents: int
    deductible_paid_cents: int
    insurer_paid_cents: int
    excess_paid_cents: int
    called_cents: int
    limit_cents: int
    deductible_cents: int
    public: bool
    blamed: str
    outcome: str | None
    closed_label: str


class CaseOut(BaseModel):
    id: int
    person_id: int
    name: str
    cause: str
    jurisdiction: str
    stage: str
    opened_label: str
    choice: str | None
    outcome: str | None
    suspended_until_label: str
    closed_label: str


class InquiryOut(BaseModel):
    id: int
    regulator: str
    reason: str
    stage: str
    opened_label: str
    ends_label: str
    fine_lo_cents: int
    fine_hi_cents: int
    choice: str | None
    outcome: str | None
    fine_cents: int


class ReconciliationOut(BaseModel):
    label: str
    bank_cents: int
    owed_cents: int
    shortfall_cents: int
    cause: str
    made_good_cents: int


class AuditOut(BaseModel):
    label: str
    bill_id: int
    client: str
    practice: str
    cut_cents: int
    padding_found_cents: int


class ArbitrationOut(BaseModel):
    id: int
    bill_id: int
    client: str
    amount_cents: int
    filed_label: str
    decide_label: str
    award_cents: int
    decided: bool


class RiskScreenOut(BaseModel):
    enabled: bool
    supervision: str
    policy: PolicyOut | None
    terms: TermsOut
    insurers: list[InsurerOut]
    limits: list[OptionOut]
    deductibles: list[OptionOut]
    compulsory_limit_cents: int
    claims: list[MalpracticeClaimOut]
    cases: list[CaseOut]
    inquiries: list[InquiryOut]
    reconciliations: list[ReconciliationOut]
    audits: list[AuditOut]
    arbitrations: list[ArbitrationOut]
    claims_12m: int  # claims noticed in the last 12 months
    lawyers: int


class TermsIn(BaseModel):
    insurer: str | None = None
    limit_cents: int | None = None
    deductible_cents: int | None = None


class SupervisionIn(BaseModel):
    supervision: Literal["standard", "lax"]


class ChoiceIn(BaseModel):
    choice: str


def _label(state: GameState, turn: int | None) -> str:
    return "" if turn is None else format_turn(turn, state.save_meta.start_ym)


def _name(state: GameState, person_id: int | None) -> str:
    if person_id is None:
        return ""
    p = state.person(person_id)
    return f"{p.first_name} {p.last_name}"


def risk_out(state: GameState, data: GameData, balance: Balance) -> RiskScreenOut:
    from ptk.sim.risk.common import lawyers

    firm = state.player.id
    risk = state.risk
    n = len(lawyers(state, firm, data))
    p = risk.policy(firm, state.turn)
    policy = None
    if p is not None:
        ins = next((i for i in data.insurance.insurers if i.key == p.insurer), None)
        policy = PolicyOut(
            id=p.id,
            insurer=ins.label if ins else p.insurer,
            insurer_kind=ins.kind if ins else "",
            start_label=_label(state, p.start_turn),
            renews_label=_label(state, p.end_turn),
            limit_cents=p.limit_cents,
            deductible_cents=p.deductible_cents,
            premium_cents=p.premium_cents,
            paid_cents=p.paid_cents,
            premium_per_lawyer_cents=p.premium_cents // max(1, p.lawyers or n),
            mod=p.mod,
            rate_bp=p.rate_bp,
            exposure_cents=p.exposure_cents,
        )
    terms = risk.firm(firm).terms
    claims = []
    for c in risk.claims:
        if c.firm_id != firm or c.stage == "latent":  # a claim not yet surfaced is hidden
            continue
        m = state.market.matter(c.matter_id)
        claims.append(
            MalpracticeClaimOut(
                id=c.id,
                matter_id=c.matter_id,
                matter=m.name if m is not None else "",
                client=state.market.client(c.client_id).name,
                practice=c.practice,
                source=c.source,
                stage=c.stage,
                stage_label=_label(state, c.stage_until),
                noticed_label=_label(state, c.noticed_turn),
                demand_cents=c.demand_cents,
                merit_lo_pct=round(c.merit_lo * 100),
                merit_hi_pct=round(c.merit_hi * 100),
                offer_cents=c.offer_cents,
                offer_expires_label=_label(state, c.offer_expires),
                defence_cents=c.defence_cents,
                indemnity_cents=c.indemnity_cents,
                deductible_paid_cents=c.deductible_paid_cents,
                insurer_paid_cents=c.insurer_paid_cents,
                excess_paid_cents=c.excess_paid_cents,
                called_cents=c.called_cents,
                limit_cents=c.limit_cents,
                deductible_cents=c.deductible_cents,
                public=c.public,
                blamed=_name(state, c.blamed_id),
                outcome=c.outcome,
                closed_label=_label(state, c.closed_turn),
            )
        )
    cases = [
        CaseOut(
            id=c.id,
            person_id=c.person_id,
            name=_name(state, c.person_id),
            cause=c.cause,
            jurisdiction=regulator_label(data, c.jurisdiction),
            stage=c.stage,
            opened_label=_label(state, c.opened_turn),
            choice=c.choice,
            outcome=c.outcome,
            suspended_until_label=_label(state, c.suspended_until),
            closed_label=_label(state, c.closed_turn),
        )
        for c in risk.cases
        if c.firm_id == firm
    ]
    inquiries = [
        InquiryOut(
            id=i.id,
            regulator=regulator_label(data, i.jurisdiction),
            reason=i.reason,
            stage=i.stage,
            opened_label=_label(state, i.opened_turn),
            ends_label=_label(state, i.stage_until),
            fine_lo_cents=i.fine_lo_cents,
            fine_hi_cents=i.fine_hi_cents,
            choice=i.choice,
            outcome=i.outcome,
            fine_cents=i.fine_cents,
        )
        for i in risk.inquiries
        if i.firm_id == firm
    ]
    recs = [
        ReconciliationOut(
            label=_label(state, r.turn),
            bank_cents=r.bank_cents,
            owed_cents=r.owed_cents,
            shortfall_cents=r.shortfall_cents,
            cause=r.cause,
            made_good_cents=r.made_good_cents,
        )
        for r in risk.reconciliations
        if r.firm_id == firm
    ]
    audits = [
        AuditOut(
            label=_label(state, a.turn),
            bill_id=a.bill_id,
            client=state.market.client(a.client_id).name,
            practice=a.practice,
            cut_cents=a.cut_cents,
            padding_found_cents=a.padding_found_cents,
        )
        for a in risk.audits
        if a.firm_id == firm
    ]
    arbs = [
        ArbitrationOut(
            id=a.id,
            bill_id=a.bill_id,
            client=state.market.client(a.client_id).name,
            amount_cents=a.amount_cents,
            filed_label=_label(state, a.filed_turn),
            decide_label=_label(state, a.decide_turn),
            award_cents=a.award_cents,
            decided=a.decided,
        )
        for a in risk.arbitrations
        if a.firm_id == firm
    ]
    since = state.turn - MONTHS
    return RiskScreenOut(
        enabled=balance.risk.enabled,
        supervision=risk.firm(firm).supervision,
        policy=policy,
        terms=TermsOut(
            insurer=terms.insurer,
            limit_cents=terms.limit_cents,
            deductible_cents=terms.deductible_cents,
        ),
        insurers=[
            InsurerOut(key=i.key, label=i.label, kind=i.kind, min_lawyers=i.min_lawyers)
            for i in data.insurance.insurers
        ],
        limits=[OptionOut(cents=x.cents, factor=x.factor) for x in data.insurance.limits],
        deductibles=[OptionOut(cents=x.cents, factor=x.factor) for x in data.insurance.deductibles],
        compulsory_limit_cents=compulsory_limit_cents(state, firm, data),
        claims=claims[::-1],
        cases=cases[::-1],
        inquiries=inquiries[::-1],
        reconciliations=recs[::-1],
        audits=audits[::-1],
        arbitrations=arbs[::-1],
        claims_12m=sum(
            1
            for c in risk.claims
            if c.firm_id == firm and c.noticed_turn is not None and c.noticed_turn > since
        ),
        lawyers=n,
    )


# --- Router -------------------------------------------------------------------------------------


def _path(slug: str) -> Path:
    return saves.open_save(get_settings().resolved_save_dir(), slug)


def _view(path: Path) -> RiskScreenOut:
    state = saves.read_state(path)[0]
    return risk_out(state, loader.game_data(), loader.balance())


def _act(slug: str, build: Any) -> RiskScreenOut:
    path = _path(slug)
    state = saves.read_state(path)[0]
    actor = state.founder_of(state.player.id)
    if actor is None:
        raise NotFoundError("the firm has no founding partner to act")
    action: Action = build(actor)
    saves.run_action(path, action, loader.balance(), loader.game_data())
    return _view(path)


def make_risk_router(errors: dict[int | str, dict[str, Any]]) -> APIRouter:
    router = APIRouter()
    base = "/api/saves/{slug}/risk"
    kw: dict[str, Any] = {"response_model": RiskScreenOut, "responses": errors}

    @router.get(base, operation_id="getRisk", **kw)
    def get_risk(slug: str) -> RiskScreenOut:
        return _view(_path(slug))

    @router.post(f"{base}/terms", operation_id="setPolicyTerms", **kw)
    def terms(slug: str, body: TermsIn) -> RiskScreenOut:
        return _act(
            slug,
            lambda a: SetPolicyTerms(a, body.insurer, body.limit_cents, body.deductible_cents),
        )

    @router.post(f"{base}/supervision", operation_id="setSupervision", **kw)
    def supervision(slug: str, body: SupervisionIn) -> RiskScreenOut:
        return _act(slug, lambda a: SetSupervision(a, body.supervision))

    @router.post(f"{base}/claims/{{claim_id}}/respond", operation_id="respondClaim", **kw)
    def respond_claim(slug: str, claim_id: int, body: ChoiceIn) -> RiskScreenOut:
        return _act(slug, lambda a: RespondClaim(a, claim_id, body.choice))

    @router.post(f"{base}/cases/{{case_id}}/respond", operation_id="respondCase", **kw)
    def respond_case(slug: str, case_id: int, body: ChoiceIn) -> RiskScreenOut:
        return _act(slug, lambda a: RespondCase(a, case_id, body.choice))

    @router.post(f"{base}/inquiries/{{inquiry_id}}/respond", operation_id="respondInquiry", **kw)
    def respond_inquiry(slug: str, inquiry_id: int, body: ChoiceIn) -> RiskScreenOut:
        return _act(slug, lambda a: RespondInquiry(a, inquiry_id, body.choice))

    return router
