"""Poaching both ways (spec 10.2, 8.7; TST formulas.md 15.6, ported).

**Rivals approach the player's people.** A rival whose utility AI picks `approach_player`
targets one of the player's lawyers in a practice it staffs (partners and senior associates
first, by book then ability; one draw chooses among the top three) and makes an offer at a
premium over their pay. At most `rivals.poach.max_per_year` approaches reach the player's
firm in any 12 months. The approach is answered in phase 1 of the next turn (stream `rival_poach`,
key `(*rival_key, ANSWER_KEY, made_turn)`): p = 1 / (1 + e^(-2 s)) with
s = 4 (R - 1) + (55 - morale) / 20 - (loyalty - 10) / 10 - 0.5. Accepted: the person gives
notice (`poached`) and joins the rival as a key person when it ends. The player can counter
before then (`CounterApproach`): a matching raise, and the approach lapses.

PT-M4's flight machinery (spec 8.7) turns a partner's monthly chance of leaving into these
same offers; until it merges, approaches come only from rivals' own decisions.

**The player approaches rivals' people.** `ApproachRival` shows 2-4 of one rival's key
people as candidates of a closed referral search (so no generic batch follows), asking
`player_ask_premium` over the market; interview and offer as for any lateral. A hire
removes them from the rival: its pool, its book (demand), its appeal on panels and its
stability (a key partner's departure counts toward the collapse hazard; history.py).
"""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np

from ptk.sim.calendar import turn_to_ym
from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import InvalidActionError
from ptk.sim.hiring.models import Candidate, Search
from ptk.sim.hiring.pay import band_cents
from ptk.sim.log import LogItem, inbox_item
from ptk.sim.people.reveal import new_reveal_state
from ptk.sim.rivals import formulas as f
from ptk.sim.rivals.decisions import add_partner, remove_lawyer
from ptk.sim.rivals.models import Approach, Member, RivalFirm, RivalsState
from ptk.sim.rivals.people import drop_member, member_kind, new_member, person_of, update_member
from ptk.sim.rng import RngFactory
from ptk.sim.state import (
    GameState,
    with_candidates,
    with_employment,
    with_reveals,
    with_search,
)

ANSWER_KEY = 0  # tunable-exempt: poach stream key part of an approach's answer
NOTICE_MONTHS = {"partner": 3, "associate": 1}  # tunable-exempt: notice periods [A]
TARGET_LEVELS = ("equity_partner", "income_partner", "counsel", "senior_associate")


def _name(p: object) -> str:
    return f"{p.first_name} {p.last_name}"  # type: ignore[attr-defined]


def approaches_last_year(rivals: RivalsState, turn: int) -> int:
    return sum(1 for a in rivals.approaches if a.made_turn > turn - 12)  # tunable-exempt: a year


def player_targets(state: GameState, data: GameData) -> list[tuple[int, str]]:
    """The player's lawyers rivals could approach, best first, with their home practice:
    partners and senior associates (never a founding partner), by book then ability."""
    ranked = []
    for e in state.staff(state.player.id):
        if e.status != "active":
            continue
        p = state.person(e.person_id)
        if p.founding_partner or p.level not in TARGET_LEVELS:  # founders: PT-M4's flight
            continue
        practice = data.role(p.role).practice
        if practice is None:
            continue
        ranked.append((-p.book_cents, -sum(v for _, v in p.skills.items), p.id, practice))
    ranked.sort()
    return [(pid, practice) for _, _, pid, practice in ranked]


def targets(state: GameState, firm: RivalFirm, pool: list[tuple[int, str]]) -> list[int]:
    """Of the pool, those in a practice the rival staffs, without an approach pending."""
    pending = {a.person_id for a in state.rivals.approaches if a.status == "pending"}
    staffed = {p.practice for p in firm.pools if p.lawyers >= 1.0}
    return [pid for pid, practice in pool if practice in staffed and pid not in pending]


def has_target(
    state: GameState, firm: RivalFirm, pool: list[tuple[int, str]], balance: Balance
) -> bool:
    if not pool:
        return False
    if approaches_last_year(state.rivals, state.turn) >= balance.rivals.poach.max_per_year:
        return False
    return bool(targets(state, firm, pool))


