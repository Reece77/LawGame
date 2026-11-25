"""Frozen risk models (PT-M15; spec 11.3-11.6; ADR PT-0017). Never mutate.

Hidden true values (never in the API or a prompt, CLAUDE.md 10): a claim's `merit` and
`size_cents` (and every claim still `latent`), a disciplinary case's `culpability`. The API
shows a claim's demand, its stage, the merit as a range and the money paid; a case's stage,
cause and outcome.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

type ClaimSource = Literal["error", "grievance"]
type ClaimStage = Literal[
    "latent", "notice", "investigation", "defence", "offer", "trial", "closed"
]
type ClaimOutcome = Literal["dropped", "settled", "won", "lost"]
type ClaimChoice = Literal["settle", "contest"]
CLAIM_CHOICES: tuple[ClaimChoice, ...] = ("settle", "contest")

type CaseCause = Literal["padding", "conflicts", "trust", "court", "neglect", "supervision"]
type CaseStage = Literal["complaint", "investigation", "hearing", "closed"]
type CaseOutcome = Literal[
    "dismissed", "admonition", "reprimand", "fine", "suspension", "disbarment"
]
type CaseChoice = Literal["cooperate", "contest"]
CASE_CHOICES: tuple[CaseChoice, ...] = ("cooperate", "contest")

type InquiryStage = Literal["inquiry", "findings", "closed"]
type InquiryOutcome = Literal["dismissed", "settled", "fined"]
type InquiryChoice = Literal["settle", "contest"]
INQUIRY_CHOICES: tuple[InquiryChoice, ...] = ("settle", "contest")

type Supervision = Literal["standard", "lax"]
SUPERVISION: tuple[Supervision, ...] = ("standard", "lax")


@dataclass(frozen=True, slots=True)
class Claim:
    """A malpractice claim (spec 11.3): latent until it surfaces, then a case with visible
    stages; the policy in force at notice answers it (claims-made)."""

    id: int
    firm_id: int
    matter_id: int
    client_id: int
    practice: str
    source: ClaimSource
    created_turn: int  # the error (or the lost case) behind it
    surfaces_turn: int  # the notice arrives this month
    merit: float  # hidden: the claimant's true chance at trial, 0-1
    size_cents: int  # hidden: the damages a court would award
    demand_cents: int  # what the claimant asks (shown from notice)
    blamed_id: int | None = None  # the lawyer blamed (never a person flagged real)
    stage: ClaimStage = "latent"
    stage_until: int | None = None  # the stage's last month
    noticed_turn: int | None = None
    merit_lo: float = 0.0  # the GC's reading of the merit (shown)
    merit_hi: float = 1.0
    policy_id: int | None = None
    deductible_cents: int = 0  # the policy's terms at notice
    limit_cents: int = 0
    defence_cents: int = 0  # defence costs so far
    indemnity_cents: int = 0  # paid to the claimant
    deductible_paid_cents: int = 0  # the firm's part within the deductible
    insurer_paid_cents: int = 0  # the insurer's part, within the limit
    excess_paid_cents: int = 0  # the firm's part above the limit
    called_cents: int = 0  # capital called from the partners to pay the excess
    offer_cents: int = 0  # the claimant's open offer (0: none)
    offer_expires: int | None = None
    contested: bool = False  # the firm turned an offer down
    public: bool = False
    outcome: ClaimOutcome | None = None
    closed_turn: int | None = None

    @property
    def is_open(self) -> bool:
        return self.stage not in ("latent", "closed")

    @property
    def paid_cents(self) -> int:
        return self.defence_cents + self.indemnity_cents

    @property
    def firm_paid_cents(self) -> int:
        return self.deductible_paid_cents + self.excess_paid_cents


@dataclass(frozen=True, slots=True)
class Policy:
    """A year of professional indemnity insurance (spec 11.3): per claim, claims-made."""

    id: int
    firm_id: int
    insurer: str  # insurance.yaml key
    start_turn: int
    end_turn: int  # the first month of the next policy year
    limit_cents: int
    deductible_cents: int
    premium_cents: int  # the year's premium
    mod: float  # the experience modifier it was priced with (shown)
    rate_bp: int  # the market's rate that year (shown)
    exposure_cents: int  # the fees it was priced on (shown)
    lawyers: int = 0  # lawyers on the books at its start (the claims history's lawyer-years)
    paid_cents: int = 0  # premium paid so far (monthly instalments)


@dataclass(frozen=True, slots=True)
class PolicyTerms:
    """The terms the firm asks for at its next renewal (None: the default)."""

    insurer: str | None = None
    limit_cents: int | None = None
    deductible_cents: int | None = None


@dataclass(frozen=True, slots=True)
class DisciplinaryCase:
    """A case against a lawyer before the bar (spec 11.4): never a person flagged real."""

    id: int
    firm_id: int
    person_id: int
    cause: CaseCause
    jurisdiction: str  # bar_rules.yaml key
    opened_turn: int
    culpability: float  # hidden, 0-1
    stage: CaseStage = "complaint"
    stage_until: int | None = None
    choice: CaseChoice | None = None
    matter_id: int | None = None
    outcome: CaseOutcome | None = None
    suspended_until: int | None = None  # the first month back
    closed_turn: int | None = None

    @property
    def is_open(self) -> bool:
        return self.stage != "closed"


@dataclass(frozen=True, slots=True)
class Inquiry:
    """A regulator's inquiry into the firm's systems (spec 11.4; TST 48.3's case machinery)."""

    id: int
    firm_id: int
    jurisdiction: str
    reason: str  # trust, cases, conflicts
    opened_turn: int
    failures: int  # the failures it counts
    fine_lo_cents: int  # the range of the fine a finding would bring (shown)
    fine_hi_cents: int
    stage: InquiryStage = "inquiry"
    stage_until: int | None = None
    choice: InquiryChoice | None = None
    outcome: InquiryOutcome | None = None
    fine_cents: int = 0
    closed_turn: int | None = None

    @property
    def is_open(self) -> bool:
        return self.stage != "closed"


@dataclass(frozen=True, slots=True)
class Reconciliation:
    """A month's client-account reconciliation (ADR PT-0003 7)."""

    turn: int
    firm_id: int
    bank_cents: int  # the client bank as found
    owed_cents: int  # owed to clients
    shortfall_cents: int = 0
    cause: Literal["", "error", "misuse"] = ""
    person_id: int | None = None  # misuse: the lawyer (never a person flagged real)
    made_good_cents: int = 0  # replaced from firm money the same month


@dataclass(frozen=True, slots=True)
class Audit:
    """A client's e-billing audit of a bill (spec 11.6)."""

    bill_id: int
    turn: int
    firm_id: int
    client_id: int
    practice: str
    cut_cents: int
    padding_found_cents: int = 0


@dataclass(frozen=True, slots=True)
class Arbitration:
    """Fee arbitration of a held dispute (spec 7.7, 11.6)."""

    id: int
    bill_id: int
    firm_id: int
    client_id: int
    practice: str
    amount_cents: int  # the disputed amount
    filed_turn: int
    decide_turn: int
    award_cents: int = 0  # the reduction awarded to the client
    decided: bool = False


@dataclass(frozen=True, slots=True)
class FirmRisk:
    """A firm's risk settings and counters."""

    firm_id: int
    supervision: Supervision = "standard"
    terms: PolicyTerms = PolicyTerms()
    inquiry_cooldown_until: int = 0


@dataclass(frozen=True, slots=True)
class RiskState:
    claims: tuple[Claim, ...] = ()  # by id; latent ones hidden from views
    policies: tuple[Policy, ...] = ()  # by id: the current and past policy years
    cases: tuple[DisciplinaryCase, ...] = ()  # by id
    inquiries: tuple[Inquiry, ...] = ()  # by id
    reconciliations: tuple[Reconciliation, ...] = ()  # the last 12 per firm, by (firm, turn)
    audits: tuple[Audit, ...] = ()  # the last 24 months', by (turn, bill id)
    arbitrations: tuple[Arbitration, ...] = ()  # by id
    firms: tuple[FirmRisk, ...] = ()  # by firm id
    next_id: int = 1  # ids for claims, policies, cases, inquiries and arbitrations

    def firm(self, firm_id: int) -> FirmRisk:
        return next((f for f in self.firms if f.firm_id == firm_id), FirmRisk(firm_id))

    def policy(self, firm_id: int, turn: int) -> Policy | None:
        """The policy in force at `turn`."""
        return next(
            (
                p
                for p in self.policies
                if p.firm_id == firm_id and p.start_turn <= turn < p.end_turn
            ),
            None,
        )

    def claim(self, claim_id: int) -> Claim | None:
        return next((c for c in self.claims if c.id == claim_id), None)

    def case(self, case_id: int) -> DisciplinaryCase | None:
        return next((c for c in self.cases if c.id == case_id), None)

    def inquiry(self, inquiry_id: int) -> Inquiry | None:
        return next((i for i in self.inquiries if i.id == inquiry_id), None)

    def suspended_ids(self, turn: int) -> frozenset[int]:
        return frozenset(
            c.person_id
            for c in self.cases
            if c.suspended_until is not None
            and c.closed_turn is not None
            and c.closed_turn <= turn < c.suspended_until
        )

    def suspended(self, person_id: int, turn: int) -> bool:
        return any(
            c.person_id == person_id
            and c.suspended_until is not None
            and c.closed_turn is not None
            and c.closed_turn <= turn < c.suspended_until
            for c in self.cases
        )


EMPTY_RISK = RiskState()


def _put[T](items: tuple[T, ...], item: T, key: str = "id") -> tuple[T, ...]:
    k = getattr(item, key)
    kept = [x for x in items if getattr(x, key) != k]
    return tuple(sorted([*kept, item], key=lambda x: getattr(x, key)))


def with_claim(risk: RiskState, claim: Claim) -> RiskState:
    return replace(risk, claims=_put(risk.claims, claim))


def with_policy(risk: RiskState, policy: Policy) -> RiskState:
    return replace(risk, policies=_put(risk.policies, policy))


def with_case(risk: RiskState, case: DisciplinaryCase) -> RiskState:
    return replace(risk, cases=_put(risk.cases, case))


def with_inquiry(risk: RiskState, inquiry: Inquiry) -> RiskState:
    return replace(risk, inquiries=_put(risk.inquiries, inquiry))


def with_arbitration(risk: RiskState, arb: Arbitration) -> RiskState:
    return replace(risk, arbitrations=_put(risk.arbitrations, arb))


def with_firm(risk: RiskState, firm: FirmRisk) -> RiskState:
    return replace(risk, firms=_put(risk.firms, firm, "firm_id"))


def take_id(risk: RiskState) -> tuple[RiskState, int]:
    return replace(risk, next_id=risk.next_id + 1), risk.next_id


AUDITS_KEPT = 24  # tunable-exempt: months of audits the Risk screen shows


def keep_audits(risk: RiskState, new: list[Audit], turn: int) -> RiskState:
    kept = [a for a in risk.audits if a.turn > turn - AUDITS_KEPT]
    return replace(risk, audits=tuple(sorted([*kept, *new], key=lambda a: (a.turn, a.bill_id))))
