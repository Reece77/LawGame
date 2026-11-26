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
partner with the most free capacity; the rest of the monthly output goes by the kind's task
levels to the practice's people at each level (nearest level when there is none) with the
most free capacity, then (PT-M7a) other practices' people with familiarity
`matters.flow_min_familiarity` or more, before the matter slips (unfamiliar people would
bill far over budget; they take flow instead). PT-M7a: the rule plans **output**, not
hours at skill 10: a member's hours are their share of the matter's monthly need divided by
their expected output an hour (`expected_output`: effective skill on the phase's tasks / 10
x the strain factor, held to `staffing.output_floor`-`staffing.output_cap`), up to
`staffing.plan_fill` of their capacity, so a typical team finishes near the planned
months. A matter near its end plans and takes only the hours its remaining work needs at
the team's expected output.

PT-M7a also fills idle capacity: flow a practice's own and familiar people cannot take goes
to any fee earner with free capacity (`matters.flow_fill`) before it is left unserved; then
pro bono flow (spec 7.8) takes lawyers' remaining free capacity (`pro_bono.flow_fill` x
capacity), up to the firm's pool (`pro_bono_pool_tenths`). Pro bono records carry
`PRO_BONO_CLIENT_ID`, no value, and count as substantive work.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Final

from ptk.sim.calendar import turn_to_ym
from ptk.sim.data_models import PARTNER_LEVELS, Balance, GameData, KindDef
from ptk.sim.fastcopy import replace
from ptk.sim.interfaces import (
    NO_TECH_HOURS,
    TechHoursView,
    lax_supervision_hours,
    suspended_ids,
    tech_hours,
)
from ptk.sim.macro import shock_share
from ptk.sim.matters import formulas as fx
from ptk.sim.matters.models import (
    PRO_BONO_CLIENT_ID,
    HoursRecord,
    MarketState,
    Matter,
    TeamMember,
    TeamRole,
)
from ptk.sim.matters.rates import client_indexes, indexed_rate
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
    # PT-M12 (T12, rule 6): the person's familiarity by practice as a dict, read once a month
    # (AttrSet's lookup scans twenty practices; staffing reads it per matter and earner)
    fam: Mapping[str, float] = field(default_factory=dict, compare=False, repr=False)

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
    assessing = assessment_tenths(state.market, firm_id, state.turn, balance)
    training = tech_hours(state, firm_id, data, balance).training_tenths  # PT-M14
    lax_hours = lax_supervision_hours(state, firm_id, balance)  # PT-M15
    off = suspended_ids(state) if state.risk.cases else frozenset()  # PT-M15: suspended
    out = []
    for person in state.people:
        if person.id not in staff:
            continue
        level = fx.task_level(person.level, data)
        if level is None:
            continue
        other = (
            (
                max(0, balance.matters.partner_other_hours - lax_hours) * fx.TENTHS
                if person.level in PARTNER_LEVELS
                else 0
            )
            + assessing.get(person.id, 0)
            + training.get(person.id, 0)
        )
        capacity = round(monthly_capacity_tenths(person, balance))
        if person.id in off:  # PT-M15: a suspended lawyer does no billable work
            other = capacity
        out.append(
            FeeEarner(
                person=person,
                level=level,
                home=home_practice(person, data),
                capacity=capacity,
                other=other,
                fam=person.familiarity.as_dict(),
            )
        )
    return tuple(out)


def assessment_tenths(
    market: MarketState, firm_id: int, turn: int, balance: Balance
) -> dict[int, int]:
    """PT-M7a: non-billable tenths this month of leads who made an early case assessment."""
    out: dict[int, int] = {}
    for m in market.open_matters(firm_id):
        a = m.assessment
        if a is not None and a.turn == turn and m.lead_id is not None:
            out[m.lead_id] = out.get(m.lead_id, 0) + balance.assessment.lead_hours * fx.TENTHS
    return out


