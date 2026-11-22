"""PT-M16 invariants: reputation stays in 0-100 under any sequence of pulses, months and press
answers; credibility and feuds stay in 0-100 (spec 12.1-12.2)."""

from __future__ import annotations

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from ptk.loader import load_balance, load_game_data
from ptk.sim.press import characters, moments
from ptk.sim.reputation import formulas as fx
from ptk.sim.reputation import phase
from tests.conftest import DATA_DIR
from tests.matters_support import game

DATA = load_game_data(DATA_DIR)
BALANCE = load_balance(DATA_DIR)
START = game(DATA, BALANCE)
FIRMS = sorted({e.firm_id for e in START.standing.reputation.entries})[:6]
PRACTICES = (None, *DATA.practice_keys)

pulse = st.tuples(
    st.sampled_from(FIRMS),
    st.sampled_from(PRACTICES),
    st.floats(-150, 150, allow_nan=False),
)
step = st.one_of(
    st.tuples(st.just("pulse"), pulse),
    st.tuples(st.just("month"), st.none()),
    st.tuples(st.just("cred"), st.floats(-80, 80, allow_nan=False)),
    st.tuples(st.just("feud"), st.floats(-80, 80, allow_nan=False)),
)


@settings(max_examples=40, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(st.lists(step, max_size=12))
def test_reputation_credibility_and_feuds_stay_in_range(steps: list[tuple[str, object]]) -> None:
    state = START
    rival = FIRMS[-1]
    for kind, arg in steps:
        if kind == "pulse":
            fid, practice, points = arg  # type: ignore[misc]
            state = fx.apply_pulse(state, fid, points, "test", BALANCE, practice)
        elif kind == "month":
            state = phase.month(state, DATA, BALANCE)
        elif kind == "cred":
            state = moments.adjust_credibility(state, arg, "test", BALANCE)  # type: ignore[arg-type]
        else:
            state = characters.add_feud(state, rival, arg, "test", BALANCE)  # type: ignore[arg-type]
    assert all(0.0 <= e.value <= 100.0 for e in state.standing.reputation.entries)
    assert all(0.0 <= e.mean <= 100.0 for e in state.standing.reputation.entries)
    assert all(0.0 <= v <= 100.0 for _, v in state.standing.reputation.prestige)
    cred = state.standing.press.credibility
    assert cred is None or 0.0 <= cred <= 100.0
    assert all(0.0 <= f.score <= 100.0 for f in state.standing.press.feuds)
