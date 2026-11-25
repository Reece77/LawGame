"""Offices as leases, their monthly postings and each office's P&L (PT-M11; spec 8.8).

Ported from backend/tst/sim/geo/offices.py @ 718997f0 (Tech Startup Tycoon); changed: who
works where is a person's city (`ptk.sim.geo.cities`), not units' offices; a lease is
recognised at signing (right-of-use asset 1510 against lease liability 2500, the term's rent
undiscounted) and each month's rent pays the liability (2500 / cash) and expenses the asset
(6000 / 1510); fit-out is capitalised (1500) and amortised straight-line over the term (6050);
a lease renews itself at the end of its term; breaking one costs `close_penalty_months` of
rent; England and Wales offices pay compulsory indemnity insurance (6300). TST's crowding and
flexible seats have no counterpart. Every line names its office (the ledger's office
dimension), so each office's P&L sums to the firm's (`office_pnl`).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import replace

from ptk.sim.data_models import Balance, GameData
from ptk.sim.geo import formulas as gf
from ptk.sim.geo.cities import person_office_id
from ptk.sim.geo.models import HOME_OFFICE_ID, Office, with_office
from ptk.sim.ledger import (
    CASH,
    DEPRECIATION,
    INSURANCE,
    LEASES,
    PPE,
    RENT,
    RIGHT_OF_USE,
    LedgerEntry,
    LedgerLine,
)
from ptk.sim.money import Cents
from ptk.sim.state import GameState

PNL_TYPES = frozenset({"income", "expense"})


def _pair(debit: str, credit: str, amount: Cents, office: int) -> tuple[LedgerLine, LedgerLine]:
    return (
        LedgerLine(debit, amount, office_id=office),
        LedgerLine(credit, -amount, office_id=office),
    )


def signing_entries(office: Office, turn: int) -> tuple[LedgerEntry, ...]:
    """A lease's signing: the liability and its asset; the fit-out paid and capitalised."""
    liability = gf.lease_liability_cents(office.rent_cents, office.term_months)
    lines = list(_pair(RIGHT_OF_USE, LEASES, liability, office.id))
    if office.fit_out_cents:
        lines += _pair(PPE, CASH, office.fit_out_cents, office.id)
    return (
        LedgerEntry(
            turn=turn,
            firm_id=office.firm_id,
            memo=f"Office lease signed and fitted out: office {office.id}",
            lines=tuple(lines),
        ),
    )


def month_entries(office: Office, turn: int) -> tuple[LedgerEntry, ...]:
    """A month of the lease: rent paid (the liability falls), rent expensed (the asset falls),
    the fit-out's amortisation."""
    k = office.lease_month(turn)
    if k < 0 or k >= office.term_months:
        return ()
    lines = [
        *_pair(LEASES, CASH, office.rent_cents, office.id),
        *_pair(RENT, RIGHT_OF_USE, office.rent_cents, office.id),
    ]
    if office.opened_turn == office.lease_start_turn:  # fit-out is the first term's only
        amort = gf.straight_line(office.fit_out_cents, office.term_months, k)
        if amort:
            lines += _pair(DEPRECIATION, PPE, amort, office.id)
    return (
        LedgerEntry(
            turn=turn,
            firm_id=office.firm_id,
            memo=f"Office lease: rent and fit-out, office {office.id}",
            lines=tuple(lines),
        ),
    )


def renewed(office: Office, turn: int) -> tuple[Office, tuple[LedgerEntry, ...]]:
    """At the term's end the lease renews for another term at the same rent."""
    if office.lease_month(turn) < office.term_months:
        return office, ()
    new = replace(office, lease_start_turn=turn)
    liability = gf.lease_liability_cents(new.rent_cents, new.term_months)
    entry = LedgerEntry(
        turn=turn,
        firm_id=office.firm_id,
        memo=f"Office lease renewed: office {office.id}",
        lines=_pair(RIGHT_OF_USE, LEASES, liability, office.id),
    )
    return new, (entry,)


