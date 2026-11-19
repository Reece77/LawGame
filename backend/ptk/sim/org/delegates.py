"""Delegated hiring in phase 2 (TST formulas.md 13.10, ADR-0015).

Ported from backend/tst/sim/org/delegates.py @ 02fba2aa (Tech Startup Tycoon); changed:
hiring is reached only through PT-M1b's delegate hook (`ptk.sim.interfaces`), so every step
is a hook request applied as the delegate; the delegate's own energy is the hook's, given
each month here (`org.delegates.energy_per_month`) and spent by the hook's costs; a plan's
hires are placed in its unit from the hook's accepted offers; campus plans hire a practice
group's first-year class (the hook only lets campus offers through in the offer month);
scouting is per search; TST's executives-with-authority reuse is not ported.

For each active plan in id order, its delegate opens a search if the plan is short and none
is open for the role, interviews the best candidates the firm does not know well, scouts
with leftover energy, and makes offers. Choosing is deterministic and reads only what the
firm can see (revealed ranges, ADR-0007); randomness happens only inside the hook's
requests, from stream `delegate` keyed (person_id, n), where n counts that delegate's
accepted requests this turn. Replay recomputes these actions from the plans in state.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, field, replace
from fractions import Fraction

import numpy as np

from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import SimError
from ptk.sim.interfaces import (
    CandidateView,
    CloseSearchRequest,
    DelegateHiringHook,
    HiringChannel,
    HiringRequest,
    InterviewRequest,
    OfferRequest,
    OpenSearchRequest,
    ScoutRequest,
)
from ptk.sim.ledger import AccountCode, LedgerEntry, apply_entries
from ptk.sim.log import LogItem
from ptk.sim.money import BP_DENOMINATOR, Cents
from ptk.sim.org.actions import pause_unqualified_plans, place, with_plan
from ptk.sim.org.models import POTENTIAL_LEVELS, HiringPlan, PlanActivity, PlanFocus
from ptk.sim.people.models import PA_KEY
from ptk.sim.people.reveal import revealed_range
from ptk.sim.rng import RngFactory
from ptk.sim.scale import PRIMARY_WEIGHT, SECONDARY_WEIGHT
from ptk.sim.state import GameState

ANY_CHANNEL: HiringChannel = "job_post"  # a plan on channel "any" searches with a job post


@dataclass(frozen=True, slots=True)
class DelegateAction:
    """One request a delegate's hook accepted, in the order taken (ADR-0015 section 5)."""

    firm_id: int
    actor_id: int
    plan_id: int
    request: HiringRequest

    def payload(self) -> dict[str, object]:
        """The decision_log payload: the request's fields and its type."""
        return {
            "actor_id": self.actor_id,
            "firm_id": self.firm_id,
            "plan_id": self.plan_id,
            "request": type(self.request).__name__,
            **{f"request_{k}": v for k, v in asdict(self.request).items()},
        }


# --- Ranking from what the firm can see ---------------------------------------------------------


def known_score(state: GameState, firm_id: int, person_id: int, data: GameData) -> float:
    """The firm's displayed range midpoints of the role's skills, primary x 3 (13.10)."""
    reveal = state.reveal(firm_id, person_id)
    if reveal is None:
        return 0.0
    person = state.person(person_id)
    role = data.role(person.role)

    def mid(skill: str) -> float:
        lo, hi = revealed_range(person, reveal, skill)
        return (lo + hi) / 2

    return PRIMARY_WEIGHT * sum(mid(s) for s in role.primary) + SECONDARY_WEIGHT * sum(
        mid(s) for s in role.secondary
    )


def known_potential(state: GameState, firm_id: int, person_id: int) -> float:
    """Midpoint of the firm's displayed potential range (13.10 focus potential)."""
    reveal = state.reveal(firm_id, person_id)
    if reveal is None:
        return 0.0
    lo, hi = revealed_range(state.person(person_id), reveal, PA_KEY)
    return (lo + hi) / 2


def ranked(
    state: GameState,
    firm_id: int,
    pool: tuple[CandidateView, ...],
    data: GameData,
    focus: PlanFocus = "current",
) -> list[CandidateView]:
    """Candidates best first (13.10 step 2). Focus current: by the known role-skill score,
    ties by id. Focus potential: juniors only, by the known potential midpoint, ties by the
    role-skill score, then id."""
    if focus == "potential":
        juniors = [c for c in pool if c.level in POTENTIAL_LEVELS]
        return sorted(
            juniors,
            key=lambda c: (
                -known_potential(state, firm_id, c.candidate_id),
                -known_score(state, firm_id, c.candidate_id, data),
                c.candidate_id,
            ),
        )
    return sorted(
        pool, key=lambda c: (-known_score(state, firm_id, c.candidate_id, data), c.candidate_id)
    )


def plan_offer_salary(ask_cents: Cents, ratio_bp: int) -> Cents:
    """The ask x the plan's ratio, rounded half to even to whole cents."""
    return round(Fraction(ask_cents * ratio_bp, BP_DENOMINATOR))


