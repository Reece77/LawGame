"""Seed-data and balance schemas for rival firms and real people (PT-M5; ADR-0008).

`firms.yaml` (the 2005 rivals and their dated history), `notables.yaml` (real lawyers) and
`judges.yaml` (real trial judges) are validated here at load; `balance.yaml`'s `rivals:` and
`world:` sections too. Invalid data fails at startup.

Kept out of `ptk.sim.data_models` so PT-M5's schemas live in its own package; that module
only adds the fields that hold them.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

type Personality = Literal[
    "elite_lockstep",
    "global_verein",
    "performance_machine",
    "litigation_boutique",
    "tech_coast",
    "regional_champion",
    "volume_mid_market",
    "big_four_legal",
    "plaintiff_firm",  # PT-M12
    "private_client_firm",  # PT-M12
    "arbitration_firm",  # PT-M12
]
type EventKind = Literal["merger", "collapse", "absorbed", "rename", "outside_merger"]
type Standing = Literal["elite", "leading", "strong"]
type MoveKind = Literal[
    "lateral", "government", "judiciary", "in_house", "chair_role", "of_counsel", "left_practice"
]

_KEY = r"^[a-z][a-z0-9_]*$"
RIVAL_ACTIONS: tuple[str, ...] = (
    "raise_rates",
    "cut_rates",
    "hire_associates",
    "hire_lateral",
    "lift_team",
    "approach_player",
    "open_office",
    "cut_costs",
    "de_equitise",
)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


# --- firms.yaml ---------------------------------------------------------------------------


class FyPoint(_Strict):
    """One fiscal year of a firm's history (Am Law fiscal years end in December)."""

    year: int
    revenue_cents: int | None = Field(default=None, gt=0)
    lawyers: int | None = Field(default=None, gt=0)
    equity_partners: int | None = Field(default=None, gt=0)
    pep_cents: int | None = Field(default=None, gt=0)
    src: str = ""  # tags and source keys, e.g. "rev S S1; lawyers S S1; EP A"


class FirmDef(_Strict):
    key: str = Field(pattern=_KEY)
    name: str = Field(min_length=1)
    short: str = Field(min_length=1)
    personality: Personality
    hq: str = Field(min_length=1)
    ny_office: bool = True
    comp: str = Field(min_length=1)  # comp system label [A] unless the dossier sources it
    offices: int = Field(gt=0)
    strong: tuple[str, ...] = ()  # practices.yaml keys: strengths (double weight in the mix)
    panel_base: float | None = None  # NY panel appeal, logit points (clients.yaml if listed)
    start_ym: tuple[int, int] | None = None  # a successor's first month; None = 2005
    fy2005: FyPoint | None = None  # required for a firm that starts in 2005
    path: tuple[FyPoint, ...] = ()  # later fiscal years, ascending
    src: str = ""

    @model_validator(mode="after")
    def _check(self) -> FirmDef:
        if self.start_ym is None and (
            self.fy2005 is None or not self.fy2005.revenue_cents or not self.fy2005.lawyers
        ):
            raise ValueError(f"firm {self.key}: a 2005 firm needs fy2005 revenue and lawyers")
        years = [p.year for p in self.path]
        if years != sorted(set(years)):
            raise ValueError(f"firm {self.key}: path years must ascend")
        return self


class HistoryEventDef(_Strict):
    """A dated event (spec 10.3; ADR PT-0008 2), conditional on the player's effects."""

    key: str = Field(pattern=_KEY)
    ym: tuple[int, int]
    kind: EventKind
    firm: str  # the firm it happens to (a merger's first party)
    other: str | None = None  # a merger's second party, or the firm that absorbs
    into: str | None = None  # a merger's successor firm key
    name: str | None = None  # a rename's or outside merger's new name
    short: str | None = None
    share: float = Field(default=0.0, ge=0, le=1)  # absorbed: share of people who move
    lawyers_added: int = Field(default=0, ge=0)  # outside merger: lawyers who join
    src: str = ""


