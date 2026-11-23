"""Schemas for PT-M14 (ADR-0008): `legal_eras.yaml` (the eras, their strength by task and the
market's adoption, dated to December 2025 and seeded after) and `tech.*` in balance.yaml. Model
definitions only (no imports from the rest of the sim), so `ptk.sim.data_models` can import them.
"""

from __future__ import annotations

from typing import Final

from pydantic import BaseModel, ConfigDict, Field, model_validator

TASKS: Final = (  # practices.yaml's task keys (ADR PT-0011 1); checked against it at load
    "review",
    "diligence",
    "research",
    "drafting",
    "management",
    "negotiation",
    "advocacy",
    "advice",
)
MONTHS_A_YEAR: Final = 12  # tunable-exempt


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def _ym_ok(ym: tuple[int, int], what: str) -> None:
    if not 1 <= ym[1] <= MONTHS_A_YEAR:
        raise ValueError(f"{what} {ym}: month must be 1-12")


class PathPoint(_Strict):
    """A dated value of a path (0-1); between points the value is linear, before the first 0
    (the era has not begun) and after the last it holds."""

    ym: tuple[int, int]
    value: float = Field(ge=0, le=1)
    src: str = ""  # the dossier row (docs/research/legal-tech.md)

    @model_validator(mode="after")
    def _check(self) -> PathPoint:
        _ym_ok(self.ym, "path point")
        return self


class SeededTarget(_Strict):
    """After history (ADR PT-0002 2, PT-0015): the path runs on from its December 2025 value to
    a value drawn U(lo, hi) at `by` (stream `tech_seed`, 110), linearly, then holds."""

    by: tuple[int, int]
    lo: float = Field(ge=0, le=1)
    hi: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def _check(self) -> SeededTarget:
        _ym_ok(self.by, "seeded target")
        if self.lo > self.hi:
            raise ValueError("seeded target: lo <= hi")
        return self


def _ordered(points: tuple[PathPoint, ...], what: str) -> None:
    yms = [p.ym for p in points]
    if yms != sorted(yms) or len(set(yms)) != len(yms):
        raise ValueError(f"{what}: points must be in strictly increasing month order")


class EraDef(_Strict):
    """One era (spec 13's table): the strength of its tools on each task at full strength
    (`tasks`, 0-1), its strength over time (`strength`, 0-1, dated to December 2025, then
    `strength_seeded`), the market's average adoption (`market`, then `market_seeded`), and
    what it costs a firm: a platform (capex to 1500, amortised to 6100) and a subscription per
    lawyer a month (6100)."""

    key: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    label: str = Field(min_length=1)
    start: tuple[int, int]  # the first month a firm can adopt it
    tasks: dict[str, float]
    strength: tuple[PathPoint, ...] = Field(min_length=1)
    strength_seeded: SeededTarget | None = None
    market: tuple[PathPoint, ...] = Field(min_length=1)
    market_seeded: SeededTarget | None = None
    platform_cents: int = Field(ge=0)  # one-off, for the firm
    subscription_cents: int = Field(ge=0)  # per lawyer a month at full coverage
    note: str = ""

    @model_validator(mode="after")
    def _check(self) -> EraDef:
        _ym_ok(self.start, f"era {self.key} start")
        if bad := sorted(set(self.tasks) - set(TASKS)):
            raise ValueError(f"era {self.key}: unknown tasks {bad}")
        if any(not 0 <= v <= 1 for v in self.tasks.values()):
            raise ValueError(f"era {self.key}: task strengths must be in [0, 1]")
        _ordered(self.strength, f"era {self.key} strength")
        _ordered(self.market, f"era {self.key} market")
        return self


class LegalEras(_Strict):
    """legal_eras.yaml (ADR PT-0011 2)."""

    history_end: tuple[int, int]  # the last month of history; seeded paths start after it
    eras: tuple[EraDef, ...] = Field(min_length=1)
    sources: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check(self) -> LegalEras:
        keys = [e.key for e in self.eras]
        if len(set(keys)) != len(keys):
            raise ValueError("legal_eras: duplicate era keys")
        return self

    def era(self, key: str) -> EraDef:
        for e in self.eras:
            if e.key == key:
                return e
        raise KeyError(f"no era {key!r}")

    @property
    def keys(self) -> tuple[str, ...]:
        return tuple(e.key for e in self.eras)


class Band(_Strict):
    lo: int
    hi: int
    default: int

    @model_validator(mode="after")
    def _check(self) -> Band:
        if not self.lo <= self.default <= self.hi:
            raise ValueError("band: lo <= default <= hi")
        return self


class AdoptionBalance(_Strict):
    speed: float = Field(gt=0, le=1)
    decay: float = Field(ge=0, le=1)
    cko_speed: float = Field(ge=0)
    training_share: float = Field(ge=0, le=1)
    training_full_hours: int = Field(gt=0)
    cko_training: float = Field(ge=0)
    buyin_from: float = Field(ge=1, le=20)
    buyin_to: float = Field(ge=1, le=20)
    buyin_floor: float = Field(ge=0, le=1)
    support_score: float = Field(ge=1, le=20)
    rollout_threshold_bp: int = Field(gt=0, le=10000)
    vote_sd: float = Field(ge=0)
    pilot_cap: float = Field(ge=0, le=1)
    retry_months: int = Field(ge=1)
    platform_months: int = Field(ge=1)
    full_from: float = Field(gt=0, le=1)

    @model_validator(mode="after")
    def _check(self) -> AdoptionBalance:
        if self.buyin_from >= self.buyin_to:
            raise ValueError("tech.adoption: buyin_from < buyin_to")
        return self


class ClientsTechBalance(_Strict):
    pressure_from: tuple[int, int]
    lag_months: int = Field(ge=0)
    pass_through: float = Field(ge=0, le=1)
    discount: float = Field(ge=0, le=1)
    max_cut: float = Field(ge=0, le=1)
    rfp_from_year: int
    w_rfp: float = Field(ge=0)


class TrainingBalance(_Strict):
    hours: Band  # the programme's hours a lawyer a year
    cost_cents_per_hour: int = Field(ge=0)
    levels: tuple[str, ...] = Field(min_length=1)  # who attends (balance people.levels keys)
    learn_loss: float = Field(ge=0, le=1)
    restore: float = Field(ge=0, le=1)
    full_hours: int = Field(gt=0)


class ProductsBalance(_Strict):
    stage: int = Field(ge=0, le=5)
    price_bp: Band
    max_products: int = Field(ge=1)
    accept_full_bp: int = Field(gt=0)
    accept_none_bp: int = Field(gt=0)

    @model_validator(mode="after")
    def _check(self) -> ProductsBalance:
        if self.accept_full_bp >= self.accept_none_bp:
            raise ValueError("tech.products: accept_full_bp < accept_none_bp")
        return self


class TechBalance(_Strict):
    adoption: AdoptionBalance
    clients: ClientsTechBalance
    training: TrainingBalance
    products: ProductsBalance
    exposed_min: float = Field(ge=0, le=1)  # a task is "exposed" at this ai_exposure or more
