"""History's dated events and collapses (spec 10.3; ADR PT-0008 2).

Each firms.yaml event happens in its month **unless the player has changed its conditions**:
- a **merger** is called off if either side has collapsed or lost at least
  `collapse.merger_calloff_share` of its key partners in the last 12 months;
- a **collapse** happens on its date if the firm is still active; it comes **forward** when
  the firm's key partners leave faster than history had them. Each month an active firm
  rolls a hazard (stream `rival_fate`, key `(*rival_key,)`, one uniform, then the scatter's
  draws if it collapses): p = (base_bp + slope_bp x 100 x max(0, d - threshold)) / 10,000,
  where d is the share of its key partners who left in the last 12 months, times 1 inside
  the 36 months before a dated collapse and `collapse.other_mult` x the personality's
  fragility otherwise;
- an **absorption** moves `share` of the firm's people to the absorbing firm on its date;
- a **rename** or an **outside merger** (a merger with a firm the game does not model)
  changes the name; an outside merger also adds the lawyers its path's step shows.

A collapse scatters the firm's key people: `share` to an absorbing firm, a share to the
player's market as free agents, the rest to the largest active rivals with the practice. Its
key leaves every client panel (an absorbing firm takes its seats).
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np
from simcore.kernel.calendar import ym_to_turn

from ptk.sim.data_models import Balance, GameData
from ptk.sim.log import LogItem
from ptk.sim.matters.models import MarketState
from ptk.sim.rivals import streams
from ptk.sim.rivals.data import HistoryEventDef
from ptk.sim.rivals.decisions import grow
from ptk.sim.rivals.economy import Month
from ptk.sim.rivals.models import (
    REAL_KEY,
    FreeAgent,
    HistoryDone,
    Pool,
    RivalFirm,
    RivalMove,
    RivalsState,
    RivalStatus,
)
from ptk.sim.rivals.path import build_path, path_value, time_of
from ptk.sim.state import GameState
from ptk.sim.streams import RngFactory

YEAR = 12  # tunable-exempt: months


def record(
    rivals: RivalsState,
    firm: RivalFirm,
    turn: int,
    action: str,
    detail: str,
    person_id: int | None = None,
    other: int | None = None,
) -> tuple[RivalsState, RivalMove]:
    move = RivalMove(
        id=rivals.next_move_id,
        firm_id=firm.id,
        turn=turn,
        action=action,
        detail=detail,
        person_id=person_id,
        other_firm_id=other,
    )
    return replace(rivals, moves=(*rivals.moves, move), next_move_id=rivals.next_move_id + 1), move


def with_firm(rivals: RivalsState, firm: RivalFirm) -> RivalsState:
    others = [f for f in rivals.firms if f.id != firm.id]
    return replace(rivals, firms=tuple(sorted([*others, firm], key=lambda f: f.id)))


def departed_share(firm: RivalFirm, rivals: RivalsState, turn: int) -> float:
    gone = sum(n for t, n in firm.departures if t > turn - YEAR)
    partners = sum(1 for m in rivals.members_of(firm.id) if m.kind == "partner")
    return gone / max(1, partners + gone)


def prune_departures(firm: RivalFirm, turn: int) -> RivalFirm:
    return replace(firm, departures=tuple((t, n) for t, n in firm.departures if t > turn - YEAR))


def replace_panel_key(market: MarketState, old: str, new: str | None) -> MarketState:
    clients = []
    changed = False
    for c in market.clients:
        if old in c.panel:
            keys = {k for k in c.panel if k != old}
            if new is not None:
                keys.add(new)
            clients.append(replace(c, panel=tuple(sorted(keys))))
            changed = True
        else:
            clients.append(c)
    return replace(market, clients=tuple(clients)) if changed else market


def _done(rivals: RivalsState, key: str, turn: int, outcome: str) -> RivalsState:
    rest = [h for h in rivals.history_done if h.key != key]
    item = HistoryDone(key=key, turn=turn, outcome=outcome)  # type: ignore[arg-type]
    return replace(rivals, history_done=tuple(sorted([*rest, item], key=lambda h: h.key)))


# --- Collapse and scatter ---------------------------------------------------------------------


def collapse(
    state: GameState,
    firm: RivalFirm,
    gen: np.random.Generator,
    month: Month,
    absorber: RivalFirm | None = None,
    share: float = 0.0,
    status: RivalStatus = "collapsed",
) -> tuple[GameState, list[RivalMove]]:
    """The firm ends; its key people scatter (draws: one uniform each, in person-id order)."""
    cb = month.balance.rivals.collapse
    turn = month.turn
    rivals = state.rivals
    moves: list[RivalMove] = []
    receivers = sorted(
        (f for f in rivals.active if f.id != firm.id and f.ny_office and f.kind == "real"),
        key=lambda f: (-f.lawyers, f.id),
    )[:10]  # tunable-exempt: the largest ten rivals take a collapse's people
    agents = list(rivals.free_agents)
    for m in rivals.members_of(firm.id):
        u = float(gen.random())
        if absorber is not None and u < share:
            rivals = _move(rivals, m.person_id, absorber.id, turn)
        elif u < share + (1 - share) * cb.scatter_player_share or not receivers:
            rivals = replace(
                rivals, members=tuple(x for x in rivals.members if x.person_id != m.person_id)
            )
            agents.append(FreeAgent(m, turn, turn + cb.free_agent_months))
        else:
            dest = receivers[
                min(int(u * 997) % len(receivers), len(receivers) - 1)
            ]  # tunable-exempt: spread
            rivals = _move(rivals, m.person_id, dest.id, turn)
    if absorber is not None and share > 0:
        moved = firm.lawyers * share
        absorber_now = rivals.firm(absorber.id) or absorber
        rivals = with_firm(rivals, _add_pools(absorber_now, firm, share))
        del moved
    ended = replace(
        firm, status=status, ended_turn=turn, successor=absorber.key if absorber else None
    )
    rivals = with_firm(rivals, ended)
    rivals = replace(rivals, free_agents=tuple(sorted(agents, key=lambda a: a.person_id)))
    words = (
        f"{firm.name}: {round(share * 100)}% of its people join {absorber.name}"
        if absorber is not None
        else f"{firm.name} dissolves"
    )
    rivals, move = record(
        rivals, firm, turn, status, words, other=absorber.id if absorber else None
    )
    moves.append(move)
    market = replace_panel_key(state.market, firm.key, absorber.key if absorber else None)
    return replace(state, rivals=rivals, market=market), moves


def _move(rivals: RivalsState, person_id: int, firm_id: int, turn: int) -> RivalsState:
    members = tuple(
        replace(m, firm_id=firm_id, since_turn=turn) if m.person_id == person_id else m
        for m in rivals.members
    )
    return replace(rivals, members=members)


def _add_pools(into: RivalFirm, source: RivalFirm, share: float) -> RivalFirm:
    pools = tuple(
        Pool(
            practice=a.practice,
            equity=a.equity + b.equity * share,
            partners=a.partners + b.partners * share,
            associates=a.associates + b.associates * share,
        )
        for a, b in zip(into.pools, source.pools, strict=True)
    )
    return replace(into, pools=pools)


# --- Dated events -----------------------------------------------------------------------------


def _event_turn(e: HistoryEventDef, month: Month) -> int:
    return ym_to_turn(e.ym[0], e.ym[1], month.start)


def dated_collapse_turn(firm: RivalFirm, month: Month) -> int | None:
    for e in month.events:
        if e.firm == firm.key and e.kind in ("collapse", "absorbed"):
            return _event_turn(e, month)
    return None


def merge(
    state: GameState, e: HistoryEventDef, month: Month, rng: RngFactory
) -> tuple[GameState, list[RivalMove]]:
    rivals = state.rivals
    a, b = rivals.by_key(e.firm), rivals.by_key(e.other or "")
    if a is None or b is None or not a.active or not b.active:
        return replace(state, rivals=_done(rivals, e.key, month.turn, "called_off")), []
    cut = month.balance.rivals.collapse.merger_calloff_share
    if departed_share(a, rivals, month.turn) >= cut or departed_share(b, rivals, month.turn) >= cut:
        rivals = _done(rivals, e.key, month.turn, "called_off")
        rivals, move = record(
            rivals,
            a,
            month.turn,
            "merger_called_off",
            f"{a.name} and {b.name} call off their merger",
            other=b.id,
        )
        return replace(state, rivals=rivals), [move]
    index = next(i for i, f in enumerate(month.data.rivals.firms.firms) if f.key == e.into)
    fdef = month.data.rivals.firms.firms[index]
    la, lb = max(a.lawyers, 1.0), max(b.lawyers, 1.0)
    w = la / (la + lb)
    merged_pools = tuple(
        Pool(p.practice, p.equity + q.equity, p.partners + q.partners, p.associates + q.associates)
        for p, q in zip(a.pools, b.pools, strict=True)
    )
    successor = RivalFirm(
        id=month.balance.rivals.first_firm_id + index,
        rival_key=(REAL_KEY, index),
        key=fdef.key,
        name=fdef.name,
        short=fdef.short,
        personality=fdef.personality,
        kind="real",
        hq=fdef.hq,
        ny_office=fdef.ny_office,
        offices=fdef.offices,
        base_offices=fdef.offices,
        founded_turn=month.turn,
        pools=merged_pools,
        rpl_cap_cents=a.rpl_cap_cents * w + b.rpl_cap_cents * (1 - w),
        cost_per_lawyer_cents=a.cost_per_lawyer_cents * w + b.cost_per_lawyer_cents * (1 - w),
        demand_cents=a.demand_cents + b.demand_cents,
        rate_index=a.rate_index * w + b.rate_index * (1 - w),
        offset_cents=a.offset_cents + b.offset_cents,
        utilisation=a.utilisation,
        revenue=tuple(x + y for x, y in zip(a.revenue, b.revenue, strict=False)),
        profit=tuple(x + y for x, y in zip(a.profit, b.profit, strict=False)),
        anchor=(month.turn, a.demand_cents + b.demand_cents),
        lawyers_anchor=la + lb,
    )
    for party in (a, b):
        rivals = with_firm(
            rivals, replace(party, status="merged", ended_turn=month.turn, successor=fdef.key)
        )
        for m in rivals.members_of(party.id):
            rivals = _move(rivals, m.person_id, successor.id, month.turn)
    rivals = with_firm(rivals, successor)
    rivals = _done(rivals, e.key, month.turn, "happened")
    rivals, move = record(
        rivals,
        successor,
        month.turn,
        "merged",
        f"{a.name} and {b.name} merge to form {successor.name}",
    )
    market = replace_panel_key(replace_panel_key(state.market, a.key, fdef.key), b.key, fdef.key)
    return replace(state, rivals=rivals, market=market), [move]


def dated_events(
    state: GameState, rng: RngFactory, month: Month
) -> tuple[GameState, list[RivalMove]]:
    """Phase 9: this month's events, in firms.yaml order."""
    moves: list[RivalMove] = []
    for e in month.events:
        if _event_turn(e, month) != month.turn or state.rivals.done(e.key) is not None:
            continue
        firm = state.rivals.by_key(e.firm)
        if e.kind == "merger":
            state, made = merge(state, e, month, rng)
            moves += made
            continue
        if firm is None or not firm.active:
            state = replace(state, rivals=_done(state.rivals, e.key, month.turn, "called_off"))
            continue
        rivals = state.rivals
        if e.kind in ("rename", "outside_merger"):
            renamed = replace(firm, name=e.name or firm.name, short=e.short or firm.short)
            if e.kind == "outside_merger":
                path = month.path(firm)
                after = None
                if path is not None:
                    after = path_value(
                        path,
                        "lawyers",
                        time_of(month.turn, month.start) + 1e-6,
                        month.balance.rivals,
                    )
                add = max(float(e.lawyers_added), (after or 0.0) - renamed.lawyers)
                renamed = grow(renamed, add, month)
            rivals = with_firm(rivals, renamed)
            rivals = _done(rivals, e.key, month.turn, "happened")
            words = (
                f"{firm.name} becomes {renamed.name}"
                if e.kind == "rename"
                else (
                    f"{firm.name} merges with another firm"
                    + (f" to form {e.name}" if e.name else "")
                )
            )
            rivals, move = record(rivals, renamed, month.turn, e.kind, words)
            moves.append(move)
            state = replace(state, rivals=rivals)
            continue
        gen = streams.rival_fate(rng, month.turn, firm.rival_key)
        float(gen.random())  # the hazard's draw slot (collapse_hazard is skipped this month)
        absorber = state.rivals.by_key(e.other) if e.kind == "absorbed" and e.other else None
        if absorber is not None and not absorber.active:
            absorber = None
        state, made = collapse(
            state,
            firm,
            gen,
            month,
            absorber=absorber,
            share=e.share,
            status="merged" if absorber else "collapsed",
        )
        state = replace(state, rivals=_done(state.rivals, e.key, month.turn, "happened"))
        moves += made
    return state, moves


