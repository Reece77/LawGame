"""Client and matter actions (ADR-0014): they take effect at once.

Staffing (assign, set hours, remove, set the lead, apply the default rule), conflict waivers
(ADR PT-0009 2), cross-sell introductions (spec 7.2), answering a settlement offer (spec
7.6), the firm's conflicts-check policy (ADR PT-0009 5) and a new case's forum (spec 7.6a).
Randomness (waivers, introductions) comes from the action's generator (stream `actions`,
keyed by the action's seq). Every rule an action could break raises a `SimError` and changes
nothing.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Final, Literal

import numpy as np

from ptk.sim.data_models import PARTNER_LEVELS, Balance, GameData
from ptk.sim.errors import (
    MatterActionError,
    OverCapacityError,
    StaffingError,
    UnknownClientError,
    UnknownMatterError,
)
from ptk.sim.hiring.actions import Outcome, acting_firm, spend_energy
from ptk.sim.log import inbox_item
from ptk.sim.matters import formulas as fx
from ptk.sim.matters.assessment import merits_range, merits_words
from ptk.sim.matters.conflicts import affected_client, conflict_index
from ptk.sim.matters.intake import bump, with_matter, with_relationship
from ptk.sim.matters.models import Matter, MeritsAssessment, TeamMember, TeamRole
from ptk.sim.matters.progress import settle
from ptk.sim.matters.staffing import fee_earners, planned_load, staff_matter
from ptk.sim.state import GameState, with_firm

type Draws = Callable[[], np.random.Generator]
HOURS_MAX: Final = 400  # tunable-exempt: planned hours a month an input may name


@dataclass(frozen=True, slots=True)
class AssignToMatter:
    actor_id: int
    matter_id: int
    person_id: int
    hours: int  # planned hours a month
    role: TeamRole | None = None  # None: from the person's level
    kind: Literal["assign_to_matter"] = "assign_to_matter"


@dataclass(frozen=True, slots=True)
class SetMatterHours:
    actor_id: int
    matter_id: int
    person_id: int
    hours: int
    kind: Literal["set_matter_hours"] = "set_matter_hours"


@dataclass(frozen=True, slots=True)
class RemoveFromMatter:
    actor_id: int
    matter_id: int
    person_id: int
    kind: Literal["remove_from_matter"] = "remove_from_matter"


@dataclass(frozen=True, slots=True)
class SetMatterLead:
    actor_id: int
    matter_id: int
    person_id: int  # a partner; joins the team if not on it
    kind: Literal["set_matter_lead"] = "set_matter_lead"


@dataclass(frozen=True, slots=True)
class DefaultStaffing:
    """Re-staff a matter by the default rule (what delegates and scripts use)."""

    actor_id: int
    matter_id: int
    kind: Literal["default_staffing"] = "default_staffing"


@dataclass(frozen=True, slots=True)
class SeekWaiver:
    actor_id: int
    matter_id: int
    advance: bool = False  # ask for an advance waiver (harder; covers future conflicts)
    kind: Literal["seek_waiver"] = "seek_waiver"


@dataclass(frozen=True, slots=True)
class Introduce:
    actor_id: int  # the introducing partner
    client_id: int
    colleague_id: int  # a lawyer whose home practice is `practice`
    practice: str
    kind: Literal["introduce"] = "introduce"


@dataclass(frozen=True, slots=True)
class RespondSettlement:
    actor_id: int
    matter_id: int
    accept: bool
    kind: Literal["respond_settlement"] = "respond_settlement"


@dataclass(frozen=True, slots=True)
class SetConflictChecks:
    actor_id: int
    enabled: bool
    kind: Literal["set_conflict_checks"] = "set_conflict_checks"


@dataclass(frozen=True, slots=True)
class ChooseForum:
    actor_id: int
    matter_id: int
    court: str
    kind: Literal["choose_forum"] = "choose_forum"


@dataclass(frozen=True, slots=True)
class AssessCase:
    """PT-M7a: early case assessment (spec 7.6) on an open case."""

    actor_id: int
    matter_id: int
    kind: Literal["assess_case"] = "assess_case"


@dataclass(frozen=True, slots=True)
class SetProBonoCredit:
    """PT-M7a: the firm's pro bono credit policy (spec 7.8), hours a year."""

    actor_id: int
    hours: int
    kind: Literal["set_pro_bono_credit"] = "set_pro_bono_credit"


