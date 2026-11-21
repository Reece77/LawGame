"""The family's month (TST formulas.md 45.1-45.3), run in phase 10 after the founder's
month. Nothing runs without a family (Family none), so those games are unchanged; nothing
runs while the head is not the player or is flagged real (ADR PT-0013: no life events for a
real person).

Ported from backend/tst/sim/family/phase.py @ 121d318a (Tech Startup Tycoon); changed:
family time eases the head's strain (Partner Track's stress, ADR PT-0006); the partner,
marriage (automatic after `marriage_months`), children and milestones as TST's; divorce
takes `divorce_share` of the personal book's liquid assets (no shares); a child at the firm
is promoted on merit and the partnership notices nepotism (spec 2.4: partner confidence);
the health step-back is succession's (`ptk.sim.family.succession`); no family-control check,
adviser board seats or dynasty.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Final

from ptk.sim.calendar import MONTHS_PER_YEAR
from ptk.sim.data_models import Balance, GameData
from ptk.sim.family.models import (
    CHILD,
    EX_PARTNER,
    PARTNER,
    FamilyMember,
    note,
    with_family_record,
    with_member,
)
from ptk.sim.family.people import (
    DEV_KEY,
    bond_mult,
    develop,
    education_mult,
    family_stream,
    narrow_view,
)
from ptk.sim.family.setup import add_child, add_partner
from ptk.sim.founder.models import (
    DIVORCE,
    FAMILY_OFFICE,
    INVESTMENTS,
    PERSONAL_CASH,
    PersonalEntry,
    with_book,
    with_life,
)
from ptk.sim.founder.persona import raise_trait
from ptk.sim.interfaces import candidate_rating, confidence_change
from ptk.sim.log import LogItem, inbox_item
from ptk.sim.people.formulas import clamp_strain
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState, with_person

SCORE_MAX: Final = 100.0  # tunable-exempt: relationship and closeness are 0-100
EVENT_PARTNER: Final = 0  # stream family's (head_id, 0, k) life-event kinds
EVENT_CHILD: Final = 1


def head_active(state: GameState) -> bool:
    """The family's systems run while its head is the player and is not real."""
    family = state.family.family
    if family is None:
        return False
    player = state.founder_of(state.player.id)
    return player == family.head_id and not state.person(family.head_id).real


def partner(state: GameState) -> FamilyMember | None:
    return next((m for m in state.family.members if m.relation == PARTNER), None)


def children(state: GameState) -> tuple[FamilyMember, ...]:
    family = state.family.family
    if family is None:
        return ()
    kids = [m for m in state.family.members if m.relation == CHILD]
    return tuple(sorted(kids, key=lambda m: (state.person(m.person_id).birth_turn, m.person_id)))


def bond_delta(time: int, burnt: bool, balance: Balance) -> float:
    """TST 45.2: bond x (time - pivot) / pivot, within +-bond, less burnout_strain."""
    fb = balance.family
    raw = fb.bond * (time - fb.bond_pivot) / fb.bond_pivot
    delta = max(-fb.bond, min(fb.bond, raw))
    return delta - (fb.burnout_strain if burnt else 0.0)


def family_month(
    state: GameState, rng: RngFactory, balance: Balance, data: GameData
) -> tuple[GameState, tuple[PersonalEntry, ...], tuple[LogItem, ...]]:
    if not head_active(state):
        return state, (), ()
    family = state.family.family
    assert family is not None
    fb = balance.family
    head = state.person(family.head_id)
    logs: list[LogItem] = []
    entries: list[PersonalEntry] = []
    time = family.family_time
    if time:
        calm = fb.calm * time / fb.max_time
        state = with_person(state, replace(head, strain=clamp_strain(head.strain - calm)))
        head = state.person(head.id)
    delta = bond_delta(time, head.burnt_out, balance)
    if partner(state) is not None:
        state, more_e, more = _relationship(state, delta, balance)
        entries += more_e
        logs += more
    for m in children(state):
        state = _child_month(state, m, delta, time, rng, balance, data)
        state, more = _milestones(state, state.family.member(m.person_id) or m, balance)
        logs += more
    state, more = _life_events(state, rng, balance, data)
    logs += more
    return state, tuple(entries), tuple(logs)


def _relationship(
    state: GameState, delta: float, balance: Balance
) -> tuple[GameState, list[PersonalEntry], list[LogItem]]:
    fb = balance.family
    family = state.family.family
    assert family is not None
    rel = max(0.0, min(SCORE_MAX, family.relationship + delta))
    low = family.low_months + 1 if rel < fb.divorce_below else 0
    family = replace(family, relationship=rel, low_months=low)
    state = replace(state, family=with_family_record(state.family, family))
    if low < fb.divorce_months:
        return state, [], []
    return _divorce(state, balance)


def _divorce(
    state: GameState, balance: Balance
) -> tuple[GameState, list[PersonalEntry], list[LogItem]]:
    """TST 45.2: the partner leaves with `divorce_share` of the personal book's cash,
    investments and family office; Beloved falls; History records it."""
    fb = balance.family
    family = state.family.family
    p = partner(state)
    assert family is not None and p is not None
    head = family.head_id
    fl = state.founder_life
    book = fl.book(head)
    entries: list[PersonalEntry] = []
    if book is not None:
        for account in (PERSONAL_CASH, INVESTMENTS, FAMILY_OFFICE):
            share = round(max(0, book.bal(account)) * fb.divorce_share)
            if share:
                e = PersonalEntry.transfer(
                    state.turn, head, "Divorce settlement", "divorce", DIVORCE, account, share
                )
                entries.append(e)
                book = book.posted((e,))
        fl = with_book(fl, book)
    life = fl.life(head)
    if life is not None:
        fl = with_life(
            fl, raise_trait(life, "beloved", -fb.divorce_beloved, "a divorce", state.turn, balance)
        )
    family = note(
        replace(family, relationship=0.0, low_months=0, married=False, partner_since=None),
        state.turn,
        "divorce",
        "The marriage ended in divorce",
        fb.history,
    )
    fs = with_member(
        with_family_record(state.family, family),
        replace(p, relation=EX_PARTNER, left_turn=state.turn),
    )
    state = replace(state, family=fs, founder_life=fl)
    log = inbox_item(state.turn, state.player.id, "family_divorce", link_kind=None)
    return state, entries, [log]


