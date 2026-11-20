"""Pure-sim helpers for the PT-M1b tests: a new game, actions and turns without a save."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from ptk.sim.actions import Action, apply_action
from ptk.sim.data_models import Balance, GameData
from ptk.sim.decisions import Decisions
from ptk.sim.ledger import LedgerEntry, apply_entries
from ptk.sim.log import LogItem
from ptk.sim.money import Cents
from ptk.sim.people.models import WorkMonth
from ptk.sim.rng import RngFactory
from ptk.sim.setup import new_game
from ptk.sim.state import GameState
from ptk.sim.turn import advance_turn


@dataclass
class Game:
    """A game played in memory: state, balances and everything posted so far."""

    state: GameState
    balances: dict[tuple[int, str], Cents]
    data: GameData
    balance: Balance
    entries: list[LedgerEntry] = field(default_factory=list)
    log: list[LogItem] = field(default_factory=list)
    seq: int = 0

    @property
    def rng(self) -> RngFactory:
        return RngFactory(self.state.save_meta.master_seed)

    @property
    def founder_id(self) -> int:
        return next(p.id for p in self.state.people if p.is_founder)

    def act(self, action: Action) -> None:
        self.seq += 1
        out = apply_action(
            self.state,
            action,
            seq=self.seq,
            rng=self.rng,
            balance=self.balance,
            data=self.data,
            ledger_balances=self.balances,
        )
        self.state = out.state
        self._post(out.entries)
        self.log += out.log

    def advance(
        self, turns: int = 1, work: Iterable[WorkMonth] = (), *, write_events: bool = False
    ) -> None:
        """`write_events` (PT-M6): after each turn, write its events with the mock adapter,
        as a save's event service does (round trips against a save)."""
        for _ in range(turns):
            result = advance_turn(
                self.state,
                Decisions(),
                self.rng,
                self.balance,
                self.data,
                self.balances,
                tuple(work),
                answer_critical=write_events,
            )
            self.state = result.new_state
            if write_events:
                self.state = mock_events(self.state, self.balance, self.data)
            self._post(result.ledger_entries)
            self.log += result.log_items
            self.seq = 0

    def advance_to(self, month: int) -> None:
        """Play turns until the next turn to be played is in calendar `month`."""
        from ptk.sim.calendar import turn_to_ym

        while turn_to_ym(self.state.turn, self.state.save_meta.start_ym)[1] != month:
            self.advance()

    def _post(self, entries: Iterable[LedgerEntry]) -> None:
        entries = list(entries)
        self.entries += entries
        self.balances = apply_entries(self.balances, entries)

    def cash(self) -> Cents:
        return self.balances.get((self.state.player.id, "1000_cash"), 0)


def mock_events(state: GameState, balance: Balance, data: GameData) -> GameState:
    """The state with its pending events written by the mock adapter (PT-M6)."""
    from ptk.events.service import Writer, write_pending_events
    from ptk.llm.offline import MockLLMAdapter
    from ptk.llm.settings import LLMSettings

    writer = Writer(MockLLMAdapter(), LLMSettings(), lambda: 1_000_000.0)
    return write_pending_events(state, 0, writer, balance, data)


def start(
    data: GameData, balance: Balance, seed: int = 11, scenario: str = "biglaw_spinout"
) -> Game:
    game = new_game(
        name="t",
        firm_name="Founders LLP",
        master_seed=seed,
        scenario_id=scenario,
        difficulty="standard",
        data=data,
        balance=balance,
    )
    return Game(
        state=game.state,
        balances=apply_entries({}, game.ledger_entries),
        data=data,
        balance=balance,
        entries=list(game.ledger_entries),
    )
