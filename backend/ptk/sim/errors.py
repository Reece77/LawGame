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
