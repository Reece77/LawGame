"""Staffing and the month's hours (spec 7.5; ADR PT-0004 section 2, PT-0005).

Each fee earner's month is the sum of their named-matter hours and their share of flow work:

1. **Named matters.** Every team member works their planned hours, but no one works more
   than `matters.max_load` x their monthly capacity on named matters (planned hours are
   scaled down to fit, in tenths, largest remainder first), and a matter near its end takes
   only what it still needs.
2. **Flow work** for each practice is absorbed by the practice's own people (lawyers whose
   home practice it is, paralegals whose most familiar practice it is) in proportion to
   their free capacity, up to `matters.flow_fill` x capacity; what they cannot take goes to
   other fee earners with at least `matters.flow_min_familiarity` in the practice; the rest
   is unserved (the client notices: spec 7.2 service, 7.1 capacity term).
3. Partners also spend `matters.partner_other_hours` a month on business development and
   management (non-billable, ADR PT-0005 5).

Every hour is a `HoursRecord` by (person, matter or client flow), so Σ person-hours =
Σ matter-hours + flow hours by construction (tests/property/test_matters.py checks it).

The default staffing rule (used at intake, by delegates and by scripts): the lead is the
relationship partner when they practise in the matter's practice, else the practice's
partner with the most free capacity; the rest of the monthly hours go by the kind's task
levels to the practice's people at each level (nearest level when there is none) with the
most free capacity.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Final

from ptk.sim.data_models import PARTNER_LEVELS, Balance, GameData, KindDef
from ptk.sim.matters import formulas as fx
from ptk.sim.matters.models import (
    HoursRecord,
    MarketState,
    Matter,
    TeamMember,
    TeamRole,
)
from ptk.sim.money import round_half_even
from ptk.sim.people.models import Person, WorkMonth
from ptk.sim.people.strain import monthly_capacity_tenths
from ptk.sim.state import GameState

ROLE_BY_LEVEL: Final[tuple[TeamRole, ...]] = ("paralegal", "junior", "junior", "senior", "lead")


@dataclass(frozen=True, slots=True)
class FeeEarner:
    person: Person
    level: int  # task level 0-4
    home: str  # home practice
    capacity: int  # monthly capacity, tenths
    other: int  # non-billable tenths (partners' business development and management)

    @property
    def id(self) -> int:
        return self.person.id


def home_practice(person: Person, data: GameData) -> str:
    practice = data.role(person.role).practice
    if practice is not None:
        return practice
    best = max(
        data.practice_keys, key=lambda k: (person.familiarity[k], -data.practice_keys.index(k))
    )
    return best


def fee_earners(
    state: GameState, firm_id: int, data: GameData, balance: Balance
) -> tuple[FeeEarner, ...]:
    """A firm's lawyers and paralegals on its books, by person id."""
    staff = set(state.staff_ids(firm_id))
    out = []
    for person in state.people:
        if person.id not in staff:
            continue
        level = fx.task_level(person.level, data)
        if level is None:
            continue
        other = (
            balance.matters.partner_other_hours * fx.TENTHS if person.level in PARTNER_LEVELS else 0
        )
        out.append(
            FeeEarner(
                person=person,
                level=level,
                home=home_practice(person, data),
                capacity=round(monthly_capacity_tenths(person, balance)),
                other=other,
            )
        )
    return tuple(out)


def planned_load(market: MarketState, firm_id: int) -> dict[int, int]:
    """Planned named-matter tenths a month by person, over the firm's open matters."""
    load: dict[int, int] = {}
    for m in market.open_matters(firm_id):
        for tm in m.team:
            load[tm.person_id] = load.get(tm.person_id, 0) + tm.planned_tenths
    return load


def completed_share(matter: Matter, kind: KindDef) -> float:
    done = sum(p.share for p in kind.phases[: matter.phase_index])
    if matter.phase_index < len(kind.phases):
        done += kind.phases[matter.phase_index].share * matter.phase_progress
    return min(1.0, done)


def monthly_need(matter: Matter) -> int:
    return max(1, round(matter.hours_needed_tenths / max(1, matter.planned_months)))


def _round_to(value: float, step: int) -> int:
    return max(step, round(value / step) * step)


