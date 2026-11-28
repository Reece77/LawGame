"""Estate planning and estate tax (TST formulas.md 45.6), with the US federal history.

Ported from backend/tst/sim/family/estate.py @ 121d318a (Tech Startup Tycoon); changed: the
estate is the head's personal book (cash, investments, the family office and their capital in
the firm), not company shares; it is taxed at a succession on health grounds (as TST's) at
`family.estate`'s rate for the year above its exemption less lifetime gifts; planning is
gifts to heirs (gift tax above the lifetime exemption, the unified US rule) and a family
trust that holds assets outside the estate; the foundation's endowment is already outside.
Estate tax, the exemption and trusts are public rules (no hidden values).
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from simcore.kernel.calendar import turn_to_ym

from ptk.sim.data_models import Balance
from ptk.sim.errors import FamilyError
from ptk.sim.family.models import CHILD, FamilyState, note, with_family_record
from ptk.sim.founder.config import EstateYear
from ptk.sim.founder.models import (
    ESTATE_TAX,
    FAMILY_OFFICE,
    FIRM_CAPITAL,
    INVESTMENTS,
    PERSONAL_CASH,
    SPENDING,
    TRUST,
    PersonalBook,
    PersonalEntry,
)


def rule_for(year: int, balance: Balance) -> EstateYear:
    rule = balance.family.estate[0]
    for row in balance.family.estate:
        if row.year <= year:
            rule = row
    return rule


@dataclass(frozen=True, slots=True)
class EstateQuote:
    estate_cents: int  # taxable assets (the trust and the endowment are outside)
    exemption_cents: int  # the year's exemption less lifetime gifts
    rate: float
    tax_cents: int


def estate_cents(book: PersonalBook) -> int:
    return max(
        0,
        sum(book.bal(a) for a in (PERSONAL_CASH, INVESTMENTS, FAMILY_OFFICE, FIRM_CAPITAL))
        + book.bal("9500_capital_loan")
        + book.bal("9510_tax_payable"),
    )


def quote(
    book: PersonalBook, fs: FamilyState, turn: int, start_ym: tuple[int, int], balance: Balance
) -> EstateQuote:
    rule = rule_for(turn_to_ym(turn, start_ym)[0], balance)
    gifts = fs.family.lifetime_gifts_cents if fs.family is not None else 0
    exemption = max(0, rule.exemption_cents - gifts)
    estate = estate_cents(book)
    tax = round(max(0, estate - exemption) * rule.rate)
    return EstateQuote(estate, exemption, rule.rate, tax)


def pay_estate_tax(
    book: PersonalBook, fs: FamilyState, turn: int, start_ym: tuple[int, int], balance: Balance
) -> tuple[PersonalBook, FamilyState, tuple[PersonalEntry, ...]]:
    """At a succession on health grounds: the estate pays from cash, then investments, then
    the family office (sold to cash). Capital in the firm comes back over three years, so
    what cannot be paid now stays unpaid (recorded as paid only for what was paid)."""
    q = quote(book, fs, turn, start_ym, balance)
    entries: list[PersonalEntry] = []
    need = q.tax_cents
    for account in (INVESTMENTS, FAMILY_OFFICE):
        short = need - book.cash
        if short <= 0:
            break
        sell = min(short, book.bal(account))
        if sell > 0:
            e = PersonalEntry.transfer(
                turn,
                book.person_id,
                "Sold to pay estate tax",
                "estate",
                PERSONAL_CASH,
                account,
                sell,
            )
            entries.append(e)
            book = book.posted((e,))
    pay = min(need, max(0, book.cash))
    if pay > 0:
        e = PersonalEntry.transfer(
            turn, book.person_id, "Estate tax", "estate", ESTATE_TAX, PERSONAL_CASH, pay
        )
        entries.append(e)
        book = book.posted((e,))
    family = fs.family
    if family is not None and pay > 0:
        family = note(
            replace(family, estate_tax_cents=family.estate_tax_cents + pay),
            turn,
            "estate_tax",
            "The estate paid its tax",
            balance.family.history,
        )
        fs = with_family_record(fs, family)
    return book, fs, tuple(entries)


def gift_to_heir(
    book: PersonalBook,
    fs: FamilyState,
    child_id: int,
    cents: int,
    turn: int,
    start_ym: tuple[int, int],
    balance: Balance,
) -> tuple[PersonalBook, FamilyState, tuple[PersonalEntry, ...]]:
    """A gift to a child: it leaves the book; above the lifetime exemption it pays gift tax
    at the estate rate (the unified US rule)."""
    member = fs.member(child_id)
    if fs.family is None or member is None or member.relation != CHILD:
        raise FamilyError("a gift goes to one of your children")
    if cents <= 0 or cents > book.cash:
        raise FamilyError("a gift is a positive amount within your personal cash")
    rule = rule_for(turn_to_ym(turn, start_ym)[0], balance)
    before = fs.family.lifetime_gifts_cents
    taxable = max(0, before + cents - rule.exemption_cents) - max(0, before - rule.exemption_cents)
    tax = round(taxable * rule.rate)
    if cents + tax > book.cash:
        raise FamilyError("the gift and its gift tax are more than your personal cash")
    entries = [
        PersonalEntry.transfer(
            turn, book.person_id, "Gift to a child", "gift_heir", SPENDING, PERSONAL_CASH, cents
        )
    ]
    if tax:
        entries.append(
            PersonalEntry.transfer(
                turn, book.person_id, "Gift tax", "gift_heir", ESTATE_TAX, PERSONAL_CASH, tax
            )
        )
    book = book.posted(entries)
    family = replace(fs.family, lifetime_gifts_cents=before + cents)
    return book, with_family_record(fs, family), tuple(entries)


def set_up_trust(
    book: PersonalBook, fs: FamilyState, cents: int, turn: int, balance: Balance
) -> tuple[PersonalBook, FamilyState, tuple[PersonalEntry, ...]]:
    """A family trust: its set-up cost, then `cents` of personal cash into the trust (outside
    the estate; it does not earn in this milestone)."""
    if fs.family is None:
        raise FamilyError("a trust needs a family")
    setup = balance.family.trust_setup_cents if fs.family.trust_turn is None else 0
    if cents <= 0 or cents + setup > book.cash:
        raise FamilyError("the trust's amount and set-up cost are more than your personal cash")
    entries = []
    if setup:
        entries.append(
            PersonalEntry.transfer(
                turn, book.person_id, "Trust set-up", "trust", SPENDING, PERSONAL_CASH, setup
            )
        )
    entries.append(
        PersonalEntry.transfer(
            turn, book.person_id, "Into the family trust", "trust", TRUST, PERSONAL_CASH, cents
        )
    )
    book = book.posted(entries)
    family = fs.family if fs.family.trust_turn is not None else replace(fs.family, trust_turn=turn)
    return book, with_family_record(fs, family), tuple(entries)
