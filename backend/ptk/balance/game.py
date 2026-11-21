"""One scripted game over the pure sim (TST's balance runner framework, ported; PT-M7).

Ported from backend/tst/balance/game.py @ 121d318a (Tech Startup Tycoon); changed: Partner
Track's actions (player actions through `apply_action`, org actions through
`apply_org_action`), the turn answers critical events itself (`answer_critical`), events are
written with `MockLLMAdapter` as a save's service does, and each month records what
docs/balance-targets.md reads (revenue and profit, people, burnout, ratios) instead of founder
value.

`act` swallows rule errors: a script that tries something the rules refuse (no energy, no cash,
a closed season) simply does not do it that month.
"""

from __future__ import annotations

import logging
import time
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field

from ptk.events.service import Writer, write_pending_events
from ptk.llm.offline import MockLLMAdapter
from ptk.llm.settings import LLMSettings
from ptk.sim.actions import Action, apply_action
from ptk.sim.calendar import turn_to_ym
from ptk.sim.data_models import Balance, GameData
from ptk.sim.decisions import Decisions
from ptk.sim.errors import SimError
from ptk.sim.hiring.pay import EQUITY_PARTNER
from ptk.sim.ledger import CASH, LedgerEntry, apply_entries
from ptk.sim.log import LogItem
from ptk.sim.org.actions import OrgAction, apply_org_action
from ptk.sim.partnership.kpis import explain
from ptk.sim.rng import RngFactory
from ptk.sim.setup import new_game
from ptk.sim.state import GameState
from ptk.sim.turn import advance_turn

log = logging.getLogger(__name__)

PLAYER = 1
ASSOCIATE_PREFIX = "associate_"
SENIOR_ASSOCIATE = "senior_associate"


def is_associate(level: str) -> bool:
    return level.startswith(ASSOCIATE_PREFIX) or level == SENIOR_ASSOCIATE


@dataclass(frozen=True, slots=True)
class Month:
    """What the targets read at one month end (cents, counts, bp)."""

    turn: int
    ym: tuple[int, int]
    revenue_cents: int  # the month's fees (accrual)
    revenue_12m_cents: int
    profit_12m_cents: int
    pep_cents: int | None
    lawyers: int  # fee earners on the books (lawyers, partners included)
    associates: int
    equity_partners: int
    associates_left: int  # associates on last month's books who are gone this month
    burnouts: int  # associates whose burnout began this month
    utilisation_bp: int | None
    realisation_bp: int | None
    collection_bp: int | None
    lockup_days: float | None
    cash_cents: int
    revolver_cents: int
    seconds: float  # the turn's wall-clock time (T12; never read by the sim)
    practice_revenue: tuple[tuple[str, int], ...] = ()  # the month's income by practice


