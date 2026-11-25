"""The automation layer's balance (`automation.*`) and fixed lists (PT-M9; spec 9.4; TST
formulas.md 40).

Ported from backend/tst/sim/automation/config.py @ 80a38079 (Tech Startup Tycoon); changed:
Partner Track's areas (spec 9.4's table) with an owner seat each, their guardrails and energy
in `balance.yaml`; spec 9.4's one-offs by the action kinds that carry them; the schema of
`automation.*` lives here (as `seat_data` holds the seats') so `data_models` only imports it.
TST's chain lists (M27b) are not ported.
"""

from __future__ import annotations

from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ptk.sim.org.seat_data import Guardrail

type AreaRule = Literal[
    "staffing",
    "intake",
    "billing",
    "pricing",
    "bd",
    "hiring",
    "development",
    "laterals",
    "offices",
    "knowledge",
    "risk",
    "pro_bono",
    "events",
]
type OwnerWho = Literal["seat", "partner"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AreaDef(_Strict):
    """One area of spec 9.4's table."""

    label: str = Field(min_length=1)
    rule: AreaRule
    who: OwnerWho = "seat"  # seat: the seat's holder; partner: any partner (pro bono)
    seat: str | None = None  # seats.yaml key whose holder owns the area
    seat_rule: bool = False  # the area runs the seat's PT-M8 authority rule (TST 40.12)
    available: bool = True  # False: the area exists but its system is a later milestone's
    unavailable_reason: str = ""
    energy: int = Field(ge=0)  # workload a month (TST 40.3)
    weights: dict[str, float] = Field(default_factory=dict)  # s for a seatless owner
    guardrails: tuple[Guardrail, ...] = ()  # the area's own (the seat's are added)
    does: str = Field(min_length=1)  # what the owner does each month (the screen)

    @model_validator(mode="after")
    def _owner(self) -> AreaDef:
        if self.who == "seat" and self.seat is None:
            raise ValueError(f"area {self.label}: a seat-owned area names its seat")
        if self.who == "partner" and abs(sum(self.weights.values()) - 1.0) > 1e-9:
            raise ValueError(f"area {self.label}: a seatless area's weights add up to 1")
        if self.seat_rule and self.seat is None:
            raise ValueError(f"area {self.label}: a seat rule needs a seat")
        return self

    def guardrail(self, key: str) -> Guardrail | None:
        return next((g for g in self.guardrails if g.key == key), None)


class AutoQuality(_Strict):
    base: float
    per_score: float
    min: float = Field(ge=0, le=1)
    max: float = Field(ge=0, le=1)


class AutomationBalance(_Strict):
    change_energy: int = Field(ge=0)  # the MP's energy to give or take back an area
    owner_energy: int = Field(ge=1)
    action_energy: int = Field(ge=0)
    overload_per_energy: float = Field(ge=0)
    overload_floor: float = Field(ge=0, le=1)
    quality: AutoQuality
    mistake_noise: float = Field(ge=0, le=1)
    default_limit_bp: int = Field(ge=0)
    min_limit_cents: int = Field(ge=0)
    limit_round_cents: int = Field(ge=1)
    monthly_limit_mult: int = Field(ge=1)
    commitment_months: int = Field(ge=1)
    proposal_months: int = Field(ge=1)
    repropose_months: int = Field(ge=0)
    keep_decision_turns: int = Field(ge=1)
    near_limit_bp: int = Field(ge=0, le=10_000)
    take_back_morale: float = Field(ge=0)
    take_back_months: int = Field(ge=0)
    high_ego: float
    proposal_month: int = Field(ge=1, le=12)  # the development area's admissions proposals
    pro_bono_month: int = Field(ge=1, le=12)  # the pro bono area reviews the policy
    areas: dict[str, AreaDef]

    @model_validator(mode="after")
    def _all_rules(self) -> AutomationBalance:
        rules = [a.rule for a in self.areas.values()]
        if sorted(rules) != sorted(set(rules)) or set(rules) != set(AREA_RULES):
            raise ValueError("automation.areas: every rule exactly once")
        return self


AREA_RULES: Final[tuple[str, ...]] = (
    "staffing",
    "intake",
    "billing",
    "pricing",
    "bd",
    "hiring",
    "development",
    "laterals",
    "offices",
    "knowledge",
    "risk",
    "pro_bono",
    "events",
)

# Spec 9.4's one-offs and the action kinds that carry them. A one-off is always a proposal,
# whatever its size, whoever owns the area, on Holiday or not (TST 40.2). `None`: the system
# that would carry it is a later milestone's (offices PT-M11, mergers PT-M13,
# funding PT-M12, ABS PT-M18); nothing in the game can take it yet.
SPEC_ONE_OFFS: Final[dict[str, tuple[str, ...] | None]] = {
    "partnership admissions": ("propose_partner",),
    "de-equitisations": ("deequitise",),
    "guarantees": ("lateral_offer", "counter"),  # with a guarantee
    "mergers and combinations": ("approach_rival",),
    "opening or closing an office": None,
    "a capital call": ("capital_call",),
    "changes to the partnership agreement": ("propose_terms", "exco_term"),
    "any AI platform above the limit": (
        "invest_in_era",
    ),  # PT-M14: an era's first investment buys its platform
    "any lease above the limit": None,  # leases are the COO's PT-M8 pitches, the player's
    "a salary-scale change above the market": ("set_pay_policy",),  # mode lead
    "litigation funding agreements": None,
    "settling a malpractice claim above the deductible": ("respond_claim",),  # PT-M15
    "taking on a matter adverse to a key client with a waiver": ("seek_waiver",),  # key client
    "ABS formation": None,
}
# Action kinds that are one-offs whatever their terms.
ONE_OFF_KINDS: Final = frozenset(
    {
        "deequitise",
        "capital_call",
        "propose_terms",
        "exco_term",
        "approach_rival",
        "counter_approach",
        "appoint_seat",  # appointing or removing a seat holder (TST 40.2)
        "set_authority",
    }
)
# Partnership actions only the managing partner may take: an owner carries them out in the
# MP's name, and the MP's energy is left as it was (TST 40.13's founder actions).
MP_ACTIONS: Final = frozenset(
    {
        "lateral_search",
        "diligence",
        "lateral_offer",
        "comp_round",
        "set_sponsor",
        "introduce",
        "propose_partner",
        "repay_revolver",
        "set_pay_policy",
    }
)
