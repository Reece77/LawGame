from __future__ import annotations

import pytest

from ptk.sim.dates import age_at, format_turn, turn_to_ym, ym_to_turn
from ptk.sim.errors import InvalidDateError


def test_default_start_is_january_2005() -> None:
    assert turn_to_ym(0) == (2005, 1)
    assert format_turn(0) == "Jan 2005"
    assert format_turn(359) == "Dec 2034"
    assert turn_to_ym(-1) == (2004, 12)


@pytest.mark.parametrize("start", [(2005, 1), (2010, 1), (2010, 7)])
def test_round_trip_for_any_start(start: tuple[int, int]) -> None:
    for turn in range(-30, 400, 7):
        year, month = turn_to_ym(turn, start)
        assert ym_to_turn(year, month, start) == turn


def test_2010_pack() -> None:
    assert turn_to_ym(0, (2010, 1)) == (2010, 1)
    assert format_turn(359, (2010, 1)) == "Dec 2039"
    assert turn_to_ym(0, (2010, 7)) == (2010, 7) and turn_to_ym(6, (2010, 7)) == (2011, 1)


def test_bad_month() -> None:
    with pytest.raises(InvalidDateError):
        ym_to_turn(2005, 13)


def test_age() -> None:
    assert age_at(12 * 30, 0) == 30
