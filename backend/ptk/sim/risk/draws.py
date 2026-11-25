"""The risk system's streams (ADR PT-0012, ids 140-149): one call site each (ADR-0013)."""

from __future__ import annotations

import numpy as np

from ptk.sim.rng import RngFactory

ERROR, GRIEVANCE = 1, 2  # risk_claim purposes
OPENED, MONTH = 1, 2  # regulator purposes
AWARD = 2  # arbitration's purpose (the filing is the action's draw)


def claim_draws(
    rng: RngFactory, turn: int, purpose: int, matter_id: int, n: int = 0
) -> np.random.Generator:
    """A latent claim's making: whether it becomes one, its delay, merit, size and demand."""
    return rng.stream(turn, "risk_claim", purpose, matter_id, n)


def claim_month(rng: RngFactory, turn: int, claim_id: int) -> np.random.Generator:
    return rng.stream(turn, "risk_case", claim_id)


def discipline_rolls(rng: RngFactory, turn: int, firm_id: int) -> np.random.Generator:
    return rng.stream(turn, "discipline", firm_id)


def case_month(rng: RngFactory, turn: int, case_id: int) -> np.random.Generator:
    return rng.stream(turn, "discipline_case", case_id)


def regulator_draws(rng: RngFactory, turn: int, purpose: int, key: int) -> np.random.Generator:
    return rng.stream(turn, "regulator", purpose, key)


def trust_draws(rng: RngFactory, turn: int, firm_id: int) -> np.random.Generator:
    return rng.stream(turn, "trust", firm_id)


def audit_draws(rng: RngFactory, turn: int, bill_id: int) -> np.random.Generator:
    return rng.stream(turn, "audit", bill_id)


def arbitration_draws(rng: RngFactory, turn: int, purpose: int, key: int) -> np.random.Generator:
    return rng.stream(turn, "arbitration", purpose, key)