def pay_of(state: GameState, person_id: int, data: GameData, balance: Balance) -> int:
    e = state.employment_of(person_id)
    salary = e.salary_cents if e is not None else 0
    if salary <= 0:  # equity partners: the income-partner band until PT-M4 values partners
        salary = band_cents(data, balance, "income_partner", state.player.home_city)
    return salary


def make_approach(
    state: GameState,
    firm: RivalFirm,
    gen: np.random.Generator,
    pool: list[tuple[int, str]],
    data: GameData,
    balance: Balance,
) -> tuple[GameState, str, int | None]:
    """Draws: the target (one uniform), the premium (one uniform)."""
    pb = balance.rivals.poach
    choices = targets(state, firm, pool)[:3]
    u, prem_u = float(gen.random()), float(gen.random())
    if not choices:
        return state, "", None
    pid = choices[min(int(u * len(choices)), len(choices) - 1)]
    premium = pb.offer_premium.lo + prem_u * (pb.offer_premium.hi - pb.offer_premium.lo)
    offer = round(pay_of(state, pid, data, balance) * premium)
    rivals = state.rivals
    approach = Approach(
        id=rivals.next_approach_id,
        firm_id=firm.id,
        person_id=pid,
        offer_cents=offer,
        made_turn=state.turn,
    )
    rivals = replace(
        rivals,
        approaches=(*rivals.approaches, approach),
        next_approach_id=rivals.next_approach_id + 1,
    )
    person = state.person(pid)
    return replace(state, rivals=rivals), f"approached {_name(person)}", pid


@dataclass(frozen=True, slots=True)
class Answer:
    probability: float
    band: str


def answer_odds(state: GameState, approach: Approach, data: GameData, balance: Balance) -> Answer:
    pb = balance.rivals.poach
    person = state.person(approach.person_id)
    ratio = approach.offer_cents / max(1, pay_of(state, person.id, data, balance))
    morale = state.person_state(person.id).morale
    loyalty = person.personality["loyalty"]
    score = f.poach_score(
        ratio, 50.0 if morale is None else morale, loyalty, pb
    )  # tunable-exempt: neutral morale
    score += (person.hidden["poachability"] - pb.loyalty_mid) / pb.poachability_divisor
    p = f.poach_probability(score, pb)
    return Answer(p, f.poach_band(p, pb))


def resolve_approaches(
    state: GameState, rng: RngFactory, data: GameData, balance: Balance
) -> tuple[GameState, tuple[LogItem, ...]]:
    """Phase 1: last turn's approaches are answered (TST 15.6)."""
    logs: list[LogItem] = []
    out = []
    turn = state.turn
    for a in state.rivals.approaches:
        if a.status != "pending" or a.made_turn >= turn:
            out.append(a)
            continue
        firm = state.rivals.firm(a.firm_id)
        e = state.employment_of(a.person_id)
        if (
            firm is None
            or not firm.active
            or e is None
            or e.status != "active"
            or e.firm_id != state.player.id
        ):
            out.append(replace(a, status="lapsed", resolved_turn=turn))
            continue
        odds = answer_odds(state, a, data, balance)
        draw = float(
            rng.stream(turn, "rival_poach", *firm.rival_key, ANSWER_KEY, a.made_turn).random()
        )
        person = state.person(a.person_id)
        if draw < odds.probability:
            months = NOTICE_MONTHS[member_kind(person.level)]
            state = with_employment(
                state, replace(e, status="notice", end_turn=turn + months, end_reason="poached")
            )
            out.append(replace(a, status="accepted", resolved_turn=turn))
            logs.append(
                inbox_item(
                    turn,
                    state.player.id,
                    "rival_poached",
                    link_kind="person",
                    link_id=person.id,
                    name=_name(person),
                    firm=firm.name,
                )
            )
        else:
            out.append(replace(a, status="declined", resolved_turn=turn))
            logs.append(
                inbox_item(
                    turn,
                    state.player.id,
                    "rival_approach_declined",
                    link_kind="person",
                    link_id=person.id,
                    name=_name(person),
                    firm=firm.name,
                )
            )
    return replace(state, rivals=replace(state.rivals, approaches=tuple(out))), tuple(logs)


