"""PT-M17's player actions (ADR-0014): the personal account, the foundation, bar politics,
the family, the retirement age and annuities, and succession. Each is taken by the player
(the firm's founding partner, or their successor) at once, spending energy from
`founder_life.energy`. Personal entries go to the founder-life state's `pending`, which the
save writes with the action (and the next turn carries for in-memory runs).

Partner Track's own, after TST's founder and family actions (`tst/sim/founder/`,
`tst/sim/family/answers.py` @ 121d318a): the choices TST asked as events are actions here.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Literal

import numpy as np

from ptk.sim import interfaces as ix
from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import FamilyError, FounderLifeError, InsufficientEnergyError, SuccessionError
from ptk.sim.family import estate, succession
from ptk.sim.family.models import CHILD, with_family_record, with_member
from ptk.sim.family.phase import head_active
from ptk.sim.founder import foundation
from ptk.sim.founder.config import LAW_SCHOOLS, SCHOOLS
from ptk.sim.founder.models import (
    EDUCATION,
    FAMILY_OFFICE,
    INVESTMENTS,
    PERSONAL_CASH,
    AnnuityTerms,
    FounderLifeState,
    PersonalEntry,
    with_book,
    with_life,
)
from ptk.sim.founder.phase import ensure_player
from ptk.sim.founder.retirement import terms as annuity_terms
from ptk.sim.hiring.actions import Outcome
from ptk.sim.log import LogItem, inbox_item
from ptk.sim.money import BP_DENOMINATOR
from ptk.sim.people.models import Employment
from ptk.sim.state import GameState, with_employment, with_people, with_person_states

type Draws = Any  # Callable[[], np.random.Generator]
CENTS_A_DOLLAR = 100  # tunable-exempt: cents in a dollar
FIRST_YEAR = "associate_1"  # a child who qualifies joins as a first-year associate
LAW_TIER = {"top": "t14", "standard": "national"}  # law school to the generator's tiers


@dataclass(frozen=True, slots=True)
class CreateFoundation:
    actor_id: int
    cause: str
    name: str = ""
    kind: Literal["create_foundation"] = "create_foundation"


@dataclass(frozen=True, slots=True)
class GiveToFoundation:
    actor_id: int
    amount_cents: int
    kind: Literal["give_to_foundation"] = "give_to_foundation"


@dataclass(frozen=True, slots=True)
class Invest:
    """Move personal cash into (positive) or out of (negative) investments."""

    actor_id: int
    amount_cents: int
    kind: Literal["invest"] = "invest"


@dataclass(frozen=True, slots=True)
class FamilyOffice:
    """Form or fund the family office (positive), withdraw (negative), set its mandate."""

    actor_id: int
    mandate: str
    amount_cents: int = 0
    kind: Literal["family_office"] = "family_office"


@dataclass(frozen=True, slots=True)
class BarCommittee:
    actor_id: int
    on: bool
    kind: Literal["bar_committee"] = "bar_committee"


@dataclass(frozen=True, slots=True)
class BarSpend:
    actor_id: int
    monthly_cents: int
    kind: Literal["bar_spend"] = "bar_spend"


@dataclass(frozen=True, slots=True)
class StandForOffice:
    actor_id: int
    kind: Literal["stand_for_office"] = "stand_for_office"


@dataclass(frozen=True, slots=True)
class PlanSuccession:
    """Name a successor-designate (the succession plan, spec 2.5); None clears it."""

    actor_id: int
    person_id: int | None
    kind: Literal["plan_succession"] = "plan_succession"


@dataclass(frozen=True, slots=True)
class NameSuccessor:
    """Hand over: the partnership votes on the successor this month (spec 2.5)."""

    actor_id: int
    person_id: int
    kind: Literal["name_successor"] = "name_successor"


@dataclass(frozen=True, slots=True)
class ProposeRetirementAge:
    actor_id: int
    age: int
    kind: Literal["propose_retirement_age"] = "propose_retirement_age"


@dataclass(frozen=True, slots=True)
class ProposeAnnuities:
    """A vote on the agreement's annuity term (spec 8.6): share_bp 0 ends them."""

    actor_id: int
    share_bp: int
    years: int
    kind: Literal["propose_annuities"] = "propose_annuities"


