"""Schemas for PT-M17's tunables (ADR-0008): `founder_life.*`, `family.*` and `succession.*`
in balance.yaml. Model definitions only (no imports from the rest of the sim), so
`ptk.sim.data_models` can import them without a cycle.

Ported from backend/tst/sim/founder/config.py and backend/tst/sim/family/config.py
@ 121d318a (Tech Startup Tycoon); changed: one module for both packages' tunables; the
personal book has Partner Track's income (draws, the true-up, capital returned, annuities),
a capital loan and an income tax on the profit share; persona sources are spec 2.3's; the
foundation's causes add access to justice and drop climate; influence is bar politics, with
no lobbying spend by region and no scandal; the family's university is law school; the
estate tax is the US federal history; succession and retirement are Partner Track's.
"""

from __future__ import annotations

from typing import Final

from pydantic import BaseModel, ConfigDict, Field, model_validator

TRAITS: Final = ("visionary", "ruthless", "beloved", "reckless")  # TST 32.4, display order
CAUSES: Final = ("access_to_justice", "education", "health", "local")  # spec 2.3, TST 32.3
# Spec 2.3: what raises each trait, as founder_life.persona.sources keys (points each time).
SOURCES: Final[dict[str, str]] = {
    "new_practice": "visionary",  # a practice group opened in a practice the firm lacked
    "first_region": "visionary",  # a new region (v2's offices; no source yet)
    "early_ai": "visionary",  # early AI adoption (v2's eras; no source yet)
    "deequitisation": "ruthless",  # a de-equitisation passed
    "hostile_lateral": "ruthless",  # a lateral partner hired from a rival firm
    "layoffs": "ruthless",  # persona.layoff_share or more of the firm fired in a month
    "pro_bono": "beloved",  # December: pro bono at or above persona.pro_bono_tenths a lawyer
    "raises": "beloved",  # raises to persona.raise_share or more of the staff in a month
    "comp_fairness": "beloved",  # December: no equity partner unhappy with their share
    "guarantee": "reckless",  # a guarantee given (a lateral's or a counter-offer's)
    "revolver_leverage": "reckless",  # a month drawn above persona.leverage_share of the facility
    "covenant_breach": "reckless",  # a covenant breached (the first month)
    "broken_claim": "reckless",  # a broken public claim (PT-M16's press; no source yet)
}
SETTINGS: Final = ("none", "partner", "children")  # TST 45.1's Family setting
SCHOOLS: Final = ("standard", "elite")  # at 12
LAW_SCHOOLS: Final = ("none", "standard", "top")  # at 18 (Partner Track: college, then law)
READINESS: Final = ("not_ready", "developing", "ready", "strong")  # TST 45.4's bands
STATUSES: Final = ("managing_partner", "partner", "senior_partner", "retired", "left")


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class FounderEnergy(_Frozen):
    """Energy each founder action spends (TST 32.3's 5 for a foundation)."""

    foundation: int = Field(ge=0)
    gift: int = Field(ge=0)
    committee: int = Field(ge=0)  # a month on a bar committee (spent each month while on it)
    stand: int = Field(ge=0)  # stand for bar office
    invest: int = Field(ge=0)
    family_office: int = Field(ge=0)
    education: int = Field(ge=0)
    mentor: int = Field(ge=0)  # a month mentoring a child at the firm
    successor: int = Field(ge=0)  # name a successor (the election)
    plan: int = Field(ge=0)  # name a successor-designate (the plan)
    trust: int = Field(ge=0)
    gift_heir: int = Field(ge=0)


class PersonalBalance(_Frozen):
    """TST 32.2: the founder's own book; ADR PT-0003 4-5 (tax, the capital loan)."""

    tax_rate: float = Field(ge=0, lt=1)  # on the founder's profit share as it is paid out
    start_cents: int = Field(ge=0)  # the founder's savings at the start
    successor_start_cents: int = Field(ge=0)  # a successor's savings when their book opens
    loan_rate: float = Field(ge=0, lt=1)  # the capital loan's yearly rate
    loan_months: int = Field(ge=1)  # principal repaid over this many months (a share a month)
    invest_return: float  # self-managed investments: the yearly expected return
    invest_vol: float = Field(ge=0)  # sd of the monthly return
    history: int = Field(ge=1)  # months of income statements kept


class MandateBalance(_Frozen):
    """TST 37.4: one family-office mandate."""

    expected: float  # yearly return
    vol: float = Field(ge=0)  # sd of the month's return


class FamilyOfficeBalance(_Frozen):
    min_cents: int = Field(gt=0)  # personal wealth to form one
    fee: float = Field(ge=0, lt=1)  # a year, on the balance
    mandates: dict[str, MandateBalance]

    @model_validator(mode="after")
    def _check(self) -> FamilyOfficeBalance:
        if sorted(self.mandates) != sorted(("conservative", "balanced", "aggressive")):
            raise ValueError("family_office.mandates must be conservative, balanced, aggressive")
        return self


