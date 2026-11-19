"""Saves: a full campaign, cold reloads, one transaction per turn (ADR-0004)."""

from __future__ import annotations

from pathlib import Path

import pytest

from ptk.db import backup, saves, state_io
from ptk.loader import load_balance
from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import GameOverError, SaveExistsError
from ptk.sim.ledger import CASH
from tests.conftest import DATA_DIR

BALANCE = load_balance(DATA_DIR)


def _new(save_dir: Path, data: GameData, slug: str = "t", seed: int = 7) -> Path:
    saves.create_save(
        save_dir,
        slug,
        firm_name="Founders LLP",
        scenario_id="biglaw_spinout",
        difficulty="standard",
        data=data,
        balance=BALANCE,
        seed=seed,
    )
    return saves.open_save(save_dir, slug)


def test_full_campaign_ends_in_december_2034(
    save_dir: Path, data: GameData, balance: Balance
) -> None:
    path = _new(save_dir, data)
    for turn in range(balance.campaign.standard_turns):
        state, _ = saves.read_state(path)  # a cold reload every month
        assert state.turn == turn and not state.ended
        result = saves.run_turn(path, balance, data)
    assert result.snapshot.turn == 359
    state, balances = saves.read_state(path)
    assert state.save_meta.game_state == "campaign_complete"
    assert state.save_meta.ended_turn == 359
    # PT-M1b: payroll and rent now spend the founders' capital; the books still balance.
    assert sum(balances.values()) == 0
    assert balances[(1, CASH)] < 60_000_000
    with pytest.raises(GameOverError):
        saves.run_turn(path, balance, data)
    backup.wait(path)
    assert len(backup.periodic_backups(path)) == balance.backups.keep_periodic


def test_crash_mid_turn_leaves_save_unchanged(
    save_dir: Path, data: GameData, balance: Balance, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _new(save_dir, data)
    saves.run_turn(path, balance, data)
    before = path.read_bytes()
    real = state_io.write_turn

    def crash(session, *args, **kwargs):  # type: ignore[no-untyped-def]
        real(session, *args, **kwargs)  # every row written, then the process "dies"
        raise RuntimeError("power cut")

    monkeypatch.setattr(saves, "write_turn", crash)
    with pytest.raises(RuntimeError):
        saves.run_turn(path, balance, data)
    state, _ = saves.read_state(path)
    assert state.turn == 1
    monkeypatch.undo()
    saves.run_turn(path, balance, data)
    assert saves.read_state(path)[0].turn == 2
    assert before  # the file existed and was readable before the failed turn


def test_duplicate_save_name_refused(save_dir: Path, data: GameData) -> None:
    _new(save_dir, data)
    with pytest.raises(SaveExistsError):
        _new(save_dir, data)


def test_seed_round_trips_at_the_extremes(save_dir: Path, data: GameData) -> None:
    for i, seed in enumerate((0, 2**63, 2**64 - 1)):
        path = _new(save_dir, data, slug=f"s{i}", seed=seed)
        assert saves.read_state(path)[0].save_meta.master_seed == seed


def test_people_round_trip_through_the_save(save_dir: Path, data: GameData) -> None:
    from ptk.sim.setup import new_game

    path = _new(save_dir, data, slug="people", seed=11)
    state, _ = saves.read_state(path)
    fresh = new_game(
        name="people",
        firm_name="Founders LLP",
        master_seed=11,
        scenario_id="biglaw_spinout",
        difficulty="standard",
        data=data,
        balance=BALANCE,
    ).state
    assert state.people == fresh.people
    assert state.employments == fresh.employments
    assert state.reveals == fresh.reveals


def test_hiring_round_trips_and_replays(save_dir: Path, data: GameData, balance: Balance) -> None:
    """PT-M1b: actions in their own transactions plus turns, reloaded cold each time, give
    the same state as the same actions and turns played in memory (ADR-0014 replay)."""
    from ptk.db.models import DecisionLogRow, InboxItemRow
    from ptk.db.session import make_sessionmaker, shared_engine
    from ptk.sim.hiring.actions import Interview, MakeOffer, OpenSearch
    from tests.hiring_helpers import start

    path = _new(save_dir, data, slug="h", seed=19)
    game = start(data, balance, seed=19)
    fid = game.founder_id

    def both(action) -> None:  # type: ignore[no-untyped-def]
        saves.run_action(path, action, balance, data)
        game.act(action)

    both(OpenSearch(fid, "corporate_ma", "campus"))
    both(OpenSearch(fid, "ip", "recruiter"))
    for _ in range(8):
        saves.run_turn(path, balance, data)
        game.advance()
        state, _ = saves.read_state(path)
        game.seq = 0
        for c in [c for c in state.candidates if c.status == "open"][:2]:
            if state.pending_offer_for(c.person_id) is None and (
                c.channel != "campus" or state.turn == c.expires_turn
            ):
                both(Interview(fid, c.person_id))
                both(MakeOffer(fid, c.person_id, int(c.ask_cents * 1.05)))
    state, balances = saves.read_state(path)
    from dataclasses import replace

    assert state == replace(game.state, save_meta=replace(game.state.save_meta, name="h"))
    assert balances == {k: v for k, v in game.balances.items() if v != 0} | {
        k: v for k, v in balances.items() if v == 0
    }
    sessions = make_sessionmaker(shared_engine(path))
    with sessions() as session:
        logged = session.query(DecisionLogRow).count()
        inbox = session.query(InboxItemRow).count()
    assert logged >= 4
    assert inbox > 0
