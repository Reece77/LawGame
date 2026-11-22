"""Pydantic schemas for balance and seed data (ADR-0008). Invalid data fails at load."""

from __future__ import annotations

from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ptk.sim.automation.config import AutomationBalance
from ptk.sim.events.data import (
    ColleaguesBalance,
    EventsBalance,
    EventTemplate,
    template_problems,
)
from ptk.sim.founder.config import FamilyBalance, FounderLifeBalance, SuccessionBalance
from ptk.sim.macro_data import SERIES as MACRO_SERIES
from ptk.sim.macro_data import MacroBalance, MacroData
from ptk.sim.org.seat_data import AuthorityBalance, PitchesBalance, SeatDef, SeatsBalance, SeatsData
from ptk.sim.rivals.data import RivalsBalance, RivalsData, WorldBalance

type AccountType = Literal["asset", "liability", "equity", "income", "expense"]
type PersonKind = Literal["lawyer", "paralegal", "business_services"]
type Version = Literal["v1", "v2", "v3"]

_KEY = r"^[a-z][a-z0-9_]*$"

# ADR PT-0006 section 1: the career ladder. Balance must define each exactly once.
LEVELS: Final = (
    "paralegal",
    "trainee",
    "associate_1",
    "associate_2",
    "associate_3",
    "associate_4",
    "associate_5",
    "associate_6",
    "associate_7",
    "associate_8",
    "senior_associate",
    "counsel",
    "income_partner",
    "equity_partner",
    "staff",
    "manager",
    "director",
    "chief",
)
PARTNER_LEVELS: Final = frozenset({"income_partner", "equity_partner"})
BUSINESS_SERVICES_LEVELS: Final = ("staff", "manager", "director", "chief")  # bill nothing
# PT-M1b: associates are paid on the class-year scale (senior associates as class 8); equity
# partners take profit, not salary (spec 5.4); everyone else is paid from a band.
SCALE_LEVELS: Final = (
    "associate_1",
    "associate_2",
    "associate_3",
    "associate_4",
    "associate_5",
    "associate_6",
    "associate_7",
    "associate_8",
    "senior_associate",
)
OFF_SCALE_LEVELS: Final = (
    "paralegal",
    "trainee",
    "counsel",
    "income_partner",
    "staff",
    "manager",
    "director",
    "chief",
)
# Knowledge actions that narrow revealed ranges (formulas.md 4; PT keeps TST's first six).
REVEAL_ACTIONS: Final = (
    "job_post_screen",
    "network_intro",
    "interview",
    "reference_check",
    "scouting_month",
    "employed_month",
)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Account(_Strict):
    code: str
    name: str
    type: AccountType
    book: Literal["firm", "client"] = "firm"

    @model_validator(mode="after")
    def _code_matches_book(self) -> Account:
        if (self.book == "client") != self.code.startswith("C"):
            raise ValueError(f"account {self.code}: client-book codes start with C, others not")
        return self


class StaffSpec(_Strict):
    """One generated person a scenario starts with."""

    role: str
    level: str
    practice: str | None = None  # a paralegal's home practice; lawyers take their role's


class CoFounderSpec(_Strict):
    background: str
    age: int


class Jurisdiction(_Strict):
    key: str = Field(pattern=_KEY)
    label: str = Field(min_length=1)


class Scenario(_Strict):
    id: str
    name: str
    description: str
    available: bool = True
    start_ym: tuple[int, int] = (2005, 1)  # ADR PT-0002: turn 0
    home_city: str
    partners_capital_cents: int = Field(ge=0)  # founders' capital paid in at turn 0
    revolver_limit_cents: int = Field(ge=0)  # used from PT-M4
    home_jurisdiction: str  # every lawyer's bar admission (spec 2.1)
    default_background: str  # the player's founding partner unless chosen
    co_founders: tuple[CoFounderSpec, ...] = ()
    starting_staff: tuple[StaffSpec, ...] = ()

    @field_validator("start_ym")
    @classmethod
    def _month(cls, value: tuple[int, int]) -> tuple[int, int]:
        if not 1 <= value[1] <= 12:  # tunable-exempt: months in a year
            raise ValueError("start month must be 1..12")
        return value


class Difficulty(_Strict):
    id: str
    name: str
    capital_mult_bp: int = Field(gt=0)
    # PT-M7b (difficulty teeth): x the founders' books, x the revolver (its facility and its
    # January floor), points on the founders' clients' starting relationships (0-100), x the
    # new firm's starting card (rates.card.start_bp)
    books_mult_bp: int = Field(default=10000, gt=0)
    revolver_mult_bp: int = Field(default=10000, gt=0)
    loyalty_points: float = Field(default=0.0, ge=-50, le=50)
    card_mult_bp: int = Field(default=10000, gt=0)


class CampaignBalance(_Strict):
    standard_turns: int = Field(gt=0)  # 360: January 2005 to December 2034


class BackupBalance(_Strict):
    every_turns: int = Field(gt=0)
    keep_periodic: int = Field(gt=0)


# --- People (PT-M1a) -----------------------------------------------------------------------


class Span(_Strict):
    """An inclusive [min, max] pair, written in YAML as a two-item list."""

    lo: float
    hi: float

    @model_validator(mode="before")
    @classmethod
    def _from_list(cls, value: object) -> object:
        if isinstance(value, list | tuple):
            if len(value) != 2:  # tunable-exempt: a pair
                raise ValueError("expected [min, max]")
            return {"lo": value[0], "hi": value[-1]}
        return value

    @model_validator(mode="after")
    def _ordered(self) -> Span:
        if self.lo > self.hi:
            raise ValueError(f"min {self.lo} is greater than max {self.hi}")
        return self


class AgeBand(_Strict):
    from_age: int = Field(ge=0)
    value: float


def _check_bands(bands: tuple[AgeBand, ...], name: str) -> None:
    if not bands or bands[0].from_age != 0:
        raise ValueError(f"{name}: the first band must start at from_age 0")
    ages = [b.from_age for b in bands]
    if ages != sorted(set(ages)):
        raise ValueError(f"{name}: from_age values must be strictly increasing")


def band_value(bands: tuple[AgeBand, ...], age: int) -> float:
    """Value of the last band whose from_age <= age."""
    value = bands[0].value
    for band in bands:
        if age >= band.from_age:
            value = band.value
    return value


class LevelCA(_Strict):
    mean: float
    sd: float = Field(ge=0)


class LevelDef(_Strict):
    kind: PersonKind
    ca: LevelCA
    age: Span
    capacity_hours: int = Field(gt=0)  # hours a year
    billable_target_hours: int = Field(ge=0)  # hours a year
    home_familiarity: Span | None = None  # lawyers and paralegals
    next_level: str | None = None  # the class year reached in September

    @model_validator(mode="after")
    def _check(self) -> LevelDef:
        if (self.kind == "business_services") != (self.home_familiarity is None):
            raise ValueError("home_familiarity is set for lawyers and paralegals only")
        return self


class SkillNoise(_Strict):
    primary: float = Field(ge=0)
    secondary: float = Field(ge=0)


class PeopleBalance(_Strict):
    levels: dict[str, LevelDef]
    ca_clip: Span
    skill_noise_sd: SkillNoise
    secondary_offset: float
    other_skill_range: Span
    ca_tolerance: float = Field(gt=0)
    pa_gap_mean: tuple[AgeBand, ...]
    pa_gap_sd: float = Field(ge=0)
    personality_mean: float
    personality_sd: float = Field(ge=0)
    interest_count: Span
    max_tags: int = Field(ge=0)
    school_tier_weights: dict[str, float]
    other_familiarity: Span
    portability_bp: Span
    class_year_month: int = Field(ge=1, le=12)
    initial_strain: Span

    @model_validator(mode="after")
    def _check(self) -> PeopleBalance:
        if list(self.levels) != list(LEVELS):
            raise ValueError(f"people.levels must define exactly {list(LEVELS)}, in order")
        for key, level in self.levels.items():
            if level.next_level is not None and level.next_level not in self.levels:
                raise ValueError(f"level {key}: unknown next_level {level.next_level!r}")
        _check_bands(self.pa_gap_mean, "pa_gap_mean")
        weights = self.school_tier_weights.values()
        if any(w < 0 for w in weights) or not any(w > 0 for w in weights):
            raise ValueError("school_tier_weights need a positive weight and none negative")
        return self


class LearnBalance(_Strict):
    reference_share: float = Field(gt=0, le=1)
    clamp: Span


class GrowthBalance(_Strict):
    rate: float = Field(ge=0)
    age_factor: tuple[AgeBand, ...]
    decline: tuple[AgeBand, ...]
    noise_rel_sd: float = Field(ge=0)
    learn: LearnBalance

    @model_validator(mode="after")
    def _check(self) -> GrowthBalance:
        _check_bands(self.age_factor, "age_factor")
        _check_bands(self.decline, "decline")
        return self