@dataclass(frozen=True, slots=True)
class SetRatePolicy:
    """PT-M7a: each January's rate rise in bp; None follows the market."""

    actor_id: int
    rise_bp: int | None
    kind: Literal["set_rate_policy"] = "set_rate_policy"


@dataclass(frozen=True, slots=True)
class SetHoursPolicy:
    """PT-M7b: the firm-wide billable target, hours a year; None: the levels' targets."""

    actor_id: int
    hours: int | None
    kind: Literal["set_hours_policy"] = "set_hours_policy"


type MatterAction = (
    AssignToMatter
    | SetMatterHours
    | RemoveFromMatter
    | SetMatterLead
    | DefaultStaffing
    | SeekWaiver
    | Introduce
    | RespondSettlement
    | SetConflictChecks
    | ChooseForum
    | AssessCase
    | SetProBonoCredit
    | SetRatePolicy
    | SetHoursPolicy
)

MATTER_ACTION_TYPES: dict[str, type[MatterAction]] = {
    "assign_to_matter": AssignToMatter,
    "set_matter_hours": SetMatterHours,
    "remove_from_matter": RemoveFromMatter,
    "set_matter_lead": SetMatterLead,
    "default_staffing": DefaultStaffing,
    "seek_waiver": SeekWaiver,
    "introduce": Introduce,
    "respond_settlement": RespondSettlement,
    "set_conflict_checks": SetConflictChecks,
    "choose_forum": ChooseForum,
    "assess_case": AssessCase,  # PT-M7a
    "set_pro_bono_credit": SetProBonoCredit,
    "set_rate_policy": SetRatePolicy,
    "set_hours_policy": SetHoursPolicy,
}


def _matter(state: GameState, firm_id: int, matter_id: int, *, status: str = "open") -> Matter:
    m = state.market.matter(matter_id)
    if m is None or m.firm_id != firm_id:
        raise UnknownMatterError(f"no matter {matter_id}")
    if m.status != status:
        raise MatterActionError(f"matter {matter_id} is {m.status}, not {status}")
    return m


def _check_capacity(
    state: GameState, firm_id: int, person_id: int, extra: int, data: GameData, balance: Balance
) -> None:
    earner = next(
        (e for e in fee_earners(state, firm_id, data, balance) if e.id == person_id), None
    )
    if earner is None:
        raise StaffingError(f"person {person_id} is not a fee earner at the firm")
    load = planned_load(state.market, firm_id).get(person_id, 0) + extra
    limit = int(balance.matters.max_load * earner.capacity) - earner.other
    if load > limit:
        raise OverCapacityError(
            f"that would plan {load // fx.TENTHS} hours a month on named matters for person "
            f"{person_id}; at most {max(0, limit) // fx.TENTHS} fit"
        )


def _hours(hours: int) -> int:
    if not 0 < hours <= HOURS_MAX:
        raise StaffingError(f"planned hours must be 1..{HOURS_MAX}")
    return hours * fx.TENTHS


def _set_team(
    state: GameState, matter: Matter, team: tuple[TeamMember, ...], lead: int | None
) -> GameState:
    """The player's staffing: the matter leaves the monthly default re-plan."""
    ordered = tuple(sorted(team, key=lambda t: t.person_id))
    m = replace(matter, team=ordered, lead_id=lead, auto_staff=False)
    return replace(state, market=with_matter(state.market, m))


def _default_role(level: str, data: GameData) -> TeamRole:
    lv = fx.task_level(level, data)
    return ("paralegal", "junior", "junior", "senior", "senior")[0 if lv is None else lv]


