"""Automation records (PT-M9; spec 9.4; TST formulas.md 40).

Ported from backend/tst/sim/automation/models.py @ 80a38079 (Tech Startup Tycoon); changed: an
owner row has a slot (a practice group's unit id for the staffing area, else 0) and a monthly
limit of its own beside the per-decision limit (the brief's "per-area monthly and per-decision
limits"); the owner's guardrails are integers as PT-M8's; proposals are automation's own
records (`AutoProposal`) holding the action as JSON; everything is one `AutomationState` on
the game state. TST's headcount targets (M27b) are not ported.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

# What one line of an owner's month was (TST 40.3, 40.4).
type DecisionKind = Literal[
    "decision",  # the right rule acted
    "mistake",  # a noisy alternative within the guardrails acted (engine-only flag)
    "proposal",  # a one-off, or at or above the limit: waiting for the player
    "over_budget",  # the month had used the area's monthly limit
    "stretched",  # the owner's areas cost more energy than they have: q falls
    "event",  # a routine event answered for the player (TST 40.5)
    "note",  # the owner's own note for the digest
]
type ProposalStatus = Literal["pending", "approved", "declined", "expired", "failed"]


@dataclass(frozen=True, slots=True)
class AreaOwner:
    """A person who runs an area of the player's firm (TST 40.1). No row: the player does."""

    firm_id: int
    area: str  # balance automation.areas key
    slot: int  # staffing: the practice group's unit id; else 0
    person_id: int
    limit_cents: int  # per decision: at or above it, a proposal (TST 40.2)
    monthly_cents: int  # per month: commitments past it wait for next month
    priority: int  # the order the owner runs its areas in, lowest first (TST 40.3)
    since_turn: int
    answer_events: bool = True  # "Let them answer routine events" (TST 40.5)
    guardrails: tuple[tuple[str, int], ...] = ()  # (key, value) by key; missing = default

    def value(self, key: str, default: int) -> int:
        return next((v for k, v in self.guardrails if k == key), default)

    @property
    def key(self) -> tuple[str, int]:
        return (self.area, self.slot)


@dataclass(frozen=True, slots=True)
class AreaDecision:
    """One logged line of an owner's month (TST 40.3's visible record, 40.4's digest). The
    `mistake` kind is shown as a decision: the API never says which was a mistake."""

    firm_id: int
    turn: int
    seq: int  # order within the month
    area: str
    slot: int
    person_id: int
    kind: DecisionKind
    action: str  # the action kind, or "" for a note
    text: str
    commitment_cents: int = 0
    link_kind: str | None = None
    link_id: int | None = None
    proposal_id: int | None = None


@dataclass(frozen=True, slots=True)
class AutoProposal:
    """A one-off, or a decision at or above its limit, waiting for the player (TST 40.2):
    the owner's recommendation, Approve or Decline. Approving runs the action as the MP."""

    id: int
    firm_id: int
    area: str
    slot: int
    person_id: int
    made_turn: int
    expires_turn: int
    action_json: str  # the action's payload (ptk.sim.actions.action_payload), sorted keys
    title: str
    why: str  # "it is a one-off", "it is at or above the limit"
    recommendation: str  # the owner's own words (from displayed facts only)
    commitment_cents: int = 0
    status: ProposalStatus = "pending"
    resolved_turn: int | None = None


@dataclass(frozen=True, slots=True)
class AutomationState:
    owners: tuple[AreaOwner, ...] = ()  # sorted by (firm_id, area index, slot)
    decisions: tuple[AreaDecision, ...] = ()  # the last keep_decision_turns months, in order
    proposals: tuple[AutoProposal, ...] = ()  # sorted by id
    next_proposal_id: int = 1

    def owner(self, firm_id: int, area: str, slot: int = 0) -> AreaOwner | None:
        for o in self.owners:
            if o.firm_id == firm_id and o.area == area and o.slot == slot:
                return o
        return None

    def proposal(self, proposal_id: int) -> AutoProposal | None:
        return next((p for p in self.proposals if p.id == proposal_id), None)

    def pending(self, firm_id: int) -> tuple[AutoProposal, ...]:
        return tuple(p for p in self.proposals if p.firm_id == firm_id and p.status == "pending")


EMPTY_AUTOMATION = AutomationState()