class FamiliarityBalance(_Strict):
    per_100h: float = Field(ge=0)
    taper_from: float = Field(ge=1, lt=20)
    decay_per_month: float = Field(ge=0)
    floor_below_peak: float = Field(ge=0)
    factor_at_one: float = Field(gt=0, le=1)
    full_at: float = Field(gt=1, le=20)


class StrainBalance(_Strict):
    load: float = Field(ge=0)
    comfort_base: float = Field(gt=0)
    comfort_per_stamina: float = Field(ge=0)
    stamina_neutral: float
    risk_base: float = Field(ge=0)
    risk_divisor: float = Field(gt=0)
    grinder_load: float = Field(ge=0)
    recover: float = Field(ge=0)
    holiday: float = Field(ge=0)
    sabbatical: float = Field(ge=0)
    burnout_at: float = Field(gt=0, le=100)
    burnout_exit: float = Field(ge=0)
    burnout_capacity: float = Field(gt=0, le=1)
    burnout_effect_months: int = Field(ge=0)
    founder_start: float = Field(ge=0, le=100)

    @model_validator(mode="after")
    def _check(self) -> StrainBalance:
        if self.burnout_exit >= self.burnout_at:
            raise ValueError("strain.burnout_exit must be below burnout_at")
        return self


class InitialHalfWidth(_Strict):
    skill: float = Field(ge=0)
    personality: float = Field(ge=0)
    pa: float = Field(ge=0)
    familiarity: float = Field(ge=0)


class RevealBalance(_Strict):
    initial_hw: InitialHalfWidth
    strength: dict[str, float]
    pa_strength: dict[str, float]
    scout_base: float
    scout_divisor: float = Field(gt=0)
    pa_scout_divisor: float = Field(gt=0)
    pa_scout_clamp: Span
    founder_pa_hw: float = Field(ge=0)
    pa_phrase_bounds: tuple[float, ...]

    @model_validator(mode="after")
    def _check(self) -> RevealBalance:
        for name, table in (("strength", self.strength), ("pa_strength", self.pa_strength)):
            if sorted(table) != sorted(REVEAL_ACTIONS):
                raise ValueError(f"{name} must define exactly {list(REVEAL_ACTIONS)}")
            if any(not 0 <= s <= 1 for s in table.values()):
                raise ValueError(f"{name} values must be fractions in [0, 1]")
        if list(self.pa_phrase_bounds) != sorted(self.pa_phrase_bounds):
            raise ValueError("pa_phrase_bounds must be increasing")
        return self


class FounderBalance(_Strict):
    skill_base: float
    skill_points: int = Field(ge=0)
    skill_cap: float
    default_age: int
    age_range: Span
    familiar_range: Span
    book_round_to_cents: int = Field(gt=0)

    @model_validator(mode="after")
    def _check(self) -> FounderBalance:
        if not self.age_range.lo <= self.default_age <= self.age_range.hi:
            raise ValueError("default_age must be within age_range")
        if self.skill_base > self.skill_cap:
            raise ValueError("skill_base must not exceed skill_cap")
        return self


# --- Hiring, pay, morale and resignations (PT-M1b) -----------------------------------------

ENERGY_ACTIONS: Final = (
    "interview",
    "reference_check",
    "scout",
    "referral",
    "job_post",
    "recruiter",
    "campus",
    "offer",
    "withdraw_offer",
    "close_search",
    "pay_policy",
    "staff",
    "seek_waiver",
    "introduce",
    "settlement",
    "conflict_policy",
    "forum",
    "write_down",  # PT-M3b: a partner writes a matter's next bill down
    "dispute",  # PT-M3b: answer a billing dispute
    "pitch",  # PT-M5: pitch for an RFP
    "approach_rival",  # PT-M5: approach a rival's key people
    # PT-M4: the partnership
    "propose_terms",
    "capital_call",
    "propose_partner",
    "deequity",
    "lobby",
    "promise",
    "withdraw_vote",
    "draws",
    "comp_round",
    "sponsor",
    "lateral_search",
    "diligence",
    "lateral_offer",
    "counter",
    "repay_revolver",
    "election_choice",
    # PT-M7a
    "case_assessment",  # early case assessment on a case (spec 7.6)
    "pro_bono_policy",  # the firm's pro bono credit policy (spec 7.8)
    "rate_policy",  # the firm's yearly rate rise
    # PT-M8
    "appoint_seat",  # appoint, replace or vacate a seat holder (spec 9.1)
    "seat_authority",  # give or take a seat's authority, or set its guardrails (TST 24.1)
    "exco_term",  # propose the agreement's exco_elected term for the December vote (spec 9.2)
    "answer_pitch",  # approve or decline a seat holder's pitch (TST 27.1)
    "hours_policy",  # PT-M7b: the firm's billable target
    "lay_off",  # PT-M10: let an associate or a member of staff go (TST's fire)
)
LATERAL_CHANNELS: Final = ("referral", "job_post", "recruiter")


class EnergyBalance(_Strict):
    per_month: int = Field(ge=0)
    cost: dict[str, int]

    @model_validator(mode="after")
    def _check(self) -> EnergyBalance:
        if sorted(self.cost) != sorted(ENERGY_ACTIONS):
            raise ValueError(f"energy.cost must define exactly {list(ENERGY_ACTIONS)}")
        if any(c < 0 for c in self.cost.values()):
            raise ValueError("energy costs must not be negative")
        return self


class HintBands(_Strict):
    lo: float
    hi: float


class OfferBalance(_Strict):
    w_salary: float
    w_fit: float
    w_risk: float
    k: float = Field(gt=0)
    threshold: float


class AskBalance(_Strict):
    noise_sd: float = Field(ge=0)
    round_to_cents: int = Field(gt=0)
    tier_bp: dict[str, int]


class RecruiterFeeBalance(_Strict):
    junior: int = Field(ge=0)
    senior: int = Field(ge=0)


class ChannelBalance(_Strict):
    size: Span
    knowledge: tuple[str, ...] = ()
    sociability_threshold: float | None = None
    sociability_bonus: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _check(self) -> ChannelBalance:
        if bad := sorted(set(self.knowledge) - set(REVEAL_ACTIONS)):
            raise ValueError(f"unknown knowledge actions {bad}")
        return self


class HiringBalance(_Strict):
    candidate_shelf_turns: int = Field(gt=0)
    lowball_ratio: float = Field(gt=0)
    hint_bands: HintBands
    offer: OfferBalance
    pitch_per_recruiting: float
    prestige_term: float
    ask: AskBalance
    recruiter_fee_bp: RecruiterFeeBalance
    recruiter_senior_from: str
    job_post_cost_cents: int = Field(ge=0)
    channels: dict[str, ChannelBalance]
    level_mix: dict[PersonKind, dict[str, float]]

    @model_validator(mode="after")
    def _check(self) -> HiringBalance:
        if sorted(self.channels) != sorted(LATERAL_CHANNELS):
            raise ValueError(f"hiring.channels must define exactly {list(LATERAL_CHANNELS)}")
        for kind in ("lawyer", "paralegal", "business_services"):
            mix = self.level_mix.get(kind)
            if not mix or any(w < 0 for w in mix.values()) or not any(mix.values()):
                raise ValueError(f"hiring.level_mix.{kind} needs positive weights")
            if bad := sorted(set(mix) - set(LEVELS)):
                raise ValueError(f"hiring.level_mix.{kind}: unknown levels {bad}")
        if self.recruiter_senior_from not in LEVELS:
            raise ValueError("hiring.recruiter_senior_from must be a level")
        return self


class CampusBalance(_Strict):
    register_months: Span
    pool_month: int = Field(ge=1, le=12)
    summer_months: Span
    offer_month: int = Field(ge=1, le=12)
    start_month: int = Field(ge=1, le=12)
    level: str
    per_tier: dict[str, int]
    knowledge: tuple[str, ...]
    summer_pay_bp: int = Field(ge=0)

    @model_validator(mode="after")
    def _check(self) -> CampusBalance:
        if not (
            self.register_months.hi <= self.pool_month < self.summer_months.lo
            and self.summer_months.hi < self.offer_month < 12  # tunable-exempt: December
        ):
            raise ValueError("campus months must run register <= pool < summer < offer")
        if self.level not in LEVELS:
            raise ValueError("campus.level must be a level")
        if any(n < 0 for n in self.per_tier.values()):
            raise ValueError("campus.per_tier counts must not be negative")
        if bad := sorted(set(self.knowledge) - set(REVEAL_ACTIONS)):
            raise ValueError(f"campus.knowledge: unknown actions {bad}")
        return self


class PayPolicyLimits(_Strict):
    min_bp: int = Field(gt=0)
    max_bp: int = Field(gt=0)


OVERHEADS: Final = ("support_staff", "technology", "insurance", "general_admin")


