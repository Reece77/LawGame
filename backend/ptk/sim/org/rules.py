"""Reporting lines and the org terms of morale and growth (TST formulas.md 13.1-13.5).

Ported from backend/tst/sim/org/rules.py @ 02fba2aa (Tech Startup Tycoon); changed: units
come from `GameState.org` and membership from `OrgState.members` (not the employment row);
the root's leader is the firm's own founding partner; the supervising partner is TST's
manager; teammate-tag morale (13.6), work-location policy (13.9) and the view's memo cache
are not ported.

Everything here is derived from the state; nothing is stored. `org_view` resolves one firm's
reporting lines once, so a phase can look up supervisors and teammates cheaply.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass

from ptk.sim.data_models import Balance, GameData
from ptk.sim.org.formulas import (
    growth_multiplier,
    manager_morale_term,
    manager_quality,
    span_factor,
    span_limit,
)
from ptk.sim.org.models import OrgUnit
from ptk.sim.state import GameState

LEADERSHIP = "leadership"
COMMUNICATION = "communication"
MENTORING = "mentoring"
MENTOR_TAG = "mentor"


@dataclass(frozen=True, slots=True)
class OrgView:
    """One firm's reporting lines. Unit id None is the firm root."""

    firm_id: int
    founder_id: int | None
    units: Mapping[int, OrgUnit]  # active units by id
    unit_of: Mapping[int, int | None]  # staff person id -> unit id
    members: Mapping[int | None, tuple[int, ...]]  # unit id -> member ids, ascending
    manager_of: Mapping[int, int | None]  # staff person id -> supervisor id (None: founder)
    reports: Mapping[int, tuple[int, ...]]  # supervisor id -> direct report ids, ascending

    def unit_chain(self, unit_id: int | None) -> tuple[int, ...]:
        """The unit and its ancestors, innermost first (the root is not listed)."""
        chain: list[int] = []
        while unit_id is not None and unit_id in self.units and unit_id not in chain:
            chain.append(unit_id)
            unit_id = self.units[unit_id].parent_id
        return tuple(chain)

    def leader_of(self, unit_id: int | None) -> int | None:
        """The unit's leader; the root's leader is the founding partner (13.1)."""
        if unit_id is None:
            return self.founder_id
        return self.units[unit_id].leader_id


_VIEWS: dict[int, tuple[tuple[object, object, object], OrgView]] = {}
_VIEWS_KEEP = 16  # tunable-exempt: memoised firms' views (a cache, not a rule)


def org_view(state: GameState, firm_id: int) -> OrgView:
    """The firm's org view, memoised on the identity of the immutable inputs it reads (the
    employments, the org and the people: PT-M10, T12, since every person's morale reads it)."""
    inputs = (state.employments, state.org, state.people)
    hit = _VIEWS.get(firm_id)
    if hit is not None and all(a is b for a, b in zip(hit[0], inputs, strict=True)):
        return hit[1]
    view = _build_org_view(state, firm_id)
    if len(_VIEWS) >= _VIEWS_KEEP:
        _VIEWS.clear()
    _VIEWS[firm_id] = (inputs, view)
    return view


def _build_org_view(state: GameState, firm_id: int) -> OrgView:
    staff = state.staff_ids(firm_id)
    founder_id = state.founder_of(firm_id)
    units = {u.id: u for u in state.org.firm_units(firm_id)}
    placed = {m.person_id: m.unit_id for m in state.org.members}
    unit_of: dict[int, int | None] = {}
    members: dict[int | None, list[int]] = defaultdict(list)
    for pid in staff:
        unit = placed.get(pid)
        unit = unit if unit in units and pid != founder_id else None
        unit_of[pid] = unit
        members[unit].append(pid)
    on_staff = set(unit_of)
    manager_of: dict[int, int | None] = {}
    reports: dict[int, list[int]] = defaultdict(list)
    for pid in staff:
        manager = _resolve_manager(pid, unit_of, units, founder_id, on_staff)
        manager_of[pid] = manager
        if manager is not None:
            reports[manager].append(pid)
    return OrgView(
        firm_id=firm_id,
        founder_id=founder_id,
        units=units,
        unit_of=unit_of,
        members={k: tuple(v) for k, v in members.items()},
        manager_of=manager_of,
        reports={k: tuple(v) for k, v in reports.items()},
    )


def _resolve_manager(
    person_id: int,
    unit_of: Mapping[int, int | None],
    units: Mapping[int, OrgUnit],
    founder_id: int | None,
    on_staff: set[int],
) -> int | None:
    """The unit's leader; leaders and members of leaderless units look one level up (13.1)."""
    if person_id == founder_id:
        return None
    unit_id = unit_of[person_id]
    seen: set[int] = set()
    while unit_id is not None and unit_id not in seen:
        seen.add(unit_id)
        unit = units[unit_id]
        leader = unit.leader_id
        if leader is not None and leader != person_id and leader in on_staff:
            return leader
        unit_id = unit.parent_id if unit.parent_id in units else None
    return founder_id