class FirmsData(_Strict):
    firms: tuple[FirmDef, ...] = Field(min_length=1)
    events: tuple[HistoryEventDef, ...] = ()

    def firm(self, key: str) -> FirmDef:
        for f in self.firms:
            if f.key == key:
                return f
        raise KeyError(f"unknown rival firm {key!r}")

    @model_validator(mode="after")
    def _refs(self) -> FirmsData:
        keys = [f.key for f in self.firms]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate rival firm keys")
        known = set(keys)
        for e in self.events:
            for ref in (e.firm, e.other, e.into):
                if ref is not None and ref not in known:
                    raise ValueError(f"event {e.key}: unknown firm {ref!r}")
            if e.kind == "merger" and (e.other is None or e.into is None):
                raise ValueError(f"event {e.key}: a merger needs other and into")
            if e.kind == "absorbed" and e.other is None:
                raise ValueError(f"event {e.key}: absorbed needs the absorbing firm (other)")
        return self


# --- notables.yaml and judges.yaml (ADR PT-0013) ------------------------------------------


class MoveDef(_Strict):
    ym: tuple[int, int]
    kind: MoveKind
    to: str | None = None  # a lateral's destination: a firms.yaml key, or None (elsewhere)


class NotableDef(_Strict):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]*__[a-z0-9_]+$")
    firm: str
    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    practice: str  # practices.yaml key
    level: Literal["equity_partner", "income_partner", "counsel"] = "equity_partner"
    standing: Standing
    chair: bool = False  # the firm's chair or managing partner in 2005
    career_start: int = Field(ge=1930, le=2005)  # law school graduation or bar admission
    left_practice: int | None = None  # the year they stopped practising, no cause (PT-0013)
    moves: tuple[MoveDef, ...] = ()
    role_2005: str = Field(min_length=1)
    src: str = Field(min_length=1)  # the [S] source for the 2005 role, plus others


class JudgeDef(_Strict):
    court: str
    name: str = Field(min_length=1)  # as commonly cited
    joined: int = Field(ge=1950, le=2025)
    left: int | None = None  # left active service on the court (any reason, no cause)
    senior: int | None = None  # senior status year (still hears cases)
    traits: dict[str, float] = Field(default_factory=dict)  # sourced per-judge traits only
    src: str = Field(min_length=1)


class CourtStats(_Strict):
    """Published court-level statistics (US Courts FCMS, 12 months to September 2005)."""

    court: str
    disposition_months: float | None = None
    trial_months: float | None = None
    trials_per_judgeship: float | None = None
    src: str = ""


class PeopleData(_Strict):
    notables: tuple[NotableDef, ...] = ()
    judges: tuple[JudgeDef, ...] = ()
    court_stats: tuple[CourtStats, ...] = ()

    @model_validator(mode="after")
    def _unique(self) -> PeopleData:
        keys = [n.key for n in self.notables]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate notable keys")
        return self


class RivalsData(_Strict):
    """Everything PT-M5 reads from seed data."""

    firms: FirmsData
    people: PeopleData

    def check(self, practices: set[str], courts: set[str]) -> None:
        for f in self.firms.firms:
            if bad := sorted(set(f.strong) - practices):
                raise ValueError(f"firm {f.key}: unknown practices {bad}")
        known = {f.key for f in self.firms.firms}
        for n in self.people.notables:
            if n.firm not in known:
                raise ValueError(f"notable {n.key}: unknown firm {n.firm!r}")
            if n.practice not in practices:
                raise ValueError(f"notable {n.key}: unknown practice {n.practice!r}")
            for m in n.moves:
                if m.to is not None and m.to not in known:
                    raise ValueError(f"notable {n.key}: unknown destination {m.to!r}")
        for j in self.people.judges:
            if j.court not in courts:
                raise ValueError(f"judge {j.name}: unknown court {j.court!r}")


# --- balance.yaml: rivals and world -------------------------------------------------------


class Band(_Strict):
    lo: float
    hi: float


