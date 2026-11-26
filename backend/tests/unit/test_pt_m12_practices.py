"""PT-M12 sub-task 2: the twenty practices' data, and a practice nobody touches changes nothing."""

from __future__ import annotations

from pathlib import Path

import pytest

from ptk.balance.game import start_game
from ptk.balance.seats import fill_seats
from ptk.balance.strategies import PLAYABLE
from ptk.loader import load_balance, load_game_data
from tests.pt_m12_support import DATA, V2, dormant_data_dir, v1_data_dir

V1_MARKET_CENTS = 1_400_000_000_000  # v1 dossier s3: the NY large-firm market, $14.0bn


@pytest.fixture(scope="module")
def data():  # type: ignore[no-untyped-def]
    return load_game_data(DATA)


def test_twenty_practices_load_with_every_column(data) -> None:  # type: ignore[no-untyped-def]
    keys = data.practice_keys
    assert len(keys) == 20 and keys[10:] == V2
    for p in data.practices:
        assert data.practice_role(p.key)  # one lawyer role each
        assert set(p.cross_sell) == set(keys) - {p.key}  # every pair
    for p in data.practices[10:]:
        assert p.billing_models  # spec 7.7's mix per practice


def test_cross_sell_is_symmetric_where_both_sides_are_given(data) -> None:  # type: ignore[no-untyped-def]
    for p in data.practices:
        for q, v in p.cross_sell.items():
            if p.key in V2 or q in V2:
                assert data.practice(q).cross_sell[p.key] == v


def test_twenty_total_within_15_percent_of_the_dossier_market(data) -> None:  # type: ignore[no-untyped-def]
    total = sum(p.demand_cents for p in data.practices)
    assert abs(total / V1_MARKET_CENTS - 1) <= 0.15


def test_every_value_is_cited_or_marked() -> None:
    text = (DATA / "practices.yaml").read_text()
    block = text[text.index("- key: international_arbitration") :]
    for line in block.splitlines():
        if "demand_cents:" in line or "rates:" in line or "beta:" in line:
            assert "[" in line and "]" in line, line  # [S], [D], [A] or [spec]


def _play(data_dir: Path, turns: int) -> list[object]:
    data, balance = load_game_data(data_dir), load_balance(data_dir)
    g = start_game(data, balance, 1)
    v1 = data.practice_keys[:10]
    out: list[object] = []
    for _ in range(turns):
        fill_seats(g)
        PLAYABLE["steady"](g)
        g.turn()
        out.append(
            (
                g.state.turn,
                sorted(g.balances.items()),
                [(i.kind, i.message) for i in g.logs],
            )
        )
    people = [
        (
            p.id,
            p.first_name,
            p.last_name,
            p.role,
            p.level,
            p.skills.items,
            p.familiarity.items[: len(v1)],
        )
        for p in g.state.people
    ]
    matters = [
        (m.id, m.client_id, m.practice, m.kind_key, m.expected_fees_cents, m.status, m.outcome)
        for m in g.state.market.matters
    ]
    out.append((people, matters, sorted(g.balances.items())))
    return out


@pytest.mark.parametrize(
    "turns",
    [48, pytest.param(132, marks=pytest.mark.nightly)],  # 132: over 60 s (PT-M11)
)
def test_a_practice_nobody_touches_changes_nothing(tmp_path: Path, turns: int) -> None:
    """Seed 1, steady: the v2 practices present but untouched (no demand, no mix, no
    strength) play exactly as v1's ten alone, month by month (48 months in check, to
    December 2015 nightly)."""
    v1 = _play(v1_data_dir(tmp_path / "v1"), turns)
    dormant = _play(dormant_data_dir(tmp_path / "dormant"), turns)
    for a, b in zip(v1, dormant, strict=True):
        assert a == b