class PayBalance(_Strict):
    benefits_bp: int = Field(ge=0)
    rent_per_head_cents: int = Field(ge=0)
    # PT-M7: a month's overhead per lawyer on the books by kind (spec 6's margin norms)
    overhead_per_lawyer_cents: dict[str, int]
    city_bp: dict[str, int]
    policy: PayPolicyLimits
    bonus_month: int = Field(ge=1, le=12)
    discretionary_bonus_bp: dict[str, int]
    severance_months: int = Field(ge=0)  # PT-M10: a layoff's months of salary

    @model_validator(mode="after")
    def _overheads(self) -> PayBalance:
        if (
            sorted(self.overhead_per_lawyer_cents) != sorted(OVERHEADS)
            or min(self.overhead_per_lawyer_cents.values()) < 0
        ):
            raise ValueError(f"pay.overhead_per_lawyer_cents must give each of {OVERHEADS}")
        return self

    def city(self, city: str) -> int:
        """A city's pay and rent multiplier in bp (10000 where none is listed)."""
        return self.city_bp.get(city, 10_000)  # tunable-exempt: 100% in bp


class MoraleBalance(_Strict):
    new_hire: float = Field(ge=0, le=100)
    start: float = Field(ge=0, le=100)
    target_base: float
    rate: float = Field(ge=0, le=1)
    noise_scale: float = Field(ge=0)
    pay_slope: float
    pay_min: float
    pay_max: float
    interest_per_match: float
    interest_weight_from: float
    hours_over_from: float
    hours_over_slope: float
    hours_idle_below: float
    hours_idle: float
    prospects_levels: tuple[str, ...]
    prospects_no_sponsor: float
    prospects_sponsor: float
    bonus_slope: float
    bonus_min: float
    bonus_max: float
    layoff_penalty: float = Field(le=0)  # PT-M10: morale points to everyone remaining, per layoff


class ResignBalance(_Strict):
    base_bp: float = Field(ge=0)
    morale_floor: float
    morale_divisor: float = Field(gt=0)
    loyalty_divisor: float = Field(gt=0)
    job_hopper_mult: float = Field(ge=0)
    burnout_mult: float = Field(ge=0)
    lifer_loyalty_floor: float
    cap_bp: float = Field(ge=0)
    lateral_market_heat: float = Field(ge=0)
    associate_months: dict[int, float]
    partner_months: dict[int, float]


class TagRevealBalance(_Strict):
    reveal_bp_per_month: float = Field(ge=0)
    reveal_bp_on_check: float = Field(ge=0)


# --- Org (PT-M2; TST formulas.md 13) --------------------------------------------------------


class ReorgMorale(_Strict):
    """One-off morale points for reorganising (TST 13.7)."""

    move: float
    new_leader_members: float
    replaced_leader: float
    dissolve_members: float


class DelegatesBalance(_Strict):
    """Delegated hiring (TST 13.10, ADR-0015): each delegate's own energy and its costs."""

    energy_per_month: int = Field(gt=0)
    reserve: int = Field(ge=0)  # kept back while interviewing, for a scouting pass
    max_ratio_bp: int = Field(gt=0)
    plan_owner_roles: tuple[str, ...]  # roles that may own a plan without leading a unit


class OrgBalance(_Strict):
    practice_group_unlock_lawyers: int = Field(gt=0)
    span_base: int = Field(ge=0)
    span_per_leadership: float = Field(gt=0)
    manager_morale_slope: float
    manager_morale_cap: float = Field(ge=0)
    manager_label_bands: Span
    mentoring_neutral: float
    mentoring_divisor: float = Field(gt=0)
    mentor_tag_bonus: float
    growth_mult_min: float = Field(gt=0)
    growth_mult_max: float = Field(gt=0)
    reorg: ReorgMorale
    raise_morale: float
    raise_threshold_bp: int = Field(ge=0)
    raise_cooldown_turns: int = Field(ge=0)
    pay_cut_morale: float
    promote_morale: float
    promote_to: dict[str, str]  # level -> the level one promotion reaches (ADR PT-0006 1)
    pitch_per_recruiting: float
    pitch_neutral: float
    delegates: DelegatesBalance

    @model_validator(mode="after")
    def _check(self) -> OrgBalance:
        if self.growth_mult_min > self.growth_mult_max:
            raise ValueError("growth_mult_min must not exceed growth_mult_max")
        unknown = (set(self.promote_to) | set(self.promote_to.values())) - set(LEVELS)
        if unknown:
            raise ValueError(f"promote_to names unknown levels {sorted(unknown)}")
        if set(self.promote_to.values()) & PARTNER_LEVELS:
            raise ValueError("a promotion never makes a partner (the partnership vote, PT-M4)")
        return self


# --- Clients and matters balance (PT-M3a) ------------------------------------------------------


class LogNormalSpan(_Strict):
    median: float = Field(gt=0)
    sigma: float = Field(ge=0)
    min: float = Field(gt=0)
    max: float = Field(gt=0)


class ClientsBalance(_Strict):
    generated_count: int = Field(ge=0)
    size_exponent: float = Field(gt=0)
    generated_revenue_bn: LogNormalSpan
    large_revenue_bn: float = Field(gt=0)
    panel_large: tuple[int, int]
    panel_mid: tuple[int, int]
    price_sensitivity: Span
    loyalty: Span
    gc_age: tuple[int, int]


class BooksBalance(_Strict):
    start_relationship: Span
    max_client_share: float = Field(gt=0, le=1)
    max_clients: int = Field(gt=0)


class AppealWeights(_Strict):
    relationship: float
    reputation: float
    price: float
    capacity: float
    conflict: float


class AppealBalance(_Strict):
    large: AppealWeights
    mid: AppealWeights
    rival_strong: float
    rate_ref_band: str


class MattersBalance(_Strict):
    named_min_cents: int = Field(gt=0)
    key_named_min_cents: int = Field(gt=0)
    key_clients: int = Field(ge=0)
    flow_fill: float = Field(gt=0, le=1.5)
    max_load: float = Field(gt=0)
    partner_other_hours: int = Field(ge=0)
    flow_min_familiarity: float = Field(ge=1, le=20)
    conflicted_window_turns: int = Field(ge=0)
    lead_share_min: float = Field(ge=0, le=1)
    staff_round_tenths: int = Field(gt=0)
    substantive_window: int = Field(ge=0)
    max_slip_months: int = Field(ge=0)
    forum_change_turns: int = Field(ge=0)


class StaffingBalance(_Strict):
    """PT-M7a: the default rule plans for each member's expected output an hour."""

    output_floor: float = Field(gt=0, le=1)
    output_cap: float = Field(ge=1)
    plan_fill: float = Field(gt=0, le=1.5)
    # PT-M7b: the firm's hours policy (a firm-wide billable target, hours a year)
    policy_min_hours: int = Field(gt=0)
    policy_max_hours: int = Field(gt=0)
    policy_fill_max: float = Field(ge=1, le=1.5)  # the most of capacity the policy may plan


class ProBonoKindDef(_Strict):
    practice: str = Field(pattern=_KEY)
    kind: str = Field(pattern=_KEY)  # a practices.yaml matter kind key of that practice
    label: str = Field(min_length=1)
    weight: float = Field(gt=0)


class ProBonoBalance(_Strict):
    """PT-M7a: pro bono (spec 7.8)."""

    credit_hours: int = Field(ge=0)  # the default credit policy, hours a year
    credit_max_hours: int = Field(ge=0)
    uncredited_hours: float = Field(ge=0)
    uptake: float = Field(ge=0)
    flow_fill: float = Field(gt=0, le=1.5)
    named_bp_per_lawyer: float = Field(ge=0)
    named_hours: Span
    named_months: tuple[int, int]
    named_kinds: tuple[ProBonoKindDef, ...] = Field(min_length=1)
    morale_full_hours: float = Field(gt=0)
    morale_max: float = Field(ge=0)
    morale_levels: tuple[str, ...]
    appeal_per_hour: float = Field(ge=0)
    appeal_max: float = Field(ge=0)
    average_rate: float = Field(gt=0, le=1)


class AssessmentBalance(_Strict):
    """PT-M7a: early case assessment (spec 7.6)."""

    lead_hours: int = Field(ge=0)
    half_width: float = Field(gt=0)  # logit points at the lead's skill 10
    skill_slope: float = Field(ge=0)  # share of the half-width lost per 10 skill points over 10
    min_half_width: float = Field(gt=0)
    skills: dict[str, float]
    centre_share: float = Field(
        ge=0, lt=1
    )  # the true merits sit within this share of the half-width of the centre


class CardBalance(_Strict):
    """PT-M7b: a new firm's rate card by practice, a share of the practices' 2005 cards."""

    start_bp: int = Field(gt=0, le=10000)  # a new firm's share of the top card in each practice
    full_reputation: float = Field(gt=0, le=1)  # reputation (0-1) at which the target is 100%
    curve: float = Field(gt=0)  # target = start + (1 - start) x (rep / full)^curve
    step_bp: int = Field(gt=0)  # most a practice's share moves toward its target each January