def default_team(
    matter: Matter,
    earners: Sequence[FeeEarner],
    load: Mapping[int, int],
    data: GameData,
    balance: Balance,
    founder_id: int | None,
) -> tuple[int | None, tuple[TeamMember, ...]]:
    """The default staffing rule: (lead id, team) for a matter (module docstring)."""
    kind = data.market.kinds[matter.kind]
    shares = fx.level_shares(fx.kind_tasks(kind), data)
    need = monthly_need(matter)
    step = balance.matters.staff_round_tenths
    free = {e.id: e.capacity - e.other - load.get(e.id, 0) for e in earners}
    pool = [e for e in earners if e.home == matter.practice]
    by_id = {e.id: e for e in earners}

    def best(cands: Sequence[FeeEarner]) -> FeeEarner | None:
        return min(cands, key=lambda c: (-free[c.id], c.id)) if cands else None

    partners = [e for e in pool if e.level == len(fx.LEVEL_BANDS) - 1]
    origin = by_id.get(matter.originator_id) if matter.originator_id is not None else None
    lead: FeeEarner | None
    if (
        origin is not None
        and origin.level == len(fx.LEVEL_BANDS) - 1
        and (origin.home == matter.practice or not partners)
    ):
        lead = origin
    else:
        lead = best(partners) or origin
    if lead is None and founder_id is not None:
        lead = by_id.get(founder_id)
    if lead is None:
        return None, ()
    plan: dict[int, int] = {}
    roles: dict[int, TeamRole] = {lead.id: "lead"}

    def give(e: FeeEarner, want: int) -> int:
        """Plan up to `want` tenths for a person, never beyond their free capacity."""
        room = (max(0, free[e.id]) // step) * step
        got = min(want, room)
        if e.id == lead.id:  # the lead is always on the team, at least one step
            got = max(got, step if not plan.get(e.id) else 0)
        if got > 0:
            plan[e.id] = plan.get(e.id, 0) + got
            roles.setdefault(e.id, ROLE_BY_LEVEL[e.level])
            free[e.id] -= got
        return got

    give(lead, _round_to(max(shares[-1], balance.matters.lead_share_min) * need, step))
    top = len(fx.LEVEL_BANDS) - 1
    for level in range(top - 1, -1, -1):
        if shares[level] <= 0:
            continue
        remaining = _round_to(shares[level] * need, step)
        for gap in range(top + 1):
            cands = sorted(
                (e for e in pool if abs(e.level - level) == gap and e.level < top),
                key=lambda e: (-free[e.id], e.id),
            )
            for e in cands:
                if remaining <= 0:
                    break
                remaining -= give(e, remaining)
            if remaining <= 0:
                break
        if remaining > 0:  # no one else is free: the lead takes what they can; the rest slips
            give(lead, remaining)
    team = tuple(
        TeamMember(person_id=pid, role=roles[pid], planned_tenths=t)
        for pid, t in sorted(plan.items())
    )
    return lead.id, team


def staff_matter(state: GameState, matter: Matter, data: GameData, balance: Balance) -> Matter:
    """Apply the default staffing rule to a matter of the state's firm."""
    earners = fee_earners(state, matter.firm_id, data, balance)
    load = planned_load(state.market, matter.firm_id)
    for tm in matter.team:  # re-staffing: its own plan does not count against itself
        load[tm.person_id] = load.get(tm.person_id, 0) - tm.planned_tenths
    lead, team = default_team(
        matter, earners, load, data, balance, state.founder_of(matter.firm_id)
    )
    return replace(matter, lead_id=lead, team=team)


# --- The month's hours ----------------------------------------------------------------------


def _scale(values: Mapping[int, int], limit: int) -> dict[int, int]:
    """Scale non-negative integers down to sum to `limit` (largest remainder, ties by key)."""
    total = sum(values.values())
    if total <= limit:
        return dict(values)
    exact = {k: v * limit / total for k, v in values.items()}
    out = {k: int(x) for k, x in exact.items()}
    left = limit - sum(out.values())
    for k in sorted(exact, key=lambda k: (-(exact[k] - out[k]), k))[:left]:
        out[k] += 1
    return out


def _split(total: int, weights: Mapping[int, float]) -> dict[int, int]:
    """Split integer `total` in proportion to weights (largest remainder, ties by key)."""
    wsum = sum(weights.values())
    if total <= 0 or wsum <= 0:
        return {k: 0 for k in weights}
    exact = {k: total * w / wsum for k, w in weights.items()}
    out = {k: int(x) for k, x in exact.items()}
    left = total - sum(out.values())
    for k in sorted(exact, key=lambda k: (-(exact[k] - out[k]), k))[:left]:
        out[k] += 1
    return out


@dataclass(frozen=True, slots=True)
class MonthHours:
    records: tuple[HoursRecord, ...]
    work: dict[int, WorkMonth]
    # (client, practice) -> unserved share of its flow in the practice; (client, "") -> of all
    unserved: dict[tuple[int, str], float]


def _record(
    turn: int,
    earner: FeeEarner,
    client_id: int,
    practice: str,
    matter_id: int | None,
    tenths: int,
    tasks: Mapping[str, float],
    data: GameData,
    balance: Balance,
) -> HoursRecord:
    sub = fx.substantive_share(tasks, earner.level, data, balance.matters.substantive_window)
    rate = fx.rate_cents(data.practice(practice), earner.person.level, data)
    return HoursRecord(
        turn=turn,
        person_id=earner.id,
        client_id=client_id,
        practice=practice,
        matter_id=matter_id,
        tenths=tenths,
        substantive_tenths=round(tenths * sub),
        value_cents=round_half_even(tenths * rate, fx.TENTHS),
    )


def month_hours(
    state: GameState,
    firm_id: int,
    flow_tenths: Mapping[tuple[int, str], int],
    data: GameData,
    balance: Balance,
) -> MonthHours:
    """Allocate the month: named matters first, then flow (module docstring)."""
    turn = state.turn
    earners = fee_earners(state, firm_id, data, balance)
    by_id = {e.id: e for e in earners}
    cap = {e.id: e.capacity for e in earners}
    matters = [m for m in state.market.open_matters(firm_id) if m.team]
    records: list[HoursRecord] = []
    # 1. named matters: planned, capped by what the matter still needs and by max load
    wanted: dict[tuple[int, int], int] = {}
    for m in matters:
        kind = data.market.kinds[m.kind]
        left = round(m.hours_needed_tenths * (1.0 - completed_share(m, kind)))
        plan = {tm.person_id: tm.planned_tenths for tm in m.team if tm.person_id in by_id}
        for pid, t in _scale(plan, max(left, 0)).items():
            if t > 0:
                wanted[(pid, m.id)] = t
    per_person: dict[int, dict[int, int]] = {}
    for (pid, mid), t in wanted.items():
        per_person.setdefault(pid, {})[mid] = t
    named: dict[tuple[int, int], int] = {}
    for pid, mats in per_person.items():
        limit = max(0, int(balance.matters.max_load * cap[pid]) - by_id[pid].other)
        for mid, t in _scale(mats, limit).items():
            if t > 0:
                named[(pid, mid)] = t
    used = {e.id: e.other for e in earners}
    by_matter = {m.id: m for m in matters}
    for (pid, mid), t in sorted(named.items()):
        m = by_matter[mid]
        phase = data.market.kinds[m.kind].phases[
            min(m.phase_index, len(data.market.kinds[m.kind].phases) - 1)
        ]
        records.append(
            _record(turn, by_id[pid], m.client_id, m.practice, mid, t, phase.tasks, data, balance)
        )
        used[pid] += t
    # 2. flow, by practice: home pools first, then familiar fee earners
    fill = balance.matters.flow_fill
    unserved: dict[tuple[int, str], float] = {}
    lost_t: dict[int, float] = {}
    all_t: dict[int, float] = {}
    flow_tasks = data.market.flow_tasks
    for practice in data.practice_keys:
        demands = {cid: t for (cid, p), t in flow_tenths.items() if p == practice and t > 0}
        total = sum(demands.values())
        if total <= 0:
            continue
        served: dict[int, int] = {}
        left = total
        pools = (
            [e for e in earners if e.home == practice],
            [
                e
                for e in earners
                if e.home != practice
                and e.person.familiarity[practice] >= balance.matters.flow_min_familiarity
            ],
        )
        for pool in pools:
            free = {e.id: max(0, int(fill * cap[e.id]) - used[e.id]) for e in pool}
            room = sum(free.values())
            if room <= 0 or left <= 0:
                continue
            take = min(left, room)
            for pid, t in _split(take, free).items():
                if t > 0:
                    served[pid] = served.get(pid, 0) + t
                    used[pid] += t
            left -= take
        done = total - left
        for cid, t in demands.items():
            unserved[(cid, practice)] = left / total
            lost_t[cid] = lost_t.get(cid, 0.0) + t * left / total
            all_t[cid] = all_t.get(cid, 0.0) + t
        # each person's flow hours split over the practice's clients by demand
        if done <= 0:
            continue
        for pid in sorted(served):
            weights = {cid: float(t) for cid, t in demands.items()}
            for cid, t in sorted(_split(served[pid], weights).items()):
                if t > 0:
                    records.append(
                        _record(turn, by_id[pid], cid, practice, None, t, flow_tasks, data, balance)
                    )
    for cid, wanted_t in all_t.items():  # (client, "") -> its unserved share of all its flow
        unserved[(cid, "")] = lost_t[cid] / wanted_t if wanted_t > 0 else 0.0
    records.sort(key=lambda r: (r.person_id, r.matter_id or 0, r.client_id, r.practice))
    work: dict[int, WorkMonth] = {}
    keys = data.practice_keys
    for e in earners:
        mine = [r for r in records if r.person_id == e.id]
        by_practice = {p: sum(r.tenths for r in mine if r.practice == p) for p in keys}
        work[e.id] = WorkMonth(
            person_id=e.id,
            practice_tenths=tuple((p, t) for p, t in by_practice.items() if t > 0),
            substantive_tenths=sum(r.substantive_tenths for r in mine),
            other_tenths=e.other,
        )
    return MonthHours(records=tuple(records), work=work, unserved=unserved)
