"""Shared lookups for the partnership modules: the firm's partnership, its partners as
people, the ledger's running P&L, books and headcounts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace

from ptk.sim.calendar import turn_to_ym
from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import NotManagingPartnerError, PartnershipError
from ptk.sim.ledger import CASH, AccountCode
from ptk.sim.partnership.models import FirmPartnership, Partner, with_firm_partnership
from ptk.sim.people.models import Person
from ptk.sim.state import GameState

LAWYER_KIND = "lawyer"


def firm_partnership(state: GameState, firm_id: int) -> FirmPartnership:
    fp = state.partnership.of(firm_id)
    if fp is None:
        raise PartnershipError(f"firm {firm_id} keeps no partnership")
    return fp


def put(state: GameState, fp: FirmPartnership) -> GameState:
    return replace(state, partnership=with_firm_partnership(state.partnership, fp))


def ym(state: GameState, turn: int | None = None) -> tuple[int, int]:
    return turn_to_ym(state.turn if turn is None else turn, state.save_meta.start_ym)


def name(person: Person) -> str:
    return f"{person.first_name} {person.last_name}"


def home_practice(person: Person, data: GameData) -> str:
    role = data.role(person.role)
    return role.practice or person.role


def cash(balances: Mapping[tuple[int, AccountCode], int], firm_id: int) -> int:
    return balances.get((firm_id, CASH), 0)


def cumulative_pnl(
    balances: Mapping[tuple[int, AccountCode], int], firm_id: int
) -> tuple[int, int]:
    """(revenue, costs) to date: the ledger's income and cost balances (no year-end close;
    each December allocation remembers where the year began)."""
    revenue = costs = 0
    for (f, account), amount in balances.items():
        if f != firm_id:
            continue
        if account[0] == "4":
            revenue -= amount
        elif account[0] in "56":
            costs += amount
    return revenue, costs


def lawyers(state: GameState, firm_id: int, balance: Balance) -> int:
    levels = balance.people.levels
    return sum(
        1
        for e in state.staff(firm_id)
        if levels[state.person(e.person_id).level].kind == LAWYER_KIND
    )


def origination_12m(state: GameState, person_id: int) -> int:
    """Origination credit over the trailing twelve months: the person's clients' work in the
    last 12 months (the relationships' rolling fees), the book's stand-in."""
    return sum(r.fees_12m for r in state.market.relationships if r.partner_id == person_id)


def book_cents(state: GameState, person: Person) -> int:
    """A partner's book a year: trailing origination once it exists, else their book."""
    orig = origination_12m(state, person.id)
    return orig if orig > 0 else person.book_cents


def require_mp(state: GameState, firm_id: int, actor_id: int) -> FirmPartnership:
    fp = firm_partnership(state, firm_id)
    if fp.mp_id != actor_id:
        raise NotManagingPartnerError("only the managing partner may do this")
    return fp


def partner_people(state: GameState, fp: FirmPartnership) -> list[tuple[Partner, Person]]:
    return [(p, state.person(p.person_id)) for p in fp.partners]


def last_month_costs(fp: FirmPartnership) -> int:
    if len(fp.pnl) < 2:
        return 0
    a, b = fp.pnl[-2], fp.pnl[-1]
    return max(0, b.costs_cents - a.costs_cents)


def revenue_12m(fp: FirmPartnership) -> int:
    if not fp.pnl:
        return 0
    first = fp.pnl[0]
    last = fp.pnl[-1]
    months = len(fp.pnl) - 1
    if months <= 0:
        return 0
    return round((last.revenue_cents - first.revenue_cents) * 12 / months)


def profit_12m(fp: FirmPartnership) -> int:
    if len(fp.pnl) < 2:
        return 0
    first, last = fp.pnl[0], fp.pnl[-1]
    months = len(fp.pnl) - 1
    gained = (last.revenue_cents - last.costs_cents) - (first.revenue_cents - first.costs_cents)
    return round(gained * 12 / months)
