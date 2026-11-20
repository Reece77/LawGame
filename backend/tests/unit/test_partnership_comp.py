"""PT-M4 sub-task 3: comp systems (spec 8.5). Acceptance: under eat what you kill a top
originator's comp is at least 2x the median partner's; under pure lockstep at most the
plateau ratio (printed)."""

from __future__ import annotations

import statistics
from dataclasses import replace

import pytest

from ptk.sim.data_models import Balance, GameData
from ptk.sim.partnership import formulas as fx
from ptk.sim.partnership.actions import CompRound
from tests.partnership_support import Game, add_partner, start


def _firm(data: GameData, balance: Balance, system: str, seed: int = 3) -> Game:
    g = start(data, balance, seed)
    fp = g.fp
    agreement = replace(fp.agreement, comp_system=system)
    g.state = replace(
        g.state,
        partnership=replace(g.state.partnership, firms=(replace(fp, agreement=agreement),)),
    )
    add_partner(g, "corporate_ma", 80_000_000, clients=20, n=1)  # the rainmaker
    for i in range(4):
        add_partner(g, "commercial_litigation", 50_000_000, clients=0, n=2 + i)  # service partners
    g.advance(12)  # to the December allocation
    return g


@pytest.mark.parametrize("system", ["eat_what_you_kill", "lockstep"])
def test_comp_spread(
    system: str, data: GameData, balance: Balance, capsys: pytest.CaptureFixture[str]
) -> None:
    g = _firm(data, balance, system)
    comps = [p.comp_last_cents for p in g.fp.equity_partners]
    # flight may take one, whose draws were their share
    assert len(comps) >= 6 and sum(comps) <= g.fp.last_profit_cents
    orig = {o.person_id: o.cents for o in g.state.market.originations}
    top = max(g.fp.equity_partners, key=lambda p: orig.get(p.person_id, 0))
    median = statistics.median(comps)
    ratio = top.comp_last_cents / median
    spread = max(comps) / min(comps)
    with capsys.disabled():
        print(
            f"\n{system}: top originator / median {ratio:.2f}, max / min {spread:.2f} "
            f"(plateau ratio {25 / 10:.2f})"
        )
    lock = balance.partnership.lockstep
    if system == "eat_what_you_kill":
        assert ratio >= 2.0
    else:
        assert spread <= lock.plateau_points / lock.start_points * (1 + 1e-6)  # cents


def test_weights_sum_to_one(balance: Balance) -> None:
    credits = {
        1: fx.Credits(5_000, 1_000, 1.0),
        2: fx.Credits(0, 3_000, 0.0),
        3: fx.Credits(1_000, 0, 0.5),
    }
    points = {1: 25.0, 2: 10.0, 3: 12.5}
    for system in ("lockstep", "modified_lockstep", "eat_what_you_kill", "committee"):
        w = fx.comp_weights(system, points, credits, {}, balance.partnership)
        assert sum(w.values()) == pytest.approx(1.0)
    lock = fx.comp_weights("lockstep", points, credits, {}, balance.partnership)
    assert lock[1] / lock[2] == pytest.approx(2.5)


def test_split_cents_is_exact() -> None:
    assert fx.split_cents(100, {1: 1.0, 2: 1.0, 3: 1.0}) == {1: 34, 2: 33, 3: 33}
    assert sum(fx.split_cents(-1_001, {1: 2.0, 2: 1.0}).values()) == -1_001
    assert fx.split_cents(10, {1: 0.0, 2: 0.0}) == {1: 5, 2: 5}


def test_lockstep_points_reach_the_plateau(balance: Balance) -> None:
    cfg = balance.partnership.lockstep
    assert [fx.lockstep_points(y, cfg) for y in (0, 1, 6, 7, 12)] == [10, 12.5, 25, 25, 25]
    assert fx.next_points(10, 0, cfg) == 12.5
    assert fx.next_points(12.5, -1, cfg) == 12.5  # held
    assert fx.next_points(10, 2, cfg) == 17.5  # moved up two steps


def test_the_comp_round_gates_a_partner(data: GameData, balance: Balance) -> None:
    g = start(data, balance, 4)
    lateral = add_partner(g, "corporate_ma", 50_000_000, clients=2, n=1)
    g.advance(11)  # the December turn is next
    g.act(CompRound(g.founder, lateral, gate_steps=2))
    before = g.fp.partner(lateral)
    assert before is not None and before.points == 10
    g.advance()
    after = g.fp.partner(lateral)
    assert after is not None and after.points == 17.5
    g.advance()
    assert g.fp.partner(lateral).confidence > 0  # type: ignore[union-attr]


def test_satisfaction(balance: Balance) -> None:
    cfg = balance.partnership
    assert fx.satisfaction(100, 100, 10, 50, cfg) == pytest.approx(0.0)
    assert fx.satisfaction(50, 100, 10, 50, cfg) == pytest.approx(-0.5)
    assert fx.satisfaction(100, 100, 15, 50, cfg) < 0  # ego: they think they did more
    assert fx.satisfaction(100, 50, 10, 200, cfg) == pytest.approx(-0.5)  # market value bites
