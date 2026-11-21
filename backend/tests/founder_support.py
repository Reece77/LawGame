"""Helpers for PT-M17 tests: a firm played month by month with its ledger and the players'
personal books carried, and the partnership's founder accounts recorded each month."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from ptk.sim.data_models import Balance, GameData
from ptk.sim.decisions import Decisions
from ptk.sim.family.setup import FamilySpec
from ptk.sim.founder.models import PersonalEntry
from ptk.sim.interfaces import PartnerAccountView, partner_account
from ptk.sim.people.founder import FounderSpec
from ptk.sim.setup import new_game
from ptk.sim.state import GameState, with_people
from ptk.sim.turn import TurnResult, advance_turn
from tests.partnership_support import Game


@dataclass
class LifeGame(Game):
    personal: list[PersonalEntry] = field(default_factory=list)
    accounts: list[tuple[int, PartnerAccountView | None, PartnerAccountView | None]] = field(
        default_factory=list
    )  # (turn, the founder's account before the turn, after it)

    def advance(self, turns: int = 1) -> TurnResult | None:
        result = None
        for _ in range(turns):
            if self.state.ended:
                return result
            you = self.founder
            before = partner_account(self.state, self.state.player.id, you)
            pending = self.state.founder_life.pending
            result = advance_turn(
                self.state, Decisions(), self.rng, self.balance, self.data, self.balances
            )
            # the turn took the actions' pending entries into its personal book
            assert all(e in result.personal_book for e in pending)
            self.state = result.new_state
            self.post(result.ledger_entries)
            self.log += result.log_items
            self.personal += result.personal_book
            after = partner_account(self.state, self.state.player.id, you)
            self.accounts.append((self.state.turn - 1, before, after))
            self.seq = 0
        return result


def start_life(
    data: GameData,
    balance: Balance,
    seed: int = 1,
    scenario: str = "group_lift",
    *,
    family: FamilySpec | None = None,
    age: int | None = None,
    difficulty: str = "standard",
) -> LifeGame:
    founder = None
    if age is not None:
        sc = data.scenario(scenario)
        assert sc is not None
        founder = FounderSpec(background=sc.default_background, age=age)
    game = new_game(
        name="t",
        firm_name="Test LLP",
        master_seed=seed,
        scenario_id=scenario,
        difficulty=difficulty,
        data=data,
        balance=balance,
        founder=founder,
        family=family,
    )
    g = LifeGame(game.state, seed, data, balance)
    g.post(game.ledger_entries)
    return g


def set_age(state: GameState, person_id: int, years: int, months: int = 0) -> GameState:
    """The person's age set to `years` (and `months`) at the state's turn."""
    p = state.person(person_id)
    return with_people(state, [replace(p, birth_turn=state.turn - 12 * years - months)])
