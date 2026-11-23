"""Frozen reputation, press and rankings state (PT-M16; spec 12). Never mutate.

Everything here is public (spec 12.1: reputation is public, like TST's brand): reputation per
(firm, practice, region) 0-100 and its long-run mean, the player's recent changes with their
causes, the player's public outcomes (named matters only), prestige, and the press and the
rankings (their own modules). `StandingState` is the one field on the game state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from ptk.sim.press.models import EMPTY_PRESS, PressState
from ptk.sim.rankings.models import EMPTY_RANKINGS, RankingsState

REGION_NEW_YORK: Final = 0  # v1's one region (matters.market's REGION_NEW_YORK)
REGIONS: Final = ("new_york",)  # region index -> key (offices beyond New York: PT-M11)


@dataclass(frozen=True, slots=True)
class Rep:
    """A firm's reputation in one practice and region, 0-100, and the long-run mean it drifts
    toward (spec 12.1)."""

    firm_id: int
    practice: str
    region: int
    value: float
    mean: float


@dataclass(frozen=True, slots=True)
class RepCause:
    """One change to the player's reputation and its cause in words (the Practices screen)."""

    turn: int
    practice: str | None  # None: every practice (press, events)
    delta: float
    cause: str


@dataclass(frozen=True, slots=True)
class PublicOutcome:
    """A named matter of the player's that ended in public (spec 12.1): its points (signed; a
    full-size win is outcomes.won) count toward the record term for record_months."""

    turn: int
    practice: str
    matter_id: int
    outcome: str
    points: float


@dataclass(frozen=True, slots=True)
class ReputationState:
    entries: tuple[Rep, ...] = ()  # sorted by (firm_id, practice, region)
    causes: tuple[RepCause, ...] = ()  # the player's last reputation.causes_kept changes
    outcomes: tuple[PublicOutcome, ...] = ()  # the player's, the last record_months, by turn
    # the player's standard value of work by practice, the last 12 months (oldest first)
    practice_value: tuple[tuple[str, tuple[int, ...]], ...] = ()
    stars: tuple[tuple[int, str], ...] = ()  # the player's star partners last month (id, practice)
    prestige: tuple[tuple[int, float], ...] = ()  # firm id -> prestige 0-100, by id

    def of(self, firm_id: int) -> tuple[Rep, ...]:
        return tuple(e for e in self.entries if e.firm_id == firm_id)

    def prestige_of(self, firm_id: int) -> float | None:
        return next((v for f, v in self.prestige if f == firm_id), None)


EMPTY_REPUTATION = ReputationState()


@dataclass(frozen=True, slots=True)
class StandingState:
    reputation: ReputationState = EMPTY_REPUTATION
    press: PressState = EMPTY_PRESS
    rankings: RankingsState = EMPTY_RANKINGS


EMPTY_STANDING = StandingState()
