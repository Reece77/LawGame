"""Founder and Family endpoints (PT-M17; spec 2.2-2.5, 16's screens; TST 32.8, 45.9).

The player's own partner as they see themselves: persona traits and their causes, the
personal account (balances, the year's income statement, recent entries), the foundation, bar
politics, the legacy score with its parts, retirement and annuities, and succession (the
candidates with the predicted vote as a range, the plan, the record of every person played).
The family: members' public facts and the player's view of them (ranges, the potential as a
phrase), closeness, education, the relationship, the estate-tax quote and planning.

Hidden values never leave the engine (CLAUDE.md section 10): partners' confidence, vote
utilities, family members' potential and hidden traits, the draws behind life events.
Writes are one action each (`saves.run_action`).
"""

from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ptk import loader
from ptk.config import get_settings
from ptk.db import saves
from ptk.sim import interfaces as ix
from ptk.sim.calendar import format_turn
from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import NotFoundError
from ptk.sim.family import estate, succession
from ptk.sim.family.models import CHILD
from ptk.sim.family.phase import head_active
from ptk.sim.founder import actions as fa
from ptk.sim.founder import influence, legacy, persona
from ptk.sim.founder.config import CAUSES, LAW_SCHOOLS, SCHOOLS, TRAITS
from ptk.sim.founder.foundation import CAUSE_WORDS
from ptk.sim.founder.models import (
    CAPITAL_LOAN,
    ENDOWMENT,
    FAMILY_OFFICE,
    FIRM_CAPITAL,
    INVESTMENTS,
    PERSONAL_CASH,
    TRUST,
    PersonalEntry,
)
from ptk.sim.founder.personal import income_statement
from ptk.sim.founder.retirement import terms as annuity_terms
from ptk.sim.people.formulas import current_ability, potential_phrase
from ptk.sim.people.models import PA_KEY
from ptk.sim.people.reveal import revealed_range
from ptk.sim.state import GameState

YEAR = 12  # tunable-exempt: months in the income statement


class BandOut(BaseModel):
    lo: float
    hi: float


class TraitOut(BaseModel):
    key: str
    value: int
    strong: bool  # at the effect line


class CauseOut(BaseModel):
    when: str
    trait: str
    change: float
    why: str


class StatementOut(BaseModel):
    draws_cents: int
    true_up_cents: int
    annuity_cents: int
    tax_cents: int
    after_tax_cents: int  # draws + true-up - tax
    gains_cents: int


class EntryOut(BaseModel):
    when: str
    memo: str
    cash_cents: int  # the entry's effect on personal cash (0: none)


class PersonalOut(BaseModel):
    cash_cents: int
    investments_cents: int
    family_office_cents: int
    mandate: str | None
    trust_cents: int
    firm_capital_cents: int
    loan_cents: int
    net_worth_cents: int
    endowment_cents: int
    year: StatementOut  # the last 12 months
    lifetime: StatementOut
    recent: list[EntryOut]
    family_office_min_cents: int
    mandates: list[str]


class FoundationOut(BaseModel):
    name: str
    cause: str
    cause_label: str
    endowment_cents: int
    grants_cents: int
    last_grant_cents: int
    gifts_cents: int


class InfluenceOut(BaseModel):
    value: int
    committee: bool
    spend_cents: int
    standing: bool
    in_office: bool
    office_until: str | None
    can_stand: bool
    max_spend_cents: int


class LegacyOut(BaseModel):
    total: int
    firm: int
    name_on_door: int
    giving: int
    persona: int
    family: int
    bar: int


class SuccessorCandidateOut(BaseModel):
    person_id: int
    name: str
    practice: str
    age: int
    rating: BandOut  # as the firm sees them (1-20)
    is_child: bool
    predicted_yes: BandOut  # vote weight for them, as a range
    total_weight: float
    needed_weight: float
    rival_name: str | None  # PT-M4's rival nominee against them


class SuccessionOut(BaseModel):
    turn: str
    trigger: str
    founder: str
    successor: str
    result: str


class PlayedOut(BaseModel):
    person_id: int
    name: str
    status: str
    since: str
    until: str | None


class AnnuityOut(BaseModel):
    person_id: int
    name: str
    monthly_cents: int
    remaining_cents: int


