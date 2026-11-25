"""Schemas for PT-M13 (ADR-0008): `mergers.*` in balance.yaml (ADR PT-0016). Model definitions
only (no imports from the rest of the sim), so `ptk.sim.data_models` can import them.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Span(_Strict):
    lo: float
    hi: float

    @model_validator(mode="after")
    def _check(self) -> Span:
        if self.lo > self.hi:
            raise ValueError("span: lo <= hi")
        return self


class BooksBalance(_Strict):
    """The other firm's closing balance sheet from its run-rates (ADR PT-0016 2)."""

    wip_days: int = Field(ge=0)
    ar_days: int = Field(ge=0)
    ar_due_months: int = Field(ge=1)
    cash_months: float = Field(ge=0)
    debt_share: float = Field(ge=0, le=1)
    annuity_share: Span
    lease_years: Span
    rent_per_seat_cents: int = Field(ge=0)  # a month, where its city has no rent of its own
    wip_rate_cents: int = Field(gt=0)  # carried WIP's hours at this rate an hour
    annuity_years: int = Field(ge=1)  # carried annuities are paid over this many years
    facility_mult: float = Field(ge=1)  # the revolver's facility grows by its debt x this


class BookBalance(_Strict):
    """The other firm's client book (ADR PT-0016 2)."""

    client_cents: int = Field(gt=0)  # a year of the firm's revenue per book client
    max_clients: int = Field(ge=1)
    relationship: Span  # its relationships' scores, 0-100
    adverse_p: float = Field(ge=0, le=1)  # an engagement adverse to another client
    adverse_player_bias: float = Field(ge=0)  # weight of the player's clients among adverse
    practices_per_client: int = Field(ge=1)


class DiligenceBalance(_Strict):
    fee_bp: int = Field(ge=0)  # of the other firm's revenue, per level
    min_fee_cents: int = Field(ge=0)
    months: int = Field(ge=0)  # months a level takes
    half_width: tuple[float, ...]  # a range's half width by level (0 = none yet)
    offset_share: float = Field(ge=0, lt=1)  # the fixed offset, as a share of the half width


class AnswerBalance(_Strict):
    """How the other partnership answers: talks (round 0) and terms."""

    talk_bias: dict[str, float | None]  # by personality; None: never merges (elite_lockstep)
    complement_weight: float
    pep_weight: float  # talks: points per unit of PEP ratio above 1 (ours / theirs)
    region_weight: float  # talks: a region the other firm lacks
    noise_sd: float = Field(ge=0)
    pep_change_weight: float  # terms: points per unit of expected PEP change
    synergy_bp: int = Field(ge=0)  # partners expect the merged pool this much above the sum
    mp_weight: float  # terms: their side loses the MP
    name_weight: float  # terms: their name goes
    comp_weight: float  # terms: their comp system changes
    rate_weight: float  # terms: points per unit of rate card change for their clients
    counter_margin: float  # a counter asks for this PEP change for its median partner
    max_rounds: int = Field(ge=1)


class ClearanceBalance(_Strict):
    waiver_base: float = Field(ge=0, le=1)
    waiver_rel: float = Field(ge=0, le=1)
    waiver_max: float = Field(ge=0, le=1)


class IntegrationBalance(_Strict):
    months: int = Field(ge=1)  # integration's length after closing
    clash_comp: dict[str, dict[str, float]]  # comp-system distance 0-1 (symmetric pairs)
    personality_distance: float = Field(ge=0, le=1)  # different personalities' distance
    flight_mult: float = Field(ge=0)  # flight x (1 + this x clash) for the other side
    pep_fall_mult: float = Field(ge=0)  # flight x (1 + this) for a partner whose PEP fell
    subordinated_mult: float = Field(ge=0)  # ... whose practice the other side leads
    subordinated_share: float = Field(ge=0, le=1)  # their side's share of the practice below
    balk_bp: int = Field(ge=0)  # monthly chance per unit of card rise x sensitivity / 10
    balk_months: int = Field(ge=0)
    surrender_months: int = Field(ge=0)  # rent paid to surrender a home-city lease
    confidence_nudge: float  # each partner's confidence at closing, by side's PEP change


class VereinBalance(_Strict):
    cost_base_cents: int = Field(ge=0)  # a month
    cost_bp: int = Field(ge=0)  # of the members' revenue, a month
    referral_months: int = Field(ge=1)  # a member introduces a client every this many months
    referral_score: Span
    talk_bias: dict[str, float | None]  # by personality, for a verein
    appeal_share: float = Field(ge=0)  # reputation shared: appeal points per member


class RivalMergersBalance(_Strict):
    approach_bp: int = Field(ge=0)  # monthly chance a rival with a reason approaches the player
    approach_min_utility: float
    min_player_lawyers: int = Field(ge=0)  # rivals approach only a firm at least this large
    cooldown_months: int = Field(ge=0)
    free_rate_bp: int = Field(ge=0)  # from 2026: a quarter's chance of one rival merger
    free_max_ratio: float = Field(gt=0)  # the smaller firm's lawyers at most this share
    free_personalities: tuple[str, ...]  # personalities that buy


class MergersBalance(_Strict):
    max_lawyers: int = Field(ge=1)
    absorbed_below_bp: int = Field(ge=0, le=10000)
    vote_bp: int = Field(ge=5001, le=10000)  # each partnership's threshold (spec 8.8: two thirds)
    confidential_months: int = Field(ge=1)
    leak_nudge: float
    talks_months: int = Field(ge=1)  # talks lapse after this many months without progress
    cooldown_months: int = Field(ge=0)  # after talks end, no new approach to the firm
    books: BooksBalance
    book: BookBalance
    diligence: DiligenceBalance
    answer: AnswerBalance
    clearance: ClearanceBalance
    integration: IntegrationBalance
    verein: VereinBalance
    rival: RivalMergersBalance
