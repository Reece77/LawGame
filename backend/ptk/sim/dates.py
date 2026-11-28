"""Partner Track's calendar defaults over sim-core's calendar (ADR PT-0002, ADR PT-0019).

The arithmetic is `simcore.kernel.calendar`'s. Engine code always passes the save's
`start_ym`; these wrappers only keep PT's own default start, January 2005 (sim-core's default
is TST's January 2010), for callers that name none.
"""

from __future__ import annotations

from typing import Final

from simcore.kernel import calendar as core
from simcore.kernel.calendar import YearMonth, age_at

DEFAULT_START: Final[YearMonth] = (2005, 1)

__all__ = ["DEFAULT_START", "YearMonth", "age_at", "format_turn", "turn_to_ym", "ym_to_turn"]


def turn_to_ym(turn: int, start: YearMonth = DEFAULT_START) -> YearMonth:
    return core.turn_to_ym(turn, start)


def ym_to_turn(year: int, month: int, start: YearMonth = DEFAULT_START) -> int:
    return core.ym_to_turn(year, month, start)


def format_turn(turn: int, start: YearMonth = DEFAULT_START) -> str:
    return core.format_turn(turn, start)
