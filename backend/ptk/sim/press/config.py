"""Schemas for PT-M16's press tunables (ADR-0008): `press.*` in balance.yaml. Model definitions
only (no imports from the rest of the sim), so `ptk.sim.data_models` can import them.

Ported from backend/tst/sim/press/config.py @ 80a3807 (Tech Startup Tycoon); changed: Partner
Track's triggers (spec 12.2) and claim kinds, audience by the firm's stage, effects on
reputation instead of the brand target (points), the promise and feud blocks under `press`,
and no recruitment fixes (TST 29.5 has no Partner Track counterpart in this milestone).
"""

from __future__ import annotations

from typing import Final

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Spec 12.2's moments, highest stakes first (the quarterly cap keeps the first ones).
MOMENT_TRIGGERS: Final = (
    "collapse",  # a rival firm collapses or fails nearby
    "layoffs",  # press.layoff_share or more of the firm fired in a month
    "verdict",  # a big verdict: a named case worth big_cents or more won or lost
    "merger",  # a rival merger (the player's own: v3)
    "lateral",  # a lateral splash: a star joins or leaves, or a rival's key partner joins
    "ranking_day",  # the spring tables or October's bands place the firm
    "salary_scale",  # the market's associate scale moves
    "jab",  # a rival managing partner's public jab (TST 29.4)
    "rivalry",  # a feud reaches rivalry (TST 29.4)
)
REMINDER: Final = "reminder"  # "you said ..." after a broken claim: outside the cap
# ADR PT-0013: these moments never name a real person (a real lawyer appears in the press only
# in professional matters: moves, matters, rankings). Enforced in `moments.queue_moment`.
RESTRICTED: Final = frozenset({"collapse", "layoffs", "jab", "rivalry", REMINDER})
CLAIM_KINDS: Final = ("headcount", "no_layoffs", "match_scale", "band")
TIMED: Final = ("headcount", "band")
TONES: Final = ("bold", "measured", "deflect")


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class AudienceBalance(_Frozen):
    """a by the firm's stage (spec 3): small below mid_stage, mid below large_stage, large."""

    small: float = Field(gt=0)
    mid: float = Field(gt=0)
    large: float = Field(gt=0)
    mid_stage: int = Field(ge=0)
    large_stage: int = Field(ge=0)


class ClaimBalance(_Frozen):
    max_open: int = Field(ge=1)
    months: tuple[int, int]  # a timed claim's deadline, months out
    fixed_months: int = Field(ge=1)  # no layoffs and matching the scale run this long
    kept_rep: float = Field(ge=0)  # reputation points, every practice
    kept_cred: float = Field(ge=0)
    kept_morale: float = Field(ge=0)  # no layoffs kept
    broken_rep: float = Field(ge=0)
    broken_cred: float = Field(ge=0)
    broken_morale: float = Field(ge=0)  # no layoffs broken
    broken_trust: float = Field(ge=0)  # partners' confidence in the managing partner
    headcount_span: float = Field(gt=0)  # growth (share of today's lawyers) for ambition 1
    band_span: int = Field(ge=1)  # bands of climb for ambition 1
    fixed_ambition: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def _check(self) -> ClaimBalance:
        lo, hi = self.months
        if not 1 <= lo < hi:
            raise ValueError("press.claims.months must be 1 <= lo < hi")
        return self


class FeudBalance(_Frozen):
    bold_mention: float = Field(ge=0)
    poach: float = Field(ge=0)  # a key partner hired from them
    approach: float = Field(ge=0)  # they approached one of the player's people
    decay: float = Field(ge=0)  # points a month
    rivalry: float = Field(gt=0, le=100)
    rivalry_stance: float = Field(ge=0)  # the rival's stance toward the player at rivalry
    causes_kept: int = Field(ge=1)


class PressBalance(_Frozen):
    max_per_quarter: int = Field(ge=0)
    bold_rep: float = Field(ge=0)  # reputation points (the moment's practice, or every one)
    measured_rep: float = Field(ge=0)
    deflect_cred: float = Field(le=0)
    bold_backfire: float = Field(ge=0)  # credibility lost when results contradict a bold claim
    backfire_months: int = Field(ge=1)
    backfire_drop: float = Field(ge=0)  # reputation points below the claim's that contradict it
    audience: AudienceBalance
    layoff_share: float = Field(gt=0, le=1)  # fired / staff in one month for a layoffs moment
    big_cents: int = Field(gt=0)  # a named case's expected fees for a big verdict
    cred_start: float = Field(ge=0, le=100)
    cred_drift: float = Field(ge=0)  # points a month toward cred_start
    cred_hiring: float = Field(ge=0)  # offer-score points at credibility 100
    cred_hiring_cap: float = Field(ge=0)
    cred_history: int = Field(ge=1)
    statement_chance: float = Field(ge=0, le=1)  # a rival MP speaks at their firm's own move
    jab_base: float = Field(ge=0, le=1)  # chance that statement is a jab at the player
    jab_feud: float = Field(ge=0)  # + this x feud / 100
    reminder_months: tuple[int, int]
    memory_months: int = Field(ge=1)  # answered moments and statements kept in the state
    energy_answer: int = Field(ge=0)
    claims: ClaimBalance
    feud: FeudBalance

    @model_validator(mode="after")
    def _check(self) -> PressBalance:
        lo, hi = self.reminder_months
        if not 1 <= lo <= hi:
            raise ValueError("press.reminder_months must be 1 <= lo <= hi")
        return self