def assign(state: GameState, a: AssignToMatter, balance: Balance, data: GameData) -> Outcome:
    firm = acting_firm(state, a.actor_id)
    matter = _matter(state, firm, a.matter_id)
    if matter.member(a.person_id) is not None:
        raise StaffingError(f"person {a.person_id} is already on matter {a.matter_id}")
    tenths = _hours(a.hours)
    _check_capacity(state, firm, a.person_id, tenths, data, balance)
    state = spend_energy(state, a.actor_id, "staff", balance)
    role: TeamRole = a.role or _default_role(state.person(a.person_id).level, data)
    if role == "lead":
        raise StaffingError("set a lead with set_matter_lead")
    member = TeamMember(person_id=a.person_id, role=role, planned_tenths=tenths)
    return Outcome(state=_set_team(state, matter, (*matter.team, member), matter.lead_id))


def set_hours(state: GameState, a: SetMatterHours, balance: Balance, data: GameData) -> Outcome:
    firm = acting_firm(state, a.actor_id)
    matter = _matter(state, firm, a.matter_id)
    member = matter.member(a.person_id)
    if member is None:
        raise StaffingError(f"person {a.person_id} is not on matter {a.matter_id}")
    tenths = _hours(a.hours)
    _check_capacity(state, firm, a.person_id, tenths - member.planned_tenths, data, balance)
    state = spend_energy(state, a.actor_id, "staff", balance)
    team = tuple(
        replace(t, planned_tenths=tenths) if t.person_id == a.person_id else t for t in matter.team
    )
    return Outcome(state=_set_team(state, matter, team, matter.lead_id))


def remove(state: GameState, a: RemoveFromMatter, balance: Balance) -> Outcome:
    firm = acting_firm(state, a.actor_id)
    matter = _matter(state, firm, a.matter_id)
    if matter.member(a.person_id) is None:
        raise StaffingError(f"person {a.person_id} is not on matter {a.matter_id}")
    if a.person_id == matter.lead_id:
        raise StaffingError("the lead cannot be removed; set another lead first")
    state = spend_energy(state, a.actor_id, "staff", balance)
    team = tuple(t for t in matter.team if t.person_id != a.person_id)
    return Outcome(state=_set_team(state, matter, team, matter.lead_id))


def set_lead(state: GameState, a: SetMatterLead, balance: Balance, data: GameData) -> Outcome:
    firm = acting_firm(state, a.actor_id)
    matter = _matter(state, firm, a.matter_id)
    if (
        a.person_id not in state.staff_ids(firm)
        or state.person(a.person_id).level not in PARTNER_LEVELS
    ):
        raise StaffingError(f"person {a.person_id} is not a partner at the firm")
    from ptk.sim.geo.admissions import may_lead  # PT-M11 (spec 11.1)

    if not may_lead(state, state.person(a.person_id), matter, data):
        raise StaffingError(
            f"person {a.person_id} is not admitted where this matter is led (bar admissions)"
        )
    member = matter.member(a.person_id)
    if member is None:
        step = balance.matters.staff_round_tenths
        _check_capacity(state, firm, a.person_id, step, data, balance)
        member = TeamMember(person_id=a.person_id, role="lead", planned_tenths=step)
    state = spend_energy(state, a.actor_id, "staff", balance)
    team = [t for t in matter.team if t.person_id != a.person_id]
    team = [replace(t, role="senior") if t.role == "lead" else t for t in team]
    return Outcome(
        state=_set_team(state, matter, (*team, replace(member, role="lead")), a.person_id)
    )


def default_staffing(
    state: GameState, a: DefaultStaffing, balance: Balance, data: GameData
) -> Outcome:
    firm = acting_firm(state, a.actor_id)
    matter = _matter(state, firm, a.matter_id)
    state = spend_energy(state, a.actor_id, "staff", balance)
    staffed = staff_matter(state, replace(matter, team=(), lead_id=None), data, balance)
    staffed = replace(staffed, auto_staff=True)
    return Outcome(state=replace(state, market=with_matter(state.market, staffed)))