@dataclass(frozen=True, slots=True)
class SetFamilyTime:
    actor_id: int
    energy: int
    kind: Literal["set_family_time"] = "set_family_time"


@dataclass(frozen=True, slots=True)
class ChooseEducation:
    actor_id: int
    child_id: int
    stage: Literal["school", "law_school"]
    tier: str
    kind: Literal["choose_education"] = "choose_education"


@dataclass(frozen=True, slots=True)
class JoinFirm:
    actor_id: int
    child_id: int
    kind: Literal["join_firm"] = "join_firm"


@dataclass(frozen=True, slots=True)
class Mentor:
    actor_id: int
    child_id: int
    on: bool
    kind: Literal["mentor"] = "mentor"


@dataclass(frozen=True, slots=True)
class GiftToChild:
    actor_id: int
    child_id: int
    amount_cents: int
    kind: Literal["gift_to_child"] = "gift_to_child"


@dataclass(frozen=True, slots=True)
class SetUpTrust:
    actor_id: int
    amount_cents: int
    kind: Literal["set_up_trust"] = "set_up_trust"


type FounderAction = (
    CreateFoundation
    | GiveToFoundation
    | Invest
    | FamilyOffice
    | BarCommittee
    | BarSpend
    | StandForOffice
    | PlanSuccession
    | NameSuccessor
    | ProposeRetirementAge
    | ProposeAnnuities
    | SetFamilyTime
    | ChooseEducation
    | JoinFirm
    | Mentor
    | GiftToChild
    | SetUpTrust
)

FOUNDER_ACTION_TYPES: dict[str, type[Any]] = {
    "create_foundation": CreateFoundation,
    "give_to_foundation": GiveToFoundation,
    "invest": Invest,
    "family_office": FamilyOffice,
    "bar_committee": BarCommittee,
    "bar_spend": BarSpend,
    "stand_for_office": StandForOffice,
    "plan_succession": PlanSuccession,
    "name_successor": NameSuccessor,
    "propose_retirement_age": ProposeRetirementAge,
    "propose_annuities": ProposeAnnuities,
    "set_family_time": SetFamilyTime,
    "choose_education": ChooseEducation,
    "join_firm": JoinFirm,
    "mentor": Mentor,
    "gift_to_child": GiftToChild,
    "set_up_trust": SetUpTrust,
}

ENERGY: dict[str, str | None] = {
    "create_foundation": "foundation",
    "give_to_foundation": "gift",
    "invest": "invest",
    "family_office": "family_office",
    "bar_committee": None,  # its energy is taken each month (`phase.month_start`)
    "bar_spend": None,
    "stand_for_office": "stand",
    "plan_succession": "plan",
    "name_successor": "successor",
    "propose_retirement_age": "plan",
    "propose_annuities": "plan",
    "set_family_time": None,
    "choose_education": "education",
    "join_firm": None,
    "mentor": "mentor",
    "gift_to_child": "gift_heir",
    "set_up_trust": "trust",
}


def _spend(state: GameState, actor: int, kind: str, balance: Balance) -> GameState:
    key = ENERGY[kind]
    if key is None:
        return state
    cost: int = getattr(balance.founder_life.energy, key)
    ps = state.person_state(actor)
    if ps.energy is None or cost == 0:
        return state
    if ps.energy < cost:
        raise InsufficientEnergyError(f"{kind} needs {cost} energy; {ps.energy} left this month")
    return with_person_states(state, [replace(ps, energy=ps.energy - cost)])


def _pend(
    fl: FounderLifeState, entries: tuple[PersonalEntry, ...] | list[PersonalEntry]
) -> FounderLifeState:
    return replace(fl, pending=(*fl.pending, *entries))