class OpinionOut(BaseModel):
    when: str
    adviser: str
    title: str
    stance: str
    text: str
    overruled: bool


class FounderOut(BaseModel):
    person_id: int
    name: str
    age: int
    status: str
    is_mp: bool
    energy: int | None
    retirement_age: int
    years_to_retirement: float
    plan_from_age: int
    persona_traits: list[TraitOut]
    public_words: str
    causes: list[CauseOut]
    personal: PersonalOut
    foundation: FoundationOut | None
    foundation_min_cents: int
    causes_available: list[str]
    influence: InfluenceOut
    legacy: LegacyOut
    annuities_granted: bool
    annuity_share_bp: int
    annuity_years: int
    annuities: list[AnnuityOut]
    annuities_owed_cents: int
    plan_id: int | None
    candidates: list[SuccessorCandidateOut]
    due: str | None  # a successor must be named by this month
    due_trigger: str | None
    open_succession: bool
    ousted: bool  # lost the MP election (ADR PT-0007 3): hand over without a vote
    successions: list[SuccessionOut]
    played: list[PlayedOut]
    opinions: list[OpinionOut]


class MemberOut(BaseModel):
    person_id: int
    name: str
    relation: str
    age: int
    closeness: int | None  # a child's
    school: str | None
    law_school: str | None
    at_firm: bool
    level: str | None
    ability: BandOut  # as the player sees them (TST 45.3)
    potential: str  # a phrase, never the number
    can_choose_school: bool
    can_choose_law_school: bool
    can_join: bool
    mentored: bool


class EstateOut(BaseModel):
    estate_cents: int
    exemption_cents: int
    rate_bp: int
    tax_cents: int
    lifetime_gifts_cents: int
    trust_cents: int


class NoteOut(BaseModel):
    when: str
    text: str


class FamilyOut(BaseModel):
    setting: str
    active: bool  # the player heads it (a successor plays without the founder's family)
    family_time: int
    max_time: int
    relationship: int | None
    married: bool
    members: list[MemberOut]
    estate: EstateOut | None
    notes: list[NoteOut]
    schools: list[str]
    law_schools: list[str]


def _path(slug: str) -> Path:
    return saves.open_save(get_settings().resolved_save_dir(), slug)


def _label(state: GameState, turn: int) -> str:
    return format_turn(turn, state.save_meta.start_ym)


def _name(state: GameState, pid: int) -> str:
    p = state.person(pid)
    return f"{p.first_name} {p.last_name}"


def _stmt(entries: tuple[PersonalEntry, ...], pid: int, since: int = 0) -> StatementOut:
    s = income_statement(entries, pid, since)
    return StatementOut(
        draws_cents=s.draws_cents,
        true_up_cents=s.true_up_cents,
        annuity_cents=s.annuity_cents,
        tax_cents=s.tax_cents,
        after_tax_cents=s.after_tax_cents,
        gains_cents=s.gains_cents,
    )


def _rating(state: GameState, pid: int, data: GameData) -> BandOut:
    person = state.person(pid)
    reveal = state.reveal(state.player.id, pid)
    role = data.role(person.role)
    if reveal is None:
        return BandOut(lo=1, hi=20)
    lows = [revealed_range(person, reveal, k)[0] for k in role.primary]
    highs = [revealed_range(person, reveal, k)[1] for k in role.primary]
    return BandOut(lo=round(sum(lows) / len(lows), 1), hi=round(sum(highs) / len(highs), 1))


