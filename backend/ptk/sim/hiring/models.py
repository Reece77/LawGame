"""Frozen hiring models: searches, candidates, offers, per-person state and pay policy.

Ported from backend/tst/sim/hiring/models.py @ 02fba2aa (Tech Startup Tycoon); changed:
firms instead of companies; Partner Track's channels (campus, recruiter, job post, referral);
a search may filter by law school tier and target a level; a candidate carries their ask
(TST kept it on the person); campus offers are signed a year ahead (`start_turn`); no
equity, no rival or exec searches, no cities; no NextIds (ids are max + 1 of each table, so
records are never dropped from the state); the firm's pay policy against the market scale.

Records whose status changes stay in the state so persistence stores the new status.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

from ptk.sim.interfaces import HiringChannel

type SearchStatus = Literal["open", "closed"]
# signed: a campus hire who accepted and starts at the offer's start_turn (spec 5.7).
type CandidateStatus = Literal["open", "signed", "hired", "declined", "expired"]
type OfferStatus = Literal["pending", "accepted", "declined", "withdrawn"]
type PolicyMode = Literal["match", "lag", "lead"]

CHANNELS: Final[tuple[HiringChannel, ...]] = ("campus", "recruiter", "job_post", "referral")
ONE_BATCH: Final = frozenset({"campus", "recruiter", "referral"})  # close after one batch


@dataclass(frozen=True, slots=True)
class Search:
    id: int
    firm_id: int
    role: str
    channel: HiringChannel
    actor_id: int  # who opened it; their judgment scouts the batch
    opened_turn: int
    status: SearchStatus = "open"
    closed_turn: int | None = None
    level: str | None = None  # a lateral search's target level; None = the channel's mix
    school_tiers: tuple[str, ...] = ()  # law school tier filter; () = any
    plan_id: int | None = None  # the PT-M2 hiring plan it serves


@dataclass(frozen=True, slots=True)
class Candidate:
    """A generated person available to one firm (the person lives in GameState.people)."""

    person_id: int
    firm_id: int
    search_id: int
    channel: HiringChannel
    ask_cents: int  # their salary expectation a year (shown exactly)
    created_turn: int  # turn whose phase 12 generated them
    expires_turn: int  # leave in phase 12 of this turn unless an offer is pending
    status: CandidateStatus = "open"
    resolved_turn: int | None = None
    interviewed_turn: int | None = None  # first interview by the firm (ADR-0016)


@dataclass(frozen=True, slots=True)
class Offer:
    id: int
    firm_id: int
    candidate_id: int  # person id
    actor_id: int
    salary_cents: int  # a year
    made_turn: int
    start_turn: int  # when the hire joins: the resolving turn, or next September (campus)
    status: OfferStatus = "pending"
    resolved_turn: int | None = None
    plan_id: int | None = None  # PT-M2 hiring plan
    unit_id: int | None = None  # PT-M2: where the hire joins; None = the firm root


@dataclass(frozen=True, slots=True)
class PersonState:
    """Per-month values for one person. None means not tracked for this person."""

    person_id: int
    energy: int | None = None  # the player's founding partner and delegates (TST 6, 13.10)
    morale: float | None = None  # everyone on the books but founding partners (TST 9)


@dataclass(frozen=True, slots=True)
class PayPolicy:
    """The firm's pay against the market scale (spec 5.4): match, lag or lead by `pct_bp`
    of the market (match = 10000). It sets associates' scale salaries and their bonuses."""

    mode: PolicyMode = "match"
    pct_bp: int = 10_000  # tunable-exempt: 100% of the market

    @staticmethod
    def of(mode: PolicyMode, pct_bp: int) -> PayPolicy:
        return PayPolicy(mode, 10_000 if mode == "match" else pct_bp)  # tunable-exempt: 100%
