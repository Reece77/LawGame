"""The founder's foundation (spec 2.3; TST formulas.md 32.3): created once personal cash
reaches `foundation.min_cents`, funded by gifts from the personal account, granting
`foundation.payout` of its endowment each December. A year's grants raise Beloved and, for
`effect_months`, add their cause's effect.

Ported from backend/tst/sim/founder/foundation.py @ 121d318a (Tech Startup Tycoon); changed:
causes are access to justice (added), education, health and local communities (climate is
TST's consumer brand, dropped); effects in Partner Track's units: education and local raise
recruiting, access to justice and health lower resignations; no cities.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Final

from ptk.sim import dmath
from ptk.sim.calendar import turn_to_ym
from ptk.sim.data_models import Balance
from ptk.sim.errors import FounderLifeError
from ptk.sim.founder.config import CAUSES
from ptk.sim.founder.models import (
    ENDOWMENT,
    GRANTS,
    PERSONAL_CASH,
    Foundation,
    FounderLifeState,
    PersonalEntry,
    with_book,
    with_foundation,
    with_life,
)
from ptk.sim.founder.persona import raise_trait
from ptk.sim.money import times

DECEMBER: Final = 12  # tunable-exempt: calendar
CENTS_A_DOLLAR: Final = 100  # tunable-exempt: cents in a dollar
MAX_NAME: Final = 60  # tunable-exempt: the same limit as a firm name is shown at
CAUSE_WORDS: Final[dict[str, str]] = {
    "access_to_justice": "access to justice",
    "education": "education",
    "health": "health",
    "local": "local communities",
}


def create(
    fl: FounderLifeState,
    person_id: int,
    last_name: str,
    name: str,
    cause: str,
    turn: int,
    balance: Balance,
) -> FounderLifeState:
    fb = balance.founder_life.foundation
    book = fl.book(person_id)
    if fl.foundation(person_id) is not None:
        raise FounderLifeError("you already have a foundation")
    if cause not in CAUSES:
        raise FounderLifeError(f"a cause is one of {', '.join(CAUSES)}")
    if book is None or book.cash < fb.min_cents:
        raise FounderLifeError(
            f"a foundation needs ${fb.min_cents // CENTS_A_DOLLAR:,} of personal cash"
        )
    title = name.strip() or f"The {last_name} Foundation"
    if len(title) > MAX_NAME:
        raise FounderLifeError(f"a name is at most {MAX_NAME} characters")
    return with_foundation(fl, Foundation(person_id, title, cause, turn))


def give(fl: FounderLifeState, person_id: int, cents: int, turn: int) -> FounderLifeState:
    foundation = fl.foundation(person_id)
    book = fl.book(person_id)
    if foundation is None or book is None:
        raise FounderLifeError("create a foundation first")
    if cents <= 0:
        raise FounderLifeError("a gift needs a positive amount")
    if cents > book.cash:
        raise FounderLifeError("the gift is more than your personal cash")
    entry = PersonalEntry.transfer(
        turn, person_id, "Gift to the foundation", "gift", ENDOWMENT, PERSONAL_CASH, cents
    )
    fl = with_book(fl, book.posted((entry,)))
    fl = with_foundation(fl, replace(foundation, gifts_cents=foundation.gifts_cents + cents))
    return replace(fl, pending=(*fl.pending, entry))


def beloved_from(grant_cents: int, balance: Balance) -> float:
    """min(cap, k x log10(g / unit)), never negative (TST 32.3)."""
    fb = balance.founder_life.foundation
    # money-exact: ratio
    dollars = grant_cents / CENTS_A_DOLLAR
    if dollars <= fb.beloved_unit_dollars:
        return 0.0
    return min(fb.beloved_cap, fb.beloved_k * dmath.log10(dollars / fb.beloved_unit_dollars))


def grants_month(
    fl: FounderLifeState, turn: int, start_ym: tuple[int, int], balance: Balance
) -> tuple[FounderLifeState, tuple[PersonalEntry, ...], tuple[tuple[str, int, str], ...]]:
    """December: each foundation grants `payout` of its endowment. Returns the entries and
    (name, cents, cause words) for the inbox."""
    if turn_to_ym(turn, start_ym)[1] != DECEMBER:
        return fl, (), ()
    entries: list[PersonalEntry] = []
    done: list[tuple[str, int, str]] = []
    for foundation in fl.foundations:
        pid = foundation.person_id
        book = fl.book(pid)
        if book is None:
            continue
        cents = times(book.bal(ENDOWMENT), balance.founder_life.foundation.payout)
        if cents <= 0:
            continue
        entry = PersonalEntry.transfer(
            turn, pid, "Foundation grants", "grant", GRANTS, ENDOWMENT, cents
        )
        entries.append(entry)
        fl = with_book(fl, book.posted((entry,)))
        fl = with_foundation(
            fl,
            replace(
                foundation,
                grants_cents=foundation.grants_cents + cents,
                last_grant_cents=cents,
                last_grant_turn=turn,
            ),
        )
        life = fl.life(pid)
        if life is not None:
            gain = beloved_from(cents, balance)
            fl = with_life(
                fl, raise_trait(life, "beloved", gain, "foundation grants", turn, balance)
            )
        done.append((foundation.name, cents, CAUSE_WORDS[foundation.cause]))
    return fl, tuple(entries), tuple(done)


def active(f: Foundation | None, turn: int, balance: Balance) -> bool:
    """The cause's effect lasts `effect_months` after a year's grants."""
    return (
        f is not None
        and f.last_grant_turn is not None
        and turn - f.last_grant_turn < balance.founder_life.foundation.effect_months
    )


def recruiting_points(f: Foundation | None, turn: int, balance: Balance) -> float:
    """Education and local communities: up to `recruiting` offer-score points, in proportion
    to the year's grants up to `recruiting_full_dollars`."""
    fb = balance.founder_life.foundation
    if f is None or not active(f, turn, balance) or f.cause not in ("education", "local"):
        return 0.0
    # money-exact: ratio
    share = min(1.0, f.last_grant_cents / CENTS_A_DOLLAR / fb.recruiting_full_dollars)
    return fb.recruiting * share


def resign_mult(f: Foundation | None, turn: int, balance: Balance) -> float:
    if f is None or not active(f, turn, balance) or f.cause not in ("access_to_justice", "health"):
        return 1.0
    return balance.founder_life.foundation.resign