class PersonaBalance(_Frozen):
    """TST 32.4: four public traits, their sources and their effects at `effect_at`."""

    start: float = Field(ge=0, le=100)
    drift: float = Field(ge=0)  # points a month toward start
    effect_at: float = Field(ge=0, le=100)
    history: int = Field(ge=1)  # causes shown
    sources: dict[str, float]  # points each time, by SOURCES key
    layoff_share: float = Field(gt=0, le=1)
    raise_share: float = Field(gt=0, le=1)
    pro_bono_tenths: float = Field(ge=0)  # a lawyer a month (the firm's moving average)
    leverage_share: float = Field(gt=0, le=1)
    leverage_year_cap: float = Field(ge=0)  # revolver_leverage points at most a calendar year
    # Effects (spec 2.3, TST 32.4's in PT units): partner confidence a month, recruiting
    visionary_recruiting: float = Field(ge=0)  # offer-score points (TST's +0.03 appeal)
    ruthless_confidence: float = Field(le=0)  # confidence points a month (TST: morale -2)
    beloved_resign: float = Field(gt=0, le=1)  # resignation chance x this (TST's 0.9)
    beloved_confidence: float = Field(ge=0)
    reckless_confidence: float = Field(le=0)  # (TST: lenders' rates +1 point)
    heir_share: float = Field(ge=0, le=1)  # a successor starts at start + this x the parent's

    @model_validator(mode="after")
    def _check(self) -> PersonaBalance:
        if sorted(self.sources) != sorted(SOURCES):
            raise ValueError(f"persona.sources must define exactly {sorted(SOURCES)}")
        return self


class FoundationBalance(_Frozen):
    """TST 32.3: the foundation and its yearly grants."""

    min_cents: int = Field(gt=0)
    payout: float = Field(gt=0, le=1)
    beloved_cap: float = Field(ge=0)
    beloved_k: float = Field(ge=0)
    beloved_unit_dollars: int = Field(gt=0)
    recruiting: float = Field(ge=0)  # education, local: offer-score points at full grants
    recruiting_full_dollars: int = Field(gt=0)
    resign: float = Field(gt=0, le=1)  # access to justice, health: resignation chance x this
    effect_months: int = Field(ge=1)
    legacy_unit_dollars: int = Field(gt=0)


class InfluenceBalance(_Frozen):
    """TST 32.5 as bar politics: committees, bar office, and spend on bar politics (6950)."""

    committee: float = Field(ge=0)  # points a month on a committee
    rate: float = Field(ge=0)  # points a month per sqrt(spend / unit)
    unit_dollars: int = Field(gt=0)
    max_monthly_dollars: int = Field(gt=0)
    decay: float = Field(ge=0, lt=1)
    cap: float = Field(gt=0, le=100)
    office_at: float = Field(ge=0, le=100)  # influence to stand for bar office
    office_month: int = Field(ge=1, le=12)  # the bar's elections
    office_years: int = Field(ge=1)
    office_win_at: float = Field(ge=0, le=100)  # influence that wins outright
    office_bonus: float = Field(ge=0)  # influence points a month in office
    recruiting: float = Field(ge=0)  # offer-score points at influence 100
    confidence: float = Field(ge=0)  # partner confidence a month at influence 100
    legacy_per_year: float = Field(ge=0)  # legacy points per year in bar office


class LegacyBalance(_Frozen):
    """TST 32.6 in PT terms: the firm, the name on the door, the foundation, the family."""

    firm_points: float = Field(ge=0)  # x log10(1 + best year's revenue / unit)
    firm_unit_dollars: int = Field(gt=0)
    name_points: float = Field(ge=0)
    child_partner_points: float = Field(ge=0)
    family_successor_points: float = Field(ge=0)


class AnnuityBalance(_Frozen):
    """Spec 8.4, 8.6: retired partners' annuities, as the agreement grants (default none)."""

    granted: bool
    share_bp: int = Field(ge=0, le=10_000)  # tunable-exempt: basis points
    years: int = Field(ge=1)
    max_share_bp: int = Field(ge=0, le=10_000)  # tunable-exempt: basis points


class FounderLifeBalance(_Frozen):
    energy: FounderEnergy
    personal: PersonalBalance
    family_office: FamilyOfficeBalance
    persona: PersonaBalance
    foundation: FoundationBalance
    influence: InfluenceBalance
    legacy: LegacyBalance
    annuity: AnnuityBalance


class Span(_Frozen):
    lo: float
    hi: float

    @model_validator(mode="before")
    @classmethod
    def _pair(cls, value: object) -> object:
        if isinstance(value, list | tuple) and len(value) == 2:  # tunable-exempt: a pair
            return {"lo": value[0], "hi": value[1]}
        return value

    @model_validator(mode="after")
    def _order(self) -> Span:
        if self.lo > self.hi:
            raise ValueError("a span's lo must not exceed its hi")
        return self


