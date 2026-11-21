"""Schemas for seats.yaml and balance's `seats`, `authority` and `pitches` sections (PT-M8;
spec 9.1-9.3; TST formulas.md 18.3, 24, 27.1). Invalid data fails at load (ADR-0008).

Kept beside the seats so `ptk.sim.data_models` only imports them (as it does PT-M5's and
PT-M7's data). Every number here has its unit and intent in balance.yaml.
"""

from __future__ import annotations

from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

type SeatWho = Literal["player", "partner", "business_services"]
type SeatSlots = Literal["one", "per_group", "per_office", "committee"]
type PitchKind = Literal[
    "lateral_partner",
    "new_group",
    "campus_size",
    "rate_move",
    "panel_push",
    "fit_out",
    "cost_programme",
]

PITCH_KINDS: Final[tuple[PitchKind, ...]] = (
    "lateral_partner",
    "new_group",
    "campus_size",
    "rate_move",
    "panel_push",
    "fit_out",
    "cost_programme",
)
# Seats whose holders write a quarterly report (spec 9.3: the chiefs; TST 27.2).
REPORTING_SEATS: Final = frozenset(
    {"general_counsel", "cfo", "coo", "cmo", "chro", "pricing_director", "cko"}
)
WEIGHT_TOLERANCE: Final = 1e-6  # tunable-exempt: float sum check


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Guardrail(_Strict):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    label: str = Field(min_length=1)
    default: int
    min: int
    max: int

    @model_validator(mode="after")
    def _range(self) -> Guardrail:
        if not self.min <= self.default <= self.max:
            raise ValueError(f"guardrail {self.key}: default outside [min, max]")
        return self


class AuthorityDef(_Strict):
    does: str
    guardrails: tuple[Guardrail, ...] = ()


class SeatDef(_Strict):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    label: str = Field(min_length=1)
    short: str = Field(min_length=1)
    stage: int = Field(ge=0, le=5)
    who: SeatWho
    income: bool = False  # an income partner may sit (partner seats)
    slots: SeatSlots
    weights: dict[str, float]
    effect: str
    authority: AuthorityDef
    pitches: tuple[PitchKind, ...] = ()

    @model_validator(mode="after")
    def _weights(self) -> SeatDef:
        if abs(sum(self.weights.values()) - 1.0) > WEIGHT_TOLERANCE:
            raise ValueError(f"seat {self.key}: weights must add up to 1")
        if any(w <= 0 for w in self.weights.values()):
            raise ValueError(f"seat {self.key}: weights must be positive")
        return self

    @property
    def has_authority(self) -> bool:
        return bool(self.authority.does)

    def guardrail(self, key: str) -> Guardrail:
        for g in self.authority.guardrails:
            if g.key == key:
                return g
        raise KeyError(f"seat {self.key} has no guardrail {key!r}")


class SeatsData(_Strict):
    seats: tuple[SeatDef, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique(self) -> SeatsData:
        keys = [s.key for s in self.seats]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate seat keys")
        return self


# --- Balance --------------------------------------------------------------------------------


class ExcoBalance(_Strict):
    min_members: int = Field(ge=1)
    max_by_stage: dict[int, int]
    appointed_below_lawyers: int = Field(ge=0)
    term_pass_confidence: float = Field(ge=0, le=100)
    warn_confidence: float = Field(ge=0, le=100)
    uneasy_confidence: float = Field(ge=0, le=100)


class SeatEffects(_Strict):
    mp_confidence: float
    exco_quality: float
    pgl_flow: float
    pgl_morale: float
    gc_conflicts: float
    cmo_pitch_points: float
    chro_morale: float
    chro_campus_points: float


class SeatsBalance(_Strict):
    vacant_effect: float
    score_mid: float
    score_span: float = Field(gt=0)
    effect_range: tuple[float, float]
    bs_min_level: str
    fit_bands: tuple[float, float, float]
    appoint_confidence_per_ambition: float
    candidates_shown: int = Field(ge=1)
    exco: ExcoBalance
    effects: SeatEffects


class QualityBalance(_Strict):
    base: float
    per_score: float
    min: float = Field(ge=0, le=1)
    max: float = Field(ge=0, le=1)


class AuthorityBalance(_Strict):
    energy_per_month: int = Field(ge=0)
    quality: QualityBalance
    keep_decision_turns: int = Field(ge=1)
    hire_step: int = Field(ge=1)
    plan_ratio_bp: int = Field(gt=0)


class PitchKindBalance(_Strict):
    central: float  # the kind's central case scale (unit in balance.yaml)
    cost_cents: int = Field(ge=0)


class PitchesBalance(_Strict):
    base: float
    per_ambition: float
    chance_clamp: tuple[float, float]
    record_months: int = Field(ge=1)
    spread_base: float = Field(ge=0)
    spread_per_point: float = Field(ge=0)
    spread_clamp: tuple[float, float]
    decline_morale: float
    decline_morale_high_ego: float
    high_ego: float
    hit_morale: float
    miss_morale: float
    hit_confidence: float
    miss_confidence: float
    new_group_min_lawyers: int = Field(ge=1)
    panel_clients: int = Field(ge=1)
    panel_bump: float
    fit_out_morale_pct: float
    fit_out_months: int = Field(ge=1)
    cost_saving_bp: int = Field(ge=0)
    cost_months: int = Field(ge=1)
    cost_morale_pct: float
    rate_step_bp: int = Field(ge=0)
    busy_bp: int = Field(ge=0)
    campus_step: int = Field(ge=1)
    kinds: dict[PitchKind, PitchKindBalance]

    @model_validator(mode="after")
    def _kinds(self) -> PitchesBalance:
        if sorted(self.kinds) != sorted(PITCH_KINDS):
            raise ValueError(f"pitches.kinds must define exactly {list(PITCH_KINDS)}")
        return self
