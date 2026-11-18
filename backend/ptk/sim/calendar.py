"""Turn <-> calendar conversion (ADR PT-0002). One turn = one month.

Ported from tst/sim/calendar.py @ 02fba2aa; changed: turn 0 is the scenario's start month
(January 2005 by default), passed in as `start`, never a module constant.

All time math in the sim goes through this module; the sim never uses `datetime`.
"""

from __future__ import annotations

from typing import Final

from ptk.sim.errors import InvalidDateError

type YearMonth = tuple[int, int]

DEFAULT_START: Final[YearMonth] = (2005, 1)
MONTHS_PER_YEAR: Final = 12
MONTH_ABBR: Final = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)


def _check(start: YearMonth) -> None:
    if not 1 <= start[1] <= MONTHS_PER_YEAR:
        raise InvalidDateError(f"start month must be 1..12, got {start[1]}")


def turn_to_ym(turn: int, start: YearMonth = DEFAULT_START) -> YearMonth:
    """Return (year, month) for a turn. Negative turns are dates before the start."""
    _check(start)
    year_offset, month_index = divmod(start[1] - 1 + turn, MONTHS_PER_YEAR)
    return start[0] + year_offset, month_index + 1


def ym_to_turn(year: int, month: int, start: YearMonth = DEFAULT_START) -> int:
    _check(start)
    if not 1 <= month <= MONTHS_PER_YEAR:
        raise InvalidDateError(f"month must be 1..12, got {month}")
    return (year - start[0]) * MONTHS_PER_YEAR + (month - start[1])


def format_turn(turn: int, start: YearMonth = DEFAULT_START) -> str:
    """Return a label such as "Jan 2005"."""
    year, month = turn_to_ym(turn, start)
    return f"{MONTH_ABBR[month - 1]} {year}"


def age_at(turn: int, birth_turn: int) -> int:
    """Age in whole years at `turn`."""
    return (turn - birth_turn) // MONTHS_PER_YEAR