def counter(state: GameState, approach_id: int, balance: Balance) -> GameState:
    """The player matches a pending offer (spec 8.7's counter-offer): the person's salary
    rises to it from the next payroll and the approach lapses."""
    from ptk.sim.interfaces import set_salary

    a = next((x for x in state.rivals.approaches if x.id == approach_id), None)
    if a is None or a.status != "pending":
        raise InvalidActionError(f"no pending approach {approach_id}")
    e = state.employment_of(a.person_id)
    if e is not None and e.salary_cents > 0:
        state = set_salary(state, a.person_id, max(e.salary_cents, a.offer_cents))
    approaches = tuple(
        replace(x, status="countered", resolved_turn=state.turn) if x.id == approach_id else x
        for x in state.rivals.approaches
    )
    return replace(state, rivals=replace(state.rivals, approaches=approaches))


def join_from_player(
    state: GameState, turn: int, data: GameData
) -> tuple[GameState, tuple[LogItem, ...]]:
    """Phase 8: people whose `poached` notice ended join the rival that approached them."""
    logs: list[LogItem] = []
    rivals = state.rivals
    for a in rivals.approaches:
        if a.status != "accepted" or state.rivals.member(a.person_id) is not None:
            continue
        e = next(
            (
                x
                for x in state.employments
                if x.person_id == a.person_id and x.end_reason == "poached" and x.status == "ended"
            ),
            None,
        )
        firm = state.rivals.firm(a.firm_id)
        if e is None or firm is None:
            continue
        person = state.person(a.person_id)
        kind = member_kind(person.level)
        practice = data.role(person.role).practice or "commercial_litigation"
        member = replace(
            new_member(firm, person.id, -1, turn, practice, person.level, person.book_cents),
            outside=True,  # their record stays in GameState.people
        )
        firm = add_partner(firm, practice, equity=kind == "partner") if kind == "partner" else firm
        gain = person.book_cents * (person.portability_bp or 0) / 10_000  # tunable-exempt: bp
        firm = replace(firm, offset_cents=firm.offset_cents + gain)
        rivals = replace(
            state.rivals,
            members=tuple(sorted((*state.rivals.members, member), key=lambda m: m.person_id)),
            firms=tuple(firm if x.id == firm.id else x for x in state.rivals.firms),
        )
        state = replace(state, rivals=rivals)
        logs.append(
            inbox_item(turn, state.player.id, "rival_joined", name=_name(person), firm=firm.name)
        )
    return state, tuple(logs)


# --- The player approaches a rival's people ---------------------------------------------------


def approach_rival(
    state: GameState,
    firm_id: int,
    practice: str | None,
    actor_id: int,
    gen: np.random.Generator,
    data: GameData,
    balance: Balance,
) -> tuple[GameState, tuple[int, ...]]:
    """A closed referral search whose candidates are 2-4 of the rival's key people (the
    best partners in the practice, or overall); they move into GameState.people as
    candidates, staying the rival's key people until hired. Draws: the count."""
    pb = balance.rivals.poach
    firm = state.rivals.firm(firm_id)
    if firm is None or not firm.active:
        raise InvalidActionError(f"no active rival firm {firm_id}")
    taken = {c.person_id for c in state.candidates if c.status == "open"}
    pool = [
        m
        for m in state.rivals.members_of(firm_id)
        if (practice is None or m.practice == practice) and m.person_id not in taken
    ]
    pool.sort(key=lambda m: (m.kind != "partner", -m.book_cents, m.person_id))
    lo, hi = int(pb.candidates.lo), int(pb.candidates.hi)
    count = int(gen.integers(lo, hi + 1))
    chosen = pool[:count]
    if not chosen:
        raise InvalidActionError("that rival has no key people to approach in that practice")
    return as_candidates(state, chosen, actor_id, data, balance)


def approach_free_agents(
    state: GameState, actor_id: int, gen: np.random.Generator, data: GameData, balance: Balance
) -> tuple[GameState, tuple[int, ...]]:
    """The free agents of collapsed or failed rivals, best first, as the firm's candidates
    (up to the approach's 2-4; draws: the count)."""
    pb = balance.rivals.poach
    taken = {c.person_id for c in state.candidates if c.status == "open"}
    pool = sorted(
        (a.member for a in state.rivals.free_agents if a.person_id not in taken),
        key=lambda m: (m.kind != "partner", -m.book_cents, m.person_id),
    )
    count = int(gen.integers(int(pb.candidates.lo), int(pb.candidates.hi) + 1))
    if not pool:
        raise InvalidActionError("no free agents are looking for work")
    return as_candidates(state, pool[:count], actor_id, data, balance)