class PersonalityDef(_Strict):
    """Utility weights (spec 10.2) and the shape of a firm of this personality."""

    label: str = Field(min_length=1)
    weights: dict[str, float]  # RIVAL_ACTIONS -> weight
    equity_share: float = Field(gt=0, lt=1)  # equity partners / lawyers
    partner_share: float = Field(gt=0, lt=1)  # all partners and counsel / lawyers
    utilisation: float = Field(gt=0, le=1)  # target share of capacity billed
    growth_bias: float  # free play: extra demand growth a year from its strategy
    fragility: float = Field(ge=0)  # multiplier on the collapse hazard
    mix: dict[str, float]  # lawyers by practice before strengths (normalised)

    @model_validator(mode="after")
    def _check(self) -> PersonalityDef:
        if bad := sorted(set(self.weights) - set(RIVAL_ACTIONS)):
            raise ValueError(f"unknown rival actions {bad}")
        if self.equity_share >= self.partner_share:
            raise ValueError("equity_share must be below partner_share")
        return self


class GeneratedBalance(_Strict):
    count: int = Field(ge=0)
    revenue_cents: Band  # LogNormal clipped: lo-hi of FY2005 revenue
    revenue_median_cents: float = Field(gt=0)
    revenue_sigma: float = Field(ge=0)
    rpl_cents: Band  # revenue per lawyer, uniform
    personalities: dict[str, float]  # weights
    ny_share: float = Field(ge=0, le=1)  # share with a New York office (panel-eligible)
    key_partners: int = Field(ge=0)
    key_associates: int = Field(ge=0)


class PinBalance(_Strict):
    end_year: int  # the history pin holds to December of this year (PT-M5: 2015)
    band: float = Field(gt=0, lt=1)  # T11's band, +-
    noise_sd: float = Field(ge=0)  # monthly AR(1) shock to demand
    noise_phi: float = Field(ge=0, lt=1)  # AR(1) persistence
    recovery_per_year: float = Field(ge=0, le=1)  # share of a player shock the firm recovers


class CollapseBalance(_Strict):
    window_months: int = Field(ge=0)  # months before a dated collapse the firm is fragile
    base_bp: float = Field(ge=0)  # monthly hazard of a firm in its window with no shock
    departed_threshold: float = Field(ge=0, le=1)  # 12-month departed share of key partners
    departed_slope_bp: float = Field(ge=0)  # hazard bp per point of share above threshold
    other_mult: float = Field(ge=0)  # hazard multiplier outside a dated window
    merger_calloff_share: float = Field(ge=0, le=1)  # departed share that calls a merger off
    scatter_player_share: float = Field(ge=0, le=1)  # of a collapse's people, free agents
    free_agent_months: int = Field(ge=0)


class PoachBalance(_Strict):
    """TST formulas.md 15.6, for law: a rival's offer to one of the player's people."""

    salary_weight: float
    morale_mid: float
    morale_divisor: float = Field(gt=0)
    loyalty_mid: float
    loyalty_divisor: float = Field(gt=0)
    leave_penalty: float
    poachability_divisor: float = Field(gt=0)  # hidden poachability: (p - 10) / divisor
    steepness: float = Field(gt=0)
    bands: Band
    offer_premium: Band  # offer over the person's pay (or partner market value)
    max_per_year: int = Field(ge=0)  # approaches to the player's people a year, cap
    player_ask_premium: float = Field(ge=0)  # a rival's person asks this much more to move
    candidates: Band  # key people shown by one "approach a rival" search


class RfpBalance(_Strict):
    review_years: int = Field(gt=0)  # a large client's panel review cycle (spec 7.2)
    bidders: Band  # rivals that bid beside the incumbents
    matter_rfp_bp: float = Field(ge=0)  # monthly chance a large client runs a matter RFP
    matter_min_cents: int = Field(gt=0)
    pitch_months: int = Field(gt=0)  # months from the RFP to the award
    w_pitch: float  # logit points per point of pitch quality above 10
    w_claim: float  # logit points per substantiated claim
    w_incumbent: float  # incumbency in the logit
    w_relationship: float  # the player's relationship (0-100) / 100
    noise_sd: float = Field(ge=0)
    team_max: int = Field(gt=0)
    player_reputation_min: float = Field(ge=0, le=1)  # invited to an RFP without a relationship
    start_score: float = Field(ge=0, le=100)  # a new relationship from an RFP win