def expected_output(
    person: Person,
    tasks: Mapping[str, float],
    practice: str,
    data: GameData,
    balance: Balance,
    hours_factor: float = 1.0,
) -> float:
    """PT-M7a: output an hour the default rule expects of a person on a task mix: effective
    skill / 10 x the strain factor, held to staffing.output_floor-output_cap. PT-M11 (T12):
    memoised on the identity of the (immutable) person, task mix, data and balance, so a month
    that staffs many matters asks once per person and mix. PT-M14: divided by the firm's hours
    factor on the mix (`interfaces.tech_hours`: AI's tasks take fewer hours, so an hour does
    more of the matter)."""
    key = (id(person), id(tasks), practice, id(data), id(balance))
    hit = _OUTPUT.get(key)
    if hit is not None and hit[0] is person and hit[1] is tasks:
        return hit[2] / hours_factor
    value = _expected_output(person, tasks, practice, data, balance)
    if len(_OUTPUT) >= _OUTPUT_KEEP:
        _OUTPUT.clear()
    _OUTPUT[key] = (person, tasks, value)
    return value / hours_factor


_OUTPUT: dict[tuple[int, int, str, int, int], tuple[Person, Mapping[str, float], float]] = {}
_OUTPUT_KEEP = 1 << 16  # tunable-exempt: memoised outputs (a cache, not a rule)


def _expected_output(
    person: Person, tasks: Mapping[str, float], practice: str, data: GameData, balance: Balance
) -> float:
    cfg = balance.staffing
    f = (
        fx.effective_skill(person, tasks, practice, data, balance)
        / 10.0
        * fx.strain_output(person.strain, balance)
    )
    return min(cfg.output_cap, max(cfg.output_floor, f))


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


def current_tasks(matter: Matter, kind: KindDef) -> Mapping[str, float]:
    """The task mix of the phase a matter is in (its last phase once all are done)."""
    return kind.phases[min(matter.phase_index, len(kind.phases) - 1)].tasks


