"""Frozen models for seats, authority, pitches and seat decisions (PT-M8; spec 9.1-9.3).

Ported from backend/tst/sim/org/models.py @ 121d318a (Tech Startup Tycoon), the seat,
authority, decision and pitch records; changed: a seat has a slot (0 for a single seat, a
practice group's unit id, or the executive committee's member slot 1..9); a practice group
leader's holder is not stored here but is PT-M2's unit leader (`OrgUnit.leader_id`), so the
two never disagree; pitches carry Partner Track's kinds and integer cases; the firm's
executive committee mode (spec 9.2) is a firm record. Everything is one `LeadershipState` on
the game state, so the seats' tables are their own (lane B beside PT-M7b and PT-M17).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ptk.sim.org.seat_data import PitchKind

type PitchStatus = Literal["pending", "approved", "declined", "lapsed", "failed"]
type PitchOutcome = Literal["hit", "miss"]
EXCO = "executive_committee"
PGL = "practice_group_leader"
MP = "managing_partner"


@dataclass(frozen=True, slots=True)
class SeatHolder:
    firm_id: int
    seat: str  # seats.yaml key
    slot: int  # 0: the seat; 1..9: an executive committee member's slot
    person_id: int
    appointed_turn: int


@dataclass(frozen=True, slots=True)
class SeatAuthority:
    """The player's grant (TST 24.1): whether the holder acts, and the guardrails set."""

    firm_id: int
    seat: str
    slot: int  # 0, or a practice group's unit id
    enabled: bool
    guardrails: tuple[tuple[str, int], ...] = ()  # (key, value), by key; missing = default

    def value(self, key: str, default: int) -> int:
        return next((v for k, v in self.guardrails if k == key), default)


@dataclass(frozen=True, slots=True)
class SeatDecision:
    """One thing a holder did under authority (TST 24.2), with whether it was a mistake.
    The mistake flag is engine-only: the API shows what was done, never the flag."""

    turn: int
    firm_id: int
    seat: str
    slot: int
    person_id: int
    action: str  # the action kind taken
    text: str
    mistake: bool = False


@dataclass(frozen=True, slots=True)
class Pitch:
    """A big move a holder proposes (TST 27.1). Cases are integers in the kind's unit
    (cents, people or bp: `pitches.case_unit`), from displayed knowledge only."""

    id: int
    firm_id: int
    seat: str
    slot: int
    person_id: int
    kind: PitchKind
    title: str
    why: str
    made_turn: int
    cost_cents: int
    low: int
    central: int
    high: int
    params: tuple[tuple[str, int], ...] = ()  # (key, value), by key: what approval does
    status: PitchStatus = "pending"
    resolved_turn: int | None = None
    baseline: int = 0  # what follow-through measures from (the kind's unit)
    outcome: PitchOutcome | None = None
    outcome_turn: int | None = None
    measured: int | None = None

    def param(self, key: str, default: int = 0) -> int:
        return next((v for k, v in self.params if k == key), default)


@dataclass(frozen=True, slots=True)
class FirmLeadership:
    """A firm's executive committee mode (spec 9.2): `exco_elected` None = the default
    (appointed below seats.exco.appointed_below_lawyers, elected from there); a proposed
    term waits for the December vote."""

    firm_id: int
    exco_elected: bool | None = None
    exco_proposed: bool | None = None
    last_meeting_turn: int | None = None


@dataclass(frozen=True, slots=True)
class LeadershipState:
    holders: tuple[SeatHolder, ...] = ()  # sorted by (firm_id, seat, slot)
    authorities: tuple[SeatAuthority, ...] = ()  # sorted by (firm_id, seat, slot)
    decisions: tuple[SeatDecision, ...] = ()  # in the order taken; the last months' only
    pitches: tuple[Pitch, ...] = ()  # sorted by id
    firms: tuple[FirmLeadership, ...] = ()  # sorted by firm id
    next_pitch_id: int = 1

    def holder(self, firm_id: int, seat: str, slot: int = 0) -> SeatHolder | None:
        for h in self.holders:
            if h.firm_id == firm_id and h.seat == seat and h.slot == slot:
                return h
        return None

    def authority(self, firm_id: int, seat: str, slot: int = 0) -> SeatAuthority | None:
        for a in self.authorities:
            if a.firm_id == firm_id and a.seat == seat and a.slot == slot:
                return a
        return None

    def firm(self, firm_id: int) -> FirmLeadership:
        return next((f for f in self.firms if f.firm_id == firm_id), FirmLeadership(firm_id))

    def pitch(self, pitch_id: int) -> Pitch | None:
        return next((p for p in self.pitches if p.id == pitch_id), None)

    def seats_of(self, person_id: int) -> tuple[SeatHolder, ...]:
        return tuple(h for h in self.holders if h.person_id == person_id)


EMPTY_LEADERSHIP = LeadershipState()