def seek_waiver(
    state: GameState, a: SeekWaiver, draws: Draws, balance: Balance, data: GameData
) -> Outcome:
    """A waiver's chance: sigmoid(base + w_rel (R - 50)/50 + w_gc (adaptability + risk - 20)/2
    [+ advance penalty]) from the affected client's relationship and GC (ADR PT-0009 2)."""
    firm = acting_firm(state, a.actor_id)
    matter = _matter(state, firm, a.matter_id, status="conflicted")
    index = conflict_index(state.market, firm, state.turn, balance)
    affected = affected_client(matter, index)
    if affected is None:  # the conflict has gone (the other matter ended): it may open
        affected = matter.adverse_client_id or matter.client_id
    state = spend_energy(state, a.actor_id, "seek_waiver", balance)
    cfg = balance.conflicts
    client = state.market.client(affected)
    rel = state.market.relationship(affected, firm)
    score = rel.score if rel is not None else 0.0
    gc = client.gc.personality
    logit = (
        cfg.waiver_base
        + cfg.waiver_relationship * (score - 50.0) / 50.0
        + cfg.waiver_gc * (gc["adaptability"] + gc["risk_appetite"] - 20.0) / 2.0
        + (cfg.advance_penalty if a.advance else 0.0)
    )
    granted = float(draws().random()) < fx.sigmoid(logit)
    market = bump(state.market, affected, firm, balance.relationships.waiver_asked)
    if not granted:
        declined = replace(matter, status="declined", closed_turn=state.turn)
        item = inbox_item(
            state.turn,
            firm,
            "waiver_refused",
            link_kind="matter",
            link_id=matter.id,
            client=client.name,
            matter=matter.name,
        )
        return Outcome(state=replace(state, market=with_matter(market, declined)), log=(item,))
    current = market.relationship(affected, firm)
    if a.advance and current is not None:
        market = with_relationship(market, replace(current, advance_waiver=True))
    opened = replace(matter, status="open", waiver=True)
    state = replace(state, market=with_matter(market, opened))
    staffed = staff_matter(state, opened, data, balance)
    item = inbox_item(
        state.turn,
        firm,
        "waiver_granted",
        link_kind="matter",
        link_id=matter.id,
        client=client.name,
        matter=matter.name,
    )
    return Outcome(state=replace(state, market=with_matter(state.market, staffed)), log=(item,))


def introduce(
    state: GameState, a: Introduce, draws: Draws, balance: Balance, data: GameData
) -> Outcome:
    """Cross-selling (spec 7.2): success adds the practice to the client's instructions."""
    firm = acting_firm(state, a.actor_id)
    try:
        client = state.market.client(a.client_id)
    except KeyError as exc:
        raise UnknownClientError(f"no client {a.client_id}") from exc
    rel = state.market.relationship(a.client_id, firm)
    if rel is None:
        raise UnknownClientError(f"the firm is not on {client.name}'s panel")
    if a.practice not in data.practice_keys:
        raise MatterActionError(f"unknown practice {a.practice!r}")
    if a.practice in rel.practices:
        raise MatterActionError(f"{client.name} already instructs the firm in {a.practice}")
    introducer = state.person(a.actor_id)
    if introducer.level not in PARTNER_LEVELS:
        raise MatterActionError("only a partner can introduce a colleague")
    staff = set(state.staff_ids(firm))
    if a.colleague_id not in staff:
        raise StaffingError(f"person {a.colleague_id} is not at the firm")
    colleague = state.person(a.colleague_id)
    if data.role(colleague.role).practice != a.practice:
        raise MatterActionError(f"person {a.colleague_id} does not practise {a.practice}")
    last = dict(rel.intro_turns).get(a.practice)
    cfg = balance.cross_sell
    if last is not None and state.turn - last < cfg.cooldown_turns:
        raise MatterActionError(f"{a.practice} was introduced to {client.name} recently")
    state = spend_energy(state, a.actor_id, "introduce", balance)
    affinity = max(
        (data.practice(p).cross_sell.get(a.practice, 0.0) for p in rel.practices), default=0.0
    )
    logit = (
        cfg.base
        + cfg.affinity * affinity
        + cfg.relationship * (rel.score - 50.0) / 50.0
        + cfg.bd * (introducer.skills["business_development"] - 10.0) / 10.0
        + cfg.care * (colleague.skills["client_care"] - 10.0) / 10.0
    )
    success = float(draws().random()) < fx.sigmoid(logit)
    intros = tuple(sorted({**dict(rel.intro_turns), a.practice: state.turn}.items()))
    name = f"{colleague.first_name} {colleague.last_name}"
    label = data.practice(a.practice).label
    if success:
        practices = tuple(p for p in data.practice_keys if p in {*rel.practices, a.practice})
        market = with_relationship(
            state.market, replace(rel, practices=practices, intro_turns=intros)
        )
        item = inbox_item(
            state.turn,
            firm,
            "introduction_made",
            link_kind="client",
            link_id=client.id,
            name=name,
            client=client.name,
            practice=label,
        )
    else:
        market = with_relationship(
            state.market,
            replace(rel, intro_turns=intros, score=max(0.0, rel.score + cfg.failure)),
        )
        item = inbox_item(
            state.turn,
            firm,
            "introduction_failed",
            link_kind="client",
            link_id=client.id,
            name=name,
            client=client.name,
            practice=label,
        )
    return Outcome(state=replace(state, market=market), log=(item,))