def policy_fill(e: FeeEarner, base: float, policy_hours: int | None, balance: Balance) -> float:
    """PT-M7b: a person's fill under the firm's hours policy (a firm-wide billable target,
    hours a year): the policy's share of their capacity when that is above `base`, never above
    `staffing.policy_fill_max`. No policy (None) keeps `base`."""
    if policy_hours is None or e.capacity <= 0:
        return base
    wanted = policy_hours * fx.TENTHS / 12 / e.capacity  # tunable-exempt: months a year
    return max(base, min(balance.staffing.policy_fill_max, wanted))


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
    policy_hours: int | None = None,
    tech: TechHoursView = NO_TECH_HOURS,
    lead_ok: Callable[[Person], bool] | None = None,
) -> tuple[int | None, tuple[TeamMember, ...]]:
    """The default staffing rule: (lead id, team) for a matter (module docstring). Wants are
    output tenths; each person's hours are their output over `expected_output`."""
    kind = data.market.kinds[matter.kind]
    shares = fx.level_shares(fx.kind_tasks(kind), data)
    tasks = current_tasks(matter, kind)  # output is expected on the phase being worked
    left_out = math.ceil(matter.hours_needed_tenths * (1.0 - completed_share(matter, kind)))
    need = min(monthly_need(matter), max(1, left_out))  # PT-M7a: never plan past the end
    step = balance.matters.staff_round_tenths
    fill = balance.staffing.plan_fill  # PT-M7a: the rule leaves headroom (strain)
    free = {  # PT-M7b: the firm's hours policy may plan above it (strain follows)
        e.id: int(policy_fill(e, fill, policy_hours, balance) * e.capacity)
        - e.other
        - load.get(e.id, 0)
        for e in earners
    }
    pool = [e for e in earners if e.home == matter.practice]
    by_id = {e.id: e for e in earners}
    factors: dict[int, float] = {}
    hours_factor = tech.factor(tasks)  # PT-M14

    def factor(e: FeeEarner) -> float:
        if e.id not in factors:
            factors[e.id] = expected_output(
                e.person, tasks, matter.practice, data, balance, hours_factor
            )
        return factors[e.id]

    def best(cands: Sequence[FeeEarner]) -> FeeEarner | None:
        return min(cands, key=lambda c: (-free[c.id], c.id)) if cands else None

    ok = lead_ok or (lambda _p: True)  # PT-M11: admitted where the matter is led
    partners = [e for e in pool if e.level == len(fx.LEVEL_BANDS) - 1 and ok(e.person)]
    origin = by_id.get(matter.originator_id) if matter.originator_id is not None else None
    if origin is not None and not ok(origin.person):
        origin = None
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
        if lead is not None and not ok(lead.person):
            lead = None
    if lead is None:
        return None, ()
    plan: dict[int, int] = {}
    roles: dict[int, TeamRole] = {lead.id: "lead"}

    def give(e: FeeEarner, want_output: float) -> float:
        """Plan the hours for up to `want_output` tenths of output, never beyond the person's
        free capacity; returns the output planned."""
        room = (max(0, free[e.id]) // step) * step
        got = min(_round_to(want_output / factor(e), step), room)
        if e.id == lead.id:  # the lead is always on the team, at least one step
            got = max(got, step if not plan.get(e.id) else 0)
        if got > 0:
            plan[e.id] = plan.get(e.id, 0) + got
            roles.setdefault(e.id, ROLE_BY_LEVEL[e.level])
            free[e.id] -= got
        return got * factor(e)

    give(lead, max(shares[-1], balance.matters.lead_share_min) * need)
    top = len(fx.LEVEL_BANDS) - 1
    enough = step / 2  # output left below half a step is not worth another person
    min_fam = balance.matters.flow_min_familiarity
    others = [e for e in earners if e.home != matter.practice]
    pools = (  # PT-M7a: other practices' familiar free people before the matter slips
        pool,
        [e for e in others if e.fam[matter.practice] >= min_fam],
    )
    for level in range(top - 1, -1, -1):
        if shares[level] <= 0:
            continue
        remaining = shares[level] * need
        for candidates in pools:
            for gap in range(top + 1):
                # PT-M11 (T12): someone with no free step takes nothing (the lead always
                # takes a step), so they are left out: the same plan, fewer calls
                cands = sorted(
                    (
                        e
                        for e in candidates
                        if abs(e.level - level) == gap
                        and e.level < top
                        and (free[e.id] >= step or e.id == lead.id)
                    ),
                    key=lambda e: (-free[e.id], e.id),
                )
                for e in cands:
                    if remaining < enough:
                        break
                    remaining -= give(e, remaining)
                if remaining < enough:
                    break
            if remaining < enough:
                break
        if remaining >= enough:  # no one else is free: the lead takes what they can; the rest slips
            give(lead, remaining)
    team = tuple(
        TeamMember(person_id=pid, role=roles[pid], planned_tenths=t)
        for pid, t in sorted(plan.items())
    )
    return lead.id, team


def staff_matter(
    state: GameState,
    matter: Matter,
    data: GameData,
    balance: Balance,
    earners: Sequence[FeeEarner] | None = None,
    planned: Mapping[int, int] | None = None,
) -> Matter:
    """Apply the default staffing rule to a matter of the state's firm. `earners` (PT-M11, T12):
    the firm's fee earners when the caller already holds them for this state. `planned`
    (PT-M12, T12): `planned_load(state.market, firm)` when the caller keeps it current."""
    if earners is None:
        earners = fee_earners(state, matter.firm_id, data, balance)
    load = dict(planned) if planned is not None else planned_load(state.market, matter.firm_id)
    for tm in matter.team:  # re-staffing: its own plan does not count against itself
        load[tm.person_id] = load.get(tm.person_id, 0) - tm.planned_tenths
    lead, team = default_team(
        matter,
        earners,
        load,
        data,
        balance,
        state.founder_of(matter.firm_id),
        state.firm(matter.firm_id).billable_target_hours,  # PT-M7b: the hours policy
        tech_hours(state, matter.firm_id, data, balance),  # PT-M14
        _lead_rule(state, matter, data),  # PT-M11: bar admissions
    )
    return replace(matter, lead_id=lead, team=team)


def _lead_rule(state: GameState, matter: Matter, data: GameData) -> Callable[[Person], bool] | None:
    """PT-M11: None while the firm has no other office and no case outside the home courts
    needs a check (v1's rule unchanged); else `ptk.sim.geo.admissions.lead_check`."""
    from ptk.sim.geo.admissions import lead_check

    return lead_check(state, matter, data) if data.geo.jurisdictions else None


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
    pro_bono: dict[int, int] = field(default_factory=dict)  # PT-M7a: person -> tenths


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
    rate_index: float = 1.0,
    tech: TechHoursView = NO_TECH_HOURS,
) -> HoursRecord:
    if client_id == PRO_BONO_CLIENT_ID:  # PT-M7a (spec 7.8): no value; real responsibility
        return HoursRecord(
            turn=turn,
            person_id=earner.id,
            client_id=client_id,
            practice=practice,
            matter_id=matter_id,
            tenths=tenths,
            substantive_tenths=tenths,
            value_cents=0,
        )
    sub, mine = _shares(tasks, earner.level, data, balance.matters.substantive_window)
    if not tech.idle:  # PT-M14 (ADR PT-0006 4): hours AI removes were learning hours
        sub *= tech.learning(mine)
    rate = indexed_rate(_rate(practice, earner.person.level, data), rate_index)
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