@dataclass(slots=True)
class Game:
    data: GameData
    balance: Balance
    state: GameState
    balances: dict[tuple[int, str], int]
    seq: int = 0
    months: list[Month] = field(default_factory=list)
    refused: Counter[str] = field(default_factory=Counter)  # action kind -> refusals
    reasons: Counter[str] = field(default_factory=Counter)  # refusal messages (debugging)
    logs: list[LogItem] = field(default_factory=list)  # the last turn's log items
    month_entries: list[LedgerEntry] = field(default_factory=list)  # this month's, actions too
    notes: dict[str, int] = field(default_factory=dict)  # a script's own memory
    hired_classes: dict[int, tuple[int, ...]] = field(default_factory=dict)  # year -> ids
    _associates: frozenset[int] = frozenset()
    _writer: Writer = field(
        default_factory=lambda: Writer(MockLLMAdapter(), LLMSettings(), lambda: 1_000_000.0)
    )

    # --- reading ------------------------------------------------------------------------

    @property
    def founder_id(self) -> int:
        return next(p.id for p in self.state.people if p.is_founder)

    @property
    def ym(self) -> tuple[int, int]:
        return turn_to_ym(self.state.turn, self.state.save_meta.start_ym)

    @property
    def cash(self) -> int:
        return self.balances.get((PLAYER, CASH), 0)

    def bal(self, account: str) -> int:
        return self.balances.get((PLAYER, account), 0)

    def energy(self) -> int:
        return self.state.person_state(self.founder_id).energy or 0

    def staff(self) -> list:
        ids = set(self.state.staff_ids(PLAYER))
        return [p for p in self.state.people if p.id in ids]

    def lawyers(self) -> list:
        return [p for p in self.staff() if self.data.role(p.role).kind == "lawyer"]

    # --- acting -------------------------------------------------------------------------

    def act(self, action: Action | OrgAction) -> bool:
        """Apply one action; False when the rules refuse it."""
        self.seq += 1
        try:
            if type(action).__module__.endswith("org.actions"):
                org = apply_org_action(self.state, action, self.balance, self.data)  # type: ignore[arg-type]
                self.state = org.state
                return True
            out = apply_action(
                self.state,
                action,  # type: ignore[arg-type]
                seq=self.seq,
                rng=RngFactory(self.state.save_meta.master_seed),
                balance=self.balance,
                data=self.data,
                ledger_balances=self.balances,
            )
        except SimError as exc:
            self.refused[action.kind] += 1
            self.reasons[f"{action.kind}: {type(exc).__name__}: {str(exc)[:60]}"] += 1
            log.debug("turn %d: %s refused: %s", self.state.turn, action.kind, exc)
            return False
        self.state = out.state
        self._post(out.entries)
        return True

    def _post(self, entries: Iterable[LedgerEntry]) -> None:
        entries = list(entries)
        self.month_entries += entries
        self.balances = dict(apply_entries(self.balances, entries))

    # --- the month ------------------------------------------------------------------------

    def turn(self) -> None:
        """Play the month (critical events take their first choice), write the next month's
        events with the mock adapter, and record the month end."""
        started = time.perf_counter()
        result = advance_turn(
            self.state,
            Decisions(),
            RngFactory(self.state.save_meta.master_seed),
            self.balance,
            self.data,
            self.balances,
            answer_critical=True,
        )
        seconds = time.perf_counter() - started
        self._post(result.ledger_entries)
        state = result.new_state
        if not state.ended:
            state = write_pending_events(state, self.cash, self._writer, self.balance, self.data)
        self.state = state
        self.logs = list(result.log_items)
        year = turn_to_ym(result.snapshot.turn, self.state.save_meta.start_ym)[0]
        for item in self.logs:
            if item.kind == "class_started" and item.firm_id == PLAYER and item.link_id is not None:
                self.hired_classes[year] = (*self.hired_classes.get(year, ()), item.link_id)
        snap = next((f for f in result.snapshot.firms if f.firm_id == PLAYER), None)
        self._record(result.snapshot.turn, snap, seconds)
        self.month_entries = []
        self.seq = 0

    def _record(self, turn: int, snap, seconds: float) -> None:
        staff = self.lawyers()
        associates = frozenset(p.id for p in staff if is_associate(p.level))
        still = set(self.state.staff_ids(PLAYER))
        left = sum(1 for pid in self._associates if pid not in still)
        burnouts = sum(
            1
            for p in staff
            if p.id in associates
            and p.last_burnout_turn is not None
            and p.last_burnout_turn == turn
        )
        self._associates = associates
        fp = self.state.partnership.of(PLAYER)
        e = explain(self.state, fp) if fp is not None else None
        types = {a.code: a.type for a in self.data.accounts}
        by_practice: Counter[str] = Counter()
        for entry in self.month_entries:
            if entry.firm_id != PLAYER:
                continue
            for line in entry.lines:
                if types.get(line.account) == "income":
                    by_practice[line.practice or ""] -= line.amount
        self.months.append(
            Month(
                turn=turn,
                ym=turn_to_ym(turn, self.state.save_meta.start_ym),
                revenue_cents=snap.revenue_cents if snap else 0,
                revenue_12m_cents=e.revenue_cents if e else 0,
                profit_12m_cents=e.profit_cents if e else 0,
                pep_cents=e.pep_cents if e else None,
                lawyers=len(staff),
                associates=len(associates),
                equity_partners=sum(1 for p in staff if p.level == EQUITY_PARTNER),
                associates_left=left,
                burnouts=burnouts,
                utilisation_bp=snap.utilisation_bp if snap else None,
                realisation_bp=snap.realisation_bp if snap else None,
                collection_bp=snap.collection_bp if snap else None,
                lockup_days=snap.lockup_days if snap else None,
                cash_cents=self.cash,
                revolver_cents=snap.revolver_cents if snap and snap.revolver_cents else 0,
                seconds=seconds,
                practice_revenue=tuple(sorted(by_practice.items())),
            )
        )

    def templates(self) -> list[str]:
        """The last turn's log kinds (inbox template ids)."""
        return [i.kind for i in self.logs]


def start_game(
    data: GameData,
    balance: Balance,
    seed: int,
    scenario: str = "biglaw_spinout",
    difficulty: str = "standard",
) -> Game:
    """A new game as `create_save` would make it, held in memory."""
    made = new_game(
        name="balance",
        firm_name="Balance LLP",
        master_seed=seed,
        scenario_id=scenario,
        difficulty=difficulty,
        data=data,
        balance=balance,
    )
    game = Game(data, balance, made.state, dict(apply_entries({}, made.ledger_entries)))
    game._associates = frozenset(p.id for p in game.lawyers() if is_associate(p.level))
    return game
