"""Domain errors. Each has a stable `code` that the API returns in its error body.

Ported from tst/sim/errors.py @ 02fba2aa; changed: generic errors only (TST's domain errors
dropped); Partner Track's own errors are appended by the milestone that needs them.
"""

from __future__ import annotations

from typing import ClassVar


class SimError(Exception):
    """Base class for all domain errors."""

    code: ClassVar[str] = "sim_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class UnbalancedEntryError(SimError):
    code = "unbalanced_entry"


class UnknownStreamError(SimError):
    code = "unknown_stream"


class InvalidMoneyError(SimError):
    code = "invalid_money"


class InvalidDateError(SimError):
    code = "invalid_date"


class InvalidSeedError(SimError):
    code = "invalid_seed"


class UnknownScenarioError(SimError):
    code = "unknown_scenario"


class UnknownDifficultyError(SimError):
    code = "unknown_difficulty"


class InvalidSaveNameError(SimError):
    code = "invalid_save_name"


class SaveNotFoundError(SimError):
    code = "save_not_found"


class SaveExistsError(SimError):
    code = "save_exists"


class SaveBusyError(SimError):
    code = "save_busy"


class NotFoundError(SimError):
    code = "not_found"


class GameOverError(SimError):
    """The campaign has ended; reads still work (ADR PT-0007 section 4)."""

    code = "game_over"


class InvalidDataError(SimError):
    code = "invalid_data"


class InvalidFounderError(SimError):
    """A founding partner build breaks a rule (formulas.md 5; spec 2.1)."""

    code = "invalid_founder"


class InvalidPersonError(SimError):
    """A person was asked for with a role and level that do not fit."""

    code = "invalid_person"


class UnknownKnowledgeActionError(SimError):
    code = "unknown_knowledge_action"


# --- Hiring and actions (PT-M1b; TST's names) ---------------------------------------------


class InvalidActionError(SimError):
    """An immediate action breaks a rule (ADR-0014)."""

    code = "invalid_action"


class InsufficientEnergyError(SimError):
    code = "insufficient_energy"


class InsufficientCashError(SimError):
    code = "insufficient_cash"


class InterviewRequiredError(SimError):
    """An offer needs an interview first (ADR-0016)."""

    code = "interview_required"


class OfferExistsError(SimError):
    code = "offer_exists"


class CampusSeasonError(SimError):
    """A campus step outside its months (spec 5.7, ADR PT-0002 section 3)."""

    code = "campus_season"


class UnknownPersonError(NotFoundError):
    code = "unknown_person"


class UnknownRoleError(SimError):
    code = "unknown_role"


class UnknownSearchError(NotFoundError):
    code = "unknown_search"


class UnknownCandidateError(NotFoundError):
    code = "unknown_candidate"


class UnknownOfferError(NotFoundError):
    code = "unknown_offer"


# --- Org (PT-M2) -------------------------------------------------------------------------------


class OrgRuleError(SimError):
    """An org action would break a rule of TST formulas.md 13.1 (or 13.7-13.10)."""

    code = "org_rule"


class UnknownUnitError(NotFoundError):
    code = "unknown_unit"


class UnknownPlanError(NotFoundError):
    code = "unknown_plan"


class OrgActionError(SimError):
    """An org action's values are invalid (an unknown role, a target below one, ...)."""

    code = "invalid_org_action"


class DelegateRefusedError(SimError):
    """A delegate's hiring step was refused (no hiring system, no candidate, ...)."""

    code = "delegate_refused"


# --- Clients and matters (PT-M3a) ------------------------------------------------------------


class UnknownMatterError(NotFoundError):
    code = "unknown_matter"


class UnknownClientError(NotFoundError):
    code = "unknown_client"


class ConflictError(SimError):
    """A matter would be adverse to a current client without a waiver (ADR PT-0009 2)."""

    code = "conflict"


class StaffingError(SimError):
    """A staffing change breaks a rule (not a fee earner, not on the team, the lead...)."""

    code = "staffing"


class OverCapacityError(StaffingError):
    """An assignment would plan a person above matters.max_load x their capacity."""

    code = "over_capacity"


class MatterActionError(SimError):
    """A matter or client action is not allowed now (no offer, not conflicted, ...)."""

    code = "invalid_matter_action"


# --- Events (PT-M6) -------------------------------------------------------------------------


class UnknownEventError(NotFoundError):
    code = "unknown_event"


class EventActionError(SimError):
    """An event cannot be answered that way (already answered, no such choice)."""

    code = "invalid_event_action"


class CriticalEventOpenError(SimError):
    """Continue is refused while a critical event waits for the player (spec 15)."""

    code = "critical_event_open"

    def __init__(self, message: str, event_id: int) -> None:
        super().__init__(message)
        self.event_id = event_id


# --- PT-M3b: billing -----------------------------------------------------------------------


class UnknownBillError(NotFoundError):
    """No such bill for the acting firm."""


class BillingActionError(SimError):
    """A billing action a rule forbids (a write-down out of range, a bill not disputed)."""


# --- PT-M4: the partnership ------------------------------------------------------------------


class PartnershipError(SimError):
    """A partnership rule forbids the action (votes, comp, capital, laterals, flight)."""

    code = "partnership_rule"


class NotManagingPartnerError(PartnershipError):
    """Only the managing partner may do this (ADR PT-0007 3: a player who lost the election
    keeps their own practice and votes)."""

    code = "not_managing_partner"


class UnknownVoteError(NotFoundError):
    code = "unknown_vote"


class UnknownApproachError(NotFoundError):
    code = "unknown_approach"


# --- PT-M8: seats, authority and pitches ----------------------------------------------------


class SeatRuleError(SimError):
    """A seat rule forbids the action (stage, eligibility, one seat each, guardrails)."""

    code = "seat_rule"


class UnknownSeatError(NotFoundError):
    code = "unknown_seat"


class UnknownPitchError(NotFoundError):
    code = "unknown_pitch"


class OneOffError(SimError):
    """Spec 9.4's one-offs are always the player's proposals, never within authority."""

    code = "one_off"


# --- PT-M17: the founder's life, family and succession ---------------------------------------


class FounderLifeError(SimError):
    """A founder-life rule forbids the action (the personal book, foundation, bar politics)."""

    code = "founder_life"


class FamilyError(SimError):
    """A family rule forbids the action (education, a child joining, estate planning)."""

    code = "family"


class SuccessionError(SimError):
    """A succession rule forbids the action (who may succeed, when)."""

    code = "succession"
