"""Golden seeds (ADR-0002): the same seed and decisions give identical results. Regenerate
with `uv run pytest tests/golden --update-golden` and record the reason in CHANGELOG.md."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest

from ptk.db import saves
from ptk.sim.data_models import Balance, GameData

SNAPSHOTS = Path(__file__).parent / "snapshots"
SEEDS = (1, 2, 3)


def _fingerprint(path: Path, balance: Balance, data: GameData) -> dict[str, object]:
    digest = hashlib.sha256()
    for _ in range(balance.campaign.standard_turns):
        result = saves.run_turn(path, balance, data, answer_critical=True)  # a script (PT-M6)
        payload = {
            "turn": result.snapshot.turn,
            "kpis": [f.kpis() for f in result.snapshot.firms],
            "entries": [
                (e.memo, [(ln.account, ln.amount) for ln in e.lines]) for e in result.ledger_entries
            ],
            "log": [(i.kind, i.message) for i in result.log_items],
        }
        digest.update(json.dumps(payload, sort_keys=True).encode())
        if result.new_state.ended:  # PT-M7: an unmanaged firm may dissolve before 2034
            break
    state, balances = saves.read_state(path)
    people = [
        [
            p.id,
            p.first_name,
            p.last_name,
            p.role,
            p.level,
            p.birth_turn,
            p.potential_ability,
            p.skills.items,
            p.personality.items,
            p.hidden.items,
            p.familiarity.items,
            p.tags,
            p.interests,
            p.school_tier,
            p.strain,
            p.book_cents,
        ]
        for p in state.people
    ]
    # PT-M3a: same seed, same intake and outcomes
    matters = [
        [
            m.id,
            m.client_id,
            m.practice,
            m.kind_key,
            m.opened_turn,
            m.expected_fees_cents,
            m.status,
            m.outcome,
            m.closed_turn,
            m.worked_tenths,
            m.wip_cents,
        ]
        for m in state.market.matters
    ]
    relationships = [
        [r.client_id, round(r.score, 9), r.fees_12m] for r in state.market.relationships
    ]
    return {
        "people": hashlib.sha256(json.dumps(people).encode()).hexdigest(),
        "matters": hashlib.sha256(json.dumps(matters).encode()).hexdigest(),
        "matter_outcomes": sorted(
            [o, n] for o, n in Counter(m.outcome or m.status for m in state.market.matters).items()
        ),
        "relationships": hashlib.sha256(json.dumps(relationships).encode()).hexdigest(),
        "names": [f"{p.first_name} {p.last_name}" for p in state.people],
        "final_turn": state.turn,
        "game_state": state.save_meta.game_state,
        "balances": sorted([f, a, v] for (f, a), v in balances.items()),
        "sha256": digest.hexdigest(),
    }


@pytest.mark.parametrize("seed", SEEDS)
def test_golden_seed(
    seed: int, save_dir: Path, data: GameData, balance: Balance, request: pytest.FixtureRequest
) -> None:
    saves.create_save(
        save_dir,
        f"g{seed}",
        firm_name="Founders LLP",
        scenario_id="biglaw_spinout",
        difficulty="standard",
        data=data,
        balance=balance,
        seed=seed,
    )
    got = _fingerprint(saves.open_save(save_dir, f"g{seed}"), balance, data)
    target = SNAPSHOTS / f"seed_{seed}.json"
    if request.config.getoption("--update-golden"):
        SNAPSHOTS.mkdir(exist_ok=True)
        target.write_text(json.dumps(got, indent=2, sort_keys=True) + "\n")
    assert target.exists(), "no golden snapshot: run with --update-golden"
    assert json.loads(target.read_text()) == got


def _world_fingerprint(data: GameData, balance: Balance, seed: int) -> dict[str, object]:
    """PT-M10: a save's seeded world from January 2026 (ptk.sim.macro_seed): its indices, rate
    rises and salary scale; history before it is asserted equal across seeds instead."""
    from ptk.sim.macro_seed import world_data

    world = world_data(data, balance, seed)
    points = [[p.ym, sorted(p.values.items())] for p in world.macro.points if p.ym >= (2026, 1)]
    rises = sorted((y, r) for y, r in world.macro.rate_rise.items() if y >= 2026)
    scale = [[r.from_ym, r.salaries] for r in world.salary_scale.scale]
    return {
        "indices": hashlib.sha256(json.dumps(points).encode()).hexdigest(),
        "rate_rise": rises,
        "scale": scale,
    }


def test_golden_seeded_world(
    data: GameData, balance: Balance, request: pytest.FixtureRequest
) -> None:
    """Every seed's world is reproducible; two seeds share history to December 2025 and diverge
    from January 2026 (PT-M10's acceptance criterion)."""
    from ptk.sim.macro import level
    from ptk.sim.macro_data import SERIES
    from ptk.sim.macro_seed import world_data

    got = {str(seed): _world_fingerprint(data, balance, seed) for seed in SEEDS}
    target = SNAPSHOTS / "seeded_world.json"
    if request.config.getoption("--update-golden"):
        target.write_text(json.dumps(got, indent=2, sort_keys=True) + "\n")
    assert target.exists(), "no golden snapshot: run with --update-golden"
    assert json.loads(json.dumps(got)) == json.loads(target.read_text())
    a, b = (world_data(data, balance, s) for s in SEEDS[:2])
    history = [(y, m) for y in range(2005, 2026) for m in range(1, 13)]
    assert all(level(a.macro, s, ym) == level(b.macro, s, ym) for s in SERIES for ym in history)
    assert any(level(a.macro, s, (2026, 1)) != level(b.macro, s, (2026, 1)) for s in SERIES)