def founder_view(
    state: GameState, entries: tuple[PersonalEntry, ...], balance: Balance, data: GameData
) -> FounderOut:
    firm = state.player.id
    you = state.founder_of(firm)
    if you is None:
        raise NotFoundError("the firm has no player partner")
    fl = state.founder_life
    life = fl.life(you) or persona.new_life(you, state.turn, balance)
    book = fl.book(you)
    pb = balance.founder_life.persona

    def bal(account: str) -> int:
        return book.bal(account) if book is not None else 0

    recent = [e for e in entries if e.person_id == you][-balance.founder_life.personal.history :]
    personal = PersonalOut(
        cash_cents=bal(PERSONAL_CASH),
        investments_cents=bal(INVESTMENTS),
        family_office_cents=bal(FAMILY_OFFICE),
        mandate=book.mandate if book is not None else None,
        trust_cents=bal(TRUST),
        firm_capital_cents=bal(FIRM_CAPITAL),
        loan_cents=-bal(CAPITAL_LOAN),
        net_worth_cents=book.net_worth if book is not None else 0,
        endowment_cents=bal(ENDOWMENT),
        year=_stmt(entries, you, state.turn - YEAR),
        lifetime=_stmt(entries, you),
        recent=[
            EntryOut(
                when=_label(state, e.turn),
                memo=e.memo,
                cash_cents=sum(ln.amount for ln in e.lines if ln.account == PERSONAL_CASH),
            )
            for e in reversed(recent)
        ],
        family_office_min_cents=balance.founder_life.family_office.min_cents,
        mandates=sorted(balance.founder_life.family_office.mandates),
    )
    f = fl.foundation(you)
    found = (
        FoundationOut(
            name=f.name,
            cause=f.cause,
            cause_label=CAUSE_WORDS[f.cause],
            endowment_cents=bal(ENDOWMENT),
            grants_cents=f.grants_cents,
            last_grant_cents=f.last_grant_cents,
            gifts_cents=f.gifts_cents,
        )
        if f is not None
        else None
    )
    ib = balance.founder_life.influence
    infl = InfluenceOut(
        value=round(life.influence),
        committee=life.committee,
        spend_cents=life.bar_spend_cents,
        standing=life.standing,
        in_office=influence.in_office(life, state.turn),
        office_until=_label(state, life.office_until_turn)
        if life.office_until_turn is not None and influence.in_office(life, state.turn)
        else None,
        can_stand=life.influence >= ib.office_at,
        max_spend_cents=ib.max_monthly_dollars * 100,  # tunable-exempt: cents in a dollar
    )
    lg = legacy.legacy_of(state, you, balance)
    t = annuity_terms(state, balance)
    is_mp = ix.managing_partner(state, firm) == you
    cands = []
    if is_mp or ix.ousted_founder(state, firm):
        for pid in succession.candidates(state):
            pred = succession.predict(state, pid, balance, data)
            m = state.family.member(pid)
            cands.append(
                SuccessorCandidateOut(
                    person_id=pid,
                    name=_name(state, pid),
                    practice=data.role(state.person(pid).role).label,
                    age=state.person(pid).age(state.turn),
                    rating=_rating(state, pid, data),
                    is_child=m is not None and m.relation == CHILD,
                    predicted_yes=BandOut(lo=pred.yes_lo, hi=pred.yes_hi),
                    total_weight=pred.total,
                    needed_weight=pred.needed,
                    rival_name=_name(state, pred.rival_id) if pred.rival_id is not None else None,
                )
            )
    last = fl.last_succession
    years = succession.years_to_retirement(state, balance) or 0.0
    return FounderOut(
        person_id=you,
        name=_name(state, you),
        age=state.person(you).age(state.turn),
        status=life.status,
        is_mp=is_mp,
        energy=state.person_state(you).energy,
        retirement_age=ix.retirement_age(state, firm, balance),
        years_to_retirement=round(years, 1),
        plan_from_age=balance.succession.plan_from_age,
        persona_traits=[
            TraitOut(key=k, value=round(life.trait(k)), strong=life.trait(k) >= pb.effect_at)
            for k in TRAITS
        ],
        public_words=persona.public_words(life, balance),
        causes=[
            CauseOut(when=_label(state, c[0]), trait=c[1], change=round(c[2], 1), why=c[3])
            for c in reversed(life.causes)
        ],
        personal=personal,
        foundation=found,
        foundation_min_cents=balance.founder_life.foundation.min_cents,
        causes_available=list(CAUSES),
        influence=infl,
        legacy=LegacyOut(
            total=lg.total,
            firm=round(lg.firm),
            name_on_door=round(lg.name_on_door),
            giving=round(lg.giving),
            persona=round(lg.persona),
            family=round(lg.family),
            bar=round(lg.bar),
        ),
        annuities_granted=t.granted,
        annuity_share_bp=t.share_bp,
        annuity_years=t.years,
        annuities=[
            AnnuityOut(
                person_id=a.person_id,
                name=_name(state, a.person_id),
                monthly_cents=a.monthly_cents,
                remaining_cents=a.remaining_cents,
            )
            for a in fl.annuities
        ],
        annuities_owed_cents=sum(a.remaining_cents for a in fl.annuities),
        plan_id=life.successor_plan,
        candidates=cands,
        due=_label(state, fl.retirement_due_turn) if fl.retirement_due_turn is not None else None,
        due_trigger=fl.due_trigger,
        open_succession=last is not None and last.result == "open",
        ousted=ix.ousted_founder(state, firm),
        successions=[
            SuccessionOut(
                turn=_label(state, s.turn),
                trigger=s.trigger,
                founder=_name(state, s.founder_id),
                successor=_name(state, s.successor_id),
                result=s.result,
            )
            for s in fl.successions
        ],
        played=[
            PlayedOut(
                person_id=x.person_id,
                name=_name(state, x.person_id),
                status=x.status,
                since=_label(state, x.since_turn),
                until=_label(state, x.until_turn) if x.until_turn is not None else None,
            )
            for x in sorted(fl.lives, key=lambda x: (x.since_turn, x.person_id))
        ],
        opinions=[
            OpinionOut(
                when=_label(state, o.turn),
                adviser=_name(state, o.adviser_id),
                title=o.title,
                stance=o.stance,
                text=o.text,
                overruled=o.overruled,
            )
            for o in reversed(fl.opinions)
        ],
    )


