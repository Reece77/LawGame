"""Pydantic schemas for balance and seed data (ADR-0008). Invalid data fails at load."""

from __future__ import annotations

from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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


class Balance(_Strict):
    campaign: CampaignBalance
    backups: BackupBalance
    people: PeopleBalance
    growth: GrowthBalance
    familiarity: FamiliarityBalance
    strain: StrainBalance
    reveal: RevealBalance
    founder: FounderBalance
    org: OrgBalance


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


class PracticeDef(_Strict):
    key: str = Field(pattern=_KEY)
    label: str = Field(min_length=1)
    short_label: str = Field(min_length=1)


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
        ):
            if len(keys) != len(set(keys)):
                raise ValueError(f"duplicate {name} keys")
        self._check_references()
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
