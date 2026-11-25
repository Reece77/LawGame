"""Pydantic schemas for cities.yaml and bar_rules.yaml (PT-M11; spec 8.8, 11.1; ADR PT-0010).

Cities are where a firm may lease an office: each has a region (the macro and reputation
region), a jurisdiction (where a lawyer must be admitted to lead its matters), a local market
sized against the home market's demand, a local rate card and salaries as basis points of the
New York ones, a lease rent per lawyer seat, and the rival keys whose headquarters are there.

Bar rules hold, per jurisdiction: how a lawyer is admitted (by exam, on motion after years in
practice elsewhere, or by qualifying as a solicitor), pro hac vice, compulsory insurance and the
dated ownership rules (ADR PT-0010 1). Values are sourced in docs/research/london-and-us-cities.md.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ptk.sim.risk.config import DisciplineRule

_KEY = r"^[a-z][a-z0-9_]*$"

type Region = Literal["us", "uk"]
type Ownership = Literal["lawyers_only", "limited_non_lawyer", "abs", "any_owner"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CityDef(_Strict):
    key: str = Field(pattern=_KEY)
    label: str = Field(min_length=1)
    region: Region
    jurisdiction: str = Field(pattern=_KEY)
    demand: float = Field(ge=0)  # local demand x the home market's D0 (by practice, with mix)
    mix: dict[str, float] = Field(default_factory=dict)  # practice multipliers on that demand
    rate_bp: int = Field(gt=0)  # the local card as bp of the firm's card (New York = 10000)
    pay_bp: int = Field(gt=0)  # local salaries (bands; associates where no local scale)
    rent_per_seat_cents: int = Field(gt=0)  # a lease's rent a lawyer seat a month
    clients: int = Field(default=0, ge=0)  # generated local clients when a firm opens there
    aliases: tuple[str, ...] = ()  # firms.yaml hq keys that mean this city
    src: str = ""


class AdmissionRule(_Strict):
    """How a lawyer is admitted in a jurisdiction (spec 11.1)."""

    exam: bool = True  # a bar exam is offered
    exam_months: tuple[int, ...] = (2, 7)  # months the exam is sat
    results_months: int = Field(default=4, ge=1)  # months from sitting to the result
    exam_cost_cents: int = Field(default=0, ge=0)  # fees and a course (6200), non-billable
    study_hours: int = Field(default=0, ge=0)  # hours a month of study until the exam
    pass_bp: int = Field(default=8000, ge=0, le=10000)  # an experienced lawyer's pass rate
    motion_years: int | None = None  # admission on motion after this many years in practice
    motion_from: tuple[str, ...] = ()  # jurisdictions whose admission counts for the motion
    motion_cost_cents: int = Field(default=0, ge=0)
    motion_months: int = Field(default=3, ge=1)  # months from application to admission


class OwnershipRule(_Strict):
    from_ym: tuple[int, int]
    rule: Ownership
    src: str = ""


class InsuranceRule(_Strict):
    """Compulsory professional indemnity insurance (England and Wales: spec 11.1, 11.3)."""

    compulsory: bool = False
    min_cover_cents: int = Field(default=0, ge=0)  # per claim, a partnership
    llp_min_cover_cents: int = Field(default=0, ge=0)  # per claim, an LLP or company
    premium_per_lawyer_cents: int = Field(
        default=0, ge=0
    )  # a year's premium a lawyer in the office
    min_premium_cents: int = Field(default=0, ge=0)  # a year's minimum premium
    src: str = ""


class JurisdictionRules(_Strict):
    key: str = Field(pattern=_KEY)
    label: str = Field(min_length=1)
    country: Literal["us", "gb"]
    regulator: str = Field(min_length=1)
    regulator_from: tuple[int, int] | None = None  # e.g. the SRA from January 2007
    admission: AdmissionRule = Field(default_factory=AdmissionRule)
    pro_hac_vice_cents: int | None = None  # a lead's one-off fee per case; None: not offered
    foreign_lawyers: str = ""  # what a foreign lawyer may do (the dossier's summary)
    foreign_lead: bool = False  # a registered foreign lawyer may lead non-contentious matters
    insurance: InsuranceRule = Field(default_factory=InsuranceRule)
    discipline: DisciplineRule = Field(default_factory=DisciplineRule)  # PT-M15 (spec 11.4)
    client_money: str = ""  # the client account rules' name (ADR PT-0003 7 enforces them)
    llp: bool = False  # firms practise as limited liability partnerships
    ownership: tuple[OwnershipRule, ...] = ()
    src: str = ""


class LondonScaleRow(_Strict):
    """The London trainee and associate scale from a date (spec 5.2, 5.4: the UK path):
    trainees' salaries a year in cents (first and second year), then associates' pay as bp of
    the New York scale's class year (a newly qualified solicitor is class 1)."""

    from_ym: tuple[int, int]
    trainee_cents: tuple[int, int]
    associate_bp: int = Field(gt=0)
    src: str = ""


