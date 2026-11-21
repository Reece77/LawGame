"""PT-M7 sub-task 5: the practice save pt-2008 (a 60-lawyer firm in June 2008 with a
December 2008 partnership candidate)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from ptk.api.app import create_app
from ptk.db import saves
from ptk.loader import load_balance, load_game_data
from ptk.sim.calendar import turn_to_ym
from ptk.sim.partnership.careers import eligible
from tests.conftest import DATA_DIR


def test_pt_2008_is_a_60_lawyer_firm_in_june_2008_with_a_december_candidate(
    save_dir: Path,
) -> None:
    client = TestClient(create_app())
    made = client.post("/api/practice/pt-2008")
    assert made.status_code == 200, made.text
    game = made.json()
    assert game["date_label"] == "Jun 2008"
    assert client.post("/api/practice/pt-2008").status_code == 409
    assert client.post("/api/practice/nope").status_code == 404

    data, balance = load_game_data(DATA_DIR), load_balance(DATA_DIR)
    path = saves.open_save(save_dir, "pt-2008")
    state = saves.read_state(path)[0]
    lawyers = [
        p
        for e in state.staff(state.player.id)
        if data.role((p := state.person(e.person_id)).role).kind == "lawyer"
    ]
    assert 55 <= len(lawyers) <= 65
    assert turn_to_ym(state.turn, state.save_meta.start_ym) == (2008, 6)
    # through to December 2008 in the save: the seventh-year is an eligible candidate
    for _ in range(6):
        saves.run_turn(path, balance, data, answer_critical=True)
    state = saves.read_state(path)[0]
    assert turn_to_ym(state.turn, state.save_meta.start_ym) == (2008, 12)
    fp = state.partnership.of(state.player.id)
    assert fp is not None
    candidates = [
        pid for pid in state.staff_ids(state.player.id) if eligible(state, fp, pid, balance)
    ]
    assert candidates, "a December 2008 partnership candidate"
    assert client.get("/api/saves/pt-2008/history").status_code == 200


def test_the_practice_save_is_deterministic() -> None:
    from ptk.practice import PRACTICE_SAVES, build

    data, balance = load_game_data(DATA_DIR), load_balance(DATA_DIR)
    a, ea = build(PRACTICE_SAVES["pt-2008"], data, balance)
    b, eb = build(PRACTICE_SAVES["pt-2008"], data, balance)
    assert a == b and ea == eb