# PT-M14 (T12): a record's substantive share, task split and card rate depend only on the
# (immutable) task mix, the level and the data, so they are memoised on their identity (a
# month records about a thousand hours records over a handful of mixes); identical results.
_SHARES: dict[tuple[int, int, int, int], tuple[object, object, float, Mapping[str, float]]] = {}
_RATES: dict[tuple[str, str, int], tuple[object, int]] = {}
_MEMO_KEEP = 4096  # tunable-exempt: memoised entries (a cache, not a rule)


def _shares(
    tasks: Mapping[str, float], level: int, data: GameData, window: int
) -> tuple[float, Mapping[str, float]]:
    key = (id(tasks), level, id(data), window)
    hit = _SHARES.get(key)
    if hit is not None and hit[0] is tasks and hit[1] is data:
        return hit[2], hit[3]
    sub = fx.substantive_share(tasks, level, data, window)
    mine = fx.person_tasks(tasks, level, data)
    if len(_SHARES) >= _MEMO_KEEP:
        _SHARES.clear()
    _SHARES[key] = (tasks, data, sub, mine)
    return sub, mine


def _rate(practice: str, level: str, data: GameData) -> int:
    key = (practice, level, id(data))
    hit = _RATES.get(key)
    if hit is not None and hit[0] is data:
        return hit[1]
    rate = fx.rate_cents(data.practice(practice), level, data)
    if len(_RATES) >= _MEMO_KEEP:
        _RATES.clear()
    _RATES[key] = (data, rate)
    return rate


def credit_hours(state: GameState, firm_id: int, balance: Balance) -> int:
    """PT-M7a: the firm's pro bono credit policy, hours a year (spec 7.8)."""
    firm = state.firm(firm_id)
    return (
        balance.pro_bono.credit_hours
        if firm.pro_bono_credit_hours is None
        else firm.pro_bono_credit_hours
    )


def pro_bono_pool_tenths(lawyers: int, credit: int, balance: Balance) -> int:
    """PT-M7a: the firm's pro bono flow a month: (uncredited + uptake x credit) / 12 hours a
    lawyer."""
    cfg = balance.pro_bono
    hours = (cfg.uncredited_hours + cfg.uptake * credit) / 12.0  # tunable-exempt: months
    return round(lawyers * hours * fx.TENTHS)


def ytd_before(state: GameState, person_id: int, balance: Balance) -> int:
    """Pro bono tenths worked earlier this calendar year (0 in January)."""
    if turn_to_ym(state.turn, state.save_meta.start_ym)[1] == 1:  # tunable-exempt: January
        return 0
    return state.person_state(person_id).pro_bono_ytd_tenths


def _is_lawyer(e: FeeEarner, data: GameData) -> bool:
    return data.role(e.person.role).kind == "lawyer"


type OfficeGroups = tuple[
    Callable[[int], float],
    Callable[[int], int],
    list[tuple[int | None, list[FeeEarner]]],
]