def family_view(state: GameState, balance: Balance, data: GameData) -> FamilyOut:
    fs = state.family
    family = fs.family
    if family is None:
        return FamilyOut(
            setting="none",
            active=False,
            family_time=0,
            max_time=balance.family.max_time,
            relationship=None,
            married=False,
            members=[],
            estate=None,
            notes=[],
            schools=list(SCHOOLS),
            law_schools=list(LAW_SCHOOLS),
        )
    fb = balance.family
    ed = fb.education
    members = []
    for m in fs.members:
        p = state.person(m.person_id)
        role = data.role(p.role)
        reveal = state.reveal(state.player.id, p.id)
        if reveal is not None:
            lows = {k: float(revealed_range(p, reveal, k)[0]) for k in role.skills}
            highs = {k: float(revealed_range(p, reveal, k)[1]) for k in role.skills}
            ability = BandOut(
                lo=math.floor(current_ability(lows, role.primary, role.secondary)),
                hi=math.ceil(current_ability(highs, role.primary, role.secondary)),
            )
            pa_lo, pa_hi = revealed_range(p, reveal, PA_KEY)
            pot = potential_phrase(pa_lo, pa_hi, balance.reveal.pa_phrase_bounds)
        else:
            ability, pot = BandOut(lo=1, hi=200), "unknown"
        age = p.age(state.turn)
        child = m.relation == CHILD
        e = state.employment_of(p.id)
        members.append(
            MemberOut(
                person_id=p.id,
                name=f"{p.first_name} {p.last_name}",
                relation=m.relation,
                age=age,
                closeness=round(m.closeness) if child else None,
                school=m.school,
                law_school=m.law_school,
                at_firm=e is not None and e.firm_id == state.player.id,
                level=p.level if e is not None else None,
                ability=ability,
                potential=pot,
                can_choose_school=child and ed.school_age <= age < ed.law_school_age,
                can_choose_law_school=child and ed.law_school_age <= age < ed.qualify_age,
                can_join=child
                and e is None
                and m.law_school not in (None, "none")
                and age >= ed.qualify_age,
                mentored=m.mentored,
            )
        )
    you = state.founder_of(state.player.id)
    book = state.founder_life.book(family.head_id)
    quote = (
        estate.quote(book, fs, state.turn, state.save_meta.start_ym, balance)
        if book is not None
        else None
    )
    del you
    return FamilyOut(
        setting=family.setting,
        active=head_active(state),
        family_time=family.family_time,
        max_time=fb.max_time,
        relationship=round(family.relationship)
        if any(m.relation == "partner" for m in fs.members)
        else None,
        married=family.married,
        members=members,
        estate=EstateOut(
            estate_cents=quote.estate_cents,
            exemption_cents=quote.exemption_cents,
            rate_bp=round(quote.rate * 10_000),  # tunable-exempt: a rate in bp
            tax_cents=quote.tax_cents,
            lifetime_gifts_cents=family.lifetime_gifts_cents,
            trust_cents=book.bal(TRUST) if book is not None else 0,
        )
        if quote is not None
        else None,
        notes=[NoteOut(when=_label(state, n.turn), text=n.text) for n in reversed(family.notes)],
        schools=list(SCHOOLS),
        law_schools=list(LAW_SCHOOLS),
    )


