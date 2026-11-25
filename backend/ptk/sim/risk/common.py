"""Shared helpers for the risk modules: the firm's view of seats, people and money, and the
partners' capital call when the firm cannot pay (ADR PT-0003 5; spec 11.3)."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field, replace

from ptk.sim.data_models import PARTNER_LEVELS, Balance, GameData
from ptk.sim.ledger import (
    CASH,
    CLAIMS,
    FEES,
    FINES,
    PARTNERS_CAPITAL,
    PROFESSIONAL_FEES,
    RECEIVABLES,
    TRUST_SHORTFALLS,
    LedgerEntry,
    LedgerLine,
)
from ptk.sim.log import LinkKind, LogItem, ParamValue, inbox_item
from ptk.sim.people.models import Person
from ptk.sim.risk.models import RiskState
from ptk.sim.state import GameState

__all__ = ["CLAIMS", "FEES", "FINES", "PROFESSIONAL_FEES", "RECEIVABLES", "TRUST_SHORTFALLS"]


def name(person: Person) -> str:
    return f"{person.first_name} {person.last_name}"


def with_risk(state: GameState, risk: RiskState) -> GameState:
    return replace(state, risk=risk)


def gc_effect(state: GameState, firm_id: int, balance: Balance, data: GameData) -> float:
    """The firm's general counsel's seat effect e (spec 9.1; -0.5 vacant from its stage)."""
    from ptk.sim.interfaces import seat_effect

    return seat_effect(state, firm_id, "general_counsel", balance, data)


def lax(state: GameState, firm_id: int) -> bool:
    return state.risk.firm(firm_id).supervision == "lax"


def lawyers(state: GameState, firm_id: int, data: GameData) -> list[Person]:
    """The firm's lawyers on its books, by id."""
    return [
        p
        for e in state.staff(firm_id)
        if data.role((p := state.person(e.person_id)).role).kind == "lawyer"
    ]


def subjects(people: Iterable[Person]) -> list[Person]:
    """Who a risk system may name (ADR PT-0013): never a person flagged real."""
    return [p for p in people if not p.real]


def practice_of(person: Person, data: GameData) -> str:
    return data.role(person.role).practice or ""


def blame(state: GameState, matter_id: int) -> int | None:
    """The lawyer a claim blames: the matter's lead, else its most senior team member, never
    a person flagged real (ADR PT-0013)."""
    m = state.market.matter(matter_id)
    if m is None:
        return None
    order = [m.lead_id] if m.lead_id is not None else []
    rank = {"lead": 0, "senior": 1, "junior": 2, "paralegal": 3}
    order += [t.person_id for t in sorted(m.team, key=lambda t: (rank[t.role], t.person_id))]
    for pid in order:
        if pid is not None and not state.person(pid).real:
            return pid
    return None


@dataclass(slots=True)
class Books:
    """A month's postings for one firm, with the running cash it may spend (TST's poster)."""

    firm_id: int
    turn: int
    cash: int
    entries: list[LedgerEntry] = field(default_factory=list)
    logs: list[LogItem] = field(default_factory=list)

    def pay(self, account: str, amount: int, memo: str) -> None:
        if amount <= 0:
            return
        self.entries.append(
            LedgerEntry(
                turn=self.turn,
                firm_id=self.firm_id,
                memo=memo,
                lines=(LedgerLine(account, amount), LedgerLine(CASH, -amount)),
            )
        )
        self.cash -= amount

    def inbox(
        self,
        template: str,
        link_id: int | None = None,
        link_kind: LinkKind = "risk",
        **params: ParamValue,
    ) -> None:
        self.logs.append(
            inbox_item(
                self.turn, self.firm_id, template, link_kind=link_kind, link_id=link_id, **params
            )
        )


def capital_call(state: GameState, books: Books, amount: int, memo: str) -> tuple[GameState, int]:
    """The partners pay in `amount` of capital at once, split by their points (ADR PT-0003 5):
    the firm could not pay a claim from its cash. Returns the amount called (0 when the firm
    keeps no partnership)."""
    from ptk.sim.partnership.common import put
    from ptk.sim.partnership.formulas import split_cents
    from ptk.sim.partnership.models import with_partner

    fp = state.partnership.of(books.firm_id)
    if amount <= 0 or fp is None or not fp.equity_partners:
        return state, 0
    shares = split_cents(amount, {p.person_id: p.points for p in fp.equity_partners})
    for p in fp.equity_partners:
        add = shares[p.person_id]
        fp = with_partner(
            fp,
            replace(
                p,
                capital_cents=p.capital_cents + add,
                capital_required_cents=p.capital_required_cents + add,
            ),
        )
    books.entries.append(
        LedgerEntry.transfer(
            turn=books.turn,
            firm_id=books.firm_id,
            memo=memo,
            debit=CASH,
            credit=PARTNERS_CAPITAL,
            amount=amount,
        )
    )
    books.cash += amount
    return put(state, fp), amount


def is_partner(person: Person) -> bool:
    return person.level in PARTNER_LEVELS
