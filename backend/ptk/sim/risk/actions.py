"""Risk actions (ADR-0014: they take effect at once; PT-M15).

- `SetPolicyTerms`: the insurer, limit and deductible the firm asks for at its next renewal
  (None: the default). A limit below a compulsory minimum (England and Wales) is refused.
- `SetSupervision`: the firm's supervision policy, standard or lax (lax frees partners'
  non-billable hours and raises claims, discipline and misuse; spec 11.4).
- `RespondClaim`: settle a claim for the claimant's open offer, or contest it.
- `RespondCase`: cooperate with the bar or contest a lawyer's case (contesting pays the firm's
  lawyers, 6600).
- `RespondInquiry`: settle a regulator's inquiry (the fine at once, 6970) or contest it.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Literal

from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import RiskActionError
from ptk.sim.hiring.actions import Outcome, acting_firm
from ptk.sim.risk import claims as cl
from ptk.sim.risk import discipline as dc
from ptk.sim.risk import inquiries as iq
from ptk.sim.risk.common import Books, with_risk
from ptk.sim.risk.insurance import compulsory_limit_cents
from ptk.sim.risk.models import (
    CASE_CHOICES,
    CLAIM_CHOICES,
    INQUIRY_CHOICES,
    SUPERVISION,
    ClaimChoice,
    PolicyTerms,
    Supervision,
    with_claim,
    with_firm,
)
from ptk.sim.state import GameState


@dataclass(frozen=True, slots=True)
class SetPolicyTerms:
    actor_id: int
    insurer: str | None = None
    limit_cents: int | None = None
    deductible_cents: int | None = None
    kind: Literal["set_policy_terms"] = "set_policy_terms"


@dataclass(frozen=True, slots=True)
class SetSupervision:
    actor_id: int
    supervision: str
    kind: Literal["set_supervision"] = "set_supervision"


@dataclass(frozen=True, slots=True)
class RespondClaim:
    actor_id: int
    claim_id: int
    choice: str
    kind: Literal["respond_claim"] = "respond_claim"


@dataclass(frozen=True, slots=True)
class RespondCase:
    actor_id: int
    case_id: int
    choice: str
    kind: Literal["respond_case"] = "respond_case"


@dataclass(frozen=True, slots=True)
class RespondInquiry:
    actor_id: int
    inquiry_id: int
    choice: str
    kind: Literal["respond_inquiry"] = "respond_inquiry"


type RiskAction = SetPolicyTerms | SetSupervision | RespondClaim | RespondCase | RespondInquiry

RISK_ACTION_TYPES: dict[str, type[Any]] = {
    "set_policy_terms": SetPolicyTerms,
    "set_supervision": SetSupervision,
    "respond_claim": RespondClaim,
    "respond_case": RespondCase,
    "respond_inquiry": RespondInquiry,
}


def _books(state: GameState, firm: int, cash: int) -> Books:
    return Books(firm, state.turn, cash)


def apply_risk_action(
    state: GameState,
    action: RiskAction,
    balance: Balance,
    data: GameData,
    cash: int,
) -> Outcome:
    firm = acting_firm(state, action.actor_id)
    if not balance.risk.enabled:
        raise RiskActionError("risk is switched off")
    books = _books(state, firm, cash)
    risk = state.risk
    match action:
        case SetPolicyTerms():
            ins = data.insurance
            if action.insurer is not None and action.insurer not in {i.key for i in ins.insurers}:
                raise RiskActionError(f"unknown insurer {action.insurer!r}")
            if action.limit_cents is not None and ins.limit(action.limit_cents) is None:
                raise RiskActionError("the limit must be one of the market's options")
            if (
                action.deductible_cents is not None
                and ins.deductible(action.deductible_cents) is None
            ):
                raise RiskActionError("the deductible must be one of the market's options")
            if action.limit_cents is not None and action.limit_cents < compulsory_limit_cents(
                state, firm, data
            ):
                raise RiskActionError("the limit is below a compulsory minimum (England and Wales)")
            terms = PolicyTerms(action.insurer, action.limit_cents, action.deductible_cents)
            state = with_risk(state, with_firm(risk, replace(risk.firm(firm), terms=terms)))
        case SetSupervision():
            if action.supervision not in SUPERVISION:
                raise RiskActionError(f"supervision is one of {SUPERVISION}")
            sup: Supervision = "lax" if action.supervision == "lax" else "standard"
            state = with_risk(state, with_firm(risk, replace(risk.firm(firm), supervision=sup)))
        case RespondClaim():
            claim = risk.claim(action.claim_id)
            if claim is None or claim.firm_id != firm or not claim.is_open:
                raise RiskActionError(f"no open claim {action.claim_id}")
            if action.choice not in CLAIM_CHOICES:
                raise RiskActionError(f"a claim is answered by {CLAIM_CHOICES}")
            if claim.stage != "offer":
                raise RiskActionError("the claimant has made no offer to answer")
            choice: ClaimChoice = "settle" if action.choice == "settle" else "contest"
            state, claim = cl.answer_offer(state, claim, choice, books)
            state = with_risk(state, with_claim(state.risk, claim))
        case RespondCase():
            case = risk.case(action.case_id)
            if case is None or case.firm_id != firm or not case.is_open:
                raise RiskActionError(f"no open case {action.case_id}")
            if action.choice not in CASE_CHOICES or case.choice is not None:
                raise RiskActionError(f"a case is answered once, by {CASE_CHOICES}")
            state = dc.respond(
                state,
                case,
                "contest" if action.choice == "contest" else "cooperate",
                books,
                balance,
            )
        case RespondInquiry():
            inquiry = risk.inquiry(action.inquiry_id)
            if inquiry is None or inquiry.firm_id != firm or not inquiry.is_open:
                raise RiskActionError(f"no open inquiry {action.inquiry_id}")
            if action.choice not in INQUIRY_CHOICES or inquiry.choice is not None:
                raise RiskActionError(f"an inquiry is answered once, by {INQUIRY_CHOICES}")
            state = iq.respond(
                state, inquiry, "settle" if action.choice == "settle" else "contest", books, balance
            )
    return Outcome(state, tuple(books.entries), tuple(books.logs))
