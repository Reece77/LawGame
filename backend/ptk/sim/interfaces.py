"""Small interfaces between lanes (PT-M1b and PT-M2 are built side by side).

The delegate hook (TST formulas.md 13.10, ADR-0015) is how PT-M2's delegated hiring drives
PT-M1b's hiring without reaching into `ptk.sim.hiring`. A delegate (a recruiting manager or a
practice group leader) acts in phase 2 by sending the same requests the player's actions
send, as its own actor, with its own energy and its own random stream (`delegate`, keyed
`(person_id, n)`, where n counts that delegate's actions this turn). Every rule the player
meets applies to the delegate: an offer needs an interview (ADR-0016), campus offers only in
the offer month, energy is spent at once.

Usage from PT-M2 (phase 2):

    hook = delegate_hiring()
    state = hook.set_energy(state, delegate_id, balance_energy)      # the month's budget
    for cand in hook.candidates(state, firm_id, role="corporate_ma"):
        ...rank by what the firm knows (revealed ranges) ...
    result = hook.apply(state, InterviewRequest(cand.candidate_id), actor_id=delegate_id,
                        draws=lambda: rng.stream(turn, "delegate", delegate_id, n),
                        balance=balance, data=data, balances=ctx.balances)
    ctx = ctx.post(*result.entries).log(*result.log); state = result.state

Offers carry a `plan_id` and a `unit_id`; `hook.hires(state, firm_id, turn)` lists the
offers accepted in phase 1 of `turn` with both, so PT-M2 can count plan hires and place each
hire in its unit. Nothing here exposes a hidden true value: candidate views carry only what
the firm can see (the ask is shown exactly, TST 7).

This module holds types only and imports no lane's package at import time; the hiring
implementation is loaded on first use.

PT-M2 (org) adds, at the end: the body of `manager_morale_term`, `org_morale_changes` (the
one-off morale of reorganising, raises and promotions, TST 13.7-13.8) and the pay seam a
raise uses (`salary_cents`, `set_salary`).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Protocol

if TYPE_CHECKING:
    import numpy as np

    from ptk.sim.data_models import Balance, GameData
    from ptk.sim.ledger import AccountCode, LedgerEntry
    from ptk.sim.log import LogItem
    from ptk.sim.money import Cents
    from ptk.sim.state import GameState

# Spec 5.7: campus (summer programme, offers in August, start the September after), and the
# lateral channels of TST 7 renamed: a recruiter search (20-25% fee on hire), a job post, a
# referral (TST's network search).
type HiringChannel = Literal["campus", "recruiter", "job_post", "referral"]


# --- Requests a delegate (or the player) sends ------------------------------------------------


@dataclass(frozen=True, slots=True)
class OpenSearchRequest:
    role: str  # roles.yaml key; a lawyer's role is their home practice
    channel: HiringChannel
    level: str | None = None  # lateral target level (balance people.levels); None: the mix
    school_tiers: tuple[str, ...] = ()  # law school tier filter; () = any tier
    plan_id: int | None = None  # the hiring plan the search serves (PT-M2)


@dataclass(frozen=True, slots=True)
class CloseSearchRequest:
    search_id: int


@dataclass(frozen=True, slots=True)
class InterviewRequest:
    candidate_id: int  # the candidate's person id


@dataclass(frozen=True, slots=True)
class ReferenceCheckRequest:
    candidate_id: int


@dataclass(frozen=True, slots=True)
class ScoutRequest:
    """Apply a month of scouting to every open candidate of one search (TST 11.12)."""

    search_id: int


@dataclass(frozen=True, slots=True)
class OfferRequest:
    candidate_id: int
    salary_cents: int  # annual
    plan_id: int | None = None  # the plan a delegate offers under (PT-M2)
    unit_id: int | None = None  # where the hire joins; None = the firm root (PT-M2)


type HiringRequest = (
    OpenSearchRequest
    | CloseSearchRequest
    | InterviewRequest
    | ReferenceCheckRequest
    | ScoutRequest
    | OfferRequest
)


# --- What a delegate can see ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SearchView:
    search_id: int
    firm_id: int
    role: str
    channel: HiringChannel
    opened_turn: int
    plan_id: int | None


@dataclass(frozen=True, slots=True)
class CandidateView:
    """An open candidate as the firm sees it. Rank candidates by the firm's revealed ranges
    (`ptk.sim.people.reveal.revealed_range` on `state.reveal(firm_id, candidate_id)`)."""

    candidate_id: int  # person id
    search_id: int
    role: str
    level: str
    channel: HiringChannel
    ask_cents: int  # the salary they expect (shown exactly, TST 7)
    interviewed: bool  # by anyone at the firm (ADR-0016)
    pending_offer_id: int | None
    offer_allowed: bool  # False for a campus candidate outside the offer month
    plan_id: int | None  # the plan of the search that found them


@dataclass(frozen=True, slots=True)
class HireView:
    """An offer accepted in phase 1: the person joins now, or at `start_turn` (campus)."""

    offer_id: int
    person_id: int
    firm_id: int
    plan_id: int | None
    unit_id: int | None
    accepted_turn: int
    start_turn: int


@dataclass(frozen=True, slots=True)
class HookResult:
    state: GameState
    entries: tuple[LedgerEntry, ...] = ()
    log: tuple[LogItem, ...] = ()


class DelegateHiringHook(Protocol):
    def energy_cost(self, request: HiringRequest, balance: Balance) -> int:
        """Energy the request costs its actor (balance `energy.cost`)."""
        ...

    def energy_left(self, state: GameState, person_id: int) -> int | None:
        """The person's energy this month; None if they do not track energy."""
        ...

    def set_energy(self, state: GameState, person_id: int, energy: int) -> GameState:
        """Give a delegate their month's energy (PT-M2 resets delegates in phase 2)."""
        ...

    def searches(self, state: GameState, firm_id: int) -> tuple[SearchView, ...]:
        """The firm's open searches, by id."""
        ...

    def candidates(
        self, state: GameState, firm_id: int, role: str | None = None
    ) -> tuple[CandidateView, ...]:
        """The firm's open candidates (optionally of one role), by candidate id."""
        ...

    def apply(
        self,
        state: GameState,
        request: HiringRequest,
        *,
        actor_id: int,
        draws: Callable[[], np.random.Generator],
        balance: Balance,
        data: GameData,
        balances: Mapping[tuple[int, AccountCode], Cents],
    ) -> HookResult:
        """Apply one request as `actor_id`, at once (ADR-0014). Raises a `SimError` and
        changes nothing if a rule forbids it. `draws` is called only if the request draws."""
        ...

    def hires(self, state: GameState, firm_id: int, turn: int) -> tuple[HireView, ...]:
        """Offers of the firm accepted in phase 1 of `turn`, by offer id."""
        ...


