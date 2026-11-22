"""The seats' turn steps (PT-M8): phase 2 (the MP's confidence effect, holders acting under
authority, pitches and their follow-through) and phase 12 (the December committee vote and
election, the quarterly partners' meeting, the chiefs' report requests). `ptk.sim.turn`
calls these two functions only, so the seats touch the pipeline in two places."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from ptk.sim import interfaces
from ptk.sim.data_models import Balance, GameData
from ptk.sim.events.models import TextRequest
from ptk.sim.ledger import AccountCode, LedgerEntry
from ptk.sim.log import LogItem
from ptk.sim.money import Cents
from ptk.sim.org.authority import seats_act
from ptk.sim.org.pitches import pitches_month
from ptk.sim.org.reports import december, partners_meeting, report_requests
from ptk.sim.org.seat_models import MP, SeatDecision
from ptk.sim.org.seats import effect
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState


@dataclass(frozen=True, slots=True)
class SeatsMonth:
    state: GameState
    entries: tuple[LedgerEntry, ...] = ()
    log: tuple[LogItem, ...] = ()
    decisions: tuple[SeatDecision, ...] = ()
    texts: tuple[TextRequest, ...] = ()


def phase_two(
    state: GameState,
    rng: RngFactory,
    balance: Balance,
    data: GameData,
    balances: Mapping[tuple[int, AccountCode], Cents],
) -> SeatsMonth:
    if state.ended or not state.firms:
        return SeatsMonth(state)
    firm = state.player.id
    e_mp = effect(state, firm, MP, balance, data)  # spec 9.1: +0.5 e confidence a month
    if e_mp:
        state = interfaces.confidence_change(
            state, firm, balance.seats.effects.mp_confidence * e_mp
        )
    run = seats_act(state, rng, balance, data, balances)
    state, entries, logs = pitches_month(run.state, rng, balance, data, balances)
    return SeatsMonth(state, run.entries + entries, run.log + logs, run.decisions)


def phase_twelve(state: GameState, balance: Balance, data: GameData) -> SeatsMonth:
    if state.ended or not state.firms:
        return SeatsMonth(state)
    state, voted = december(state, balance, data)
    state, met = partners_meeting(state, balance, data)
    return SeatsMonth(state, (), (*voted, *met), (), report_requests(state, balance, data))