def apply_founder_action(
    state: GameState, action: FounderAction, draws: Draws, balance: Balance, data: GameData
) -> Outcome:
    a = action
    you = state.founder_of(state.player.id)
    if you is None or a.actor_id != you:
        raise FounderLifeError("only the player's own partner acts on their life")
    state, opened = ensure_player(state, balance)
    if opened:
        state = replace(state, founder_life=_pend(state.founder_life, opened))
    state = _spend(state, you, a.kind, balance)
    fl = state.founder_life
    book = fl.book(you)
    life = fl.life(you)
    assert book is not None and life is not None
    turn = state.turn
    logs: list[LogItem] = []
    firm = state.player.id
    if isinstance(a, CreateFoundation):
        fl = foundation.create(fl, you, state.person(you).last_name, a.name, a.cause, turn, balance)
        f = fl.foundation(you)
        assert f is not None
        logs.append(
            inbox_item(
                turn,
                firm,
                "foundation_created",
                link_kind=None,
                name=f.name,
                cause=foundation.CAUSE_WORDS[f.cause],
            )
        )
    elif isinstance(a, GiveToFoundation):
        fl = foundation.give(fl, you, a.amount_cents, turn)
    elif isinstance(a, Invest):
        if a.amount_cents == 0:
            raise FounderLifeError("an amount is needed")
        if a.amount_cents > book.cash or -a.amount_cents > book.bal(INVESTMENTS):
            raise FounderLifeError("not enough to move")
        e = (
            PersonalEntry.transfer(
                turn, you, "Investments", "invest", INVESTMENTS, PERSONAL_CASH, a.amount_cents
            )
            if a.amount_cents > 0
            else PersonalEntry.transfer(
                turn, you, "Investments sold", "invest", PERSONAL_CASH, INVESTMENTS, -a.amount_cents
            )
        )
        fl = _pend(with_book(fl, book.posted((e,))), (e,))
    elif isinstance(a, FamilyOffice):
        cfg = balance.founder_life.family_office
        if a.mandate not in cfg.mandates:
            raise FounderLifeError(f"a mandate is one of {', '.join(sorted(cfg.mandates))}")
        if book.mandate is None and book.net_worth < cfg.min_cents:
            raise FounderLifeError(
                f"a family office needs ${cfg.min_cents // CENTS_A_DOLLAR:,} of personal wealth"
            )
        if a.amount_cents > book.cash or -a.amount_cents > book.bal(FAMILY_OFFICE):
            raise FounderLifeError("not enough to move")
        book = replace(book, mandate=a.mandate)
        entries: list[PersonalEntry] = []
        if a.amount_cents > 0:
            entries.append(
                PersonalEntry.transfer(
                    turn,
                    you,
                    "Into the family office",
                    "invest",
                    FAMILY_OFFICE,
                    PERSONAL_CASH,
                    a.amount_cents,
                )
            )
        elif a.amount_cents < 0:
            entries.append(
                PersonalEntry.transfer(
                    turn,
                    you,
                    "From the family office",
                    "invest",
                    PERSONAL_CASH,
                    FAMILY_OFFICE,
                    -a.amount_cents,
                )
            )
        fl = _pend(with_book(fl, book.posted(entries)), entries)
    elif isinstance(a, BarCommittee):
        fl = with_life(fl, replace(life, committee=a.on))
    elif isinstance(a, BarSpend):
        cap = balance.founder_life.influence.max_monthly_dollars * CENTS_A_DOLLAR
        if not 0 <= a.monthly_cents <= cap:
            raise FounderLifeError(f"bar politics spend is $0-${cap // CENTS_A_DOLLAR:,} a month")
        fl = with_life(fl, replace(life, bar_spend_cents=a.monthly_cents))
    elif isinstance(a, StandForOffice):
        if life.influence < balance.founder_life.influence.office_at:
            raise FounderLifeError("you need more standing in the bar to stand for office")
        fl = with_life(fl, replace(life, standing=True))
    elif isinstance(a, PlanSuccession):
        if a.person_id is not None and a.person_id not in succession.candidates(state):
            raise SuccessionError("a successor-designate is another equity partner")
        fl = with_life(fl, replace(life, successor_plan=a.person_id))
    elif isinstance(a, NameSuccessor):
        trigger = fl.due_trigger or "choice"
        state = succession.name_successor(state, a.person_id, trigger, balance)
        fl = state.founder_life
    elif isinstance(a, ProposeRetirementAge):
        if ix.managing_partner(state, firm) != you:
            raise SuccessionError("only the managing partner proposes the agreement's terms")
        if not 55 <= a.age <= 80:  # tunable-exempt: PT-M4's agreement bounds
            raise SuccessionError("the retirement age must be 55-80")
        if a.age == ix.retirement_age(state, firm, balance):
            raise SuccessionError(f"the retirement age is already {a.age}")
        if any(
            k == "terms" and t == "retirement_age" for _, k, t in ix.open_vote_kinds(state, firm)
        ):
            raise SuccessionError("the same vote is already open")
        state, _ = ix.open_partnership_vote(
            state, firm, "terms", None, {"term": "retirement_age", "value": a.age}
        )
        fl = state.founder_life
    elif isinstance(a, ProposeAnnuities):
        state, fl, logs = _annuity_vote(state, a, draws, balance)
    else:
        state, fl, more = _family_action(state, a, you, draws, balance, data)
        logs += more
    return Outcome(replace(state, founder_life=fl), (), tuple(logs))


