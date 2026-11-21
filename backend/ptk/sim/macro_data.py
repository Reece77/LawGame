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


class MacroData(_Strict):
    sources: dict[str, str]  # series -> the dossier's source line
    points: tuple[MacroPoint, ...] = Field(min_length=1)
    rate_rise: dict[int, float]  # year -> the market's January rate rise (0.065 = 6.5%)

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


class MacroBalance(_Strict):
    """balance.yaml `macro:` (PT-M7): how the indices act on the firm."""

    beta_scale: float = Field(ge=0)  # multiplier on every practice's beta
    demand_floor: float = Field(gt=0)  # the least a practice's driver term can fall to
    collections_weight: float = Field(ge=0)  # days to pay x (1 + w (I - 1))
    lateral_heat_weight: float = Field(ge=0)  # resignations and V_mkt x (1 + w (I - 1))
    estate_mult: float = Field(ge=0)  # a bankrupt client's restructuring weight multiplier
    estate_months: int = Field(ge=0)  # months the estate keeps instructing restructuring work
    rescue_months: int = Field(ge=0)  # months a rescued client's wallet runs on, then ends