def delegate_draws(rng: RngFactory, turn: int, actor: int, n: int) -> np.random.Generator:
    """Stream `delegate` keyed (person_id, n): the one call site (ADR-0013, ADR-0015)."""
    return rng.stream(turn, "delegate", actor, n)


# --- The run ---------------------------------------------------------------------------------


@dataclass(slots=True)
class _Run:
    """Accumulates one phase 2: the state, running balances, and everything to report."""

    state: GameState
    balances: dict[tuple[int, AccountCode], Cents]
    rng: RngFactory
    balance: Balance
    data: GameData
    hook: DelegateHiringHook
    entries: list[LedgerEntry] = field(default_factory=list)
    logs: list[LogItem] = field(default_factory=list)
    taken: list[DelegateAction] = field(default_factory=list)
    counts: dict[int, int] = field(default_factory=dict)  # accepted requests per delegate

    def energy(self, person_id: int) -> int:
        return self.hook.energy_left(self.state, person_id) or 0

    def cost(self, request: HiringRequest) -> int:
        return self.hook.energy_cost(request, self.balance)

    def attempt(self, plan: HiringPlan, request: HiringRequest) -> bool:
        """Apply the request as the plan's delegate; a refused one changes nothing."""
        actor, turn = plan.owner_id, self.state.turn
        n = self.counts.get(actor, 0)

        def draws() -> np.random.Generator:
            return delegate_draws(self.rng, turn, actor, n)

        try:
            out = self.hook.apply(
                self.state,
                request,
                actor_id=actor,
                draws=draws,
                balance=self.balance,
                data=self.data,
                balances=self.balances,
            )
        except SimError:
            return False
        self.state = out.state
        self.balances = apply_entries(self.balances, out.entries)
        self.entries += out.entries
        self.logs += out.log
        self.taken.append(DelegateAction(plan.firm_id, actor, plan.id, request))
        self.counts[actor] = n + 1
        return True


def _pending(run: _Run, plan: HiringPlan) -> int:
    pool = run.hook.candidates(run.state, plan.firm_id, plan.role)
    return sum(1 for c in pool if c.pending_offer_id is not None and c.plan_id == plan.id)


def still_needed(run: _Run, plan: HiringPlan) -> int:
    current = run.state.org.plan(plan.id) or plan
    return current.target - current.hired - _pending(run, current)


def _role_pool(run: _Run, plan: HiringPlan) -> tuple[CandidateView, ...]:
    pool = run.hook.candidates(run.state, plan.firm_id, plan.role)
    if plan.campus:
        return tuple(c for c in pool if c.channel == "campus")
    return tuple(c for c in pool if plan.level is None or c.level == plan.level)


def _work_plan(run: _Run, plan: HiringPlan) -> PlanActivity:
    """Steps 1-5 of TST formulas.md 13.10 for one plan."""
    firm, owner, role = plan.firm_id, plan.owner_id, plan.role
    activity = PlanActivity(turn=run.state.turn)
    reserve = run.balance.org.delegates.reserve

    # 1. Short, and nothing open for the role: open a search.
    channel: HiringChannel = ANY_CHANNEL if plan.channel == "any" else plan.channel
    searching = any(
        s.role == role and (s.channel == "campus") == plan.campus
        for s in run.hook.searches(run.state, firm)
    )
    if still_needed(run, plan) > 0 and not searching:
        opening = OpenSearchRequest(role=role, channel=channel, level=plan.level, plan_id=plan.id)
        if run.energy(owner) >= run.cost(opening) and run.attempt(plan, opening):
            activity = replace(activity, searches=activity.searches + 1)

    # 2-3. Interview the best uninterviewed candidates while more than the reserve remains.
    for cand in ranked(run.state, firm, _role_pool(run, plan), run.data, plan.focus):
        if cand.interviewed:
            continue
        request = InterviewRequest(cand.candidate_id)
        if run.energy(owner) - run.cost(request) <= reserve:
            break
        if run.attempt(plan, request):
            activity = replace(activity, interviews=activity.interviews + 1)

    # 4. Scout each of the role's searches once with the energy left.
    pool_ids = {c.search_id for c in _role_pool(run, plan)}
    for open_search in run.hook.searches(run.state, firm):
        if open_search.search_id not in pool_ids:
            continue
        scout = ScoutRequest(open_search.search_id)
        if run.energy(owner) < max(reserve, run.cost(scout)):
            break
        scouted = sum(1 for c in _role_pool(run, plan) if c.search_id == open_search.search_id)
        if run.attempt(plan, scout):
            activity = replace(activity, scouted=activity.scouted + scouted)

    # 5. Offer to the best interviewed candidates without a pending offer, as many as needed.
    needed = still_needed(run, plan)
    for cand in ranked(run.state, firm, _role_pool(run, plan), run.data, plan.focus):
        if needed <= 0:
            break
        if not cand.interviewed or cand.pending_offer_id is not None or not cand.offer_allowed:
            continue
        offer = OfferRequest(
            candidate_id=cand.candidate_id,
            salary_cents=plan_offer_salary(cand.ask_cents, plan.ratio_bp),
            plan_id=plan.id,
            unit_id=plan.unit_id,
        )
        if run.energy(owner) >= run.cost(offer) and run.attempt(plan, offer):
            needed -= 1
            activity = replace(activity, offers=activity.offers + 1)
    return activity