def respond_settlement(
    state: GameState, a: RespondSettlement, balance: Balance, data: GameData
) -> Outcome:
    firm = acting_firm(state, a.actor_id)
    matter = _matter(state, firm, a.matter_id)
    offer = matter.settlement
    if offer is None or state.turn > offer.expires_turn:
        raise MatterActionError(f"matter {a.matter_id} has no open settlement offer")
    state = spend_energy(state, a.actor_id, "settlement", balance)
    if not a.accept:
        return Outcome(
            state=replace(state, market=with_matter(state.market, replace(matter, settlement=None)))
        )
    people = {p.id: p for p in state.people}
    market, item = settle(state.market, matter, state.turn, balance, data, people)
    return Outcome(state=replace(state, market=market), log=(item,))


def set_conflict_checks(state: GameState, a: SetConflictChecks, balance: Balance) -> Outcome:
    firm = acting_firm(state, a.actor_id)
    state = spend_energy(state, a.actor_id, "conflict_policy", balance)
    return Outcome(state=with_firm(state, replace(state.firm(firm), conflict_checks=a.enabled)))


def choose_forum(state: GameState, a: ChooseForum, balance: Balance, data: GameData) -> Outcome:
    """Forum choice (spec 7.6a): a new case may move to another of its kind's forums before
    a judge is assigned (in its intake month, by default)."""
    firm = acting_firm(state, a.actor_id)
    matter = _matter(state, firm, a.matter_id)
    kind = data.practice(matter.practice).kind(matter.kind_key)
    if a.court not in kind.forums:
        raise MatterActionError(f"{a.court!r} is not a forum for {kind.label}")
    if (
        matter.judge_id is not None
        or state.turn - matter.opened_turn > balance.matters.forum_change_turns
    ):
        raise MatterActionError("the forum can only be chosen before the case starts")
    state = spend_energy(state, a.actor_id, "forum", balance)
    old = data.courts.court(matter.court).pace if matter.court else 1.0
    new = data.courts.court(a.court).pace
    months = max(1, round(matter.planned_months * new / old))
    moved = replace(matter, court=a.court, planned_months=months)
    return Outcome(state=replace(state, market=with_matter(state.market, moved)))


