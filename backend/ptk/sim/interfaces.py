"""Seams between lanes that are built at the same time (PT-M1b hiring and pay, PT-M2 org).

PT-M2 (org) defined this module because PT-M1b had not published one when delegated hiring
was built (the PT-M2 brief, sub-task 4). Each protocol is what the org needs from hiring or
pay; each has a default that does nothing, so the game runs before the other lane lands.
PT-M1b wires its implementations by replacing `PAY` and `DELEGATE_HIRING` below (one line
each) and calls `ptk.sim.org.morale.org_morale_inputs` from its morale step.

Contracts:

- **Pay** (`PayAccess`): an employee's salary, read and set. A raise (TST 13.8) sets the
  new salary through it; the new salary applies from the next payroll.
- **Delegated hiring** (`DelegateHiring`, TST 13.10, ADR-0015): the hiring actions a
  delegate takes. Org chooses (deterministically, from displayed ranges); hiring applies.
  Every step takes `draws`, a factory for the delegate's own generator (stream `delegate`,
  key `(person_id, n)`); a step that needs randomness calls it once, others never. A step
  that the rules refuse raises a `SimError` and changes nothing. Energy is the delegate's
  own and is spent by the org (balance `org.delegates`), never the founder's.
- **Hires join the plan's unit**: hiring reports who was hired under a plan through
  `DelegateHiring.hires`; the org places them in the plan's unit in phase 2.
- **Morale** (PT-M1b): `org_morale_inputs(state, balance)` gives each employee's supervisor
  term W_mgr (TST 13.4) and this turn's one-off changes (13.7, 13.8) to apply in phase 8;
  the org clears the one-off changes at the end of phase 8.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

import numpy as np

from ptk.sim.errors import DelegateRefusedError
from ptk.sim.ledger import LedgerEntry
from ptk.sim.log import LogItem
from ptk.sim.state import GameState

type Draws = Callable[[], np.random.Generator]


# --- Pay -----------------------------------------------------------------------------------------


class PayAccess(Protocol):
    def salary_cents(self, state: GameState, person_id: int) -> int | None:
        """The employee's annual salary, or None while the firm pays nobody (no payroll)."""
        ...

    def set_salary(self, state: GameState, person_id: int, salary_cents: int) -> GameState:
        """The state with the employee's annual salary changed (from the next payroll)."""
        ...


class NoPay:
    """Before PT-M1b: nobody has a salary, so raises are refused."""

    def salary_cents(self, state: GameState, person_id: int) -> int | None:
        return None

    def set_salary(self, state: GameState, person_id: int, salary_cents: int) -> GameState:
        raise DelegateRefusedError("salaries arrive with payroll (PT-M1b)")


# --- Delegated hiring ----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CandidateView:
    """An open candidate of the firm's searches, as a delegate may see it (no true values)."""

    person_id: int
    role: str
    level: str
    channel: str
    interviewed: bool  # the firm has interviewed them (TST ADR-0016: needed for an offer)
    offer_pending: bool
    ask_cents: int  # their salary expectation


@dataclass(frozen=True, slots=True)
class HiringStep:
    """What one hiring action did."""

    state: GameState
    ledger_entries: tuple[LedgerEntry, ...] = ()
    log_items: tuple[LogItem, ...] = ()


class DelegateHiring(Protocol):
    def candidates(self, state: GameState, firm_id: int, role: str) -> tuple[CandidateView, ...]:
        """The firm's open candidates for a role, by person id."""
        ...

    def has_open_search(self, state: GameState, firm_id: int, role: str) -> bool: ...

    def pending_offers(self, state: GameState, plan_id: int) -> int:
        """Offers made under the plan that are not yet answered."""
        ...

    def hires(self, state: GameState, plan_id: int) -> tuple[int, ...]:
        """Person ids who accepted an offer made under the plan, ascending."""
        ...

    def open_search(
        self,
        state: GameState,
        actor_id: int,
        role: str,
        channel: str,
        plan_id: int,
        level: str | None,
        draws: Draws,
    ) -> HiringStep: ...

    def interview(
        self, state: GameState, actor_id: int, person_id: int, draws: Draws
    ) -> HiringStep: ...

    def make_offer(
        self,
        state: GameState,
        actor_id: int,
        person_id: int,
        salary_cents: int,
        plan_id: int,
        draws: Draws,
    ) -> HiringStep: ...

    def close_plan_searches(
        self, state: GameState, actor_id: int, plan_id: int, draws: Draws
    ) -> HiringStep:
        """Close the searches the plan opened that no other open plan for its role uses."""
        ...


class NoDelegateHiring:
    """Before PT-M1b: no searches and no candidates, so delegates find nothing to do."""

    def candidates(self, state: GameState, firm_id: int, role: str) -> tuple[CandidateView, ...]:
        return ()

    def has_open_search(self, state: GameState, firm_id: int, role: str) -> bool:
        return False

    def pending_offers(self, state: GameState, plan_id: int) -> int:
        return 0

    def hires(self, state: GameState, plan_id: int) -> tuple[int, ...]:
        return ()

    def open_search(
        self,
        state: GameState,
        actor_id: int,
        role: str,
        channel: str,
        plan_id: int,
        level: str | None,
        draws: Draws,
    ) -> HiringStep:
        raise DelegateRefusedError("searches arrive with hiring (PT-M1b)")

    def interview(
        self, state: GameState, actor_id: int, person_id: int, draws: Draws
    ) -> HiringStep:
        raise DelegateRefusedError("interviews arrive with hiring (PT-M1b)")

    def make_offer(
        self,
        state: GameState,
        actor_id: int,
        person_id: int,
        salary_cents: int,
        plan_id: int,
        draws: Draws,
    ) -> HiringStep:
        raise DelegateRefusedError("offers arrive with hiring (PT-M1b)")

    def close_plan_searches(
        self, state: GameState, actor_id: int, plan_id: int, draws: Draws
    ) -> HiringStep:
        return HiringStep(state)


PAY: PayAccess = NoPay()  # PT-M1b: its payroll's implementation
DELEGATE_HIRING: DelegateHiring = NoDelegateHiring()  # PT-M1b: its hiring's implementation
