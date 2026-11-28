"""Shared builders for the automation tests (PT-M9): PT-M8's led firm with every area that can
be automated given to its owner, and the player approving one-offs and nothing else."""

from __future__ import annotations

from dataclasses import replace

from ptk.sim.automation import owners
from ptk.sim.automation.actions import AnswerProposal, GiveArea, apply_automation_action
from ptk.sim.automation.run import AutoRun, area_gen
from ptk.sim.data_models import Balance, GameData
from ptk.sim.state import GameState, with_person_states
from ptk.sim.streams import RngFactory
from tests.seats_support import funded, led_firm, mp

CASH = 5_000_000_000  # funded()'s $50M


def refill(state: GameState, balance: Balance) -> GameState:
    ps = state.person_state(mp(state))
    return with_person_states(state, [replace(ps, energy=balance.energy.per_month)])


def give(
    state: GameState,
    data: GameData,
    balance: Balance,
    area: str,
    person_id: int,
    slot: int = 0,
    **kw: object,
) -> GameState:
    state = refill(state, balance)
    out = apply_automation_action(
        state,
        GiveArea(mp(state), area, person_id, slot, **kw),  # type: ignore[arg-type]
        seq=1,
        rng=RngFactory(state.save_meta.master_seed),
        b=balance,
        data=data,
        ledger_balances=funded(state),
    )
    return out.state


def automate_all(state: GameState, data: GameData, balance: Balance, **kw: object) -> GameState:
    """Every area that can be automated, to its first eligible owner."""
    firm = state.player.id
    for area in owners.area_keys(balance):
        for slot in owners.area_slots(state, firm, area, balance):
            people = owners.eligible_people(state, firm, area, slot, balance, data)
            if people:
                state = give(state, data, balance, area, people[0], slot, **kw)
    return state


def automated_firm(
    data: GameData, balance: Balance, seed: int = 1, lawyers: int = 110
) -> GameState:
    return automate_all(led_firm(data, balance, seed=seed, lawyers=lawyers), data, balance)


def approve_all(
    state: GameState, data: GameData, balance: Balance, balances: dict[tuple[int, str], int]
) -> tuple[GameState, dict[tuple[int, str], int], int]:
    """The player's only action: approve every pending proposal. Returns approvals made."""
    from ptk.sim.ledger import apply_entries

    made = 0
    for p in state.automation.pending(state.player.id):
        state = refill(state, balance)
        out = apply_automation_action(
            state,
            AnswerProposal(mp(state), p.id, True),
            seq=100 + p.id,
            rng=RngFactory(state.save_meta.master_seed),
            b=balance,
            data=data,
            ledger_balances=balances,
        )
        state = out.state
        balances = dict(apply_entries(balances, out.entries))
        made += 1
    return state, balances, made


def auto_run(
    state: GameState, data: GameData, balance: Balance, area: str, slot: int = 0
) -> AutoRun:
    o = state.automation.owner(state.player.id, area, slot)
    assert o is not None
    rng = RngFactory(state.save_meta.master_seed)
    gen = area_gen(rng, state.turn, owners.area_index(balance, area), o.firm_id, slot)
    return AutoRun(state, rng, balance, data, funded(state), o, gen, True)