def _entries(path: Path, person_id: int | None = None) -> tuple[PersonalEntry, ...]:
    from ptk.db.founder_io import personal_entries
    from ptk.db.session import make_sessionmaker, shared_engine

    with make_sessionmaker(shared_engine(path))() as session:
        return personal_entries(session, person_id)


def _founder(path: Path) -> FounderOut:
    state, _ = saves.read_state(path)
    you = state.founder_of(state.player.id)
    return founder_view(state, _entries(path, you), loader.balance(), loader.game_data())


def _family(path: Path) -> FamilyOut:
    state, _ = saves.read_state(path)
    return family_view(state, loader.balance(), loader.game_data())


def _act(slug: str, make: Any) -> Path:
    path = _path(slug)
    state = saves.read_state(path)[0]
    actor = state.founder_of(state.player.id)
    if actor is None:
        raise NotFoundError("the firm has no player partner")
    action: fa.FounderAction = make(actor)
    saves.run_action(path, action, loader.balance(), loader.game_data())
    return path


class CauseIn(BaseModel):
    cause: str
    name: str = ""


class FounderAmountIn(BaseModel):
    amount_cents: int


class OfficeIn(BaseModel):
    mandate: str
    amount_cents: int = 0


class OnIn(BaseModel):
    on: bool


class SpendIn(BaseModel):
    monthly_cents: int = Field(ge=0)


class SuccessionPlanIn(BaseModel):
    person_id: int | None


class SuccessorIn(BaseModel):
    person_id: int


class AgeIn(BaseModel):
    age: int


class AnnuityIn(BaseModel):
    share_bp: int
    years: int


class TimeIn(BaseModel):
    energy: int


class EducationIn(BaseModel):
    child_id: int
    stage: Literal["school", "law_school"]
    tier: str


class ChildIn(BaseModel):
    child_id: int


class MentorIn(BaseModel):
    child_id: int
    on: bool


class GiftIn(BaseModel):
    child_id: int
    amount_cents: int