def delegate_hiring() -> DelegateHiringHook:
    """PT-M1b's implementation of the hook."""
    from ptk.sim.hiring.hook import HIRING_HOOK

    return HIRING_HOOK


def manager_morale_term(
    state: GameState, person_id: int, balance: Balance, data: GameData
) -> float:
    """TST 13.4's manager term in a person's morale target (spec 5.3). PT-M1b's morale calls
    this for every person it updates. PT-M2: W_mgr from the person's supervising partner's
    true leadership, communication and mentoring and their span (0 for the founding partner
    and anyone not on a firm's books)."""
    from ptk.sim.org.rules import supervisor_morale

    return supervisor_morale(state, person_id, balance)


# --- PT-M2 (org): one-off morale changes and pay --------------------------------------------


def org_morale_changes(state: GameState, person_id: int) -> float:
    """One-off morale points from this turn's org actions (TST 13.7 reorganising, 13.8
    raises, pay cuts and promotions), not yet applied. The org adds them to each person's
    current morale (`PersonState.morale`) at the end of phase 8, after PT-M1b's morale step,
    and then clears them, so each counts exactly once. 0 for the founding partner."""
    return sum(n.points for n in state.org.nudges if n.person_id == person_id)


def salary_cents(state: GameState, person_id: int) -> int | None:
    """An employee's annual salary (PT-M1b's `Employment.salary_cents`); None if they are
    not on a firm's books. A raise (TST 13.8) reads it."""
    for e in state.employments:
        if e.person_id == person_id and e.counts_as_staff:
            return e.salary_cents
    return None


def set_salary(state: GameState, person_id: int, salary: int) -> GameState:
    """The state with an employee's annual salary changed, from the next payroll (TST 13.8)."""
    from dataclasses import replace

    from ptk.sim.errors import OrgRuleError
    from ptk.sim.state import with_employment

    for e in state.employments:
        if e.person_id == person_id and e.counts_as_staff:
            return with_employment(state, replace(e, salary_cents=salary))
    raise OrgRuleError(f"person {person_id} is not on a firm's books")
