"""Helpers for PT-M4 tests: a firm with a partnership, played month by month with its ledger
carried, plus the scripted exodus of balance target T9's mechanism."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field, replace

from simcore.kernel.money import Cents

from ptk.sim.actions import Action, apply_action
from ptk.sim.data_models import Balance, GameData
from ptk.sim.decisions import Decisions
from ptk.sim.interfaces import LateralArrival, Suitor, partner_flight
from ptk.sim.ledger import LedgerEntry, apply_entries
from ptk.sim.log import LogItem
from ptk.sim.matters.intake import with_relationship
from ptk.sim.matters.models import Relationship
from ptk.sim.partnership.models import FirmPartnership
from ptk.sim.people.generator import generate_person, people_gen_stream
from ptk.sim.people.reveal import new_reveal_state
from ptk.sim.setup import new_game
from ptk.sim.state import GameState, with_people, with_reveals
from ptk.sim.streams import RngFactory
from ptk.sim.turn import TurnResult, advance_turn

EXTRA_SEARCH = 9_000  # people_gen search id for test partners (never a real search's)
TEST_PARTNER_MAX_AGE = 55  # PT-M17: ten years under the default retirement age


@dataclass
class Game:
    state: GameState
    seed: int
    data: GameData
    balance: Balance
    balances: dict[tuple[int, str], Cents] = field(default_factory=dict)
    entries: list[LedgerEntry] = field(default_factory=list)
    log: list[LogItem] = field(default_factory=list)
    seq: int = 0

    @property
    def rng(self) -> RngFactory:
        return RngFactory(self.seed)

    @property
    def fp(self) -> FirmPartnership:
        fp = self.state.partnership.of(self.state.player.id)
        assert fp is not None
        return fp

    @property
    def founder(self) -> int:
        f = self.state.founder_of(self.state.player.id)
        assert f is not None
        return f

    def post(self, entries: Iterable[LedgerEntry]) -> None:
        entries = list(entries)
        self.entries += entries
        self.balances = apply_entries(self.balances, entries)

    def advance(self, turns: int = 1) -> TurnResult | None:
        result = None
        for _ in range(turns):
            if self.state.ended:
                return result
            result = advance_turn(
                self.state, Decisions(), self.rng, self.balance, self.data, self.balances
            )
            self.state = result.new_state
            self.post(result.ledger_entries)
            self.log += result.log_items
            self.seq = 0
        return result

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
        self.post(out.entries)
        self.log += out.log

    def bal(self, account: str) -> Cents:
        return self.balances.get((self.state.player.id, account), 0)

    def templates(self) -> list[str]:
        return [i.template or "" for i in self.log]


def start(data: GameData, balance: Balance, seed: int = 1, scenario: str = "group_lift") -> Game:
    ng = new_game(
        name="t",
        firm_name="Partners LLP",
        master_seed=seed,
        scenario_id=scenario,
        difficulty="standard",
        data=data,
        balance=balance,
    )
    g = Game(state=ng.state, seed=seed, data=data, balance=balance)
    g.post(ng.ledger_entries)
    return g


def add_partner(
    g: Game,
    practice: str,
    comp_cents: int,
    *,
    guarantee_years: int = 0,
    clients: int = 0,
    n: int = 0,
    book_cents: int = 150_000_000,
) -> int:
    """A lateral equity partner joins now (through the flight hook's `arrive`), with
    `clients` of the universe's unclaimed clients as immediate relationships."""
    state = g.state
    pid = max(p.id for p in state.people) + 1
    person = generate_person(
        people_gen_stream(g.rng, state.turn, EXTRA_SEARCH, pid + n),
        g.data,
        g.balance,
        state.turn,
        g.data.practice_role(practice),
        "equity_partner",
        person_id=pid,
        city=state.player.home_city,
        jurisdiction="us_ny",
    )
    person = replace(person, book_cents=book_cents)
    # PT-M17: partners retire at the agreement's age; a test partner is young enough that a
    # scripted scenario's years never reach it (at most `TEST_PARTNER_MAX_AGE`)
    if person.age(state.turn) > TEST_PARTNER_MAX_AGE:
        person = replace(person, birth_turn=state.turn - 12 * TEST_PARTNER_MAX_AGE)
    state = with_people(state, [person])
    reveal = new_reveal_state(
        observer_firm_id=state.player.id,
        person=person,
        turn=state.turn,
        rng=g.rng,
        data=g.data,
        balance=g.balance,
    )
    state = with_reveals(state, [reveal])
    res = partner_flight().arrive(
        state,
        LateralArrival(pid, state.player.id, None, comp_cents, guarantee_years),
        draws=lambda: g.rng.stream(state.turn, "misc", pid),
        balance=g.balance,
        data=g.data,
        balances=g.balances,
    )
    state = res.state
    g.post(res.entries)
    have = {r.client_id for r in state.market.relationships}
    market = state.market
    added = 0
    for c in sorted(market.clients, key=lambda c: (-c.revenue_bn, c.id)):
        if added >= clients:
            break
        if c.id in have:
            continue
        market = with_relationship(
            market,
            Relationship(
                client_id=c.id,
                firm_id=state.player.id,
                score=60.0,
                partner_id=pid,
                practices=(practice,),
                since_turn=state.turn,
                last_instructed_turn=state.turn,
            ),
        )
        added += 1
    g.state = replace(state, market=market)
    return pid


def depart(g: Game, person_id: int, suitor: str = "skadden") -> None:
    hook = partner_flight()
    name = next(f.name for f in g.data.clients.panel_firms if f.key == suitor)
    res = hook.depart(
        g.state,
        person_id,
        Suitor(suitor, name),
        "approach",
        draws=lambda: g.rng.stream(g.state.turn, "misc", 1_000 + person_id),
        balance=g.balance,
        data=g.data,
        balances=g.balances,
    )
    g.state = res.state
    g.post(res.entries)
    g.log += res.log


type Response = Callable[[Game], None]
