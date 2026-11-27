"""PT-M5's work in the turn pipeline (spec 4.1). Each function is called by one phase of
`ptk.sim.turn`; each returns the new state plus what the turn records.

- phase 1, `answer_approaches`: rivals' approaches made last month are answered;
- phase 2, `decide`: every active rival's month (economy.py, decisions.py; stream
  `rival_firm`), its ledger entry, and the panel appeal table intake reads;
- phase 4, `rfps_before_intake` (awards, then new RFPs) and `after_intake` (opposing
  counsel for last month's new cases; stream `opposing`, key `(matter_id,)`);
- phase 8, `people`: key people the player hired leave their rival, people the player lost
  join theirs, notables' real moves, January's roster;
- phase 9, `market`: dated history, collapse hazards, boutiques, December's year records.
"""

from __future__ import annotations

from dataclasses import dataclass

from ptk.sim.data_models import Balance, GameData
from ptk.sim.fastcopy import replace
from ptk.sim.ledger import LedgerEntry
from ptk.sim.log import LogItem, inbox_item
from ptk.sim.rivals import boutiques, history, poaching, rfp, roster
from ptk.sim.rivals.decisions import apply_simple, choose, with_cooldown
from ptk.sim.rivals.economy import Month, book_month, january, price_levels, update_demand
from ptk.sim.rivals.market import appeal_table
from ptk.sim.rivals.models import RivalFirm, RivalMove, YearRecord
from ptk.sim.rivals.people import find_person, key_people
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState

DECEMBER = 12  # tunable-exempt
MOVES_KEPT = 24  # tunable-exempt: months of moves kept in the state (the decision log keeps all)
STANCE_DECAY = 0.95  # tunable-exempt: a rival's grievance fades by 5% a month
STANCE_FLOOR = 0.01  # tunable-exempt: below this it is gone
CASE_KINDS = frozenset({"case", "investigation"})  # tunable-exempt: as PT-M3a's
REAL_SHARE = 0.6  # tunable-exempt: share of cases where a named rival is opposing counsel [A]
OPPOSING_BLEND = 0.5  # tunable-exempt: weight of the rival team's craft in opposing quality [A]


@dataclass(frozen=True, slots=True)
class Phase:
    state: GameState
    entries: tuple[LedgerEntry, ...] = ()
    log: tuple[LogItem, ...] = ()
    moves: tuple[RivalMove, ...] = ()


def month_of(state: GameState, data: GameData, balance: Balance) -> Month:
    return Month(turn=state.turn, start=state.save_meta.start_ym, data=data, balance=balance)


def enabled(state: GameState) -> bool:
    return bool(state.rivals.firms)


def answer_approaches(state: GameState, rng: RngFactory, data: GameData, balance: Balance) -> Phase:
    if not enabled(state):
        return Phase(state)
    state, logs = poaching.resolve_approaches(state, rng, data, balance)
    return Phase(state, log=logs)