def office_groups(
    state: GameState, firm_id: int, earners: Sequence[FeeEarner], data: GameData
) -> OfficeGroups:
    """PT-M11: (client -> rate factor, client -> office, flow groups). Without other offices
    every factor is 1.0 and one group holds everyone (v1's allocation, unchanged)."""
    if not state.geo.firm_offices(firm_id):
        return (lambda _cid: 1.0), (lambda _cid: 0), [(None, list(earners))]
    from ptk.sim.geo.cities import client_office_id, office_city, person_office_id
    from ptk.sim.geo.formulas import rate_factor

    rates: dict[int, float] = {}
    offices: dict[int, int] = {}

    def office(cid: int) -> int:
        if cid not in offices:
            offices[cid] = client_office_id(state, firm_id, state.market.client(cid))
        return offices[cid]

    def rate(cid: int) -> float:
        if cid not in rates:
            oid = office(cid)
            city = data.geo.city(office_city(state, firm_id, oid)) if oid else None
            rates[cid] = rate_factor(city) if city is not None else 1.0
        return rates[cid]

    ids = [0, *(o.id for o in state.geo.firm_offices(firm_id))]
    groups: list[tuple[int | None, list[FeeEarner]]] = [
        (oid, [e for e in earners if person_office_id(state, firm_id, e.person) == oid])
        for oid in ids
    ]
    return rate, office, groups


