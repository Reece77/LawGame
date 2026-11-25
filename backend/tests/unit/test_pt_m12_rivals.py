"""PT-M12 sub-task 5: rivals' practice mixes cover the twenty practices, and the specialists
the dossier names (an arbitration firm, a private client firm, a plaintiff firm) are
specialists (docs/research/practices-v2.md s8)."""

from __future__ import annotations

from typing import Any

import pytest

from ptk.balance.game import start_game
from ptk.loader import load_balance, load_game_data
from tests.pt_m12_support import DATA, V2


@pytest.fixture(scope="module")
def world() -> Any:
    data, balance = load_game_data(DATA), load_balance(DATA)
    return data, balance, start_game(data, balance, 1).state


def _shares(firm: Any) -> dict[str, float]:
    total = sum(p.lawyers for p in firm.pools)
    return {p.practice: p.lawyers / total for p in firm.pools}


def test_every_personality_mix_names_the_twenty(world: Any) -> None:
    data, balance, _ = world
    for key, pdef in balance.rivals.personalities.items():
        if key in ("plaintiff_firm", "private_client_firm", "arbitration_firm"):
            continue  # specialists name only their practices
        assert set(pdef.mix) == set(data.practice_keys), key


def test_large_rivals_practise_the_new_practices(world: Any) -> None:
    _, _, state = world
    real = [f for f in state.rivals.active if f.kind == "real" and f.lawyers > 500]
    assert real
    for f in real:
        shares = _shares(f)
        assert sum(shares.get(p, 0.0) for p in V2) > 0.05, f.key


@pytest.mark.parametrize(
    ("key", "practice", "least"),
    [
        ("curtis_mallet", "international_arbitration", 0.2),
        ("withers_bergman", "private_client", 0.4),
        ("lieff_cabraser", "mass_torts", 0.6),
    ],
)
def test_specialists_are_specialists(world: Any, key: str, practice: str, least: float) -> None:
    _, _, state = world
    firm = state.rivals.by_key(key)
    assert firm is not None
    shares = _shares(firm)
    assert max(shares, key=lambda p: shares[p]) == practice
    assert shares[practice] >= least


def test_dossier_strengths_lead_their_practices(world: Any) -> None:
    """A firm strong in a new practice has more lawyers in it than its personality's peers."""
    _, _, state = world
    cleary = _shares(state.rivals.by_key("cleary"))
    cravath = _shares(state.rivals.by_key("cravath"))
    assert cleary["antitrust"] > cravath["antitrust"]  # Cleary strong in antitrust, Cravath not