def decide(state: GameState, rng: RngFactory, data: GameData, balance: Balance) -> Phase:
    if not enabled(state):
        return Phase(state)
    month = month_of(state, data, balance)
    entries: list[LedgerEntry] = []
    moves: list[RivalMove] = []
    logs: list[LogItem] = []
    firms = {f.id: f for f in state.rivals.firms}
    next_move = state.rivals.next_move_id
    pool = poaching.player_targets(state, data)  # the player's people rivals may approach
    from ptk.sim.geo.cities import rival_region

    # PT-M18: the market's price level in each firm's terms, from the month's opening rates
    levels = price_levels(state.rivals.active, month, lambda f: rival_region(data, f.hq))
    for firm_id in [f.id for f in state.rivals.active]:
        firm = firms[firm_id]
        gen = rng.stream(month.turn, "rival_firm", *firm.rival_key)
        firm = january(firm, month)
        firm = update_demand(firm, float(gen.standard_normal()), month, levels[firm_id])
        target = poaching.has_target(state, firm, pool, balance, data)
        for choice in choose(firm, month, gen, target):
            firm = with_cooldown(firm, choice.action, month)
            person_id = None
            if choice.action == "approach_player":
                state, words, person_id = poaching.make_approach(
                    state, firm, gen, pool, data, balance
                )
                if person_id is None:
                    continue
                offer = state.rivals.approaches[-1].offer_cents
                who = state.person(person_id)
                logs.append(
                    inbox_item(
                        month.turn,
                        state.player.id,
                        "rival_approach",
                        link_kind="person",
                        link_id=person_id,
                        name=f"{who.first_name} {who.last_name}",
                        firm=firm.name,
                        offer_cents=offer,
                    )
                )
            elif choice.action == "lift_team":
                words = "looked for a team to lift"  # free play only; the lift is a hire here
                firm, _ = apply_simple(firm, "hire_lateral", month)
            else:
                firm, words = apply_simple(firm, choice.action, month)
            moves.append(
                RivalMove(id=next_move, firm_id=firm.id, turn=month.turn, action=choice.action,
                          detail=f"{firm.name} {words}", person_id=person_id)
            )  # fmt: skip
            next_move += 1
        books = book_month(firm, month)
        firms[firm.id] = books.firm
        if books.entry is not None:
            entries.append(books.entry)
    rivals = replace(
        state.rivals,
        firms=tuple(firms[k] for k in sorted(firms)),
        moves=(*state.rivals.moves, *moves),
        next_move_id=next_move,
    )
    state = replace(state, rivals=appeal_table(rivals, data, balance))
    return Phase(state, entries=tuple(entries), log=tuple(logs), moves=tuple(moves))


def rfps_before_intake(
    state: GameState, rng: RngFactory, data: GameData, balance: Balance
) -> Phase:
    if not enabled(state):
        return Phase(state)
    state, awarded = rfp.award_due(state, rng, data, balance)
    state, opened = rfp.open_rfps(state, rng, data, balance)
    return Phase(state, log=(*awarded, *opened))


def after_intake(state: GameState, rng: RngFactory, data: GameData, balance: Balance) -> Phase:
    """Opposing counsel for last month's new cases (spec 7.6: Q_them is a named rival's team
    when a real rival represents the other side, else a pool)."""
    if not enabled(state):
        return Phase(state)
    known = dict(state.rivals.opposing)
    lit = [f for f in state.rivals.active if f.kind == "real" and f.ny_office]
    weights = [
        f.pool("commercial_litigation").lawyers + f.pool("white_collar").lawyers for f in lit
    ]
    total = sum(weights)
    new: list[tuple[int, str]] = []
    matters = []
    for m in state.market.matters:
        if (
            m.kind not in CASE_KINDS
            or m.id in known
            or m.opened_turn >= state.turn
            or not m.is_open
        ):
            matters.append(m)
            continue
        gen = rng.stream(state.turn, "opposing", m.id)
        u, v = float(gen.random()), float(gen.random())
        m_lit, m_weights, m_total = lit, weights, total
        client = state.market.client(m.client_id)
        if client.city:  # PT-M11: a local case's other side is a firm of its region
            m_lit, m_weights, m_total = _local_litigators(state, client.city, data)
        if u >= REAL_SHARE or m_total <= 0:
            new.append((m.id, ""))
            matters.append(m)
            continue
        x = v * m_total
        firm = m_lit[-1]
        for f, w in zip(m_lit, m_weights, strict=True):
            if x < w:
                firm = f
                break
            x -= w
        q = team_craft(state, firm, data, balance)
        blended = (1 - OPPOSING_BLEND) * m.opposing_quality + OPPOSING_BLEND * q
        matters.append(replace(m, opposing_quality=min(20.0, max(1.0, blended))))
        new.append((m.id, firm.key))
    if not new:
        return Phase(state)
    opposing = tuple(sorted((*state.rivals.opposing, *new)))
    market = replace(state.market, matters=tuple(matters))
    return Phase(replace(state, market=market, rivals=replace(state.rivals, opposing=opposing)))


