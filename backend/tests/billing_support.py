"""Helpers for PT-M3b tests: a grown firm played month by month, keeping every entry."""

from __future__ import annotations

from dataclasses import dataclass, field

from ptk.sim.billing.models import ClientBookEntry
from ptk.sim.data_models import Balance, GameData
from ptk.sim.decisions import Decisions
from ptk.sim.ledger import LedgerEntry, apply_entries
from ptk.sim.money import Cents
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState
from ptk.sim.turn import TurnResult, advance_turn
from tests.matters_support import grown_firm, top_up


@dataclass
class Played:
    """A game played in memory with the ledger carried between turns."""

    state: GameState
    seed: int
    balances: dict[tuple[int, str], Cents] = field(default_factory=dict)
    entries: list[LedgerEntry] = field(default_factory=list)
    book: list[ClientBookEntry] = field(default_factory=list)
    results: list[TurnResult] = field(default_factory=list)
    befores: list[GameState] = field(default_factory=list)

    def advance(self, data: GameData, balance: Balance, *, keep_size: bool = True) -> TurnResult:
        before = self.state
        result = advance_turn(
            before, Decisions(), RngFactory(self.seed), balance, data, self.balances
        )
        self.balances = apply_entries(self.balances, result.ledger_entries)
        self.entries += result.ledger_entries
        self.book += result.client_book
        self.results.append(result)
        self.befores.append(before)
        self.state = (
            top_up(result.new_state, data, balance, before) if keep_size else result.new_state
        )
        return result

    def balance_of(self, account: str, firm_id: int = 1) -> Cents:
        return self.balances.get((firm_id, account), 0)


def played(data: GameData, balance: Balance, lawyers: int, months: int, seed: int = 1) -> Played:
    game = Played(state=grown_firm(data, balance, lawyers, seed), seed=seed)
    for _ in range(months):
        game.advance(data, balance)
    return game
