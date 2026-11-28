"""ADR-0015's replay test: delegate actions are logged for history but never re-applied as
inputs. Replaying the starting state, then each turn's player actions in `seq` order, then
`advance_turn`, recomputes the delegates' actions exactly and reaches the same save."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from simcore_llm.offline import MockLLMAdapter
from simcore_llm.settings import LLMSettings
from sqlalchemy import select

from ptk.db import saves
from ptk.db.core import make_sessionmaker, shared_engine
from ptk.db.models import DecisionLogRow
from ptk.db.org_io import action_from_payload, run_org_action
from ptk.events.service import Writer, write_pending_events
from ptk.sim import turn as turn_module
from ptk.sim.data_models import Balance, GameData
from ptk.sim.decisions import Decisions
from ptk.sim.ledger import apply_entries
from ptk.sim.org.actions import CreatePlan, CreateUnit, MovePerson, SetLeader, apply_org_action
from ptk.sim.setup import new_game
from ptk.sim.streams import RngFactory
from ptk.sim.turn import advance_turn
from tests.org_fake_hiring import FakeHiring

SEED, TURNS = 21, 8


def _log(path: Path) -> list[DecisionLogRow]:
    with make_sessionmaker(shared_engine(path))() as session:
        return list(
            session.scalars(
                select(DecisionLogRow).order_by(DecisionLogRow.turn, DecisionLogRow.seq)
            )
        )


def test_replay_recomputes_delegate_actions(
    save_dir: Path, data: GameData, balance: Balance, monkeypatch: pytest.MonkeyPatch
) -> None:
    played = FakeHiring(seed=SEED)
    monkeypatch.setattr(turn_module, "delegate_hiring", lambda: played)
    saves.create_save(
        save_dir, "replay", firm_name="Replay LLP", scenario_id="group_lift",
        difficulty="standard", data=data, balance=balance, seed=SEED,
    )  # fmt: skip
    path = saves.open_save(save_dir, "replay")
    state, _ = saves.read_state(path)
    fid = state.founder_of(1)
    assert fid is not None
    lit = next(p.id for p in state.people if p.level == "associate_6")
    corp = next(p.id for p in state.people if p.level == "associate_5")

    def player(action: object) -> int | None:
        out = run_org_action(path, action, balance, data)  # type: ignore[arg-type]
        return out.unit_id

    for turn in range(TURNS):
        if turn == 0:
            g1 = player(CreateUnit(fid, "practice_group", practice="commercial_litigation"))
            assert g1 is not None
            player(MovePerson(fid, lit, g1))
            player(SetLeader(fid, g1, lit))
            player(CreatePlan(fid, lit, "commercial_litigation", 2, "job_post", 10500, unit_id=g1))
        if turn == 3:  # a second delegate joins mid-game
            g2 = player(CreateUnit(fid, "practice_group", practice="corporate_ma"))
            assert g2 is not None
            player(MovePerson(fid, corp, g2))
            player(SetLeader(fid, g2, corp))
            player(
                CreatePlan(
                    fid, corp, "corporate_ma", 3, "any", 11000, unit_id=g2, focus="potential"
                )
            )
        saves.run_turn(path, balance, data, answer_critical=True)
    final, _ = saves.read_state(path)
    rows = _log(path)
    logged = {
        t: [json.loads(r.payload_json) for r in rows if r.turn == t and r.source == "delegate"]
        for t in range(TURNS)
    }
    assert sum(len(v) for v in logged.values()) > 10  # delegates really acted
    assert {p["actor_id"] for v in logged.values() for p in v} == {lit, corp}

    # Replay from the starting state with a fresh hiring world: player actions are inputs,
    # delegate actions are recomputed.
    replayed = FakeHiring(seed=SEED)
    game = new_game(
        name="replay", firm_name="Replay LLP", master_seed=SEED, scenario_id="group_lift",
        difficulty="standard", data=data, balance=balance,
    )  # fmt: skip
    state = game.state
    # PT-M4: the partnership reads cash, so the replay carries the ledger as the save did
    ledger = apply_entries({}, game.ledger_entries)
    rng = RngFactory(SEED)
    writer = Writer(MockLLMAdapter(), LLMSettings(), lambda: 1_000_000.0)
    for t in range(TURNS):
        for r in rows:
            if r.turn == t and r.source == "player":
                state = apply_org_action(
                    state, action_from_payload(r.payload_json), balance, data
                ).state
        result = advance_turn(
            state,
            Decisions(),
            rng,
            balance,
            data,
            ledger,
            hiring_hook=replayed,
            answer_critical=True,
        )
        ledger = apply_entries(ledger, result.ledger_entries)
        recomputed = [json.loads(json.dumps(a.payload())) for a in result.delegate_actions]
        assert recomputed == logged[t], f"turn {t}"
        # PT-M6: the event service writes the month's events after the turn, as the save did
        # (the same adapter gives the same words and choices; TST's replay copies them).
        state = write_pending_events(result.new_state, 0, writer, balance, data)
    assert state.org == final.org
    assert state.people == final.people
    assert played.draw_log == replayed.draw_log
