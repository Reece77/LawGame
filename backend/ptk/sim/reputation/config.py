"""Schemas for PT-M16's reputation tunables (ADR-0008): `reputation.*` in balance.yaml. Model
definitions only (no imports from the rest of the sim), so `ptk.sim.data_models` can import
them without a cycle."""

from __future__ import annotations

from typing import Final

from pydantic import BaseModel, ConfigDict, Field, model_validator

# How a public matter ended (matters.models.Outcome) as reputation sees it (spec 12.1): only
# named matters are public; flow work never moves reputation.
OUTCOME_KEYS: Final = ("won", "lost", "settled", "closed", "collapsed", "done")
BANDS: Final = 6  # directory bands 1-6 (spec 12.3)


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class MeanWeights(_Frozen):
    """The long-run mean a firm's reputation in a practice drifts toward (0-100 points):
    floor + size x s + record x r + pep x q (spec 12.1)."""

    floor: float = Field(ge=0, le=100)
    size: float = Field(ge=0)
    record: float = Field(ge=0)
    pep: float = Field(ge=0)
    size_full_lawyers: float = Field(gt=0)  # lawyers in the practice for the full size term

    @model_validator(mode="after")
    def _check(self) -> MeanWeights:
        if self.floor + self.size + self.record + self.pep > 100 + 1e-9:  # tunable-exempt: tol
            raise ValueError("reputation.mean weights must sum to at most 100")
        return self


class RivalRecord(_Frozen):
    """A rival's record term: its strong practices (firms.yaml) and its share of the market."""

    strong: float = Field(ge=0, le=1)
    share: float = Field(ge=0, le=1)


class LeaguePulse(_Frozen):
    top3: float = Field(ge=0)  # points for a top-three place in a quarter's league table
    top10: float = Field(ge=0)  # points for places four to ten


class PrestigeBalance(_Frozen):
    pep_points: float = Field(ge=0)  # prestige points for the top profit-per-partner rank
    offer_weight: float = Field(ge=0)  # offer-score points at prestige 100 (campus, laterals)


class CardCurve(_Frozen):
    """PT-M7b's card target from reputation; PT-M7c (Reece, 2026-11-23): relative, read as the
    firm's percentile among all firms in the practice and region:
    start + (1 - start) x min(1, percentile / top_quantile)^curve."""

    curve: float = Field(gt=0)
    top_quantile: float = Field(gt=0, lt=1)  # a firm at this percentile or above is "top"


class ReputationBalance(_Frozen):
    start_founders: float = Field(ge=0, le=100)  # a new firm in its founders' practices
    start_other: float = Field(ge=0, le=100)  # and elsewhere
    speed: float = Field(gt=0, le=1)  # share of the gap to the long-run mean closed a month
    mean: MeanWeights
    rival_record: RivalRecord
    share_ref_place: int = Field(ge=1)  # the market's nth-largest practice revenue scores share 1
    record_months: int = Field(ge=1)  # months of public outcomes in the record term
    record_full: float = Field(gt=0)  # outcome points over record_months for the full record
    outcomes: dict[str, float]  # points by outcome for a matter of full size
    big_cents: int = Field(gt=0)  # expected fees of a full-size matter (smaller ones scale)
    pulse: float = Field(ge=0)  # reputation points a full outcome point moves at once
    star_book_cents: int = Field(gt=0)  # a partner with this book or more is a star
    star_join: float = Field(ge=0)
    star_leave: float = Field(ge=0)
    rival_departure: float = Field(ge=0)  # points a rival loses in each practice per key partner
    league: LeaguePulse
    bands: tuple[float, ...]  # October's points by directory band 1..6
    prestige: PrestigeBalance
    card: CardCurve
    appeal_span: float = Field(ge=0)  # the appeal's Rep gained from reputation 0 to 100
    causes_kept: int = Field(ge=1)  # the player's reputation changes kept with their causes

    @model_validator(mode="after")
    def _check(self) -> ReputationBalance:
        if sorted(self.outcomes) != sorted(OUTCOME_KEYS):
            raise ValueError(f"reputation.outcomes must name {OUTCOME_KEYS}")
        if len(self.bands) != BANDS:
            raise ValueError(f"reputation.bands needs {BANDS} values")
        return self
