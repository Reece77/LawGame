"""PT-M16 press state (spec 12.2; TST formulas.md 29): press moments, public claims,
credibility, rival managing partners' statements and feuds. Everything here is public (TST
29.6) except where marked.

Ported from backend/tst/sim/press/models.py @ 80a3807 (Tech Startup Tycoon); changed: a moment
names a practice, a rival firm and a person (its subject) instead of a product; claims are
Partner Track's kinds (headcount, no layoffs, matching the scale, a directory band) and judged
on public values; no departures (TST 29.5's recruitment fixes stay in TST); a statement may come
from the firm (person None) when its managing partner is a real person and the statement's kind
is restricted (ADR PT-0013).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

type MomentStatus = Literal["pending", "open", "skipped", "answered"]
type ClaimStatus = Literal["open", "kept", "broken"]
type StatementKind = Literal["statement", "jab", "answer"]
type Fact = tuple[str, int | str]
type Cause = tuple[int, float, str]  # (turn, change, cause in words)


@dataclass(frozen=True, slots=True)
class PressMoment:
    """One press moment (TST 29.1). Raised by the engine as "pending"; phase 12 keeps at most
    press.max_per_quarter a quarter and one a month, highest stakes first, and opens it for the
    player to answer next month (`due_turn`); an unanswered moment gets the press office's
    measured answer at the end of its due month."""

    id: int
    trigger: str  # press.config.MOMENT_TRIGGERS or REMINDER
    turn: int  # the month it was raised
    status: MomentStatus = "pending"
    due_turn: int | None = None  # the month it is open to answer
    practice: str | None = None
    rival_id: int | None = None  # the rival firm it names, if any
    person_id: int | None = None  # the person it is about, if any (never real if restricted)
    facts: tuple[Fact, ...] = ()  # displayed words only, for the inbox and the screen
    tone: str | None = None
    answered_turn: int | None = None
    by_office: bool = False  # answered by the press office (not answered in time)
    # A bold answer (TST 29.1): the reputation it was given at, and whether it has backfired.
    # Hidden only in that the API never shows a backfire before it happens.
    baseline: float | None = None
    backfired: bool = False


@dataclass(frozen=True, slots=True)
class Claim:
    """A public claim (spec 12.2; TST 29.2's promises), judged on public values only."""

    id: int
    kind: str  # press.config.CLAIM_KINDS
    made_turn: int
    deadline_turn: int
    moment_id: int | None = None
    practice: str | None = None  # band: the practice
    target: int = 0  # headcount: lawyers; band: the band to reach (1 best)
    baseline: int = 0  # the public value when made (lawyers, or the practice's band, 7 none)
    ambition: float = 0.0
    audience: float = 1.0  # a when made
    status: ClaimStatus = "open"
    resolved_turn: int | None = None
    reminder_turn: int | None = None  # a broken claim's "you said ..." month

    @property
    def open(self) -> bool:
        return self.status == "open"


@dataclass(frozen=True, slots=True)
class Feud:
    """The player's managing partner against one rival's, 0-100 (TST 29.4)."""

    rival_id: int
    score: float = 0.0
    causes: tuple[Cause, ...] = ()
    rivalry_turn: int | None = None  # when it last reached rivalry
    lost_seen: int = 0  # the rival's key partners lost to the player, as last counted


@dataclass(frozen=True, slots=True)
class Statement:
    """A rival managing partner's public statement (TST 29.4): at their firm's own moves, or
    in answer to a bold claim that named them. A jab is aimed at the player and opens a
    moment. `person_id` None: the firm's spokesperson."""

    id: int
    rival_id: int
    person_id: int | None
    turn: int
    kind: StatementKind
    text: str


@dataclass(frozen=True, slots=True)
class PressState:
    moments: tuple[PressMoment, ...] = ()  # pending, open and the last 24 months', by id
    claims: tuple[Claim, ...] = ()  # by id
    credibility: float | None = None  # the player's, 0-100; None: press.cred_start
    cred_history: tuple[Cause, ...] = ()  # its last press.cred_history changes
    feuds: tuple[Feud, ...] = ()  # by rival id
    statements: tuple[Statement, ...] = ()  # the last 24 months', by id
    next_id: int = 1  # moments, claims and statements share one counter
    scale_seen: int = 0  # the market's first-year salary last month (a salary-scale moment)

    def moment(self, moment_id: int) -> PressMoment | None:
        return next((m for m in self.moments if m.id == moment_id), None)

    def feud(self, rival_id: int) -> Feud | None:
        return next((f for f in self.feuds if f.rival_id == rival_id), None)

    @property
    def open_claims(self) -> tuple[Claim, ...]:
        return tuple(c for c in self.claims if c.open)


EMPTY_PRESS = PressState()
