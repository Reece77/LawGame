"""PT-M15's turn step (spec 4.1), in phase 6 after payroll and the offices' costs: the player's
firm only (rivals carry their risk inside their pinned economics, ADR PT-0008).

Order: new latent claims from this month's escaped errors and lost cases (`claims`); the
policy year (renewal, England and Wales' minimum terms, the month's instalment; `insurance`);
each claim's stage. Later sub-tasks add discipline, inquiries, the client-account
reconciliation and audits here.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from ptk.sim.data_models import Balance, GameData
from ptk.sim.ledger import CASH, AccountCode, LedgerEntry
from ptk.sim.log import LogItem
from ptk.sim.money import Cents
from ptk.sim.risk import claims
from ptk.sim.risk.common import Books
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState


@dataclass(frozen=True, slots=True)
class RiskMonth:
    state: GameState
    entries: tuple[LedgerEntry, ...]
    log: tuple[LogItem, ...]


def month(
    state: GameState,
    start: GameState,
    rng: RngFactory,
    balance: Balance,
    data: GameData,
    balances: Mapping[tuple[int, AccountCode], Cents],
) -> RiskMonth:
    if not balance.risk.enabled or state.ended:
        return RiskMonth(state, (), ())
    firm_id = state.player.id
    books = Books(firm_id, state.turn, balances.get((firm_id, CASH), 0))
    state = claims.make_claims(start, state, rng, balance, data)
    state = claims.claims_month(state, rng, books, balance, data)
    return RiskMonth(state, tuple(books.entries), tuple(books.logs))