def _local_litigators(
    state: GameState, city: str, data: GameData
) -> tuple[list[RivalFirm], list[float], float]:
    """PT-M11: real firms of a city's region, weighted by their litigators."""
    from ptk.sim.geo.cities import region_of_city, rival_region

    region = region_of_city(data, city)
    lit = [
        f for f in state.rivals.active if f.kind == "real" and rival_region(data, f.hq) == region
    ]
    weights = [
        f.pool("commercial_litigation").lawyers + f.pool("white_collar").lawyers for f in lit
    ]
    return lit, weights, sum(weights)


def team_craft(state: GameState, firm: RivalFirm, data: GameData, balance: Balance) -> float:
    """A rival's trial team: its three best key litigators' advocacy and reasoning."""
    scores = sorted(
        (
            (p.skills["advocacy"] + p.skills["legal_reasoning"]) / 2
            for m, p in key_people(state, firm.id, data, balance)
            if m.practice in ("commercial_litigation", "white_collar", "ip")
        ),
        reverse=True,
    )[:3]
    return sum(scores) / len(scores) if scores else 12.0  # tunable-exempt: a pool's craft [A]


def people(state: GameState, rng: RngFactory, data: GameData, balance: Balance) -> Phase:
    if not enabled(state):
        return Phase(state)
    month = month_of(state, data, balance)
    state, lost = poaching.hired_by_player(state, month.turn)
    moves: list[RivalMove] = []
    for firm, m in lost:
        person = find_person(state, m.person_id, data, balance)
        name = f"{person.first_name} {person.last_name}" if person else "a partner"
        rivals, move = history.record(
            state.rivals,
            firm,
            month.turn,
            "lost_to_player",
            f"{name} leaves {firm.name} for {state.player.name}",
            m.person_id,
        )
        state = replace(state, rivals=rivals)
        moves.append(move)
    state, joined = poaching.join_from_player(state, month.turn, data)
    state, notable = roster.notable_moves(state, month)
    state, yearly = roster.january(state, rng, month)
    state = replace(state, rivals=roster.free_agents_expire(state.rivals, month.turn))
    return Phase(state, log=joined, moves=(*moves, *notable, *yearly))


def market(state: GameState, rng: RngFactory, data: GameData, balance: Balance) -> Phase:
    if not enabled(state):
        return Phase(state)
    month = month_of(state, data, balance)
    state, dated = history.dated_events(state, rng, month)
    state, fallen = history.collapse_hazard(state, rng, month)
    state, founded = boutiques.found(state, rng, month)
    rivals = state.rivals
    december = month.ym[1] == DECEMBER
    firms = []
    for f in rivals.firms:
        if f.departures and f.departures[0][0] <= month.turn - history.YEAR:
            f = history.prune_departures(f, month.turn)
        if f.stance:
            f = replace(f, stance=f.stance * STANCE_DECAY if f.stance > STANCE_FLOOR else 0.0)
        if december and f.active:
            f = year_record(f, month.ym[0])
        firms.append(f)
    stance = tuple(firms)
    keep_from = month.turn - MOVES_KEPT
    rivals = replace(
        rivals,
        firms=stance,
        moves=tuple(m for m in rivals.moves if m.turn > keep_from),
    )
    rivals = rfp.prune(rivals, month.turn)
    return Phase(replace(state, rivals=rivals), moves=(*dated, *fallen, *founded))


def year_record(firm: RivalFirm, year: int) -> RivalFirm:
    eq = max(firm.equity_partners, 1.0)
    rec = YearRecord(
        year=year,
        revenue_cents=firm.revenue_12m,
        lawyers=round(firm.lawyers),
        equity_partners=round(firm.equity_partners),
        pep_cents=round(firm.profit_12m / eq),
    )
    return replace(firm, history=(*firm.history, rec))
