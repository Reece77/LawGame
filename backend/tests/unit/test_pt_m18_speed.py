"""PT-M18 sub-task 6: the turn-time speed-ups give identical results.

The golden seeds and the state cache replay prove the whole turn unchanged; these pin the
helpers themselves: `fastcopy.replace` against `dataclasses.replace`, the sim's dataclasses
having only init fields (which `fastcopy` relies on), and the memoised state lookups against
the scans they replace.
"""

from __future__ import annotations

import dataclasses
import importlib
import inspect
import pkgutil

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import ptk.sim
from ptk.sim import state as state_mod
from ptk.sim.data_models import Balance, GameData
from ptk.sim.fastcopy import replace
from ptk.sim.people.models import Employment
from ptk.sim.rng import STREAM_IDS, RngFactory
from ptk.sim.state import GameState
from tests.matters_support import grown_firm


def _sim_dataclasses() -> list[type]:
    out = []
    for info in pkgutil.walk_packages(ptk.sim.__path__, "ptk.sim."):
        module = importlib.import_module(info.name)
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if obj.__module__ == module.__name__ and dataclasses.is_dataclass(obj):
                out.append(obj)
    return out


def test_every_sim_dataclass_has_only_init_fields() -> None:
    """`fastcopy.replace` calls a class positionally with its fields: every field must be an
    init field (no `init=False`), as `dataclasses.replace` would otherwise treat it apart."""
    classes = _sim_dataclasses()
    assert len(classes) > 100
    bad = [
        f"{cls.__module__}.{cls.__name__}.{f.name}"
        for cls in classes
        for f in dataclasses.fields(cls)
        if not f.init
    ]
    assert bad == []


_FIRM: list[GameState] = []  # the module's firm, for the Hypothesis test


@pytest.fixture(scope="module", autouse=True)
def firm(data: GameData, balance: Balance) -> GameState:
    _FIRM[:] = [grown_firm(data, balance, 12, 1)]
    return _FIRM[0]


def test_fastcopy_matches_dataclasses_replace(firm: GameState) -> None:
    person = firm.people[3]
    for changes in ({}, {"level": "associate_3"}, {"strain": 41.5, "first_name": "Ada"}):
        assert replace(person, **changes) == dataclasses.replace(person, **changes)
    assert replace(firm, turn=firm.turn + 1) == dataclasses.replace(firm, turn=firm.turn + 1)
    # __post_init__ runs as before: AttrSet clamps
    skills = person.skills
    assert replace(skills, items=(("a", 25.0), ("b", 0.0))).items == (("a", 20.0), ("b", 1.0))


def test_fastcopy_refuses_unknown_fields(firm: GameState) -> None:
    with pytest.raises(TypeError, match="no fields"):
        replace(firm.people[0], no_such_field=1)


@settings(max_examples=60, deadline=None)
@given(
    st.dictionaries(
        st.sampled_from(["strain", "book_cents", "potential_ability", "birth_turn"]),
        st.integers(0, 10**6),
    ),
    st.integers(0, 11),
)
def test_fastcopy_property(changes: dict[str, int], index: int) -> None:
    person = _FIRM[0].people[index]
    assert replace(person, **changes) == dataclasses.replace(person, **changes)


def _scan_employment(state: GameState, pid: int) -> Employment | None:
    return next((e for e in state.employments if e.person_id == pid and e.counts_as_staff), None)


def test_memoised_lookups_match_the_scans(firm: GameState) -> None:
    ids = [p.id for p in firm.people] + [10**6]
    ended = dataclasses.replace(firm.employments[0], status="ended", id=10**5)
    # an ended employment first for a person: the staff lookup still finds the active one
    state = dataclasses.replace(firm, employments=(ended, *firm.employments))
    for _ in range(state_mod._INDEX_AFTER + 2):  # past the threshold: the index answers
        for pid in ids:
            assert state.employment_of(pid) == _scan_employment(state, pid)
            assert state.employer_of(pid) == (
                None
                if _scan_employment(state, pid) is None
                else _scan_employment(state, pid).firm_id  # type: ignore[union-attr]
            )
            assert state.person_state(pid) == next(
                (ps for ps in state.person_states if ps.person_id == pid),
                state_mod.PersonState(person_id=pid),
            )
            if pid in {p.id for p in state.people}:
                assert state.person(pid) == next(p for p in state.people if p.id == pid)
            else:
                with pytest.raises(KeyError):
                    state.person(pid)
            assert state.reveal(1, pid) == next(
                (r for r in state.reveals if r.observer_firm_id == 1 and r.person_id == pid), None
            )


@settings(max_examples=300, deadline=None)
@given(
    st.integers(0, 2**64 - 1),
    st.integers(0, 2**33),
    st.sampled_from(sorted(STREAM_IDS)),
    st.lists(st.integers(0, 2**34), max_size=4),
)
def test_streams_match_the_documented_seed_sequence(
    seed: int, turn: int, name: str, key: list[int]
) -> None:
    """`RngFactory.stream` passes the seed's and key's words as SeedSequence's entropy; its
    draws equal `SeedSequence(entropy=seed, spawn_key=(turn, id, *key))`'s, for keys of any
    size (32 bits and over take the documented path)."""
    ours = RngFactory(seed).stream(turn, name, *key)
    seq = np.random.SeedSequence(entropy=seed, spawn_key=(turn, STREAM_IDS[name], *key))
    theirs = np.random.Generator(np.random.PCG64(seq))
    assert ours.integers(0, 2**62, 6).tolist() == theirs.integers(0, 2**62, 6).tolist()
    assert ours.bit_generator.state == theirs.bit_generator.state


def test_reputation_means_match_long_run_mean(data: GameData, balance: Balance) -> None:
    """`means` inlines `long_run_mean` for every firm and practice: the same values."""
    from ptk.sim.reputation import formulas as fx
    from tests.rivals_support import rivals_month, start

    state = start(data, balance, 2)
    rng = RngFactory(2)
    for _ in range(14):  # past a year: rivals' books and the player's record fill in
        state = rivals_month(state, rng, data, balance)
    funds = fx.fundamentals(state, data)
    peps = fx.pep_percentiles(funds)
    refs = fx.share_refs(funds, balance, data.practice_keys)
    record = fx.record_points(state.standing.reputation)
    expected = {
        (f.firm_id, p): fx.long_run_mean(f, p, peps.get(f.firm_id, 0.0), refs[p], record, balance)
        for f in funds
        for p in data.practice_keys
    }
    assert fx.means(state, data, balance, funds) == expected
    assert len(expected) > 1000
