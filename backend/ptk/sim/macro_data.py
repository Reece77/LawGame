"""Seed-data and balance schemas for the macro and legal indices (PT-M7; spec 6, 14; ADR-0008).

`macro_history.yaml` holds dated points of each index (1.0 = the 2005 average) and the market's
yearly rate rises; `balance.yaml`'s `macro:` section the weights that connect them to demand,
collections and the lateral market. Kept out of `ptk.sim.data_models` as PT-M5's schemas are.
"""

from __future__ import annotations

from typing import Final

from pydantic import BaseModel, ConfigDict, Field, model_validator

# The indices (spec 14's macro layer, v1's subset). Each practice's demand driver is one of
# them (practices.yaml `index`); the last three drive the firm's environment, not demand.
SERIES: Final = (
    "growth",  # long-run real growth of large-firm legal work, G in spec 6
    "ma",  # M&A volume
    "pe",  # PE deal and fundraising volume
    "issuance",  # IPO and securities issuance
    "lending",  # leveraged lending
    "credit",  # credit conditions: the 2005 default rate over the month's (falls in a crisis)
    "cycle",  # broad business activity (litigation and employment move against it)
    "enforcement",  # SEC and DOJ enforcement intensity
    "ip",  # patent litigation and tech activity
    "real_estate",  # commercial property transactions
    "lateral_heat",  # the lateral market: moves per year over 2005's
    "collections",  # clients' payment stress: days to pay over 2005's
)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class MacroPoint(_Strict):
    """The indices at one month; a series a point omits is interpolated across it."""

    ym: tuple[int, int]
    values: dict[str, float]
    note: str = ""

    @model_validator(mode="after")
    def _check(self) -> MacroPoint:
        if not 1 <= self.ym[1] <= 12:  # tunable-exempt: calendar months
            raise ValueError(f"macro point {self.ym}: month must be 1-12")
        if bad := sorted(set(self.values) - set(SERIES)):
            raise ValueError(f"macro point {self.ym}: unknown series {bad}")
        if any(v <= 0 for v in self.values.values()):
            raise ValueError(f"macro point {self.ym}: indices must be positive")
        return self


class ShockDef(_Strict):
    """PT-M10: a dated shock the indices alone do not carry (the 2020 pandemic): for `months`
    from `from`, each named practice loses a share of its demand (new work and flow) and of the
    hours its named matters plan (deals paused, hearings adjourned), and open court cases'
    planned duration grows a month for each month the courts are slowed (`docket`)."""

    from_ym: tuple[int, int] = Field(alias="from")
    months: int = Field(ge=1)
    demand: dict[str, float]  # practice -> share of the month's demand lost, 0-1
    hours: dict[str, float]  # practice -> share of named matters' planned hours paused, 0-1
    docket: bool  # courts slowed: open cases' planned months extend by one each month
    src: str

    @model_validator(mode="after")
    def _check(self) -> ShockDef:
        if any(not 0 <= v < 1 for v in (*self.demand.values(), *self.hours.values())):
            raise ValueError(f"shock {self.from_ym}: shares must be in [0, 1)")
        return self


class MacroData(_Strict):
    sources: dict[str, str]  # series -> the dossier's source line
    points: tuple[MacroPoint, ...] = Field(min_length=1)
    rate_rise: dict[int, float]  # year -> the market's January rate rise (0.065 = 6.5%)
    shocks: tuple[ShockDef, ...] = ()  # PT-M10: dated shocks (the 2020 pandemic)
    seed: int | None = None  # PT-M10: set on a save's seeded world (ptk.sim.macro_seed)

    @model_validator(mode="after")
    def _check(self) -> MacroData:
        yms = [p.ym for p in self.points]
        if yms != sorted(yms) or len(set(yms)) != len(yms):
            raise ValueError("macro_history points must be in date order, one per month")
        for key in SERIES:
            if not any(key in p.values for p in self.points):
                raise ValueError(f"macro_history: no point gives series {key!r}")
            if key not in self.sources:
                raise ValueError(f"macro_history: series {key!r} needs a source")
        if any(not -0.2 < r < 0.5 for r in self.rate_rise.values()):  # tunable-exempt: sanity
            raise ValueError("macro_history rate_rise must be a fraction, e.g. 0.065")
        return self


