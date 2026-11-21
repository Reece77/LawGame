"""Real clients that history fails (PT-M7; clients.yaml `fails`, docs/research/v1-macro.md s1).

In the month a client files for bankruptcy, the firm's open named matters for it outside
restructuring stop (closed as collapsed); a firm that has the client on its books and a
restructuring lawyer is instructed in restructuring (the estate's work, its wallet
`macro.estate_mult` times its weight: `macro.wallet_factors`). Billing writes the client's open
bills off as bad debts (`billing.phase`). A rescued client (a distressed sale) pays its bills and
its wallet ends a few months later; its matters run on.
"""

from __future__ import annotations

from dataclasses import replace

from ptk.sim.data_models import Balance, GameData
from ptk.sim.log import LogItem, inbox_item
from ptk.sim.macro import RESTRUCTURING, failure_of, failure_turn
from ptk.sim.matters.intake import with_relationship
from ptk.sim.matters.progress import close_matter
from ptk.sim.matters.staffing import home_practice
from ptk.sim.state import GameState

NEUTRAL = 10.0  # tunable-exempt: a neutral 1-20 quality for work the client's failure stopped


def fail_clients(
    state: GameState, data: GameData, balance: Balance
) -> tuple[GameState, tuple[LogItem, ...]]:
    """Clients whose dated failure is this month, by id."""
    start = state.save_meta.start_ym
    failing = [
        c for c in state.market.clients if c.real and failure_turn(c, data, start) == state.turn
    ]
    if not failing:
        return state, ()
    firm_id = state.player.id
    staff = set(state.staff_ids(firm_id))
    has_restructuring = any(
        home_practice(p, data) == RESTRUCTURING for p in state.people if p.id in staff
    )
    market = state.market
    logs: list[LogItem] = []
    for client in failing:
        fails = failure_of(client, data)
        assert fails is not None
        rel = market.relationship(client.id, firm_id)
        if fails.kind == "bankruptcy":
            for m in [
                x
                for x in market.matters
                if x.is_open and x.client_id == client.id and x.practice != RESTRUCTURING
            ]:
                market, _ = close_matter(market, m, "collapsed", NEUTRAL, state.turn, balance)
            if rel is not None and has_restructuring and RESTRUCTURING not in rel.practices:
                practices = tuple(
                    p for p in data.practice_keys if p in {*rel.practices, RESTRUCTURING}
                )
                market = with_relationship(market, replace(rel, practices=practices))
        if rel is not None or any(m.client_id == client.id for m in market.matters):
            logs.append(
                inbox_item(
                    state.turn,
                    firm_id,
                    "client_failed" if fails.kind == "bankruptcy" else "client_rescued",
                    link_kind="client",
                    link_id=client.id,
                    client=client.name,
                )
            )
    return replace(state, market=market), tuple(logs)