def month_hours(
    state: GameState,
    firm_id: int,
    flow_tenths: Mapping[tuple[int, str], int],
    data: GameData,
    balance: Balance,
) -> MonthHours:
    """Allocate the month: named matters first, then flow, then pro bono (module docstring)."""
    turn = state.turn
    ym = turn_to_ym(turn, state.save_meta.start_ym)
    firm = state.firm(firm_id)
    index = client_indexes(state, firm, balance)  # PT-M7b: by practice; PT-M7c: by client tier
    earners = fee_earners(state, firm_id, data, balance)
    by_id = {e.id: e for e in earners}
    cap = {e.id: e.capacity for e in earners}
    matters = [m for m in state.market.open_matters(firm_id) if m.team]
    tech = tech_hours(state, firm_id, data, balance)  # PT-M14: hours on each task x efficiency
    records: list[HoursRecord] = []
    # PT-M11: each client's work is its city's office's, at the city's card; flow work is
    # served by that office's people (one group, everyone, without other offices: v1)
    rate_f, client_office, groups = office_groups(state, firm_id, earners, data)
    # 1. named matters: planned, capped by what the matter still needs (at the team's expected
    # output, PT-M7a) and by max load
    wanted: dict[tuple[int, int], int] = {}
    for m in matters:
        kind = data.market.kinds[m.kind]
        plan = {tm.person_id: tm.planned_tenths for tm in m.team if tm.person_id in by_id}
        tasks = current_tasks(m, kind)
        planned = sum(plan.values())
        hf = tech.factor(tasks)
        f_team = (
            sum(
                t * expected_output(by_id[pid].person, tasks, m.practice, data, balance, hf)
                for pid, t in plan.items()
            )
            / planned
            if planned
            else 1.0
        )
        # ceil (PT-M7a): a matter a hair from done rounded to 0 and never finished
        left = math.ceil(m.hours_needed_tenths * (1.0 - completed_share(m, kind)) / f_team)
        paused = shock_share(data.macro, "hours", m.practice, ym)  # PT-M10: a dated shock
        if paused > 0:
            plan = {pid: round(t * (1.0 - paused)) for pid, t in plan.items()}
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
            _record(
                turn,
                by_id[pid],
                m.client_id,
                m.practice,
                mid,
                t,
                phase.tasks,
                data,
                balance,
                index(m.practice, m.client_id) * rate_f(m.client_id),
                tech,
            )
        )
        used[pid] += t
    # 2. flow, by practice: home pools first, then familiar fee earners, then anyone idle
    policy = firm.billable_target_hours  # PT-M7b: flow fills to the hours policy too
    fills = {e.id: policy_fill(e, balance.matters.flow_fill, policy, balance) for e in earners}
    unserved: dict[tuple[int, str], float] = {}
    lost_t: dict[int, float] = {}
    all_t: dict[int, float] = {}
    flow_tasks = data.market.flow_tasks
    min_fam = balance.matters.flow_min_familiarity
    flow_factor = tech.factor(flow_tasks)  # PT-M14: flow's base hours x efficiency
    if flow_factor != 1.0:
        flow_tenths = {k: round(t * flow_factor) for k, t in flow_tenths.items()}
    for practice, (group, members) in ((p, g) for p in data.practice_keys for g in groups):
        demands = {
            cid: t
            for (cid, p), t in flow_tenths.items()
            if p == practice and t > 0 and (group is None or client_office(cid) == group)
        }
        total = sum(demands.values())
        if total <= 0:
            continue
        served: dict[int, int] = {}
        left = total
        pools = (
            [e for e in members if e.home == practice],
            [e for e in members if e.home != practice and e.fam[practice] >= min_fam],
            [  # PT-M7a: idle capacity takes flow before it is left unserved
                e for e in members if e.home != practice and e.fam[practice] < min_fam
            ],
            # PT-M11: then the practice's lawyers in the firm's other offices (none in v1)
            [e for e in earners if e.home == practice and e not in members]
            if group is not None
            else [],
        )
        for pool in pools:
            free = {e.id: max(0, int(fills[e.id] * cap[e.id]) - used[e.id]) for e in pool}
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
        weights = {cid: float(t) for cid, t in demands.items()}
        card = {cid: index(practice, cid) * rate_f(cid) for cid in demands}  # PT-M13 (T12)
        for pid in sorted(served):
            for cid, t in sorted(_split(served[pid], weights).items()):
                if t > 0:
                    records.append(
                        _record(
                            turn,
                            by_id[pid],
                            cid,
                            practice,
                            None,
                            t,
                            flow_tasks,
                            data,
                            balance,
                            card[cid],
                            tech,
                        )
                    )
    for cid, wanted_t in all_t.items():  # (client, "") -> its unserved share of all its flow
        unserved[(cid, "")] = lost_t[cid] / wanted_t if wanted_t > 0 else 0.0
    # 3. PT-M7a: pro bono flow (spec 7.8) takes lawyers' remaining free capacity
    lawyers = [e for e in earners if _is_lawyer(e, data)]
    credit = credit_hours(state, firm_id, balance)
    pool_t = pro_bono_pool_tenths(len(lawyers), credit, balance)
    pb_fill = balance.pro_bono.flow_fill
    free_pb = {e.id: max(0, int(pb_fill * cap[e.id]) - used[e.id]) for e in lawyers}
    room = sum(free_pb.values())
    if pool_t > 0 and room > 0:
        for pid, t in sorted(_split(min(pool_t, room), free_pb).items()):
            if t > 0:
                e = by_id[pid]
                records.append(
                    _record(turn, e, PRO_BONO_CLIENT_ID, e.home, None, t, flow_tasks, data, balance)
                )
                used[pid] += t
    records.sort(key=lambda r: (r.person_id, r.matter_id or 0, r.client_id, r.practice))
    work: dict[int, WorkMonth] = {}
    pro_bono: dict[int, int] = {}
    keys = data.practice_keys
    cap_t = credit * fx.TENTHS
    by_person: dict[int, list[HoursRecord]] = {}  # PT-M10 (T12): one pass, record order kept
    for r in records:
        by_person.setdefault(r.person_id, []).append(r)
    for e in earners:
        mine = by_person.get(e.id, [])
        by_practice = {p: sum(r.tenths for r in mine if r.practice == p) for p in keys}
        pb = sum(r.tenths for r in mine if r.client_id == PRO_BONO_CLIENT_ID)
        before = ytd_before(state, e.id, balance)
        credited = min(before + pb, cap_t) - min(before, cap_t)
        if pb:
            pro_bono[e.id] = pb
        work[e.id] = WorkMonth(
            person_id=e.id,
            practice_tenths=tuple((p, t) for p, t in by_practice.items() if t > 0),
            substantive_tenths=sum(r.substantive_tenths for r in mine)
            + tech.training_tenths.get(e.id, 0),  # PT-M14: training is learning
            other_tenths=e.other,
            pro_bono_tenths=pb,
            credited_tenths=credited,
        )
    return MonthHours(records=tuple(records), work=work, unserved=unserved, pro_bono=pro_bono)