def closing_entries(office: Office, turn: int, balance: Balance) -> tuple[LedgerEntry, ...]:
    """Breaking the lease: the penalty, the rest of the liability and asset derecognised, the
    fit-out's unamortised rest written off."""
    k = max(0, office.lease_month(turn))  # months already paid this term
    left = gf.lease_liability_cents(office.rent_cents, max(0, office.term_months - k))
    lines: list[LedgerLine] = []
    penalty = gf.close_penalty_cents(office.rent_cents, balance.geo)
    if penalty:
        lines += _pair(RENT, CASH, penalty, office.id)
    if left:
        lines += _pair(LEASES, RIGHT_OF_USE, left, office.id)
    if office.opened_turn == office.lease_start_turn and office.fit_out_cents:
        rest = office.fit_out_cents - gf.amortised_cents(
            office.fit_out_cents, office.term_months, k
        )
        if rest:
            lines += _pair(DEPRECIATION, PPE, rest, office.id)
    if not lines:
        return ()
    return (
        LedgerEntry(
            turn=turn,
            firm_id=office.firm_id,
            memo=f"Office closed: office {office.id}",
            lines=tuple(lines),
        ),
    )


def office_lawyers(state: GameState, firm_id: int, office_id: int, data: GameData) -> int:
    return sum(
        1
        for e in state.staff(firm_id)
        if data.role((p := state.person(e.person_id)).role).kind == "lawyer"
        and person_office_id(state, firm_id, p) == office_id
    )


def insurance_entry(state: GameState, office: Office, data: GameData) -> tuple[LedgerEntry, ...]:
    """Compulsory indemnity insurance where the office's jurisdiction requires it (England and
    Wales: spec 11.1): a twelfth of max(minimum premium, lawyers x premium a lawyer)."""
    city = data.geo.city(office.city)
    rules = data.geo.rules(city.jurisdiction)
    if rules is None or not rules.insurance.compulsory:
        return ()
    ins = rules.insurance
    lawyers = office_lawyers(state, office.firm_id, office.id, data)
    year = max(ins.min_premium_cents, lawyers * ins.premium_per_lawyer_cents)
    month = year // 12  # tunable-exempt: months in a year
    if month <= 0:
        return ()
    return (
        LedgerEntry(
            turn=state.turn,
            firm_id=office.firm_id,
            memo=f"Professional indemnity insurance: office {office.id}",
            lines=_pair(INSURANCE, CASH, month, office.id),
        ),
    )


def office_costs(
    state: GameState, balance: Balance, data: GameData
) -> tuple[GameState, tuple[LedgerEntry, ...]]:
    """Phase 6: every open office's lease month (renewing a lease at its term's end) and its
    insurance."""
    entries: list[LedgerEntry] = []
    geo = state.geo
    for office in [o for o in geo.offices if o.is_open]:
        office, renewal = renewed(office, state.turn)
        if renewal:
            geo = with_office(geo, office)
            entries.extend(renewal)
        entries.extend(month_entries(office, state.turn))
        if not balance.risk.enabled:  # PT-M15: the firm's policy covers it (ptk.sim.risk)
            entries.extend(insurance_entry(state, office, data))
    return replace(state, geo=geo), tuple(entries)


def office_pnl(entries: Iterable[LedgerEntry], firm_id: int, data: GameData) -> dict[int, Cents]:
    """Each office's profit (income less expenses) from a month's entries: a line with no
    office is the home office's. The offices' profits sum to the firm's."""
    types = {a.code: a.type for a in data.accounts}
    out: dict[int, Cents] = {}
    for e in entries:
        if e.firm_id != firm_id:
            continue
        for line in e.lines:
            if types.get(line.account) in PNL_TYPES:
                oid = line.office_id if line.office_id is not None else HOME_OFFICE_ID
                out[oid] = out.get(oid, 0) - line.amount
    return out


def firm_profit(entries: Iterable[LedgerEntry], firm_id: int, data: GameData) -> Cents:
    types = {a.code: a.type for a in data.accounts}
    return -sum(
        line.amount
        for e in entries
        if e.firm_id == firm_id
        for line in e.lines
        if types.get(line.account) in PNL_TYPES
    )


def lease_liability(balances: Mapping[tuple[int, str], Cents], firm_id: int) -> Cents:
    """The firm's lease liabilities outstanding (a credit balance, shown positive)."""
    return -balances.get((firm_id, LEASES), 0)
