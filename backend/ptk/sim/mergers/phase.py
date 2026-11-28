"""PT-M13's turn hooks (spec 4.1's phases; ADR PT-0016). A game with no deal, integration or
verein passes through each hook unchanged (no draws).

- Phase 1, before the partnership's votes: diligence levels end; talks lapse or leak; the other
  partnership answers terms put (a yes opens the player's vote, counted the same phase).
- Phase 1, after the votes: a passed vote moves to clearance; a failed one ends the deal; deals
  cleared last month close (merger, verein or exit).
- Phase 6: the verein's shared costs.
- Phase 8 (after flight): integration's records and clients balking.
- Phase 9: verein referrals; rivals' approaches to the player; from 2026, rivals' mergers.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace

from simcore.kernel.money import Cents

from ptk.sim.data_models import Balance, GameData
from ptk.sim.ledger import AccountCode, LedgerEntry
from ptk.sim.log import LogItem, inbox_item
from ptk.sim.mergers import clearance, closing, diligence, exits, integration, talks, terms, verein
from ptk.sim.mergers.actions import end_deal
from ptk.sim.mergers.models import Deal, with_deal
from ptk.sim.rivals.models import RivalMove
from ptk.sim.state import GameState
from ptk.sim.streams import RngFactory

OPEN_TALKS = ("talks", "terms", "countered", "approached")


@dataclass(frozen=True, slots=True)
class Step:
    state: GameState
    entries: tuple[LedgerEntry, ...] = ()
    log: tuple[LogItem, ...] = ()
    moves: tuple[RivalMove, ...] = ()


def _name(state: GameState, deal: Deal) -> str:
    firm = state.rivals.firm(deal.rival_id)
    return firm.name if firm is not None else deal.rival_key


def _lapse_and_leak(state: GameState, balance: Balance) -> tuple[GameState, list[LogItem]]:
    from ptk.sim.partnership.models import with_partner
    from ptk.sim.press.moments import queue_moment

    cfg = balance.mergers
    logs: list[LogItem] = []
    for deal in state.mergers.open_deals():
        if deal.stage not in OPEN_TALKS:
            continue
        if state.turn - deal.stage_turn >= cfg.talks_months and deal.diligence_due_turn is None:
            state = end_deal(state, deal, "talks lapsed", balance)
            logs.append(
                inbox_item(
                    state.turn,
                    state.player.id,
                    "merger_lapsed",
                    link_kind="mergers",
                    link_id=deal.id,
                    firm=_name(state, deal),
                )
            )
            continue
        if not deal.leaked and state.turn - deal.opened_turn >= cfg.confidential_months:
            state = talks.put_mergers(state, with_deal(state.mergers, replace(deal, leaked=True)))
            fp = state.partnership.of(state.player.id)
            if fp is not None:
                for p in fp.equity_partners:
                    if p.person_id != fp.mp_id:
                        fp = with_partner(fp, replace(p, nudge=p.nudge + cfg.leak_nudge))
                from ptk.sim.partnership.common import put

                state = put(state, fp)
            state = queue_moment(
                state,
                "merger",
                {"result": f"talks with {_name(state, deal)} leak"},
                rival_id=deal.rival_id,
            )
    return state, logs


def before_votes(state: GameState, rng: RngFactory, data: GameData, balance: Balance) -> Step:
    if not state.mergers.open_deals():
        return Step(state)
    state, done = diligence.finish(state)
    state, lapsed = _lapse_and_leak(state, balance)
    state, answered = terms.answer_terms(state, rng, data, balance)
    return Step(state, (), (*done, *lapsed, *answered))


def after_votes(state: GameState, rng: RngFactory, data: GameData, balance: Balance) -> Step:
    if not state.mergers.open_deals():
        return Step(state)
    entries: list[LedgerEntry] = []
    logs: list[LogItem] = []
    pid = state.player.id
    for deal in state.mergers.open_deals():
        if deal.stage == "clearance" and deal.stage_turn < state.turn:
            firm = state.rivals.firm(deal.rival_id)
            if firm is None or not firm.active:
                state = end_deal(state, deal, "the other firm no longer exists", balance)
                continue
            if deal.form == "verein":
                state, more = verein.join(state, deal, rng, data, balance)
            elif deal.absorbed:
                state, more = exits.absorb(state, deal, data, balance)
            else:
                state, made, more = closing.close_merger(state, deal, rng, data, balance)
                entries += made
            logs += more
            continue
        if deal.stage != "voting" or deal.our_vote_id is None:
            continue
        fp = state.partnership.of(pid)
        vote = fp.vote(deal.our_vote_id) if fp is not None else None
        if vote is None or vote.status == "open":
            continue
        if vote.status == "passed":
            if deal.absorbed:  # the player's firm is absorbed: its conflicts are the buyer's
                cleared, more = deal, ()
            else:
                state, cleared, more = clearance.clear(state, deal, rng, balance)
            cleared = replace(cleared, stage="clearance", stage_turn=state.turn)
            state = talks.put_mergers(state, with_deal(state.mergers, cleared))
            logs += more
            logs.append(
                inbox_item(
                    state.turn,
                    pid,
                    "merger_voted",
                    link_kind="mergers",
                    link_id=deal.id,
                    firm=_name(state, deal),
                )
            )
        else:
            state = end_deal(state, deal, "the partnership voted no", balance)
            logs.append(
                inbox_item(
                    state.turn,
                    pid,
                    "merger_our_no",
                    link_kind="mergers",
                    link_id=deal.id,
                    firm=_name(state, deal),
                )
            )
    return Step(state, tuple(entries), tuple(logs))


def phase_six(
    state: GameState, balances: Mapping[tuple[int, AccountCode], Cents], balance: Balance
) -> Step:
    if not state.mergers.vereins:
        return Step(state)
    from ptk.sim.partnership.common import revenue_12m

    fp = state.partnership.of(state.player.id)
    revenue = revenue_12m(fp) if fp is not None else 0
    state, entries = verein.costs(state, revenue, balance)
    return Step(state, entries)


def phase_seven(state: GameState, balance: Balance) -> GameState:
    """After financing: December's budgets of partners who joined by a merger this year."""
    return closing.december_budgets(state, balance)


def phase_eight(state: GameState, rng: RngFactory, balance: Balance) -> Step:
    if not state.mergers.integrations:
        return Step(state)
    state, logs = integration.month(state, rng, balance)
    return Step(state, (), logs)


def phase_nine(state: GameState, rng: RngFactory, data: GameData, balance: Balance) -> Step:
    from ptk.sim.rivals.mergers import free_play

    state, referred = verein.referrals(state, rng, data, balance)
    state, approached = talks.rival_approaches(state, rng, data, balance)
    state, moves = free_play(state, rng, balance)
    return Step(state, (), (*referred, *approached), moves)