class BoutiqueBalance(_Strict):
    monthly_bp: float = Field(ge=0)  # chance a large rival's partner group leaves to found one
    partners: Band
    associates_per_partner: float = Field(ge=0)
    book_share: float = Field(ge=0, le=1)  # of the founders' books that follows them
    failure_bp: float = Field(ge=0)  # monthly hazard while below break-even
    growth_bias: Band  # demand growth a year, uniform
    max_alive: int = Field(ge=0)


class RivalsBalance(_Strict):
    first_firm_id: int = Field(gt=1)  # firm ids below this are the player's
    first_person_id: int = Field(gt=0)  # rival people ids start here (never a player's id)
    key_partners: int = Field(ge=0)  # top partners kept as individuals (ADR PT-0008 3)
    key_associates: int = Field(ge=0)
    key_book_share: float = Field(ge=0, le=1)  # key partners' books, share of revenue
    book_pareto: float = Field(gt=0)  # book_i ~ rank^-a
    personalities: dict[str, PersonalityDef]
    actions_per_month: int = Field(gt=0)
    second_action_min: float  # a second action needs this utility
    noise_sd: float = Field(ge=0)  # U's N(0, 0.1)
    cooldown_months: dict[str, int]
    rate_step: float = Field(gt=0)  # a rate rise or cut
    rate_need_span: float = Field(gt=0)  # RPL gap that makes the need 1
    rate_elasticity: float = Field(ge=0)  # demand lost per unit of rate above the market
    hire_span: float = Field(gt=0)  # headcount gap (share of lawyers) that makes the need 1
    hire_max_monthly: float = Field(gt=0)  # share of lawyers hired in a month, at most
    cut_max_monthly: float = Field(gt=0)  # share laid off in a month, at most
    lateral_book_cents: float = Field(gt=0)  # a lateral partner's book from the market
    lateral_portability: float = Field(ge=0, le=1)
    office_demand: float = Field(ge=0)  # free play: demand added by an office over 2 years
    office_cost_cents: int = Field(ge=0)  # a year
    cost_growth: float  # cost per lawyer growth a year (wages, rent)
    rate_inflation: float  # free play: revenue per lawyer at capacity grows this much a year
    market_growth: dict[int, float]  # nominal large-firm market growth by year (free play)
    market_growth_after: float  # each year after the table
    cut_costs_margin: float  # cut costs when the margin falls below this
    de_equitise_pep: float  # de-equitise when PEP falls below this share of last year's
    approach_need: float = Field(ge=0, le=1)  # need of approach_player when it has a target
    appeal_size_base: float  # NY appeal of a $100M firm without a clients.yaml panel appeal
    appeal_size_slope: float  # appeal points per tenfold revenue
    appeal_size_min: float
    appeal_size_max: float
    appeal_rep_weight: float  # NY panel appeal per point of key-partner quality change
    appeal_price_weight: float
    appeal_capacity_weight: float
    pin: PinBalance
    collapse: CollapseBalance
    poach: PoachBalance
    rfp: RfpBalance
    boutique: BoutiqueBalance
    generated: GeneratedBalance
    standing_ca: dict[str, Band]  # a real notable's CA range from their standing (PT-0013)
    judge_trait_sd: float = Field(ge=0)  # a real judge's traits around their court's figures
    notable_familiarity: float = Field(ge=1, le=20)  # a notable's home-practice familiarity
    retire_age: int = Field(gt=0)  # rival people retire at this age (real people: their year)
    career_start_age: int = Field(gt=0)  # a notable's age at career start (no birth date)


class WorldBalance(_Strict):
    real_people: bool = True  # ADR PT-0013: the default for a new game