class GeoData(_Strict):
    cities: tuple[CityDef, ...] = ()
    jurisdictions: tuple[JurisdictionRules, ...] = ()
    courts: dict[str, str | None] = Field(default_factory=dict)  # court -> jurisdiction
    london_scale: tuple[LondonScaleRow, ...] = ()

    @model_validator(mode="after")
    def _check(self) -> GeoData:
        keys = [c.key for c in self.cities]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate city keys")
        rules = {j.key for j in self.jurisdictions}
        if len(rules) != len(self.jurisdictions):
            raise ValueError("duplicate bar_rules jurisdictions")
        for c in self.cities:
            if self.jurisdictions and c.jurisdiction not in rules:
                raise ValueError(f"city {c.key}: no bar rules for {c.jurisdiction!r}")
        for court, cj in self.courts.items():
            if cj is not None and cj not in rules:
                raise ValueError(f"court {court}: no bar rules for {cj!r}")
        for jr in self.jurisdictions:
            if bad := sorted(set(jr.admission.motion_from) - rules):
                raise ValueError(f"{jr.key}: motion_from names unknown jurisdictions {bad}")
            dates = [o.from_ym for o in jr.ownership]
            if dates != sorted(dates):
                raise ValueError(f"{jr.key}: ownership rules must be in date order")
        froms = [r.from_ym for r in self.london_scale]
        if froms != sorted(set(froms)):
            raise ValueError("london_scale rows must be in strictly increasing date order")
        return self

    def city(self, key: str) -> CityDef:
        for c in self.cities:
            if c.key == key or key in c.aliases:
                return c
        raise KeyError(f"unknown city {key!r}")

    def has_city(self, key: str) -> bool:
        return any(c.key == key or key in c.aliases for c in self.cities)

    def city_key(self, key: str) -> str | None:
        """A city key, or a firms.yaml hq alias's city; None if it is not a modelled city."""
        for c in self.cities:
            if c.key == key or key in c.aliases:
                return c.key
        return None

    def rules(self, jurisdiction: str) -> JurisdictionRules | None:
        return next((j for j in self.jurisdictions if j.key == jurisdiction), None)

    def court_jurisdiction(self, court: str | None) -> str | None:
        """The jurisdiction a court sits in; None for arbitration (no admission needed)."""
        if court is None:
            return None
        return self.courts.get(court)

    def london_row(self, ym: tuple[int, int]) -> LondonScaleRow | None:
        current = self.london_scale[0] if self.london_scale else None
        for row in self.london_scale:
            if row.from_ym <= ym:
                current = row
        return current


class GeoBalance(_Strict):
    """Offices and the UK path's tunables (balance.yaml `geo:`; PT-M11)."""

    seat_sizes: tuple[int, ...]  # lease sizes, lawyer seats
    lease_months: int = Field(gt=0)  # a lease's term
    fit_out_per_seat_cents: int = Field(ge=0)  # once, to 1500, amortised over the term
    close_penalty_months: int = Field(ge=0)  # months of rent to break a lease
    reach_penalty: float = Field(ge=0)  # appeal logit points without a local office
    lift_portability: tuple[float, float]  # a lifted partner's share of book that follows
    lift_months: int = Field(gt=0)  # a lifted team's clients follow within this many months
    organic_clients: int = Field(ge=0)  # local clients an organic start's partner is introduced to
    organic_relationship: tuple[float, float]  # their relationship's start (0-100)
    omp_appeal: float = Field(ge=0)  # appeal logit points x the office MP's effect, its clients
    lift_associates_per_partner: float = Field(ge=0)
    lift_book_share: float = Field(ge=0, le=1)  # of a lifted partner's book
    local_client_revenue_bn: tuple[float, float]  # generated local clients' range
    training_contract_cost_cents: int = Field(ge=0)  # a contract's fees (6200)
    trainee_seat_months: int = Field(gt=0)
    training_months: int = Field(gt=0)
    qualify_month: int = Field(ge=1, le=12)
    contract_lead_years: int = Field(ge=0)
    max_contracts: int = Field(gt=0)  # a year's training contracts at most
    rfl_cost_cents: int = Field(ge=0)  # registering a foreign lawyer (6200)
