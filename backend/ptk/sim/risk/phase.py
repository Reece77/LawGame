"""PT-M15's turn step (spec 4.1), in phase 6 after payroll and the offices' costs: the player's
firm only (rivals carry their risk inside their pinned economics, ADR PT-0008).

Order: new latent claims from this month's escaped errors and lost cases (`claims`); the
policy year (renewal, England and Wales' minimum terms, the month's instalment; `insurance`);
each claim's stage; the GC's billing review (`review`); the client-account reconciliation
(`trust`); new disciplinary cases (padders found, surfaced conflicts, claims noticed, misuse,
the month's rolls) and each case's stage (`discipline`); regulators' inquiries (`inquiries`);
fee arbitration awards (`arbitration`). Billing's audits run inside phase 5's bills.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from simcore.kernel.money import Cents

from ptk.sim.billing.models import ClientBookEntry
from ptk.sim.data_models import Balance, GameData
from ptk.sim.ledger import CASH, AccountCode, LedgerEntry
from ptk.sim.log import LogItem
from ptk.sim.risk import arbitration, claims, discipline, inquiries, insurance, review, trust
from ptk.sim.risk import draws as dr
from ptk.sim.risk.common import Books
from ptk.sim.state import GameState
from ptk.sim.streams import RngFactory


@dataclass(frozen=True, slots=True)
class RiskMonth:
    state: GameState
    entries: tuple[LedgerEntry, ...]
    log: tuple[LogItem, ...]
    book: tuple[ClientBookEntry, ...] = ()  # the client book's shortfall entries


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
    state = insurance.insurance_month(state, firm_id, books, balance, data)
    state = claims.claims_month(state, rng, books, balance, data)
    noticed = [
        c.id for c in state.risk.claims if c.noticed_turn == state.turn and c.firm_id == firm_id
    ]
    gen = dr.discipline_rolls(rng, state.turn, firm_id)
    state = review.billing_review(state, gen, books, balance, data)
    state, book, rec = trust.reconcile(state, rng, books, balance, data)
    home = discipline.home_jurisdiction(state, data)
    triggers: list[tuple[str, str]] = []
    if rec is not None and rec.shortfall_cents:
        triggers.append((home, "trust"))
        if rec.person_id is not None:
            state = discipline.open_case(state, rec.person_id, "trust", gen, books, balance, data)
    if not state.firm(firm_id).conflict_checks and discipline.conflicts_surfaced(start, state):
        triggers.append((home, "conflicts"))
    state = discipline.new_cases(start, state, gen, books, balance, data, noticed)
    state = discipline.cases_month(state, rng, books, balance, data, balances)
    state = inquiries.new_inquiries(state, rng, books, balance, data, triggers)
    state = inquiries.inquiries_month(state, rng, books, balance)
    state = arbitration.awards_month(state, rng, books, balance)
    return RiskMonth(state, tuple(books.entries), tuple(books.logs), book)