def assess_case(
    state: GameState, a: AssessCase, draws: Draws, balance: Balance, data: GameData
) -> Outcome:
    """Early case assessment (spec 7.6): energy from the actor and `assessment.lead_hours`
    of the lead's non-billable time this month; the merits are revealed as a range."""
    firm = acting_firm(state, a.actor_id)
    matter = _matter(state, firm, a.matter_id)
    if data.market.kinds[matter.kind].outcome != "case":
        raise MatterActionError("only a case's merits can be assessed")
    if matter.assessment is not None:
        raise MatterActionError(f"{matter.name} has been assessed already")
    if matter.lead_id is None:
        raise MatterActionError(f"{matter.name} has no lead to assess it")
    state = spend_energy(state, a.actor_id, "case_assessment", balance)
    lead = state.person(matter.lead_id)
    lo, hi = merits_range(matter.merits, lead, float(draws().random()), balance)
    assessed = replace(matter, assessment=MeritsAssessment(turn=state.turn, lo=lo, hi=hi))
    item = inbox_item(
        state.turn,
        firm,
        "case_assessed",
        link_kind="matter",
        link_id=matter.id,
        name=f"{lead.first_name} {lead.last_name}",
        matter=matter.name,
        merits=merits_words(lo, hi),
    )
    return Outcome(state=replace(state, market=with_matter(state.market, assessed)), log=(item,))


def set_pro_bono_credit(state: GameState, a: SetProBonoCredit, balance: Balance) -> Outcome:
    firm = acting_firm(state, a.actor_id)
    if not 0 <= a.hours <= balance.pro_bono.credit_max_hours:
        raise MatterActionError(
            f"the credit policy is 0 to {balance.pro_bono.credit_max_hours} hours a year"
        )
    state = spend_energy(state, a.actor_id, "pro_bono_policy", balance)
    return Outcome(state=with_firm(state, replace(state.firm(firm), pro_bono_credit_hours=a.hours)))


def set_rate_policy(state: GameState, a: SetRatePolicy, balance: Balance) -> Outcome:
    firm = acting_firm(state, a.actor_id)
    cfg = balance.rates
    if a.rise_bp is not None and not cfg.rise_min_bp <= a.rise_bp <= cfg.rise_max_bp:
        raise MatterActionError(
            f"the yearly rise is {cfg.rise_min_bp / 100:+.0f}% to {cfg.rise_max_bp / 100:+.0f}%"
        )
    state = spend_energy(state, a.actor_id, "rate_policy", balance)
    return Outcome(state=with_firm(state, replace(state.firm(firm), rate_rise_bp=a.rise_bp)))


def set_hours_policy(state: GameState, a: SetHoursPolicy, balance: Balance) -> Outcome:
    firm = acting_firm(state, a.actor_id)
    cfg = balance.staffing
    if a.hours is not None and not cfg.policy_min_hours <= a.hours <= cfg.policy_max_hours:
        raise MatterActionError(
            f"the billable target is {cfg.policy_min_hours} to {cfg.policy_max_hours} hours a year"
        )
    state = spend_energy(state, a.actor_id, "hours_policy", balance)
    firm_state = replace(state.firm(firm), billable_target_hours=a.hours)
    return Outcome(state=with_firm(state, firm_state))


def apply_matter_action(
    state: GameState, action: MatterAction, draws: Draws, balance: Balance, data: GameData
) -> Outcome:
    match action:
        case AssignToMatter():
            return assign(state, action, balance, data)
        case SetMatterHours():
            return set_hours(state, action, balance, data)
        case RemoveFromMatter():
            return remove(state, action, balance)
        case SetMatterLead():
            return set_lead(state, action, balance, data)
        case DefaultStaffing():
            return default_staffing(state, action, balance, data)
        case SeekWaiver():
            return seek_waiver(state, action, draws, balance, data)
        case Introduce():
            return introduce(state, action, draws, balance, data)
        case RespondSettlement():
            return respond_settlement(state, action, balance, data)
        case SetConflictChecks():
            return set_conflict_checks(state, action, balance)
        case ChooseForum():
            return choose_forum(state, action, balance, data)
        case AssessCase():
            return assess_case(state, action, draws, balance, data)
        case SetProBonoCredit():
            return set_pro_bono_credit(state, action, balance)
        case SetRatePolicy():
            return set_rate_policy(state, action, balance)
        case SetHoursPolicy():
            return set_hours_policy(state, action, balance)