def hazard(firm: RivalFirm, rivals: RivalsState, month: Month) -> tuple[float, bool]:
    """A firm's collapse probability this month, and whether it is a losing firm's failure."""
    cb = month.balance.rivals.collapse
    d = departed_share(firm, rivals, month.turn)
    dated = dated_collapse_turn(firm, month)
    in_window = dated is not None and 0 < dated - month.turn <= cb.window_months
    mult = 1.0 if in_window else cb.other_mult * month.personality(firm).fragility
    p = (
        (cb.base_bp + cb.departed_slope_bp * 100 * max(0.0, d - cb.departed_threshold))
        * mult
        / 10_000
    )
    if not month.pinned(firm) and month.follows_history(firm):
        # PT-M18 (T16): after the pin, history's firms carry history's own hazard
        p += cb.free_play_bp * month.personality(firm).fragility / 10_000
    losing = firm.kind != "real" and len(firm.profit) >= YEAR and firm.profit_12m < 0
    if losing:  # boutiques and generated firms losing money for a year (boutiques.py)
        p += month.balance.rivals.boutique.failure_bp / 10_000
    return p, losing


def collapse_hazard(
    state: GameState, rng: RngFactory, month: Month
) -> tuple[GameState, list[RivalMove]]:
    """Phase 9: every active firm without a dated event this month rolls its hazard."""
    moves: list[RivalMove] = []
    this_month = {e.firm for e in month.events if _event_turn(e, month) == month.turn}
    for firm in state.rivals.active:
        if firm.key in this_month:
            continue
        current = state.rivals.firm(firm.id)
        if current is None or not current.active:
            continue
        p, losing = hazard(current, state.rivals, month)
        if p <= 0:
            continue  # no roll: nothing to draw for (the stream is the month's own)
        gen = streams.rival_fate(rng, month.turn, current.rival_key)
        if float(gen.random()) >= p:
            continue
        state, made = collapse(
            state, current, gen, month, status="failed" if losing else "collapsed"
        )
        key = next(
            (
                e.key
                for e in month.events
                if e.firm == current.key and e.kind in ("collapse", "absorbed")
            ),
            None,
        )
        if key is not None:
            state = replace(state, rivals=_done(state.rivals, key, month.turn, "forward"))
        moves += made
    return state, moves


_UNUSED = (build_path, LogItem, Balance, GameData)