class RatesBalance(_Strict):
    """PT-M7a: the firm's yearly rate rise (bp a year; the market's is rivals.rate_inflation)."""

    rise_min_bp: int
    rise_max_bp: int
    month: int = Field(ge=1, le=12)
    card: CardBalance  # PT-M7b


class HolidayBalance(_Strict):
    """PT-M7a: Holiday and continue-until (spec 4.2)."""

    max_months: int = Field(gt=0)
    default_months: int = Field(gt=0)


class OutcomesBalance(_Strict):
    case_k: float = Field(gt=0)
    merits_sd: float = Field(ge=0)
    opposing_mean: float = Field(ge=1, le=20)
    opposing_sd: float = Field(ge=0)
    big_moments: float
    prep: float = Field(ge=0)
    craft_skills: dict[str, float]
    deal_skills: dict[str, float]
    deal_base: float
    deal_k: float = Field(ge=0)
    critical_deal: float
    stakes_mult: Span


class ErrorsBalance(_Strict):
    base_bp: int = Field(ge=0)
    strain_slope: float = Field(ge=0)
    burnout_mult: float = Field(ge=1)
    cowboy_mult: float = Field(ge=1)
    max_bp: int = Field(gt=0, le=10000)
    catch_bp: int = Field(ge=0, le=10000)
    rework_share: float = Field(ge=0)
    deadline_miss_bp: int = Field(ge=0, le=10000)


class ProgressBalance(_Strict):
    strain_from: float = Field(ge=0, lt=100)
    strain_output: float = Field(ge=0, le=1)
    under_pace: float = Field(ge=0, le=1)


class JudgesBalance(_Strict):
    speed: float = Field(ge=0, lt=1)
    discovery: float = Field(ge=0)
    settlement: float = Field(ge=0)
    trial: float = Field(ge=0)
    settlement_floor: float = Field(gt=0)
    summary_judgment_bp: int = Field(ge=0, le=10000)
    summary_judgment: float = Field(ge=0)
    sanctions: float = Field(ge=0)
    procedure: float = Field(ge=0)
    appearance_full_hours: int = Field(gt=0)
    appearance_bonus: float = Field(ge=0)


class SettlementBalance(_Strict):
    base_bp: int = Field(ge=0, le=10000)
    discount: float = Field(gt=0, le=1)
    view_sd: float = Field(ge=0)
    window_turns: int = Field(gt=0)


class RelationshipsBalance(_Strict):
    drift_to: float = Field(ge=0, le=100)
    drift: float = Field(ge=0, le=1)
    win: float
    loss: float
    settle: float
    critical_mult: float = Field(ge=0)
    service: float
    strain: float
    strain_at: float
    care: float
    breadth: float
    breadth_cap: float = Field(ge=0)
    conflict_refused: float
    waiver_asked: float
    positional: float
    escaped_error: float
    missed_deadline: float
    disqualified: float


class CrossSellBalance(_Strict):
    base: float
    affinity: float
    relationship: float
    bd: float
    care: float
    failure: float
    cooldown_turns: int = Field(ge=0)


class ConflictsBalance(_Strict):
    current_months: int = Field(gt=0)
    former_months: int = Field(gt=0)
    waiver_base: float
    waiver_relationship: float
    waiver_gc: float
    advance_penalty: float
    hidden_surface_bp: int = Field(ge=0, le=10000)


class AgeStep(_Strict):
    from_months: int = Field(ge=0)
    value: int = Field(ge=0, le=10000)


class BillingBalance(_Strict):
    """PT-M3b (spec 7.7; ADR PT-0003, PT-0005)."""

    models: dict[str, dict[str, float]]
    quarterly_bp: int = Field(ge=0, le=10000)
    discount_base_bp: int = Field(ge=0, le=10000)
    discount_per_point_bp: int = Field(ge=0, le=10000)
    discount_max_bp: int = Field(ge=0, le=10000)
    blended_mult: float = Field(gt=0)
    cap_mult: tuple[float, float]
    fixed_mult: tuple[float, float]
    retainer_mult: tuple[float, float]
    success_share_bp: int = Field(ge=0, le=10000)
    success_bonus_bp: int = Field(ge=0)
    contingency_bp: tuple[int, int]
    recovery_bp: int = Field(ge=0, le=10000)
    settlement_fallback_bp: int = Field(ge=0, le=10000)
    overrun_tolerance: float = Field(ge=0)
    overrun_writedown: float = Field(ge=0, le=1)
    writedown_points: float = Field(ge=0)
    writedown_max_bp: int = Field(ge=0, le=10000)
    guideline_bp: int = Field(ge=0, le=10000)
    guideline_per_point_bp: int = Field(ge=0, le=10000)
    guideline_share: tuple[float, float]
    days_to_pay: dict[str, float]
    days_per_point: float = Field(ge=0)
    days_sigma: float = Field(ge=0)
    macro_stress: float = Field(gt=0)
    days_per_month: float = Field(gt=0)
    short_pay_bp: int = Field(ge=0, le=10000)
    short_pay_per_point_bp: int = Field(ge=0, le=10000)
    short_pay_share: tuple[float, float]
    bankruptcy_bp: dict[str, int]
    write_off_months: int = Field(gt=0)
    provision_bp: tuple[AgeStep, ...] = Field(min_length=1)
    contingency_ev_bp: int = Field(ge=0, le=10000)
    deposit_bp: int = Field(ge=0, le=10000)
    deposit_months: int = Field(ge=0)
    dispute_bp: int = Field(ge=0, le=10000)
    dispute_temperament: float = Field(ge=0)
    dispute_padding_mult: float = Field(ge=1)
    dispute_share: tuple[float, float]
    dispute_window: int = Field(gt=0)
    concede_points: float
    negotiate_share: float = Field(ge=0, le=1)
    hold_base: float
    hold_relationship: float
    hold_fail_points: float
    padding_share: float = Field(ge=0, le=1)
    padding_points: float

    @model_validator(mode="after")
    def _check(self) -> BillingBalance:
        from ptk.sim.billing.models import BILLING_MODELS

        for kind, mix in self.models.items():
            if any(k not in BILLING_MODELS for k in mix) or any(w < 0 for w in mix.values()):
                raise ValueError(f"billing.models.{kind}: unknown model or negative weight")
            if abs(sum(mix.values()) - 1.0) > 1e-6:  # tunable-exempt: weights sum to 1
                raise ValueError(f"billing.models.{kind}: weights must sum to 1")
        for name in (
            "cap_mult",
            "fixed_mult",
            "retainer_mult",
            "guideline_share",
            "short_pay_share",
            "dispute_share",
            "contingency_bp",
        ):
            lo, hi = getattr(self, name)
            if not 0 <= lo <= hi:
                raise ValueError(f"billing.{name} must be an ordered non-negative range")
        if sorted(self.days_to_pay) != ["large", "mid"] or sorted(self.bankruptcy_bp) != [
            "large",
            "mid",
        ]:
            raise ValueError("billing.days_to_pay and bankruptcy_bp are by size class (large, mid)")
        steps = [s.from_months for s in self.provision_bp]
        if steps[0] != 0 or steps != sorted(set(steps)):
            raise ValueError("billing.provision_bp steps must start at 0 and ascend")
        return self


# --- PT-M4: the partnership (spec 5.5, 5.7, 8; ADR PT-0003, PT-0007) -------------------------

type CompSystem = Literal["lockstep", "modified_lockstep", "eat_what_you_kill", "committee"]
COMP_SYSTEMS: Final[tuple[CompSystem, ...]] = (
    "lockstep",
    "modified_lockstep",
    "eat_what_you_kill",
    "committee",
)
type VotingRule = Literal["per_capita", "points"]


class AgreementTerms(_Strict):
    """The partnership agreement's terms (spec 8.6): the founders' defaults, then voted."""

    comp_system: CompSystem
    two_tier: bool
    voting: VotingRule
    admission_bp: int = Field(gt=0, le=10000)
    equity_lockstep_bp: int = Field(gt=0, le=10000)
    terms_bp: int = Field(gt=0, le=10000)
    capital_call_bp: int = Field(gt=0, le=10000)
    deequity_bp: int = Field(gt=0, le=10000)
    track_years: int = Field(ge=6, le=12)
    mp_term_years: int = Field(ge=1, le=10)
    retirement_age: int = Field(ge=55, le=80)
    notice_months: int = Field(ge=0, le=12)
    capital_share_bp: int = Field(ge=0, le=10000)
    draw_share_bp: int = Field(ge=0, le=10000)
    retain_bp: int = Field(ge=0, le=5000)


class LockstepBalance(_Strict):
    start_points: float = Field(gt=0)
    step_points: float = Field(ge=0)
    plateau_points: float = Field(gt=0)
    founder_points: float = Field(gt=0)


