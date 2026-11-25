"""Helpers for PT-M13 tests: a played game with rivals' run-rates, a target, and deals forced to
a stage (so a test reaches closing without playing the talks)."""

from __future__ import annotations

from dataclasses import replace

from ptk.sim.data_models import Balance, GameData
from ptk.sim.decisions import Decisions
from ptk.sim.ledger import apply_entries
from ptk.sim.mergers.models import Deal, Terms, with_deal
from ptk.sim.mergers.profile import rival_side
from ptk.sim.mergers.talks import open_deal, put_mergers
from ptk.sim.rivals.models import RivalFirm
from ptk.sim.rng import RngFactory
from ptk.sim.setup import new_game
from ptk.sim.state import GameState
from ptk.sim.turn import advance_turn

Balances = dict[tuple[int, str], int]


def played(
    data: GameData, balance: Balance, seed: int, months: int = 6
) -> tuple[GameState, Balances]:
    made = new_game(
        name="m",
        firm_name="Founders LLP",
        master_seed=seed,
        scenario_id="biglaw_spinout",
        difficulty="standard",
        data=data,
        balance=balance,
    )
    state = made.state
    balances: Balances = dict(apply_entries({}, made.ledger_entries))
    for _ in range(months):
        r = advance_turn(
            state, Decisions(), RngFactory(seed), balance, data, balances, answer_critical=True
        )
        balances = dict(apply_entries(balances, r.ledger_entries))
        state = r.new_state
    return state, balances


def targets(state: GameState, data: GameData, balance: Balance) -> list[RivalFirm]:
    """Integrable firms in the home city, smallest first."""
    out = [
        f
        for f in state.rivals.active
        if f.kind == "generated"
        and data.geo.city_key(f.hq) == state.player.home_city
        and rival_side(f, data).lawyers <= balance.mergers.max_lawyers
    ]
    return sorted(out, key=lambda f: (rival_side(f, data).lawyers, f.id))


def forced(
    state: GameState,
    firm: RivalFirm,
    terms: Terms,
    data: GameData,
    balance: Balance,
    stage: str = "clearance",
    form: str = "merger",
) -> tuple[GameState, Deal]:
    """A deal with `firm` at `stage` with `terms`, its book drawn (talks skipped)."""
    rng = RngFactory(state.save_meta.master_seed)
    state, deal = open_deal(state, firm, form, "player", rng, data, balance, terms)  # type: ignore[arg-type]
    deal = replace(
        deal,
        stage=stage,  # type: ignore[arg-type]
        stage_turn=state.turn - 1,
        absorbed=form == "merger" and terms.our_share_bp < balance.mergers.absorbed_below_bp,
    )
    return put_mergers(state, with_deal(state.mergers, deal)), deal
