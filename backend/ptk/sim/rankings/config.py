"""Schemas for PT-M16's rankings tunables (ADR-0008): `rankings.*` in balance.yaml. Model
definitions only (no imports from the rest of the sim)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

BANDS = 6  # tunable-exempt: directory bands 1-6 (spec 12.3)


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class TablesBalance(_Frozen):
    """The spring revenue and PEP tables for the prior fiscal year (spec 12.3)."""

    month: int = Field(ge=1, le=12)  # calendar month they publish
    revenue_places: int = Field(ge=1)  # the Am Law 100 and 200 analogue
    pep_places: int = Field(ge=1)
    min_revenue_cents: int = Field(ge=0)  # a firm enters once its revenue is this large


class LeagueBalance(_Frozen):
    """Quarterly league tables by practice and region (spec 12.3)."""

    kinds: tuple[str, ...]  # matter kinds that are deals for the tables (practices.yaml kinds)
    value_per_fee: float = Field(gt=0)  # a deal's transaction value per dollar of fees
    rival_deal_share: float = Field(ge=0, le=1)  # share of a rival's practice fees from deals
    places: int = Field(ge=1)  # places published


class DirectoryBalance(_Frozen):
    """October's directory bands (spec 12.3)."""

    month: int = Field(ge=1, le=12)
    thresholds: tuple[float, ...]  # the score for band 1..6, descending
    submission_months: tuple[int, int]  # the March-April window
    max_matters: int = Field(ge=1)
    max_referees: int = Field(ge=0)
    referee_cost: float = Field(ge=0)  # relationship points a referee spends
    energy: int = Field(ge=0)  # the founding partner's energy for a submission
    submission_points: float = Field(ge=0)  # score points for the strongest submission
    no_submission: float = Field(
        ge=0
    )  # score points lost with no submission (a weak one loses bands)
    matter_full_cents: int = Field(gt=0)  # a showcased matter's fees for its full weight
    key_matters: float = Field(ge=0)  # score points for key matters (the record) at the full record
    appeal_bonus: tuple[float, ...]  # the appeal's Rep added by band 1..6 (spec 7.1)
    recruit_bonus: tuple[float, ...]  # offer-score points by band in the candidate's practice
    standing_band: dict[str, int]  # a real notable's band by notables.yaml standing
    people_min_matters: int = Field(ge=1)  # public matters led in three years to be named
    people_offset: int = Field(
        ge=0
    )  # a named partner's band: the firm's band + this - their record

    @model_validator(mode="after")
    def _check(self) -> DirectoryBalance:
        for name in ("thresholds", "appeal_bonus", "recruit_bonus"):
            if len(getattr(self, name)) != BANDS:
                raise ValueError(f"rankings.directory.{name} needs {BANDS} values")
        if list(self.thresholds) != sorted(self.thresholds, reverse=True):
            raise ValueError("rankings.directory.thresholds must descend")
        lo, hi = self.submission_months
        if not 1 <= lo <= hi <= 12:  # tunable-exempt: calendar
            raise ValueError("rankings.directory.submission_months must be months lo <= hi")
        return self


class PlacesBalance(_Frozen):
    """Best places to work, the associates' survey (spec 12.3)."""

    month: int = Field(ge=1, le=12)
    min_associates: int = Field(ge=1)
    places: int = Field(ge=1)
    weights: dict[str, float]  # morale, hours, pay, training
    hours_best: int = Field(gt=0)  # billable hours a year scoring the full hours term
    hours_worst: int = Field(gt=0)  # and scoring 0
    training_full: float = Field(gt=0)  # partners per ten associates for the full training term
    rival_base: dict[str, float]  # a rival's survey score 0-100 by personality
    rival_utilisation: float = Field(
        ge=0
    )  # points a rival loses per point of utilisation over 0.85
    top: int = Field(ge=1)  # a place this high or better earns the campus bonus for a year
    campus_bonus: float = Field(ge=0)  # offer-score points on campus offers

    @model_validator(mode="after")
    def _check(self) -> PlacesBalance:
        if sorted(self.weights) != ["hours", "morale", "pay", "training"]:
            raise ValueError("rankings.places.weights: morale, hours, pay, training")
        if abs(sum(self.weights.values()) - 1) > 1e-9:  # tunable-exempt: tolerance
            raise ValueError("rankings.places.weights must sum to 1")
        if self.hours_best >= self.hours_worst:
            raise ValueError("rankings.places.hours_best must be below hours_worst")
        return self


class RankingsBalance(_Frozen):
    tables: TablesBalance
    league: LeagueBalance
    directory: DirectoryBalance
    places: PlacesBalance
    news_top: int = Field(ge=1)  # names from each list's top in the inbox item