def _plural(word: str, count: int) -> str:
    return word if count == 1 else f"{word}s"


def activity_text(activity: PlanActivity, role_label: str, focus: PlanFocus = "current") -> str:
    """'interviewed 4 corporate and M&A lawyers and made 2 offers', plus ', favouring
    potential' for a potential plan (13.10)."""
    parts = []
    if activity.searches:
        parts.append("opened a new search")
    if activity.interviews:
        parts.append(
            f"interviewed {activity.interviews} {_plural(role_label, activity.interviews)}"
        )
    if activity.scouted:
        parts.append(f"scouted {activity.scouted} {_plural('candidate', activity.scouted)}")
    if activity.offers:
        parts.append(f"made {activity.offers} {_plural('offer', activity.offers)}")
    text = parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]
    return f"{text}, favouring potential" if focus == "potential" else text


def _record_hires(run: _Run) -> None:
    """Offers accepted in phase 1 of this turn: count plan hires, place hires in units."""
    for firm in run.state.firms:
        for hire in run.hook.hires(run.state, firm.id, run.state.turn):
            plan = run.state.org.plan(hire.plan_id) if hire.plan_id is not None else None
            unit = hire.unit_id if hire.unit_id is not None else (plan.unit_id if plan else None)
            live = run.state.org.unit(unit) if unit is not None else None
            if live is not None and live.status == "active" and live.firm_id == firm.id:
                run.state = place(run.state, hire.person_id, unit)
            if plan is None or hire.person_id in plan.hires:
                continue
            hired = plan.hired + 1
            status = "filled" if hired >= plan.target and plan.status == "active" else plan.status
            run.state = with_plan(
                run.state,
                replace(
                    plan,
                    hired=hired,
                    hires=tuple(sorted((*plan.hires, hire.person_id))),
                    status=status,
                ),
            )


def _release_searches(run: _Run) -> None:
    """A filled or closed plan's delegate closes the searches it opened, unless another
    active plan for the same role still uses one (13.10)."""
    for plan in run.state.org.plans:
        if plan.status not in ("filled", "closed"):
            continue
        if run.state.employer_of(plan.owner_id) != plan.firm_id:
            continue
        others = any(
            p.status == "active" and p.role == plan.role and p.id != plan.id
            for p in run.state.org.firm_plans(plan.firm_id)
        )
        if others:
            continue
        for search in run.hook.searches(run.state, plan.firm_id):
            if search.plan_id == plan.id:
                run.attempt(plan, CloseSearchRequest(search.search_id))


def run_delegates(
    state: GameState,
    rng: RngFactory,
    balance: Balance,
    data: GameData,
    balances: Mapping[tuple[int, AccountCode], Cents],
    hook: DelegateHiringHook | None,
) -> tuple[GameState, tuple[LedgerEntry, ...], tuple[LogItem, ...], tuple[DelegateAction, ...]]:
    """Phase 2 for every firm's delegates (ADR-0015). Plans act in id order. Without a
    hiring system (`hook` None) plans only pause when their owners leave."""
    state = pause_unqualified_plans(state, balance)
    if hook is None or not state.org.plans:
        return state, (), (), ()
    run = _Run(state=state, balances=dict(balances), rng=rng, balance=balance, data=data, hook=hook)
    _record_hires(run)
    _release_searches(run)
    energised: set[int] = set()
    for plan_id in sorted(p.id for p in run.state.org.plans):
        plan = run.state.org.plan(plan_id)
        if plan is None or plan.status != "active":
            continue
        if plan.owner_id not in energised:  # the month's own budget, never the founder's
            run.state = hook.set_energy(
                run.state, plan.owner_id, balance.org.delegates.energy_per_month
            )
            energised.add(plan.owner_id)
        activity = _work_plan(run, plan)
        if not activity.acted:
            continue
        current = run.state.org.plan(plan_id)
        assert current is not None
        run.state = with_plan(run.state, replace(current, last_activity=activity))
        owner = run.state.person(plan.owner_id)
        role_label = data.role(plan.role).label.lower()
        run.logs.append(
            LogItem(
                turn=run.state.turn,
                firm_id=plan.firm_id,
                kind="plan_activity",
                message=(
                    f"{owner.first_name} {owner.last_name} "
                    f"{activity_text(activity, role_label, plan.focus)}"
                ),
                link_kind="person",
                link_id=owner.id,
            )
        )
    return run.state, tuple(run.entries), tuple(run.logs), tuple(run.taken)


def available_hook(load: Callable[[], DelegateHiringHook]) -> DelegateHiringHook | None:
    """PT-M1b's hook, or None until its hiring is built (the placeholder raises)."""
    try:
        hook = load()
        hook.energy_left  # noqa: B018 - the placeholder raises on any attribute
    except (ImportError, NotImplementedError):
        return None
    return hook
