"""A real rival's published path (ADR PT-0008 2): points, interpolation, steps, anchors."""

from __future__ import annotations

import pytest

from ptk.sim.data_models import Balance, GameData
from ptk.sim.rivals.path import build_path, market_factor, path_value


def test_points_hold_at_mid_year_and_interpolate_between(data: GameData, balance: Balance) -> None:
    firm = data.rivals.firms.firm("skadden")
    path = build_path(firm, data.rivals.firms.events)
    rb = balance.rivals
    assert path_value(path, "revenue", 2005.5, rb) == pytest.approx(161_000_000_000)
    assert path_value(path, "revenue", 2009.5, rb) == pytest.approx(210_000_000_000)
    mid = path_value(path, "revenue", 2008.5, rb)
    assert mid is not None and 210_000_000_000 < mid < 217_000_000_000  # geometric
    assert path_value(path, "lawyers", 2005.5, rb) == pytest.approx(1616)


def test_an_outside_merger_is_a_step(data: GameData, balance: Balance) -> None:
    firm = data.rivals.firms.firm("hogan_hartson")
    path = build_path(firm, data.rivals.firms.events)
    rb = balance.rivals
    before = path_value(path, "revenue", 2010.2, rb)
    after = path_value(path, "revenue", 2010.4, rb)
    assert before == pytest.approx(86_450_000_000)  # Hogan & Hartson alone, held
    assert after == pytest.approx(165_200_000_000)  # Hogan Lovells from May 2010


def test_after_the_last_point_the_path_grows_with_the_market(
    data: GameData, balance: Balance
) -> None:
    firm = data.rivals.firms.firm("dla_piper")
    path = build_path(firm, data.rivals.firms.events)
    rb = balance.rivals
    base = path_value(path, "revenue", 2009.5, rb)
    later = path_value(path, "revenue", 2011.5, rb)
    assert base is not None and later is not None
    assert later / base == pytest.approx(market_factor(2009.5, 2011.5, rb))
    assert market_factor(2009.5, 2010.5, rb) == pytest.approx(1 + rb.market_growth[2010])


def test_a_successor_starts_from_its_anchor(data: GameData, balance: Balance) -> None:
    firm = data.rivals.firms.firm("dewey_leboeuf")
    path = build_path(firm, data.rivals.firms.events)
    rb = balance.rivals
    anchor = (2007.79, 95_000_000_000.0)
    assert path_value(path, "revenue", 2007.79, rb, anchor) == pytest.approx(95_000_000_000)
    assert path_value(path, "revenue", 2009.5, rb, anchor) == pytest.approx(91_400_000_000)
