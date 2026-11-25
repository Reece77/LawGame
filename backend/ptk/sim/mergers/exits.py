"""Being absorbed: the exit (spec 8.8; ADR PT-0016 1, 6; TST formulas.md 28.6).

When both partnerships pass terms in which the player's firm takes the other firm's name and
managing partner, or brings its partners under `mergers.absorbed_below_bp` of the merged pool
(`terms.is_absorption`), closing ends the campaign with outcome `exit`.
The score: the founder's capital account, the founder's draws and true-ups to date (their
personal book; PT-M7's T2 score is the same allocations), and the merged firm's rank by revenue
among active firms (the other firm's revenue plus the player's). Nothing is drawn.
"""

from __future__ import annotations

from dataclasses import replace

from ptk.sim.data_models import Balance, GameData
from ptk.sim.log import LogItem, inbox_item
from ptk.sim.mergers.models import Deal, ExitScore, with_deal
from ptk.sim.mergers.profile import annualised, player_side
from ptk.sim.mergers.talks import put_mergers
from ptk.sim.state import GameState


def founder_earnings(state: GameState, founder_id: int | None) -> int:
    from ptk.sim.founder.models import DRAWS, TRUE_UP

    if founder_id is None:
        return 0
    book = state.founder_life.book(founder_id)
    if book is None:
        return 0
    return max(0, -(book.bal(DRAWS) + book.bal(TRUE_UP)))


def absorb(
    state: GameState, deal: Deal, data: GameData, balance: Balance
) -> tuple[GameState, tuple[LogItem, ...]]:
    firm = state.rivals.firm(deal.rival_id)
    assert firm is not None
    pid = state.player.id
    founder = state.founder_of(pid)
    fp = state.partnership.of(pid)
    partner = fp.partner(founder) if fp is not None and founder is not None else None
    merged = annualised(firm.revenue) + player_side(state, data, balance).revenue_cents
    others = sorted(
        (annualised(f.revenue) for f in state.rivals.active if f.id != firm.id), reverse=True
    )
    rank = 1 + sum(1 for r in others if r > merged)
    score = ExitScore(
        turn=state.turn,
        firm_name=firm.name,
        capital_cents=partner.capital_cents if partner is not None else 0,
        earnings_cents=founder_earnings(state, founder),
        rank=rank,
        revenue_cents=merged,
    )
    deal = replace(deal, stage="closed", stage_turn=state.turn, ended_turn=state.turn)
    ms = replace(with_deal(state.mergers, deal), exit=score)
    state = put_mergers(state, ms)
    meta = replace(state.save_meta, game_state="exit", ended_turn=state.turn)
    state = replace(state, save_meta=meta)
    log = inbox_item(
        state.turn,
        pid,
        "merger_exit",
        link_kind="mergers",
        link_id=deal.id,
        firm=firm.name,
        rank=rank,
    )
    return state, (log,)
