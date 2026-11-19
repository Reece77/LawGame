"""Golden seeds (ADR-0002): the same seed and decisions give identical results. Regenerate
with `uv run pytest tests/golden --update-golden` and record the reason in CHANGELOG.md."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from ptk.db import saves
from ptk.sim.data_models import Balance, GameData

SNAPSHOTS = Path(__file__).parent / "snapshots"
SEEDS = (1, 2, 3)


def _fingerprint(path: Path, balance: Balance, data: GameData) -> dict[str, object]:
    digest = hashlib.sha256()
    for _ in range(balance.campaign.standard_turns):
        result = saves.run_turn(path, balance, data)
        payload = {
            "turn": result.snapshot.turn,
            "kpis": [f.kpis() for f in result.snapshot.firms],
            "entries": [
                (e.memo, [(ln.account, ln.amount) for ln in e.lines]) for e in result.ledger_entries
            ],
            "log": [(i.kind, i.message) for i in result.log_items],
        }
        digest.update(json.dumps(payload, sort_keys=True).encode())
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
    return {
        "people": hashlib.sha256(json.dumps(people).encode()).hexdigest(),
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
