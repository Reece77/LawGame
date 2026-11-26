"""Rival key people over time (ADR PT-0008 3; ADR PT-0013 history of real people).

Phase 8, each month:
1. **Real notables' moves** (notables.yaml `moves`) happen in their month, if the person is
   still a key person of the firm the dossier has them at (conditions unchanged): a lateral
   moves them to the destination rival (if it is active; otherwise they leave the roster);
   government, the bench, in-house and leaving practice take them off the roster; a
   chair role is news.
2. **January:** associates step a class year (a senior associate three years on becomes an
   income partner); people retire: real notables the January after their `left_practice` year,
   everyone at
   `rivals.retire_age`; each firm whose key partners fall below its target makes new ones
   (stream `rival_people`, its n counting on from `people_made`).

While pinned, people moving between rivals change no demand (history's path holds them).
"""

from __future__ import annotations

from dataclasses import replace

from ptk.sim.calendar import turn_to_ym
from ptk.sim.data_models import Balance, GameData
from ptk.sim.rivals.decisions import add_partner, remove_lawyer
from ptk.sim.rivals.economy import Month
from ptk.sim.rivals.history import record, with_firm
from ptk.sim.rivals.models import RivalMove, RivalsState
from ptk.sim.rivals.people import (
    add_members,
    books,
    drop_member,
    find_person,
    move_member,
    new_member,
    person_of,
    update_member,
)
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState, with_people

JANUARY = 1  # tunable-exempt
PARTNER_AFTER_YEARS = 3  # tunable-exempt: years a key senior associate waits for partnership [A]
NEXT_LEVEL = {
    "associate_5": "associate_6",
    "associate_6": "associate_7",
    "associate_7": "senior_associate",
}


def notable_moves(state: GameState, month: Month) -> tuple[GameState, list[RivalMove]]:
    moves: list[RivalMove] = []
    ym = month.ym
    by_key = {m.notable: m for m in state.rivals.members if m.notable is not None}
    for nd in month.data.rivals.people.notables:
        for mv in nd.moves:
            if tuple(mv.ym) != ym:
                continue
            member = by_key.get(nd.key)
            if member is None:
                continue  # no longer a key person of a rival (the player hired them, or gone)
            firm = state.rivals.firm(member.firm_id)
            if firm is None:
                continue
            person = find_person(state, member.person_id, month.data, month.balance)
            name = f"{person.first_name} {person.last_name}" if person else nd.key
            rivals = state.rivals
            if mv.kind == "chair_role":
                rivals, move = record(
                    rivals,
                    firm,
                    month.turn,
                    "chair_role",
                    f"{name} takes a leadership role at {firm.name}",
                    member.person_id,
                )
            elif (
                mv.kind == "lateral"
                and mv.to is not None
                and (dest := rivals.by_key(mv.to)) is not None
                and dest.active
            ):
                rivals = move_member(rivals, member.person_id, dest.id, month.turn)
                rivals = with_firm(
                    rivals, remove_lawyer(firm, member.practice, member.kind == "partner")
                )
                rivals = with_firm(rivals, add_partner(dest, member.practice))
                rivals, move = record(
                    rivals,
                    dest,
                    month.turn,
                    "lateral_in",
                    f"{name} joins {dest.name} from {firm.name}",
                    member.person_id,
                    firm.id,
                )
            else:
                rivals = drop_member(rivals, member.person_id)
                rivals = with_firm(
                    rivals, remove_lawyer(firm, member.practice, member.kind == "partner")
                )
                words = {
                    "government": "leaves for government",
                    "judiciary": "joins the bench",
                    "in_house": "moves in-house",
                    "of_counsel": "becomes of counsel",
                    "lateral": "leaves the firm",
                }.get(mv.kind, "leaves practice")
                rivals, move = record(
                    rivals,
                    firm,
                    month.turn,
                    mv.kind,
                    f"{name} {words} ({firm.name})",
                    member.person_id,
                )
            moves.append(move)
            state = replace(state, rivals=rivals)
    return state, moves


def january(state: GameState, rng: RngFactory, month: Month) -> tuple[GameState, list[RivalMove]]:
    if month.ym[1] != JANUARY or month.turn == 0:
        return state, []
    rb = month.balance.rivals
    year = month.ym[0]
    moves: list[RivalMove] = []
    notables = {n.key: n for n in month.data.rivals.people.notables}
    rivals = state.rivals
    changed = []
    for m in rivals.members:
        person = person_of(state, m, month.data, month.balance)
        firm = rivals.firm(m.firm_id)
        nd = notables.get(m.notable) if m.notable else None
        retire = person.age(month.turn) >= rb.retire_age or (
            nd is not None and nd.left_practice is not None and nd.left_practice < year
        )
        if retire and firm is not None:
            rivals = drop_member(rivals, m.person_id)
            rivals = with_firm(rivals, remove_lawyer(firm, m.practice, m.kind == "partner"))
            rivals, move = record(
                rivals,
                firm,
                month.turn,
                "retired",
                f"{person.first_name} {person.last_name} retires from {firm.name}",
                m.person_id,
            )
            moves.append(move)
            continue
        if m.kind == "associate":
            nxt = NEXT_LEVEL.get(m.level)
            if nxt is not None:
                rivals = update_member(rivals, replace(m, level=nxt))
            elif year - turn_to_ym(m.since_turn, month.start)[0] >= PARTNER_AFTER_YEARS:
                rivals = update_member(rivals, replace(m, level="income_partner", kind="partner"))
            if m.outside and (nxt or person.level) != person.level:
                changed.append(replace(person, level=nxt or person.level))
    state = with_people(replace(state, rivals=rivals), changed)
    state = _replenish(state, rng, month)
    return state, moves


def _replenish(state: GameState, rng: RngFactory, month: Month) -> GameState:
    rb = month.balance.rivals
    rivals = state.rivals
    counts: dict[int, int] = {}
    for m in rivals.members:
        if m.kind == "partner":
            counts[m.firm_id] = counts.get(m.firm_id, 0) + 1
    for firm in rivals.active:
        need = firm.key_target - counts.get(firm.id, 0)
        if need <= 0:
            continue
        members = []
        pid = rivals.next_person_id
        n = firm.people_made
        # PT-M12: key partners go to the practices the firm has lawyers in (twenty practices
        # leave a specialist with many empty pools)
        practices = sorted(
            [p for p in firm.pools if p.lawyers > 0] or list(firm.pools),
            key=lambda p: (-p.lawyers, p.practice),
        )
        book = books(firm.demand_cents * rb.key_book_share, firm.key_target, rb.book_pareto)[-1]
        for i in range(need):
            practice = practices[i % len(practices)].practice
            members.append(new_member(firm, pid, n, month.turn, practice, "equity_partner", book))
            pid += 1
            n += 1
        rivals = add_members(rivals, members)
        rivals = with_firm(rivals, replace(rivals.firm(firm.id) or firm, people_made=n))
    return replace(state, rivals=rivals)


def free_agents_expire(rivals: RivalsState, turn: int) -> RivalsState:
    return replace(rivals, free_agents=tuple(a for a in rivals.free_agents if a.until_turn >= turn))


_UNUSED = (Balance, GameData)