def _annuity_vote(
    state: GameState, a: ProposeAnnuities, draws: Draws, balance: Balance
) -> tuple[GameState, FounderLifeState, list[LogItem]]:
    """A vote on the annuity term, counted at once (the partners' confidence and PT-M4's
    status-quo bias for any term, plus how near each is to retiring: older partners favour
    annuities, younger ones pay for them). Noise from the action's stream."""
    firm = state.player.id
    cfg = balance.founder_life.annuity
    if ix.managing_partner(state, firm) != a.actor_id:
        raise SuccessionError("only the managing partner proposes the agreement's terms")
    if not 0 <= a.share_bp <= cfg.max_share_bp or not 1 <= a.years <= 30:  # tunable-exempt
        raise SuccessionError(f"annuities are 0-{cfg.max_share_bp} bp for 1-30 years")
    now = annuity_terms(state, balance)
    new = AnnuityTerms(a.share_bp > 0, a.share_bp, a.years)
    if (now.granted, now.share_bp if now.granted else 0, now.years) == (
        new.granted,
        new.share_bp,
        new.years,
    ):
        raise SuccessionError("the agreement already says that")
    gen: np.random.Generator = draws()
    weight, bias = ix.terms_bias(balance)
    sd = balance.partnership.votes.noise_sd
    yes = no = 0.0
    limit = ix.retirement_age(state, firm, balance)
    for pid in ix.equity_partner_ids(state, firm):
        w = ix.vote_weight(state, firm, pid)
        noise = float(gen.normal(0.0, sd))
        if pid == a.actor_id:
            ok = True
        else:
            conf = ix.partner_confidence(state, firm, pid) or 50.0
            age = state.person(pid).age(state.turn)
            near = (age - (limit - 15)) / 15  # tunable-exempt: a partner's last 15 years
            u = weight * (conf - 50) / 50 + bias + near * (1 if new.granted else -1)
            ok = u + noise > 0
        yes, no = (yes + w, no) if ok else (yes, no + w)
    threshold = ix.terms_threshold_bp(state, firm, balance)
    passed = yes + no > 0 and yes * BP_DENOMINATOR >= threshold * (yes + no)
    fl = state.founder_life
    if passed:
        fl = replace(fl, annuity_terms=new)
    log = inbox_item(
        state.turn,
        firm,
        "annuity_vote",
        link_kind="partnership",
        result="passed" if passed else "failed",
        yes=f"{yes:g}",
        no=f"{no:g}",
    )
    return state, fl, [log]


def _child(state: GameState, child_id: int) -> tuple[int, str]:
    m = state.family.member(child_id)
    if m is None or m.relation != CHILD:
        raise FamilyError("that is not one of your children")
    return child_id, m.relation