def as_candidates(
    state: GameState, chosen: list[Member], actor_id: int, data: GameData, balance: Balance
) -> tuple[GameState, tuple[int, ...]]:
    """A closed referral search (so no generic batch follows) whose candidates are these
    people, asking `player_ask_premium` over the market. Their records move into
    GameState.people; key people stay their rival's until hired."""
    pb = balance.rivals.poach
    search_id = state.next_id("search")
    role = data.practice_role(chosen[0].practice).key
    search = Search(
        id=search_id,
        firm_id=state.player.id,
        role=role,
        channel="referral",
        actor_id=actor_id,
        opened_turn=state.turn,
        status="closed",
        closed_turn=state.turn,
    )
    state = with_search(state, search)
    ym = turn_to_ym(state.turn, state.save_meta.start_ym)
    from ptk.sim.hiring.pay import market_pay_cents

    shelf = balance.hiring.candidate_shelf_turns
    cands, reveals, moved = [], [], []
    rivals = state.rivals
    for m in chosen:
        person = person_of(state, m, data, balance)
        level = "income_partner" if person.level == "equity_partner" else person.level
        market = market_pay_cents(data, balance, level, ym, state.player.home_city)
        ask = round(market * (1 + pb.player_ask_premium) / 1000) * 1000  # tunable-exempt: $1,000s
        cands.append(
            Candidate(
                person_id=person.id,
                firm_id=state.player.id,
                search_id=search_id,
                channel="referral",
                ask_cents=ask,
                created_turn=state.turn,
                expires_turn=state.turn + shelf,
            )
        )
        if state.reveal(state.player.id, person.id) is None:
            reveals.append(
                new_reveal_state(
                    observer_firm_id=state.player.id,
                    person=person,
                    turn=state.turn,
                    rng=RngFactory(state.save_meta.master_seed),
                    data=data,
                    balance=balance,
                )
            )
        if not m.outside:
            moved.append(person)
            if rivals.member(m.person_id) is not None:
                rivals = update_member(rivals, replace(m, outside=True))
            else:  # a free agent
                rivals = replace(
                    rivals,
                    free_agents=tuple(
                        replace(a, member=replace(a.member, outside=True))
                        if a.person_id == m.person_id
                        else a
                        for a in rivals.free_agents
                    ),
                )
    state = replace(state, rivals=rivals)
    if moved:
        state = replace(state, people=tuple(sorted((*state.people, *moved), key=lambda p: p.id)))
    state = with_candidates(state, cands)
    state = with_reveals(state, reveals)
    return state, tuple(c.person_id for c in cands)


def hired_by_player(
    state: GameState, month_turn: int
) -> tuple[GameState, list[tuple[RivalFirm, Member]]]:
    """Phase 8: key people now on the player's books leave their rival."""
    lost = []
    rivals = state.rivals
    player = state.player.id
    firms = {f.id: f for f in rivals.firms}
    for m in rivals.members:
        e = state.employment_of(m.person_id)
        if e is None or e.firm_id != player:
            continue
        firm = firms[m.firm_id]
        firm = remove_lawyer(firm, m.practice, m.kind == "partner")
        person = state.person(m.person_id)
        loss = m.book_cents * (person.portability_bp or 0) / 10_000  # tunable-exempt: bp
        firm = replace(
            firm,
            offset_cents=firm.offset_cents - loss,
            departures=(*firm.departures, (month_turn, 1))
            if m.kind == "partner"
            else firm.departures,
            lost_to_player=firm.lost_to_player + (1 if m.kind == "partner" else 0),
            stance=firm.stance + 1.0,
        )
        firms[firm.id] = firm
        lost.append((firm, m))
        rivals = drop_member(rivals, m.person_id)
    rivals = replace(rivals, firms=tuple(firms[k] for k in sorted(firms)))
    return replace(state, rivals=rivals), lost