class CrisisBalance(_Strict):
    """balance.yaml `macro.crisis:` (PT-M7b; spec 14's 2008-2009: "clients demand discounts").

    The month's stress is 0-1: the larger of the collections index's rise above
    `collections_from` (1 at `collections_full`) and the credit index's fall below `credit_from`
    (1 at `credit_full`)."""

    collections_from: float = Field(gt=0)
    collections_full: float = Field(gt=0)
    credit_from: float = Field(gt=0)
    credit_full: float = Field(ge=0)
    sector_weight: float = Field(ge=0)  # a client's factor x (1 + w x its sector's stress)
    sensitivity_neutral: float = Field(gt=0)  # price sensitivity at which the factor is 1
    discount_bp: int = Field(ge=0)  # bp off new engagements at stress 1 and factor 1
    discount_max_bp: int = Field(ge=0)  # the most a crisis discount reaches
    ask_bp: int = Field(ge=0, le=10000)  # chance a bill meets a write-down request (stress 1)
    writedown_bp: tuple[int, int]  # the request's size, bp of the bill, uniform
    collapse_month_bp: int = Field(ge=0, le=10000)  # a deal's monthly collapse chance per unit
    close_k: float = Field(ge=0)  # logit points off p_close per unit of the driver's shortfall


class EpisodeBalance(_Strict):
    """A recession in history (PT-M10): its start month and its trough."""

    from_ym: tuple[int, int] = Field(alias="from")
    trough: tuple[int, int]

    @model_validator(mode="after")
    def _check(self) -> EpisodeBalance:
        if not self.from_ym < self.trough:
            raise ValueError("a recession episode's trough must follow its start")
        return self


class ScaleSeedBalance(_Strict):
    """balance.yaml `macro.seeded.scale:` (PT-M10): when the market leader raises the scale."""

    month: int = Field(ge=1, le=12)  # the month a step takes effect
    heat_from: float = Field(gt=0)  # lateral heat (12-month mean) at least this
    rate_from: float  # and the year's rate rise at least this (profits running hot)
    min_gap_years: int = Field(ge=1)  # years since the last step
    chance_bp: int = Field(ge=0, le=10000)  # chance a hot year brings a step
    step_years_from: int  # history's steps from this year are the step sizes drawn
    fallback_step: float = Field(gt=0)  # the step when history gives none


class SeededBalance(_Strict):
    """balance.yaml `macro.seeded:` (PT-M10, ptk.sim.macro_seed): the world after history."""

    start: tuple[int, int]  # the first seeded month (history is pinned to the month before)
    until: tuple[int, int]  # the last seeded month
    fit_years: tuple[int, int]  # the history the processes are fitted to (July values)
    mean_years: tuple[int, int]  # a mean-reverting index's long-run level: these years' mean
    trend_series: tuple[str, ...]  # indices that revert to a fitted trend, not a mean
    phi_range: tuple[float, float]  # the annual AR(1) coefficient is held in this range
    noise_scale: float = Field(ge=0)  # multiplier on the fitted residual spread
    episodes: tuple[EpisodeBalance, ...] = Field(min_length=1)  # history's recessions
    recession_hazard_scale: float = Field(ge=0)  # multiplier on history's frequency
    recession_gap_months: int = Field(ge=1)  # the least time between two recessions' starts
    rate_range: tuple[float, float]  # a seeded rate rise is held in this range
    scale: ScaleSeedBalance

    @model_validator(mode="after")
    def _check(self) -> SeededBalance:
        if not self.fit_years[0] < self.fit_years[1] < self.start[0]:
            raise ValueError("macro.seeded: fit years must end before the seeded start")
        if not self.start <= self.until:
            raise ValueError("macro.seeded: start must not follow until")
        if bad := sorted(set(self.trend_series) - set(SERIES)):
            raise ValueError(f"macro.seeded: unknown trend series {bad}")
        return self


class MacroBalance(_Strict):
    """balance.yaml `macro:` (PT-M7): how the indices act on the firm."""

    beta_scale: float = Field(ge=0)  # multiplier on every practice's beta
    demand_floor: float = Field(gt=0)  # the least a practice's driver term can fall to
    collections_weight: float = Field(ge=0)  # days to pay x (1 + w (I - 1))
    lateral_heat_weight: float = Field(ge=0)  # resignations and V_mkt x (1 + w (I - 1))
    estate_mult: float = Field(ge=0)  # a bankrupt client's restructuring weight multiplier
    estate_months: int = Field(ge=0)  # months the estate keeps instructing restructuring work
    rescue_months: int = Field(ge=0)  # months a rescued client's wallet runs on, then ends
    crisis: CrisisBalance  # PT-M7b: crisis discounts, write-downs and collapsing deals
    seeded: SeededBalance | None = None  # PT-M10: the seeded world after history (None: held)