def make_founder_router(errors: dict[int | str, dict[str, Any]]) -> APIRouter:
    router = APIRouter()
    base = "/api/saves/{slug}/founder"
    fam = "/api/saves/{slug}/family"
    kw: dict[str, Any] = {"response_model": FounderOut, "responses": errors}
    kf: dict[str, Any] = {"response_model": FamilyOut, "responses": errors}

    @router.get(base, operation_id="getFounder", **kw)
    def get_founder(slug: str) -> FounderOut:
        return _founder(_path(slug))

    @router.post(f"{base}/foundation", operation_id="createFoundation", **kw)
    def create_foundation(slug: str, body: CauseIn) -> FounderOut:
        return _founder(_act(slug, lambda a: fa.CreateFoundation(a, body.cause, body.name)))

    @router.post(f"{base}/foundation/gift", operation_id="giveToFoundation", **kw)
    def give(slug: str, body: FounderAmountIn) -> FounderOut:
        return _founder(_act(slug, lambda a: fa.GiveToFoundation(a, body.amount_cents)))

    @router.post(f"{base}/invest", operation_id="invest", **kw)
    def invest(slug: str, body: FounderAmountIn) -> FounderOut:
        return _founder(_act(slug, lambda a: fa.Invest(a, body.amount_cents)))

    @router.post(f"{base}/family-office", operation_id="familyOffice", **kw)
    def office(slug: str, body: OfficeIn) -> FounderOut:
        return _founder(_act(slug, lambda a: fa.FamilyOffice(a, body.mandate, body.amount_cents)))

    @router.post(f"{base}/bar/committee", operation_id="barCommittee", **kw)
    def committee(slug: str, body: OnIn) -> FounderOut:
        return _founder(_act(slug, lambda a: fa.BarCommittee(a, body.on)))

    @router.post(f"{base}/bar/spend", operation_id="barSpend", **kw)
    def spend(slug: str, body: SpendIn) -> FounderOut:
        return _founder(_act(slug, lambda a: fa.BarSpend(a, body.monthly_cents)))

    @router.post(f"{base}/bar/stand", operation_id="standForOffice", **kw)
    def stand(slug: str) -> FounderOut:
        return _founder(_act(slug, lambda a: fa.StandForOffice(a)))

    @router.post(f"{base}/succession/plan", operation_id="planSuccession", **kw)
    def plan(slug: str, body: SuccessionPlanIn) -> FounderOut:
        return _founder(_act(slug, lambda a: fa.PlanSuccession(a, body.person_id)))

    @router.post(f"{base}/succession/name", operation_id="nameSuccessor", **kw)
    def name_successor(slug: str, body: SuccessorIn) -> FounderOut:
        return _founder(_act(slug, lambda a: fa.NameSuccessor(a, body.person_id)))

    @router.post(f"{base}/retirement-age", operation_id="proposeRetirementAge", **kw)
    def retirement(slug: str, body: AgeIn) -> FounderOut:
        return _founder(_act(slug, lambda a: fa.ProposeRetirementAge(a, body.age)))

    @router.post(f"{base}/annuities", operation_id="proposeAnnuities", **kw)
    def annuities(slug: str, body: AnnuityIn) -> FounderOut:
        return _founder(_act(slug, lambda a: fa.ProposeAnnuities(a, body.share_bp, body.years)))

    @router.get(fam, operation_id="getFamily", **kf)
    def get_family(slug: str) -> FamilyOut:
        return _family(_path(slug))

    @router.post(f"{fam}/time", operation_id="setFamilyTime", **kf)
    def family_time(slug: str, body: TimeIn) -> FamilyOut:
        return _family(_act(slug, lambda a: fa.SetFamilyTime(a, body.energy)))

    @router.post(f"{fam}/education", operation_id="chooseEducation", **kf)
    def education(slug: str, body: EducationIn) -> FamilyOut:
        return _family(
            _act(slug, lambda a: fa.ChooseEducation(a, body.child_id, body.stage, body.tier))
        )

    @router.post(f"{fam}/join", operation_id="joinFirm", **kf)
    def join(slug: str, body: ChildIn) -> FamilyOut:
        return _family(_act(slug, lambda a: fa.JoinFirm(a, body.child_id)))

    @router.post(f"{fam}/mentor", operation_id="mentorChild", **kf)
    def mentor(slug: str, body: MentorIn) -> FamilyOut:
        return _family(_act(slug, lambda a: fa.Mentor(a, body.child_id, body.on)))

    @router.post(f"{fam}/gift", operation_id="giftToChild", **kf)
    def gift(slug: str, body: GiftIn) -> FamilyOut:
        return _family(_act(slug, lambda a: fa.GiftToChild(a, body.child_id, body.amount_cents)))

    @router.post(f"{fam}/trust", operation_id="setUpTrust", **kf)
    def trust(slug: str, body: FounderAmountIn) -> FamilyOut:
        return _family(_act(slug, lambda a: fa.SetUpTrust(a, body.amount_cents)))

    if os.environ.get("PTK_DEBUG_ROUTES") == "1":
        router.include_router(_debug_router(errors))
    return router


# --- Test-only routes (PTK_DEBUG_ROUTES=1; the e2e suite) ------------------------------------


class AgeDebugIn(BaseModel):
    years: int
    months: int = 0


def _debug_router(errors: dict[int | str, dict[str, Any]]) -> APIRouter:
    router = APIRouter()

    @router.post(
        "/api/saves/{slug}/debug/founder-age",
        response_model=FounderOut,
        responses=errors,
        operation_id="debugFounderAge",
        include_in_schema=False,
    )
    def founder_age(slug: str, body: AgeDebugIn) -> FounderOut:
        """Set the player's age (e2e: retire the founder at 65 without playing 15 years)."""
        from dataclasses import replace

        from ptk.db.session import make_sessionmaker, shared_engine
        from ptk.db.state_io import load_state, write_people
        from ptk.sim.state import with_people

        path = _path(slug)
        with make_sessionmaker(shared_engine(path))() as session, session.begin():
            state = load_state(session)
            you = state.founder_of(state.player.id)
            if you is None:
                raise NotFoundError("no player partner")
            p = state.person(you)
            birth = state.turn - YEAR * body.years - body.months
            write_people(session, with_people(state, [replace(p, birth_turn=birth)]))
        return _founder(path)

    return router