class ModifiedLockstepBalance(_Strict):
    gate_min_steps: int = Field(le=0)
    gate_max_steps: int = Field(ge=0)
    bonus_pool_bp: int = Field(ge=0, le=10000)


class EwykBalance(_Strict):
    origination: float = Field(ge=0)
    working: float = Field(ge=0)
    management: float = Field(ge=0)


class CommitteeBalance(_Strict):
    origination: float = Field(ge=0, le=1)
    adjust_max_bp: int = Field(ge=0, le=10000)


class ManagementCredit(_Strict):
    mp: float = Field(ge=0)
    unit_leader: float = Field(ge=0)


class SatisfactionBalance(_Strict):
    ego_weight: float = Field(ge=0)
    floor: float
    ceiling: float


class BudgetBalance(_Strict):
    first_year_margin_bp: int = Field(ge=0, le=10000)


class CapitalBalance(_Strict):
    pay_in_months: int = Field(gt=0)
    return_months: int = Field(gt=0)


class RevolverBalance(_Strict):
    receivables_bp: int = Field(ge=0, le=10000)
    wip_bp: int = Field(ge=0, le=10000)
    unsecured_bp: int = Field(ge=0, le=10000)
    facility_of_revenue_bp: int = Field(ge=0)
    rate_bp: int = Field(ge=0)
    leverage_max_bp: int = Field(gt=0)
    min_capital_bp: int = Field(ge=0)
    departures_max_bp: int = Field(gt=0)
    cure_months: int = Field(gt=0)
    call_months: int = Field(gt=0)
    warning_headroom_bp: int = Field(ge=0, le=10000)
    # PT-M7b: the CFO's forecast (spec 8.7): covenants projected from the trailing trend
    forecast_months: int = Field(gt=0)  # months ahead the CFO projects (and warns)
    forecast_window: int = Field(ge=2, le=12)  # trailing months the trend is fitted on


class ConfidenceBalance(_Strict):
    start: float = Field(ge=0, le=100)
    rate: float = Field(gt=0, le=1)
    target_base: float
    pep_weight: float
    trend_weight: float
    mp_weight: float
    draws_suspended: float
    bank_trouble: float
    departure_hit: float
    comp_step: float
    deequity_fear: float
    supportive: float
    restless: float
    range_half_width: float = Field(ge=0)
    petition_below: float
    petition_months: int = Field(gt=0)


class VotesBalance(_Strict):
    noise_sd: float = Field(ge=0)
    confidence_weight: float
    lobby_points: float
    promise_per_point: float
    predict_k: float = Field(ge=0)
    quality_weight: float
    quality_ref: float
    quality_scale: float = Field(gt=0)
    need_weight: float
    need_ref: float
    dilution_weight: float
    income_dilution_bp: int = Field(ge=0, le=10000)
    sponsor_weight: float
    terms_weight: float
    terms_bias: float
    capital_call_weight: float
    capital_call_stress: float
    deequity_weight: float
    election_weight: float


class UpOrOutBalance(_Strict):
    sponsor_from: str
    leave_months: int = Field(gt=0)
    in_house_bp: int = Field(ge=0, le=10000)


class StayHintBands(_Strict):
    lo: float = Field(ge=0, le=1)
    hi: float = Field(ge=0, le=1)


class FlightBalance(_Strict):
    base_bp: float = Field(ge=0)
    gap_weight: float = Field(ge=0)
    loyalty_ref: float
    loyalty_divisor: float = Field(gt=0)
    contagion: float = Field(ge=0)
    confidence_ref: float
    confidence_divisor: float = Field(gt=0)
    lockstep_star_mult: float = Field(gt=0)
    star_book_mult: float = Field(gt=0)
    cap_bp: int = Field(ge=0, le=10000)
    market_multiple_bp: int = Field(ge=0)
    min_book_cents: int = Field(ge=0)
    answer_months: int = Field(gt=0)
    guarantee_years: tuple[int, int]
    offer_mult: tuple[float, float]
    stay_base: float
    stay_gap_weight: float
    stay_loyalty: float
    stay_confidence: float
    seat_bonus: float
    guarantee_value: float
    stay_hint_bands: StayHintBands
    follow_months: tuple[int, int]
    orphan_drop: float = Field(ge=0)


class LateralPartnerBalance(_Strict):
    batch: tuple[int, int]
    search_cost_cents: int = Field(ge=0)
    fee_bp: int = Field(ge=0, le=10000)
    book_cents: tuple[int, int]
    book_range_bp: int = Field(ge=0, le=10000)
    diligence_range_bp: int = Field(ge=0, le=10000)
    diligence_cost_cents: int = Field(ge=0)
    comp_of_book_bp: int = Field(gt=0)
    notice_premium_bp: int = Field(ge=0)
    guarantee_years: tuple[int, int]
    shelf_turns: int = Field(gt=0)
    accept_k: float = Field(gt=0)
    accept_base: float
    guarantee_weight: float
    realised_sd_bp: int = Field(ge=0)
    arrival_months: tuple[int, int]
    start_relationship: tuple[float, float]


class ElectionBalance(_Strict):
    stage: int = Field(ge=0, le=5)
    rival_ambition_min: float


class PartnershipBalance(_Strict):
    agreement: AgreementTerms
    lockstep: LockstepBalance
    modified: ModifiedLockstepBalance
    ewyk: EwykBalance
    committee: CommitteeBalance
    management_credit: ManagementCredit
    satisfaction: SatisfactionBalance
    budget: BudgetBalance
    capital: CapitalBalance
    reforecast_months: tuple[int, ...]
    true_up_months: tuple[int, ...]
    cash_buffer_months: float = Field(ge=0)
    revolver: RevolverBalance
    insolvency_months: int = Field(gt=0)
    dissolve_vote_months: int = Field(gt=0)
    dissolve_restless_bp: int = Field(ge=0, le=10000)
    confidence: ConfidenceBalance
    votes: VotesBalance
    up_or_out: UpOrOutBalance
    income_partner_salary_bp: int = Field(gt=0)
    flight: FlightBalance
    lateral: LateralPartnerBalance
    election: ElectionBalance
    stages: tuple[int, ...] = Field(min_length=6, max_length=6)
    cfo_warning_cooldown: int = Field(ge=0)


class Balance(_Strict):
    campaign: CampaignBalance
    backups: BackupBalance
    people: PeopleBalance
    growth: GrowthBalance
    familiarity: FamiliarityBalance
    strain: StrainBalance
    reveal: RevealBalance
    founder: FounderBalance
    energy: EnergyBalance
    hiring: HiringBalance
    campus: CampusBalance
    pay: PayBalance
    morale: MoraleBalance
    resign: ResignBalance
    tags: TagRevealBalance
    org: OrgBalance
    rivals: RivalsBalance  # PT-M5
    world: WorldBalance  # PT-M5
    clients: ClientsBalance  # PT-M3a
    books: BooksBalance
    appeal: AppealBalance
    matters: MattersBalance
    outcomes: OutcomesBalance
    errors: ErrorsBalance
    progress: ProgressBalance
    judges: JudgesBalance
    settlement: SettlementBalance
    relationships: RelationshipsBalance
    cross_sell: CrossSellBalance
    conflicts: ConflictsBalance
    events: EventsBalance  # PT-M6 (ptk.sim.events.data)
    colleagues: ColleaguesBalance  # PT-M6: colleague relationships (TST 16.7)
    billing: BillingBalance  # PT-M3b
    partnership: PartnershipBalance  # PT-M4
    staffing: StaffingBalance  # PT-M7a
    pro_bono: ProBonoBalance  # PT-M7a
    assessment: AssessmentBalance  # PT-M7a
    rates: RatesBalance  # PT-M7a
    macro: MacroBalance  # PT-M7: the macro and legal indices
    holiday: HolidayBalance  # PT-M7a
    seats: SeatsBalance  # PT-M8 (ptk.sim.org.seat_data)
    authority: AuthorityBalance  # PT-M8
    pitches: PitchesBalance  # PT-M8
    founder_life: FounderLifeBalance  # PT-M17
    family: FamilyBalance  # PT-M17
    succession: SuccessionBalance  # PT-M17
    automation: AutomationBalance  # PT-M9 (ptk.sim.automation.config)


# --- People seed data (PT-M1a) ------------------------------------------------------------


class SkillDef(_Strict):
    key: str = Field(pattern=_KEY)
    label: str = Field(min_length=1)
    short_label: str = Field(min_length=1)
    group: Literal["legal", "client", "working", "leadership", "business_services"]


class TraitDef(_Strict):
    key: str = Field(pattern=_KEY)
    label: str = Field(min_length=1)


class HiddenTraitDef(_Strict):
    key: str = Field(pattern=_KEY)


# --- Practices, clients and courts (PT-M3a; spec 6, 7) ----------------------------------------

