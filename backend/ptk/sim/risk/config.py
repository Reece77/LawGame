"""Schemas for PT-M15 (ADR-0008; ADR PT-0017): `risk.*` in balance.yaml and `insurance.yaml`
(the insurers, the policy options and the market's rate path). Model definitions only (no
imports from the rest of the sim), so `ptk.sim.data_models` can import them.

Sources and S/D/A tags for every number: docs/research/risk-and-ethics.md.
"""

from __future__ import annotations

from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

MONTHS_A_YEAR: Final = 12  # tunable-exempt: calendar

type InsurerKind = Literal["mutual", "commercial"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Span(_Strict):
    """An inclusive integer range (months, bp)."""

    lo: int = Field(ge=0)
    hi: int = Field(ge=0)

    @model_validator(mode="after")
    def _check(self) -> Span:
        if self.lo > self.hi:
            raise ValueError("span: lo <= hi")
        return self


class FloatSpan(_Strict):
    lo: float = Field(ge=0)
    hi: float = Field(ge=0)

    @model_validator(mode="after")
    def _check(self) -> FloatSpan:
        if self.lo > self.hi:
            raise ValueError("span: lo <= hi")
        return self


# --- balance.yaml `risk` -------------------------------------------------------------------


class ClaimStages(_Strict):
    """Months each visible stage lasts, drawn uniformly (spec 11.3)."""

    notice: Span
    investigation: Span
    defence: Span
    trial: Span


class ClaimsBalance(_Strict):
    from_error_bp: int = Field(ge=0, le=10000)
    # PT-M12: a practice's weight on from_error_bp (1.0 when not listed; docs/research/
    # risk-and-ethics.md section 2a)
    practice_weight: dict[str, float] = Field(default_factory=dict)
    grievance_min_stakes_cents: int = Field(ge=0)
    grievance_bp: int = Field(ge=0, le=10000)
    delay_months: Span
    merit: tuple[float, float]  # Beta(a, b): the claimant's true chance at trial
    size_fee_mult: FloatSpan  # deals, advisory, filings: x expected fees (log-uniform)
    size_stakes_share: FloatSpan  # cases: share of the stakes (log-uniform)
    size_min_cents: int = Field(ge=0)
    size_max_cents: int = Field(gt=0)
    demand_mult: FloatSpan  # what the claimant asks: the true size x U(range)
    stages: ClaimStages
    drop_bp: int = Field(ge=0, le=10000)  # a month in investigation, x (1 - merit)
    defence_bp: int = Field(ge=0, le=10000)  # defence costs a month, bp of the size
    defence_min_cents: int = Field(ge=0)
    defence_max_cents: int = Field(ge=0)
    offer_bp: int = Field(ge=0, le=10000)  # a month in defence: the claimant offers to settle
    offer_share: FloatSpan  # an offer is merit x size x U(range)
    offer_window: int = Field(gt=0)  # months to answer an offer
    trial_cost_mult: float = Field(ge=0)  # a trial's month costs this many defence months
    public_points: float = Field(le=0)  # reputation in the practice when a claim is filed
    public_min_cents: int = Field(ge=0)  # ... a claim filed with a demand above this is public
    relationship_points: float = Field(le=0)  # the claimant's relationship at notice
    merit_width: float = Field(gt=0, le=1)  # the merit range's half-width at a GC effect of 0
    merit_width_gc: float = Field(ge=0)  # ... narrowed by this x the GC's effect
    lax_mult: float = Field(ge=1)  # conversion x this under lax supervision
    gc_bp: int = Field(ge=0, le=10000)  # conversion x (1 - this x the GC's effect)
    checks_off_mult: float = Field(ge=1)  # conversion x this with conflict checks off


class InsuranceBalance(_Strict):
    exposure_floor_cents: int = Field(ge=0)  # a year's fees a lawyer at least (new firms)
    history_years: int = Field(gt=0)  # the claims history a renewal reads
    expected_per_100: float = Field(gt=0)  # claims a 100 lawyer-years the market expects
    count_weight: float = Field(ge=0)  # premium x (1 + this x (frequency / expected - 1))
    loss_weight: float = Field(ge=0)  # ... + this x (loss ratio - target)
    loss_target: float = Field(ge=0)
    mod: FloatSpan  # the experience modifier's bounds
    default_limit_per_lawyer_cents: int = Field(gt=0)  # the default limit: lawyers x this ...


class DisciplineCauses(_Strict):
    """A lawyer's monthly chance of a case by cause, bp at integrity 10 (spec 11.4)."""

    court: int = Field(ge=0, le=10000)  # misleading the court (litigators on a case matter)
    neglect: int = Field(ge=0, le=10000)  # any lawyer: a client's complaint to the bar
    padding_bp: int = Field(ge=0, le=10000)  # a padder found: chance of a case
    conflicts_bp: int = Field(ge=0, le=10000)  # a conflict surfaced: the lead's case
    supervision_bp: int = Field(ge=0, le=10000)  # a claim noticed: the lead's failure to supervise


class DisciplineStages(_Strict):
    complaint: Span
    investigation: Span
    hearing: Span


class DisciplineOutcome(_Strict):
    """Sanctions by culpability: a case found against the lawyer (u < culpability) takes the
    first band whose `min` the culpability reaches, from the top."""

    key: Literal["admonition", "reprimand", "fine", "suspension", "disbarment"]
    min: float = Field(ge=0, le=1)


class DisciplineBalance(_Strict):
    causes: DisciplineCauses
    integrity_slope: float = Field(ge=0)  # chance x exp(slope x (10 - integrity) / 10)
    rule_bender_mult: float = Field(ge=1)
    cowboy_mult: float = Field(ge=1)
    lax_mult: float = Field(ge=1)
    gc_bp: int = Field(ge=0, le=10000)  # chance x (1 - this x the GC's effect)
    culpability_sd: float = Field(ge=0)  # culpability = (20 - integrity) / 20 + N(0, sd)
    cooperate_bp: int = Field(ge=0, le=10000)  # cooperating: culpability x (1 - this)
    contest_cents: int = Field(ge=0)  # contesting: the firm's lawyers' costs (6600)
    contest_bp: int = Field(ge=0, le=10000)  # ... and culpability x (1 - this), or x (1 + this)
    stages: DisciplineStages
    outcomes: tuple[DisciplineOutcome, ...] = Field(min_length=1)
    suspension_months: Span
    morale_points: float = Field(le=0)  # the subject's morale at a sanction
    public_points: float = Field(le=0)  # reputation in the practice at a public sanction
    window: int = Field(gt=0)  # months to answer a case


class RegulatorBalance(_Strict):
    """Regulators' inquiries into the firm where its systems failed (spec 11.4)."""

    trust_bp: int = Field(ge=0, le=10000)  # a trust shortfall: chance of an inquiry
    cases_12m: int = Field(gt=0)  # this many disciplinary cases opened in 12 months ...
    cases_bp: int = Field(ge=0, le=10000)  # ... bring an inquiry with this chance
    conflict_bp: int = Field(ge=0, le=10000)  # a conflict surfaced with the checks off
    cooldown_months: int = Field(ge=0)  # a regulator waits this long after closing one
    found_bp: int = Field(ge=0, le=10000)  # a contested inquiry's chance of a finding, ...
    found_per_failure_bp: int = Field(ge=0, le=10000)  # ... + this per failure counted
    fine_share_bp: int = Field(ge=0, le=10000)  # the fine: this bp of a year's fees, capped
    settle_share_bp: int = Field(ge=0, le=10000)  # settling: this bp of the expected fine
    contest_cents: int = Field(ge=0)  # contesting: the firm's lawyers' costs (6600)
    public_points: float = Field(le=0)  # reputation (every practice) at a finding
    window: int = Field(gt=0)  # months to answer
    months: Span  # an inquiry lasts this long


class TrustBalance(_Strict):
    """The monthly client-account reconciliation (ADR PT-0003 7, spec 11.4)."""

    error_bp: int = Field(ge=0, le=10000)  # a month with client money: a posting error
    misuse_bp: int = Field(ge=0, le=10000)  # ... a lawyer's misuse, at integrity 10
    integrity_slope: float = Field(ge=0)  # misuse x exp(slope x (10 - integrity) / 10)
    share: FloatSpan  # the shortfall: this share of the money held (uniform)
    min_cents: int = Field(ge=0)
    gc_bp: int = Field(ge=0, le=10000)  # error x (1 - this x the GC's effect)
    lax_mult: float = Field(ge=1)  # misuse x this under lax supervision


class AuditsBalance(_Strict):
    """Clients' e-billing audits and fee disputes (spec 11.6, 7.7)."""

    from_ym: tuple[int, int]  # e-billing review spreads from this month
    audit_bp: int = Field(ge=0, le=10000)  # a large client's bill: chance of an audit
    audit_per_point_bp: int = Field(ge=0, le=10000)  # + this per price-sensitivity point > 10
    cut_share: FloatSpan  # an audit's cut for block billing, staffing and rates (uniform)
    overrun_mult: float = Field(ge=1)  # a bill on an overrun matter: dispute chance x this
    guideline_mult: float = Field(ge=1)  # a bill with a guideline rejection: x this
    review_bp: int = Field(ge=0, le=10000)  # the GC's billing review finds a padder: x e
    arbitration_bp: int = Field(ge=0, le=10000)  # a held dispute in range: the client files
    arbitration_months: Span
    award_share: FloatSpan  # an award cuts the disputed amount by this share (uniform)
    award_fee_bp: int = Field(ge=0, le=10000)  # ... when the arbitrator finds for the client
    public_min_cents: int = Field(ge=0)  # a held dispute above this goes public (a fee suit)
    public_points: float = Field(le=0)  # reputation in the practice


class RiskPolicyBalance(_Strict):
    """The firm's supervision policy (PT-M15): lax supervision frees partners' hours."""

    lax_hours: int = Field(ge=0)  # partners' non-billable hours a month freed by lax supervision


class RiskBalance(_Strict):
    enabled: bool = True
    claims: ClaimsBalance
    insurance: InsuranceBalance
    discipline: DisciplineBalance
    regulator: RegulatorBalance
    trust: TrustBalance
    audits: AuditsBalance
    policy: RiskPolicyBalance

    @model_validator(mode="after")
    def _check(self) -> RiskBalance:
        bands = [o.min for o in self.discipline.outcomes]
        if bands != sorted(bands):
            raise ValueError("risk.discipline.outcomes: min ascending")
        return self


# --- insurance.yaml ------------------------------------------------------------------------


class RatePoint(_Strict):
    """The market's premium rate: bp of a year's fees, linear between points, held after."""

    ym: tuple[int, int]
    rate_bp: int = Field(gt=0, le=10000)
    src: str = ""


class Insurer(_Strict):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    label: str = Field(min_length=1)
    kind: InsurerKind
    factor: float = Field(gt=0)  # premium x this
    min_premium_cents: int = Field(ge=0)
    min_lawyers: int = Field(ge=0)  # members or insureds of at least this size
    max_mod: float = Field(gt=0)  # declines a firm whose experience modifier is above this
    src: str = ""


class LimitOption(_Strict):
    cents: int = Field(gt=0)
    factor: float = Field(gt=0)  # premium x this


class DeductibleOption(_Strict):
    cents: int = Field(ge=0)
    factor: float = Field(gt=0)  # premium x this (a credit below 1)


class InsuranceData(_Strict):
    insurers: tuple[Insurer, ...] = ()
    limits: tuple[LimitOption, ...] = ()
    deductibles: tuple[DeductibleOption, ...] = ()
    rates: tuple[RatePoint, ...] = ()
    practice_rating: dict[str, float] = Field(default_factory=dict)  # 1.0 when not listed
    src: str = ""

    @model_validator(mode="after")
    def _check(self) -> InsuranceData:
        if not self.insurers:
            return self
        if not self.limits or not self.deductibles or not self.rates:
            raise ValueError("insurance.yaml: limits, deductibles and rates are required")
        if [x.cents for x in self.limits] != sorted({x.cents for x in self.limits}):
            raise ValueError("insurance.yaml: limits ascending and unique")
        if [x.cents for x in self.deductibles] != sorted({x.cents for x in self.deductibles}):
            raise ValueError("insurance.yaml: deductibles ascending and unique")
        if [r.ym for r in self.rates] != sorted({r.ym for r in self.rates}):
            raise ValueError("insurance.yaml: rate points by date")
        keys = [i.key for i in self.insurers]
        if len(keys) != len(set(keys)):
            raise ValueError("insurance.yaml: insurer keys unique")
        return self

    def insurer(self, key: str) -> Insurer:
        for i in self.insurers:
            if i.key == key:
                return i
        raise KeyError(key)

    def limit(self, cents: int) -> LimitOption | None:
        return next((x for x in self.limits if x.cents == cents), None)

    def deductible(self, cents: int) -> DeductibleOption | None:
        return next((x for x in self.deductibles if x.cents == cents), None)


# --- bar_rules.yaml: the disciplinary process (spec 11.1, 11.4) ------------------------------


class FineCap(_Strict):
    from_ym: tuple[int, int]
    cap_cents: int = Field(ge=0)  # 0: no fine on the firm
    src: str = ""


class DisciplineRule(_Strict):
    """A jurisdiction's disciplinary process: who investigates, whether firms are sanctioned
    (England and Wales: the SRA; New York disciplines firms too), the firm fine caps by date,
    and fee arbitration (New York's Part 137)."""

    body: str = ""  # who hears lawyers' cases
    firm_sanctions: bool = False
    firm_fine_caps: tuple[FineCap, ...] = ()
    individual_fines: bool = False  # lawyers can be fined (England and Wales)
    fee_arbitration: bool = False
    arbitration_min_cents: int = Field(default=0, ge=0)
    arbitration_max_cents: int = Field(default=0, ge=0)
    src: str = ""

    def fine_cap(self, ym: tuple[int, int]) -> int:
        cap = 0
        for c in self.firm_fine_caps:
            if c.from_ym <= ym:
                cap = c.cap_cents
        return cap