class EducationBalance(_Frozen):
    """TST 45.3: the education multiplier `e` and each tier's cost (cents)."""

    school_age: int = Field(ge=1)
    law_school_age: int = Field(ge=1)
    qualify_age: int = Field(ge=1)  # law school's multiplier applies until this age
    mult: dict[str, float]  # school_<tier>, law_<tier>
    cents: dict[str, int]  # elite_school, law_standard, law_top
    reveal: float = Field(ge=0, lt=1)

    @model_validator(mode="after")
    def _check(self) -> EducationBalance:
        need = {f"school_{s}" for s in SCHOOLS} | {f"law_{u}" for u in LAW_SCHOOLS}
        if set(self.mult) != need:
            raise ValueError(f"family.education.mult must define {sorted(need)}")
        if set(self.cents) != {"elite_school", "law_standard", "law_top"}:
            raise ValueError("family.education.cents must define elite_school, law_*")
        if not self.school_age < self.law_school_age < self.qualify_age:
            raise ValueError("family.education ages must rise")
        return self


class EstateYear(_Frozen):
    year: int
    rate: float = Field(ge=0, lt=1)
    exemption_cents: int = Field(ge=0)


class FamilyBalance(_Frozen):
    """TST 45.1-45.3, 45.6 (the partner, children, education, estate tax) and 45.4's
    readiness, for a child in the firm."""

    default_time: int = Field(ge=0)
    max_time: int = Field(gt=0)
    calm: float = Field(ge=0)  # strain points a month at max_time
    bond: float = Field(ge=0)
    bond_pivot: float = Field(gt=0)
    burnout_strain: float = Field(ge=0)
    relationship_start: float = Field(ge=0, le=100)
    closeness_start: float = Field(ge=0, le=100)
    divorce_below: float = Field(ge=0, le=100)
    divorce_months: int = Field(ge=1)
    divorce_share: float = Field(ge=0, le=1)
    divorce_beloved: float = Field(ge=0)
    inherit: float = Field(ge=0, le=1)
    trait_noise_sd: float = Field(ge=0)
    partner_rate: float = Field(ge=0)  # a year
    partner_ages: Span
    partner_strain_below: float = Field(ge=0, le=100)
    partner_age_sd: float = Field(ge=0)
    marriage_months: int = Field(ge=0)
    child_rate: float = Field(ge=0)  # a year
    child_parent_age_max: int = Field(ge=1)
    max_children: int = Field(ge=0)
    start_child_ages: Span
    child_pa: Span
    child_skill_birth: float = Field(ge=1)
    child_skill_year: float = Field(ge=0)
    child_skill_sd: float = Field(ge=0)
    child_growth: float = Field(ge=0)  # skill points a year toward potential, before e
    develop_from: int = Field(ge=0)
    milestones: tuple[int, ...]
    reveal_rate: float = Field(ge=0, lt=1)
    pa_hw_floor: float = Field(gt=0)
    education: EducationBalance
    join_closeness: float = Field(ge=0, le=100)
    mentor_growth: float = Field(ge=0)  # leadership skill points a month while mentored
    mentor_closeness: float = Field(ge=0)
    nepotism_confidence: float = Field(le=0)  # partners' confidence when a child is promoted
    merit_confidence: float = Field(ge=0)
    estate: tuple[EstateYear, ...] = Field(min_length=1)
    trust_setup_cents: int = Field(ge=0)
    history: int = Field(ge=1)  # family notes kept

    @model_validator(mode="after")
    def _check(self) -> FamilyBalance:
        if self.default_time > self.max_time:
            raise ValueError("family.default_time must not exceed family.max_time")
        if list(self.milestones) != sorted(set(self.milestones)):
            raise ValueError("family.milestones must rise")
        years = [e.year for e in self.estate]
        if years != sorted(set(years)):
            raise ValueError("family.estate years must rise")
        return self


class SuccessionBalance(_Frozen):
    """Spec 2.5; TST 45.5 (play the heir, the adviser, health)."""

    plan_from_age: int = Field(ge=1)  # from this age the partnership expects a plan
    no_plan_confidence: float = Field(le=0)  # confidence points a month without one
    grace_months: int = Field(ge=0)  # at mandatory retirement: months to name a successor
    quality_weight: float = Field(ge=0)  # a candidate's rating against the rival's, in a vote
    quality_scale: float = Field(gt=0)  # rating points per unit of utility
    endorse_weight: float = Field(ge=0)  # the founder's confidence carries to their candidate
    retry_months: int = Field(ge=0)  # after a lost succession vote, before naming again
    step_back_from: int = Field(ge=1)  # TST 45.5's health from this age
    step_back_rate: float = Field(ge=0, le=1)
    persona_reset: bool  # the successor's persona starts from persona.start
    adviser_oppose: float = Field(ge=0)  # confidence points when the MP overrules the adviser
    adviser_memory: int = Field(ge=1)
    risky_votes: tuple[str, ...]  # vote kinds a bold adviser backs