RATE_BANDS: Final = ("paralegal", "junior", "mid", "senior", "counsel", "partner")
# Task levels (practices.yaml tasks): 0 paralegal, 1 junior, 2 mid, 3 senior and counsel,
# 4 partner. Each rate band works at one task level.
BAND_TASK_LEVEL: Final = {
    "paralegal": 0,
    "junior": 1,
    "mid": 2,
    "senior": 3,
    "counsel": 3,
    "partner": 4,
}
type MatterKind = Literal["deal", "case", "investigation", "restructuring", "advisory", "filing"]
type OutcomeKind = Literal["deal", "case", "quality"]
MATTER_KINDS: Final = ("deal", "case", "investigation", "restructuring", "advisory", "filing")


def _weights_positive(weights: dict[str, float], name: str) -> None:
    if any(w < 0 for w in weights.values()) or not any(w > 0 for w in weights.values()):
        raise ValueError(f"{name}: weights need a positive weight and none negative")


class RateRange(_Strict):
    low: int = Field(gt=0)
    median: int = Field(gt=0)
    high: int = Field(gt=0)

    @model_validator(mode="after")
    def _ordered(self) -> RateRange:
        if not self.low <= self.median <= self.high:
            raise ValueError("rate card: low <= median <= high")
        return self


class Norms2005(_Strict):
    revenue_per_lawyer_cents: int = Field(gt=0)
    pep_cents: int = Field(gt=0)
    realisation_bp: int = Field(gt=0, le=10000)
    collection_bp: int = Field(gt=0, le=10000)
    leverage: Span
    billable_target_hours: Span
    associate_attrition_bp: Span


class TaskDef(_Strict):
    key: str = Field(pattern=_KEY)
    level: int = Field(ge=0, le=4)
    ai_exposure: float = Field(ge=0, le=1)
    skills: dict[str, float]

    @model_validator(mode="after")
    def _check(self) -> TaskDef:
        _weights_positive(self.skills, f"task {self.key}")
        return self


class PhaseDef(_Strict):
    key: str = Field(pattern=_KEY)
    share: float = Field(gt=0, le=1)
    tasks: dict[str, float]

    @model_validator(mode="after")
    def _check(self) -> PhaseDef:
        _weights_positive(self.tasks, f"phase {self.key}")
        return self