# --- Terms for one person ---------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ManagerTerms:
    manager_id: int | None  # the supervising partner (TST's manager)
    reports: int  # the supervisor's direct reports
    span_limit: int
    span: float  # S
    quality: float  # Q
    morale: float  # W_mgr
    growth: float  # M_growth


NO_MANAGER = ManagerTerms(None, 0, 0, 1.0, 0.0, 0.0, 1.0)


def manager_terms(
    state: GameState, view: OrgView, person_id: int, balance: Balance
) -> ManagerTerms:
    """W_mgr and M_growth from the person's supervisor's true skills (13.3-13.5).

    The founding partner has no supervisor: both terms are neutral (0 and 1).
    """
    org = balance.org
    manager_id = view.manager_of.get(person_id)
    if manager_id is None:
        return NO_MANAGER
    manager = state.person(manager_id)
    n = len(view.reports.get(manager_id, ()))
    leadership = manager.skills[LEADERSHIP]
    s = span_factor(leadership, n, org)
    q = manager_quality(leadership, manager.skills[COMMUNICATION], manager.skills[MENTORING], s)
    return ManagerTerms(
        manager_id=manager_id,
        reports=n,
        span_limit=span_limit(leadership, org),
        span=s,
        quality=q,
        morale=manager_morale_term(q, org),
        growth=growth_multiplier(
            manager.skills[MENTORING], s, has_mentor_teammate(state, view, person_id), org
        ),
    )


def teammates(view: OrgView, person_id: int) -> tuple[int, ...]:
    """The other members of the person's unit."""
    unit = view.unit_of.get(person_id)
    return tuple(p for p in view.members.get(unit, ()) if p != person_id)


def has_mentor_teammate(state: GameState, view: OrgView, person_id: int) -> bool:
    """Another member of the unit truly has the `mentor` tag, noticed or not (13.5).

    PT-M14 (T12): the mentors of each unit are counted once per (immutable) view and people
    tuple, so each person's question is a lookup, not a scan of the unit; identical results."""
    unit = view.unit_of.get(person_id)
    counts = _mentors(state, view)
    n = counts.get(unit, 0)
    if n and MENTOR_TAG in state.person(person_id).tags and person_id in view.members.get(unit, ()):
        n -= 1
    return n > 0


_MENTORS: dict[int, tuple[OrgView, tuple[object, ...], dict[object, int]]] = {}


def _mentors(state: GameState, view: OrgView) -> dict[object, int]:
    """Members with the mentor tag, by unit (memoised on the view's and people's identity)."""
    hit = _MENTORS.get(id(view))
    if hit is not None and hit[0] is view and hit[1] is state.people:
        return hit[2]
    tagged = {p.id for p in state.people if MENTOR_TAG in p.tags}
    counts: dict[object, int] = {}
    for unit, members in view.members.items():
        n = sum(1 for pid in members if pid in tagged)
        if n:
            counts[unit] = n
    if len(_MENTORS) >= _MENTORS_KEEP:
        _MENTORS.clear()
    _MENTORS[id(view)] = (view, state.people, counts)
    return counts


_MENTORS_KEEP = 64  # tunable-exempt: memoised views (a cache, not a rule)


def growth_multipliers(state: GameState, balance: Balance) -> dict[int, float]:
    """M_growth for everyone on a firm's books, by person id (phase 8, 13.5)."""
    out: dict[int, float] = {}
    for firm in state.firms:
        view = org_view(state, firm.id)
        for pid in view.unit_of:
            out[pid] = manager_terms(state, view, pid, balance).growth
    return out


def lawyer_count(state: GameState, firm_id: int, data: GameData) -> int:
    """Lawyers on the firm's books, founding partners included (the practice-group gate)."""
    return sum(
        1 for pid in state.staff_ids(firm_id) if data.role(state.person(pid).role).kind == "lawyer"
    )


def practice_groups_unlocked(
    state: GameState, firm_id: int, data: GameData, balance: Balance
) -> bool:
    """Practice groups unlock at 10 lawyers (spec 3, stage 1)."""
    return lawyer_count(state, firm_id, data) >= balance.org.practice_group_unlock_lawyers


def supervisor_morale(state: GameState, person_id: int, balance: Balance) -> float:
    """W_mgr for one person (13.4): 0 for the founding partner and anyone off the books."""
    firm = state.employer_of(person_id)
    if firm is None:
        return 0.0
    return manager_terms(state, org_view(state, firm), person_id, balance).morale