def _family_action(
    state: GameState,
    a: FounderAction,
    you: int,
    draws: Draws,
    balance: Balance,
    data: GameData,
) -> tuple[GameState, FounderLifeState, list[LogItem]]:
    fb = balance.family
    if state.family.family is None:
        raise FamilyError("you have no family in this game")
    if not head_active(state):
        raise FamilyError("your family is your predecessor's")
    fl = state.founder_life
    book = fl.book(you)
    assert book is not None
    turn = state.turn
    logs: list[LogItem] = []
    family = state.family.family
    assert family is not None
    if isinstance(a, SetFamilyTime):
        if not 0 <= a.energy <= fb.max_time:
            raise FamilyError(f"family time is 0-{fb.max_time} energy a month")
        state = replace(
            state, family=with_family_record(state.family, replace(family, family_time=a.energy))
        )
    elif isinstance(a, ChooseEducation):
        _child(state, a.child_id)
        m = state.family.member(a.child_id)
        assert m is not None
        age = state.person(a.child_id).age(turn)
        ed = fb.education
        if a.stage == "school":
            if a.tier not in SCHOOLS or not ed.school_age <= age < ed.law_school_age:
                raise FamilyError(f"school is chosen from {ed.school_age} ({', '.join(SCHOOLS)})")
            cost = ed.cents["elite_school"] if a.tier == "elite" else 0
            m = replace(m, school=a.tier)
        else:
            if a.tier not in LAW_SCHOOLS or not ed.law_school_age <= age < ed.qualify_age:
                raise FamilyError(
                    f"law school is chosen from {ed.law_school_age} ({', '.join(LAW_SCHOOLS)})"
                )
            cost = ed.cents.get(f"law_{a.tier}", 0)
            m = replace(m, law_school=a.tier)
        if cost > book.cash:
            raise FamilyError("the fees are more than your personal cash")
        entries = []
        if cost:
            entries.append(
                PersonalEntry.transfer(
                    turn, you, "School fees", "education", EDUCATION, PERSONAL_CASH, cost
                )
            )
        fl = _pend(with_book(fl, book.posted(entries)), entries)
        state = replace(state, family=with_member(state.family, m))
    elif isinstance(a, JoinFirm):
        _child(state, a.child_id)
        state = _join(state, a.child_id, balance, data)
        p = state.person(a.child_id)
        logs.append(
            inbox_item(
                turn,
                state.player.id,
                "family_joined_firm",
                link_kind="person",
                link_id=p.id,
                name=f"{p.first_name} {p.last_name}",
            )
        )
    elif isinstance(a, Mentor):
        _child(state, a.child_id)
        m = state.family.member(a.child_id)
        assert m is not None
        if a.on and state.employer_of(a.child_id) != state.player.id:
            raise FamilyError("you mentor a child who works at the firm")
        state = replace(state, family=with_member(state.family, replace(m, mentored=a.on)))
    elif isinstance(a, GiftToChild):
        _child(state, a.child_id)
        book, fs, entries2 = estate.gift_to_heir(
            book, state.family, a.child_id, a.amount_cents, turn, state.save_meta.start_ym, balance
        )
        fl = _pend(with_book(fl, book), entries2)
        state = replace(state, family=fs)
    elif isinstance(a, SetUpTrust):
        book, fs, entries3 = estate.set_up_trust(book, state.family, a.amount_cents, turn, balance)
        fl = _pend(with_book(fl, book), entries3)
        state = replace(state, family=fs)
    else:  # pragma: no cover - every action is handled above
        raise FamilyError(f"unknown action {a.kind!r}")
    return state, fl, logs


def _join(state: GameState, child_id: int, balance: Balance, data: GameData) -> GameState:
    """A qualified child (law school, at the qualifying age) joins the firm as a first-year
    associate on the firm's scale (spec 2.4), if close enough to the player to want to."""
    from ptk.sim.calendar import turn_to_ym
    from ptk.sim.family.setup import jurisdiction
    from ptk.sim.hiring.pay import firm_pay_cents

    fb = balance.family
    m = state.family.member(child_id)
    person = state.person(child_id)
    assert m is not None
    if state.employment_of(child_id) is not None:
        raise FamilyError("they already work at a firm")
    if m.law_school in (None, "none") or person.age(state.turn) < fb.education.qualify_age:
        raise FamilyError(f"a child joins once qualified (law school, {fb.education.qualify_age})")
    if m.closeness < fb.join_closeness:
        raise FamilyError("they would rather make their own way")
    firm = state.firm(state.player.id)
    salary = firm_pay_cents(
        data,
        balance,
        FIRST_YEAR,
        turn_to_ym(state.turn, state.save_meta.start_ym),
        firm.home_city,
        firm.pay_policy,
    )
    tier = LAW_TIER.get(m.law_school or "", "regional")
    state = with_people(
        state,
        [
            replace(
                person,
                level=FIRST_YEAR,
                school_tier=tier,
                bar_admissions=(jurisdiction(state, data),),
            )
        ],
    )
    e = Employment(state.next_id("employment"), child_id, firm.id, state.turn, salary_cents=salary)
    state = with_employment(state, e)
    ps = state.person_state(child_id)
    state = with_person_states(state, [replace(ps, morale=balance.morale.start)])
    fs = with_member(state.family, replace(m, joined_firm_turn=state.turn, seen_level=FIRST_YEAR))
    return replace(state, family=fs)