def _child_month(
    state: GameState,
    m: FamilyMember,
    delta: float,
    time: int,
    rng: RngFactory,
    balance: Balance,
    data: GameData,
) -> GameState:
    fb = balance.family
    closeness = m.closeness + delta + (fb.mentor_closeness if m.mentored else 0.0)
    m = replace(m, closeness=max(0.0, min(SCORE_MAX, closeness)))
    person = state.person(m.person_id)
    employed = state.employment_of(m.person_id) is not None
    if not employed:  # phase 8 grows them once they work at a firm
        age = person.age(state.turn)
        if age >= fb.develop_from:
            gen = family_stream(rng, state.turn, m.person_id, DEV_KEY)
            e = education_mult(m, age, balance)
            state = with_person(state, develop(person, gen, e, bond_mult(m.closeness), balance))
    else:
        if m.mentored:
            lead = person.skills["leadership"]
            state = with_person(
                state,
                replace(
                    person, skills=person.skills.updated({"leadership": lead + fb.mentor_growth})
                ),
            )
        state, m = _promotion(state, m, balance, data)
    state = replace(state, family=with_member(state.family, m))
    return narrow_view(state, m.person_id, fb.reveal_rate * time / fb.max_time, balance)


def _promotion(
    state: GameState, m: FamilyMember, balance: Balance, data: GameData
) -> tuple[GameState, FamilyMember]:
    """Spec 2.4 (TST 45.4's staff reactions, applied to partner confidence): when a child at
    the firm moves up a level, partners compare them (as the firm sees them) with the others
    at that level: below the median is nepotism, above it merit."""
    person = state.person(m.person_id)
    if m.seen_level is None or m.seen_level == person.level:
        return state, replace(m, seen_level=person.level)
    firm = state.player.id
    peers = [
        candidate_rating(state, firm, pid, data)
        for pid in state.staff_ids(firm)
        if pid != person.id and state.person(pid).level == person.level
    ]
    mine = candidate_rating(state, firm, person.id, data)
    if peers:
        peers.sort()
        median = peers[len(peers) // 2]
        fb = balance.family
        points = fb.nepotism_confidence if mine < median else fb.merit_confidence
        state = confidence_change(state, firm, points)
    return state, replace(m, seen_level=person.level)


def _milestones(
    state: GameState, m: FamilyMember, balance: Balance
) -> tuple[GameState, list[LogItem]]:
    fb = balance.family
    person = state.person(m.person_id)
    age = person.age(state.turn)
    logs: list[LogItem] = []
    for at in fb.milestones:
        if at > age or at in m.milestones:
            continue
        m = replace(m, milestones=(*m.milestones, at))
        state = replace(state, family=with_member(state.family, m))
        logs.append(
            inbox_item(
                state.turn,
                state.player.id,
                "family_milestone",
                link_kind=None,
                name=f"{person.first_name} {person.last_name}",
                age=at,
            )
        )
    return state, logs


def _life_events(
    state: GameState, rng: RngFactory, balance: Balance, data: GameData
) -> tuple[GameState, list[LogItem]]:
    fb = balance.family
    family = state.family.family
    assert family is not None
    head = state.person(family.head_id)
    turn = state.turn
    age = head.age(turn)
    logs: list[LogItem] = []
    p = partner(state)
    if p is None:
        if (
            fb.partner_ages.lo <= age <= fb.partner_ages.hi
            and head.strain < fb.partner_strain_below
        ):
            u = float(family_stream(rng, turn, head.id, 0, EVENT_PARTNER).random())
            if u < fb.partner_rate / MONTHS_PER_YEAR:
                state, person = add_partner(state, head, rng, balance, data)
                logs.append(
                    inbox_item(
                        turn,
                        state.player.id,
                        "family_partner_met",
                        link_kind=None,
                        name=f"{person.first_name} {person.last_name}",
                    )
                )
        return state, logs
    since = family.partner_since if family.partner_since is not None else turn
    if not family.married and turn - since >= fb.marriage_months:
        family = note(replace(family, married=True), turn, "married", "Married", fb.history)
        state = replace(state, family=with_family_record(state.family, family))
        logs.append(inbox_item(turn, state.player.id, "family_married", link_kind=None))
    spouse = state.person(p.person_id)
    if spouse.age(turn) < fb.child_parent_age_max and len(children(state)) < fb.max_children:
        u = float(family_stream(rng, turn, head.id, 0, EVENT_CHILD).random())
        if u < fb.child_rate / MONTHS_PER_YEAR:
            state, child = add_child(state, (head, spouse), 0, rng, balance, data)
            logs.append(
                inbox_item(
                    turn,
                    state.player.id,
                    "family_child_born",
                    link_kind=None,
                    name=f"{child.first_name} {child.last_name}",
                )
            )
    return state, logs