class KindDef(_Strict):
    outcome: OutcomeKind
    phases: tuple[PhaseDef, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _check(self) -> KindDef:
        if abs(sum(p.share for p in self.phases) - 1.0) > 1e-9:  # tunable-exempt: rounding
            raise ValueError("phase shares must sum to 1")
        return self


class MatterKindDef(_Strict):
    key: str = Field(pattern=_KEY)
    label: str = Field(min_length=1)
    kind: MatterKind
    weight: float = Field(gt=0)
    median_cents: int = Field(gt=0)
    sigma: float = Field(gt=0)
    months: tuple[int, int]
    critical_bp: int = Field(ge=0, le=10000)
    forums: dict[str, float] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check(self) -> MatterKindDef:
        if not 1 <= self.months[0] <= self.months[1]:
            raise ValueError(f"matter kind {self.key}: months must be 1 <= min <= max")
        if (self.kind == "case") != bool(self.forums):
            raise ValueError(f"matter kind {self.key}: case kinds, and only they, name forums")
        if self.forums:
            _weights_positive(self.forums, f"matter kind {self.key} forums")
        return self


class PracticeDef(_Strict):
    key: str = Field(pattern=_KEY)
    label: str = Field(min_length=1)
    short_label: str = Field(min_length=1)
    demand_cents: int = Field(gt=0)  # NY 2005 annual demand base D0 (spec 6)
    driver: str = Field(min_length=1)
    beta: float  # sensitivity to the driver index (spec 6)
    index: str  # PT-M7: the driver's macro_history.yaml series
    sigma: float = Field(ge=0)  # monthly LogNormal demand noise
    rates: dict[str, int]  # rate band -> cents an hour
    leverage: float = Field(gt=0)
    margin_bp: int = Field(ge=0, le=10000)
    realisation_bp: int = Field(gt=0, le=10000)
    collection_bp: int = Field(gt=0, le=10000)
    flow_share: float = Field(ge=0, le=1)
    conflict_bp: int = Field(ge=0, le=10000)
    seasonality: tuple[float, ...] = Field(min_length=12, max_length=12)
    matter_kinds: tuple[MatterKindDef, ...] = Field(min_length=1)
    cross_sell: dict[str, float]

    @model_validator(mode="after")
    def _check(self) -> PracticeDef:
        if sorted(self.rates) != sorted(RATE_BANDS) or min(self.rates.values()) <= 0:
            raise ValueError(f"practice {self.key}: rates must give every band {RATE_BANDS}")
        if abs(sum(self.seasonality) / 12 - 1.0) > 1e-6:  # tunable-exempt: mean 1, rounding
            raise ValueError(f"practice {self.key}: seasonality must average 1")
        keys = [k.key for k in self.matter_kinds]
        if len(keys) != len(set(keys)):
            raise ValueError(f"practice {self.key}: duplicate matter kind keys")
        if any(not 0 <= v <= 1 for v in self.cross_sell.values()):
            raise ValueError(f"practice {self.key}: cross_sell affinities are 0-1")
        return self

    def kind(self, key: str) -> MatterKindDef:
        for k in self.matter_kinds:
            if k.key == key:
                return k
        raise KeyError(f"practice {self.key}: no matter kind {key!r}")


class PracticeMarket(_Strict):
    """practices.yaml beyond the practice list: rate bands, the rate card, norms, tasks."""

    rate_bands: dict[str, str]  # level -> rate band
    rate_card: dict[str, RateRange]
    norms_2005: Norms2005
    tasks: tuple[TaskDef, ...] = Field(min_length=1)
    kinds: dict[str, KindDef]
    flow_tasks: dict[str, float]

    @model_validator(mode="after")
    def _check(self) -> PracticeMarket:
        if sorted(self.rate_card) != sorted(RATE_BANDS):
            raise ValueError(f"rate_card must give every band {RATE_BANDS}")
        if bad := sorted(set(self.rate_bands.values()) - set(RATE_BANDS)):
            raise ValueError(f"rate_bands name unknown bands {bad}")
        if bad := sorted(set(self.rate_bands) - set(LEVELS)):
            raise ValueError(f"rate_bands name unknown levels {bad}")
        if sorted(self.kinds) != sorted(MATTER_KINDS):
            raise ValueError(f"kinds must define exactly {list(MATTER_KINDS)}")
        tasks = {t.key for t in self.tasks}
        if len(tasks) != len(self.tasks):
            raise ValueError("duplicate task keys")
        for key, kind in self.kinds.items():
            for phase in kind.phases:
                if bad := sorted(set(phase.tasks) - tasks):
                    raise ValueError(f"kind {key} phase {phase.key}: unknown tasks {bad}")
        if bad := sorted(set(self.flow_tasks) - tasks):
            raise ValueError(f"flow_tasks: unknown tasks {bad}")
        _weights_positive(self.flow_tasks, "flow_tasks")
        return self

    def task(self, key: str) -> TaskDef:
        for t in self.tasks:
            if t.key == key:
                return t
        raise KeyError(f"unknown task {key!r}")


class SectorDef(_Strict):
    key: str = Field(pattern=_KEY)
    label: str = Field(min_length=1)
    intensity: float = Field(gt=0)  # legal spend per unit of size, relative
    mix: dict[str, float]  # practice -> weight
    suffixes: tuple[str, ...] = Field(min_length=1)  # generated client names


class ClientFailureDef(_Strict):
    """PT-M7: a real client's dated failure (docs/research/v1-macro.md). A bankruptcy leaves
    the firm's open bills unpaid and keeps the estate instructing restructuring work; a rescue
    (a distressed sale) pays its bills and its wallet ends after `macro.rescue_months`."""

    ym: tuple[int, int]
    kind: Literal["bankruptcy", "rescue"]
    src: str = Field(min_length=1)


class RealClientDef(_Strict):
    name: str = Field(min_length=1)
    sector: str
    revenue_bn: float = Field(gt=0)
    country: str = "us"
    fails: ClientFailureDef | None = None  # PT-M7


class PanelFirmDef(_Strict):
    key: str = Field(pattern=_KEY)
    name: str = Field(min_length=1)
    base: float  # appeal, logit points
    strong: tuple[str, ...] = ()  # practices with the strength bonus


class ClientsData(_Strict):
    sectors: tuple[SectorDef, ...] = Field(min_length=1)
    generated_sector_weights: dict[str, float]
    panel_firms: tuple[PanelFirmDef, ...] = Field(min_length=1)
    real_clients: tuple[RealClientDef, ...]

    def sector(self, key: str) -> SectorDef:
        for s in self.sectors:
            if s.key == key:
                return s
        raise KeyError(f"unknown sector {key!r}")

    def panel_firm(self, key: str) -> PanelFirmDef:
        for f in self.panel_firms:
            if f.key == key:
                return f
        raise KeyError(f"unknown panel firm {key!r}")


class CourtDef(_Strict):
    key: str = Field(pattern=_KEY)
    label: str = Field(min_length=1)
    kind: Literal["federal", "state", "arbitration"]
    pace: float = Field(gt=0)  # multiplier on a case's planned duration
    trial_bp: int = Field(ge=0, le=10000)
    judges: int = Field(gt=0)


class CourtsData(_Strict):
    courts: tuple[CourtDef, ...] = Field(min_length=1)
    judge_traits: tuple[TraitDef, ...] = Field(min_length=1)

    def court(self, key: str) -> CourtDef:
        for c in self.courts:
            if c.key == key:
                return c
        raise KeyError(f"unknown court {key!r}")


class SchoolTier(_Strict):
    key: str = Field(pattern=_KEY)
    label: str = Field(min_length=1)
    country: Literal["us", "uk"]
    available_in: Version
    ca_shift: float  # ability points added to the level's target CA mean
    pa_shift: float  # ability points added to the potential gap mean


class Role(_Strict):
    key: str = Field(pattern=_KEY)
    label: str = Field(min_length=1)
    kind: PersonKind
    practice: str | None = None  # a lawyer's home practice (spec 5.1)
    summary: str = Field(min_length=1)
    primary: tuple[str, ...] = Field(min_length=1)
    secondary: tuple[str, ...]
    work_style: str
    work_style_weights: dict[str, float]
    interest_weights: dict[str, float]  # interests left out weigh 1

    @model_validator(mode="after")
    def _check(self) -> Role:
        skills = self.primary + self.secondary
        if len(set(skills)) != len(skills):
            raise ValueError(f"role {self.key!r}: a skill is listed twice")
        if (self.kind == "lawyer") != (self.practice is not None):
            raise ValueError(f"role {self.key!r}: lawyer roles, and only they, name a practice")
        for name, weights in (
            ("work_style_weights", self.work_style_weights),
            ("interest_weights", self.interest_weights),
        ):
            if any(w < 0 for w in weights.values()):
                raise ValueError(f"role {self.key!r}: {name} must not be negative")
        if not any(w > 0 for w in self.work_style_weights.values()):
            raise ValueError(f"role {self.key!r}: work_style_weights need a positive weight")
        return self

    @property
    def skills(self) -> tuple[str, ...]:
        return self.primary + self.secondary


class TagCondition(_Strict):
    attr: str
    op: Literal[">=", "<="]
    value: float

    def holds(self, value: float) -> bool:
        return value >= self.value if self.op == ">=" else value <= self.value


class TagBoost(_Strict):
    multiplier: float = Field(ge=0)
    when: tuple[TagCondition, ...] = Field(min_length=1)


class Tag(_Strict):
    key: str = Field(pattern=_KEY)
    label: str = Field(min_length=1)
    base_bp: int = Field(ge=0)
    boost: TagBoost
    excludes: tuple[str, ...]
    reveal_text: str = Field(min_length=1)
    effect_note: str
    negative: bool = False  # ADR PT-0013: never attached to a person flagged real


class Background(_Strict):
    key: str = Field(pattern=_KEY)
    label: str = Field(min_length=1)
    available_in: Version
    description: str = Field(min_length=1)
    home_practice: str
    familiar_practices: tuple[str, ...] = Field(min_length=1)
    book_cents: tuple[int, int]
    bar_admissions: tuple[str, ...]
    bonuses: dict[str, float]
    default_allocation: dict[str, int]

    @model_validator(mode="after")
    def _check(self) -> Background:
        lo, hi = self.book_cents
        if not 0 <= lo <= hi:
            raise ValueError(f"background {self.key!r}: book_cents must be 0 <= min <= max")
        if self.home_practice not in self.familiar_practices:
            raise ValueError(f"background {self.key!r}: home_practice must be familiar")
        return self

    @property
    def selectable(self) -> bool:
        return self.available_in == "v1"


class PersonalityPreset(_Strict):
    key: str = Field(pattern=_KEY)
    label: str = Field(min_length=1)
    description: str = Field(min_length=1)
    values: dict[str, float]


class NamePool(_Strict):
    first: tuple[str, ...] = Field(min_length=1)
    last: tuple[str, ...] = Field(min_length=1)


class ScaleRow(_Strict):
    """The market associate scale from a month on (spec 5.4)."""

    from_ym: tuple[int, int] = Field(alias="from")
    salaries: tuple[int, ...] = Field(min_length=8, max_length=8)  # class years 1-8, cents


class BonusRow(_Strict):
    year: int
    amounts: tuple[int, ...] = Field(min_length=8, max_length=8)  # class years 1-8, cents


class SalaryScale(_Strict):
    scale: tuple[ScaleRow, ...] = Field(min_length=1)
    bonuses: tuple[BonusRow, ...] = Field(min_length=1)
    bands: dict[str, int]  # off-scale levels: a New York salary a year, cents

    @model_validator(mode="after")
    def _check(self) -> SalaryScale:
        froms = [r.from_ym for r in self.scale]
        if froms != sorted(set(froms)):
            raise ValueError("salary scale rows must be in strictly increasing date order")
        years = [b.year for b in self.bonuses]
        if years != sorted(set(years)):
            raise ValueError("bonus rows must be in strictly increasing year order")
        for row in self.scale:
            if list(row.salaries) != sorted(row.salaries) or row.salaries[0] <= 0:
                raise ValueError(f"scale from {row.from_ym}: salaries must rise by class year")
        for brow in self.bonuses:
            if any(a < 0 for a in brow.amounts):
                raise ValueError(f"bonuses {brow.year}: amounts must not be negative")
        if any(v <= 0 for v in self.bands.values()):
            raise ValueError("salary bands must be positive")
        return self

    def market_salaries(self, ym: tuple[int, int]) -> tuple[int, ...]:
        """The market scale in force in month `ym` (the first row before 2005)."""
        current = self.scale[0].salaries
        for row in self.scale:
            if row.from_ym <= ym:
                current = row.salaries
        return current

    def market_bonuses(self, year: int) -> tuple[int, ...]:
        current = self.bonuses[0].amounts
        for row in self.bonuses:
            if row.year <= year:
                current = row.amounts
        return current


class InboxTemplate(_Strict):
    title: str = Field(min_length=1)
    body: str = Field(min_length=1)


class GameData(_Strict):
    accounts: tuple[Account, ...]
    scenarios: tuple[Scenario, ...]
    difficulties: tuple[Difficulty, ...]
    jurisdictions: tuple[Jurisdiction, ...]
    skills: tuple[SkillDef, ...] = Field(min_length=1)
    personality: tuple[TraitDef, ...] = Field(min_length=1)
    hidden: tuple[HiddenTraitDef, ...] = Field(min_length=1)
    work_styles: tuple[TraitDef, ...] = Field(min_length=1)
    interests: tuple[TraitDef, ...] = Field(min_length=1)
    practices: tuple[PracticeDef, ...] = Field(min_length=1)
    school_tiers: tuple[SchoolTier, ...] = Field(min_length=1)
    roles: tuple[Role, ...] = Field(min_length=1)
    tags: tuple[Tag, ...]
    backgrounds: tuple[Background, ...] = Field(min_length=1)
    personality_presets: tuple[PersonalityPreset, ...]
    names: dict[str, NamePool]
    salary_scale: SalaryScale
    inbox_templates: dict[str, InboxTemplate]
    market: PracticeMarket  # PT-M3a: practices.yaml's rate card, norms, tasks and kinds
    clients: ClientsData  # PT-M3a: clients.yaml
    courts: CourtsData  # PT-M3a: courts.yaml
    rivals: RivalsData  # PT-M5: firms.yaml, notables.yaml, judges.yaml
    event_templates: tuple[EventTemplate, ...] = ()  # PT-M6: events/*.yaml (TST 16.4)
    macro: MacroData  # PT-M7: macro_history.yaml
    seats: SeatsData  # PT-M8: seats.yaml

    @model_validator(mode="after")
    def _unique(self) -> GameData:
        for name, keys in (
            ("account", [a.code for a in self.accounts]),
            ("scenario", [s.id for s in self.scenarios]),
            ("difficulty", [d.id for d in self.difficulties]),
            ("jurisdiction", [j.key for j in self.jurisdictions]),
            ("skill", [s.key for s in self.skills]),
            ("trait", [t.key for t in self.personality] + [t.key for t in self.hidden]),
            ("work style", [w.key for w in self.work_styles]),
            ("interest", [i.key for i in self.interests]),
            ("practice", [p.key for p in self.practices]),
            ("school tier", [s.key for s in self.school_tiers]),
            ("role", [r.key for r in self.roles]),
            ("tag", [t.key for t in self.tags]),
            ("background", [b.key for b in self.backgrounds]),
            ("personality preset", [p.key for p in self.personality_presets]),
            ("sector", [x.key for x in self.clients.sectors]),
            ("panel firm", [f.key for f in self.clients.panel_firms]),
            ("real client", [c.name for c in self.clients.real_clients]),
            ("court", [c.key for c in self.courts.courts]),
            ("judge trait", [t.key for t in self.courts.judge_traits]),
        ):
            if len(keys) != len(set(keys)):
                raise ValueError(f"duplicate {name} keys")
        self._check_references()
        if bad := sorted({p.index for p in self.practices} - set(MACRO_SERIES)):
            raise ValueError(f"practices: unknown macro index {bad}")
        for shock in self.macro.shocks:  # PT-M10
            if bad := sorted((set(shock.demand) | set(shock.hours)) - set(self.practice_keys)):
                raise ValueError(f"macro shock {shock.from_ym}: unknown practices {bad}")
        self.rivals.check(set(self.practice_keys), {c.key for c in self.courts.courts})
        traits = set(self.skill_keys) | {t.key for t in self.personality}
        for seat in self.seats.seats:  # PT-M8: seat weights name skills or personality traits
            if bad := sorted(set(seat.weights) - traits):
                raise ValueError(f"seat {seat.key!r}: unknown skills {bad}")
        if problems := template_problems(self.event_templates):
            raise ValueError("event templates: " + "; ".join(problems))
        return self

    def _check_references(self) -> None:
        skills, practices = set(self.skill_keys), set(self.practice_keys)
        traits = set(self.personality_keys)
        styles, interests = set(self.work_style_keys), set(self.interest_keys)
        jurisdictions = {j.key for j in self.jurisdictions}
        roles = {r.key: r for r in self.roles}
        for role in self.roles:
            if bad := sorted(set(role.skills) - skills):
                raise ValueError(f"role {role.key!r}: unknown skills {bad}")
            if role.practice is not None and role.practice not in practices:
                raise ValueError(f"role {role.key!r}: unknown practice {role.practice!r}")
            if role.work_style not in styles or set(role.work_style_weights) != styles:
                raise ValueError(f"role {role.key!r}: work styles must be {sorted(styles)}")
            if bad := sorted(set(role.interest_weights) - interests):
                raise ValueError(f"role {role.key!r}: unknown interests {bad}")
        if sorted({r.practice for r in self.roles if r.practice}) != sorted(practices):
            raise ValueError("every practice needs exactly one lawyer role")
        if len([r for r in self.roles if r.practice]) != len(practices):
            raise ValueError("every practice needs exactly one lawyer role")
        tag_keys = {t.key for t in self.tags}
        for tag in self.tags:
            if bad := sorted({c.attr for c in tag.boost.when} - traits):
                raise ValueError(f"tag {tag.key!r}: conditions on unknown traits {bad}")
            if bad := sorted(set(tag.excludes) - tag_keys):
                raise ValueError(f"tag {tag.key!r}: excludes unknown tags {bad}")
        for bg in self.backgrounds:
            if bg.home_practice not in practices or set(bg.familiar_practices) - practices:
                raise ValueError(f"background {bg.key!r}: unknown practice")
            if bad := sorted((set(bg.bonuses) | set(bg.default_allocation)) - skills):
                raise ValueError(f"background {bg.key!r}: unknown skills {bad}")
            if bad := sorted(set(bg.bar_admissions) - jurisdictions):
                raise ValueError(f"background {bg.key!r}: unknown jurisdictions {bad}")
        for preset in self.personality_presets:
            if set(preset.values) != traits:
                raise ValueError(f"preset {preset.key!r}: must set every personality trait")
        if "us" not in self.names:
            raise ValueError("names.yaml needs the `us` pool")
        if missing := sorted(set(OFF_SCALE_LEVELS) - set(self.salary_scale.bands)):
            raise ValueError(f"salary_scale.yaml bands must cover {missing}")
        self._check_market(practices, skills)
        backgrounds = {b.key for b in self.backgrounds}
        for sc in self.scenarios:
            if sc.home_jurisdiction not in jurisdictions:
                raise ValueError(f"scenario {sc.id!r}: unknown jurisdiction")
            if sc.default_background not in backgrounds or any(
                c.background not in backgrounds for c in sc.co_founders
            ):
                raise ValueError(f"scenario {sc.id!r}: unknown background")
            for staff in sc.starting_staff:
                if staff.role not in roles:
                    raise ValueError(f"scenario {sc.id!r}: unknown role {staff.role!r}")
                if staff.practice is not None and staff.practice not in practices:
                    raise ValueError(f"scenario {sc.id!r}: unknown practice {staff.practice!r}")

    def _check_market(self, practices: set[str], skills: set[str]) -> None:
        """PT-M3a's practices, clients and courts refer to known keys."""
        fee_earners = set(LEVELS) - set(BUSINESS_SERVICES_LEVELS)
        if missing := sorted(fee_earners - set(self.market.rate_bands)):
            raise ValueError(f"practices.yaml rate_bands must cover fee earners {missing}")
        for task in self.market.tasks:
            if bad := sorted(set(task.skills) - skills):
                raise ValueError(f"task {task.key}: unknown skills {bad}")
        courts = {c.key for c in self.courts.courts}
        for p in self.practices:
            if bad := sorted(set(p.cross_sell) - practices) or (
                [p.key] if p.key in p.cross_sell else []
            ):
                raise ValueError(f"practice {p.key}: bad cross_sell practices {bad}")
            for mk in p.matter_kinds:
                if bad := sorted(set(mk.forums) - courts):
                    raise ValueError(f"matter kind {mk.key}: unknown forums {bad}")
        sectors = {s.key for s in self.clients.sectors}
        for sector in self.clients.sectors:
            if bad := sorted(set(sector.mix) - practices):
                raise ValueError(f"sector {sector.key}: unknown practices {bad}")
        if bad := sorted(set(self.clients.generated_sector_weights) - sectors):
            raise ValueError(f"generated_sector_weights: unknown sectors {bad}")
        for client in self.clients.real_clients:
            if client.sector not in sectors:
                raise ValueError(f"client {client.name!r}: unknown sector {client.sector!r}")
        for firm in self.clients.panel_firms:
            if bad := sorted(set(firm.strong) - practices):
                raise ValueError(f"panel firm {firm.key}: unknown practices {bad}")

    # --- lookups ---------------------------------------------------------------------------

    @property
    def skill_keys(self) -> tuple[str, ...]:
        return tuple(s.key for s in self.skills)

    @property
    def personality_keys(self) -> tuple[str, ...]:
        return tuple(t.key for t in self.personality)

    @property
    def hidden_keys(self) -> tuple[str, ...]:
        return tuple(t.key for t in self.hidden)

    @property
    def work_style_keys(self) -> tuple[str, ...]:
        return tuple(w.key for w in self.work_styles)

    @property
    def interest_keys(self) -> tuple[str, ...]:
        return tuple(i.key for i in self.interests)

    @property
    def practice_keys(self) -> tuple[str, ...]:
        return tuple(p.key for p in self.practices)

    def seat(self, key: str) -> SeatDef:
        """A seats.yaml seat (PT-M8)."""
        for seat in self.seats.seats:
            if seat.key == key:
                return seat
        raise KeyError(f"unknown seat {key!r}")

    def practice(self, key: str) -> PracticeDef:
        for p in self.practices:
            if p.key == key:
                return p
        raise KeyError(f"unknown practice {key!r}")

    def event_template(self, template_id: str) -> EventTemplate:
        for template in self.event_templates:
            if template.id == template_id:
                return template
        raise KeyError(f"unknown event template {template_id!r}")

    def role(self, key: str) -> Role:
        for role in self.roles:
            if role.key == key:
                return role
        raise KeyError(f"unknown role {key!r}")

    def practice_role(self, practice: str) -> Role:
        for role in self.roles:
            if role.practice == practice:
                return role
        raise KeyError(f"no lawyer role for practice {practice!r}")

    def background(self, key: str) -> Background | None:
        return next((b for b in self.backgrounds if b.key == key), None)

    def preset(self, key: str) -> PersonalityPreset | None:
        return next((p for p in self.personality_presets if p.key == key), None)

    def school_tier(self, key: str) -> SchoolTier:
        for tier in self.school_tiers:
            if tier.key == key:
                return tier
        raise KeyError(f"unknown school tier {key!r}")

    def scenario(self, scenario_id: str) -> Scenario | None:
        return next((s for s in self.scenarios if s.id == scenario_id), None)

    def difficulty(self, difficulty_id: str) -> Difficulty | None:
        return next((d for d in self.difficulties if d.id == difficulty_id), None)

    def account_types(self) -> dict[str, AccountType]:
        return {a.code: a.type for a in self.accounts}
