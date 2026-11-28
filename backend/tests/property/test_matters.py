"""PT-M3a invariants under random seeds, months and staffing changes:

- hours reconcile: Σ person-hours = Σ matter-hours + flow hours, every month, and each
  person's month of work is exactly their hours records (ADR PT-0004 2, PT-0005);
- no matter is ever open adverse to a current client without a waiver (ADR PT-0009);
- relationships stay in 0-100, judges' traits in 1-20, hours and values non-negative.
"""

from __future__ import annotations

from dataclasses import replace

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from ptk.loader import load_balance, load_game_data
from ptk.sim.actions import apply_action
from ptk.sim.decisions import Decisions
from ptk.sim.errors import SimError
from ptk.sim.matters.actions import AssignToMatter, SeekWaiver, SetMatterHours
from ptk.sim.matters.conflicts import open_conflicts
from ptk.sim.matters.intake import with_relationship
from ptk.sim.matters.models import Relationship
from ptk.sim.matters.phase import intake_and_staffing
from ptk.sim.state import GameState
from ptk.sim.streams import RngFactory
from ptk.sim.turn import advance_turn
from tests.conftest import DATA_DIR
from tests.matters_support import game, grown_firm, solvent

DATA = load_game_data(DATA_DIR)
BALANCE = load_balance(DATA_DIR)
SCENARIOS = ("biglaw_spinout", "group_lift", "solo_founder")


def _check_month(state: GameState, seed: int) -> None:
    month = intake_and_staffing(state, RngFactory(seed), DATA, BALANCE)
    records = month.state.market.hours
    by_matter = sum(r.tenths for r in records if r.matter_id is not None)
    flow = sum(r.tenths for r in records if r.matter_id is None)
    person_hours = sum(w.total_tenths - w.other_tenths for w in month.work.values())
    assert person_hours == by_matter + flow
    for pid, w in month.work.items():
        mine = [r for r in records if r.person_id == pid]
        assert sum(t for _, t in w.practice_tenths) == sum(r.tenths for r in mine)
        assert w.substantive_tenths == sum(r.substantive_tenths for r in mine)
    assert all(r.tenths > 0 and r.value_cents >= 0 for r in records)
    open_ids = {m.id for m in month.state.market.open_matters(state.player.id)}
    assert {r.matter_id for r in records if r.matter_id is not None} <= open_ids


def _act(state: GameState, action: object, seq: int) -> GameState:
    try:
        return apply_action(
            state,
            action,
            seq=seq,
            rng=RngFactory(seq),
            balance=BALANCE,
            data=DATA,
            ledger_balances={},  # type: ignore[arg-type]
        ).state
    except SimError:
        return state


@settings(max_examples=12, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    seed=st.integers(0, 2**32),
    scenario=st.sampled_from(SCENARIOS),
    months=st.integers(1, 14),
    moves=st.lists(
        st.tuples(st.integers(0, 50), st.integers(0, 50), st.integers(1, 120)), max_size=6
    ),
)
def test_hours_reconcile_and_no_open_conflict(
    seed: int, scenario: str, months: int, moves: list[tuple[int, int, int]]
) -> None:
    state = game(DATA, BALANCE, seed=seed, scenario=scenario)
    founder = state.founder_of(state.player.id)
    assert founder is not None
    for month in range(months):
        _check_month(state, seed)
        # the player changes staffing and seeks waivers between turns
        open_m = state.market.open_matters(state.player.id)
        staff = state.staff_ids(state.player.id)
        for n, (mi, pi, hours) in enumerate(moves):
            if open_m and staff:
                m, p = open_m[mi % len(open_m)], staff[pi % len(staff)]
                action = (
                    SetMatterHours(founder, m.id, p, hours)
                    if m.member(p)
                    else AssignToMatter(founder, m.id, p, hours)
                )
                state = _act(state, action, month * 100 + n + 1)
        for m in [x for x in state.market.matters if x.status == "conflicted"]:
            state = _act(state, SeekWaiver(founder, m.id), month * 100 + 99)
        assert open_conflicts(state.market, state.player.id, state.turn, BALANCE) == []
        state = advance_turn(
            state, Decisions(), RngFactory(seed), solvent(BALANCE), DATA, {}
        ).new_state
        assert open_conflicts(state.market, state.player.id, state.turn, BALANCE) == []
        for r in state.market.relationships:
            assert 0.0 <= r.score <= 100.0 and 0.0 <= r.lost_share <= 1.0
        for m in state.market.matters:
            assert m.worked_tenths >= 0 and m.wip_cents >= 0 and m.hours_needed_tenths > 0
            assert 0.0 <= m.phase_progress <= 1.0


@settings(max_examples=6, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(seed=st.integers(0, 2**32))
def test_unchecked_conflicts_are_flagged_hidden(seed: int) -> None:
    """With checks skipped, every open matter adverse to a current client carries
    hidden_conflict (the invariant's only exception besides waivers)."""
    state = game(DATA, BALANCE, seed=seed, scenario="group_lift")
    state = replace(state, firms=tuple(replace(f, conflict_checks=False) for f in state.firms))
    for _ in range(12):
        state = advance_turn(
            state, Decisions(), RngFactory(seed), solvent(BALANCE), DATA, {}
        ).new_state
        assert open_conflicts(state.market, state.player.id, state.turn, BALANCE) == []
        assert all(not m.checked for m in state.market.matters if m.status != "declined")


def test_judge_traits_in_range() -> None:
    state = game(DATA, BALANCE, seed=8)
    for j in state.market.judges:
        assert all(1.0 <= v <= 20.0 for _, v in j.traits.items)


# A conflict-heavy world: every matter's adverse party is a company, and the firm sits on the
# largest clients' panels, so conflicts arise every few months.
HEAVY = DATA.model_copy(
    update={"practices": tuple(p.model_copy(update={"conflict_bp": 10000}) for p in DATA.practices)}
)
SMALL = BALANCE.model_copy(
    update={"clients": BALANCE.clients.model_copy(update={"generated_count": 20})}
)
GROWN = grown_firm(HEAVY, SMALL, 30, seed=3)
_partner = next(p.id for p in GROWN.people if p.founding_partner)
_market = GROWN.market
for _c in sorted(_market.clients, key=lambda c: -c.revenue_bn)[:40]:  # the largest clients too
    if _market.relationship(_c.id, 1) is None:
        _market = with_relationship(
            _market,
            Relationship(
                _c.id, 1, 55.0, _partner, ("commercial_litigation",), 0, last_instructed_turn=0
            ),
        )
GROWN = replace(GROWN, market=_market)


@settings(max_examples=8, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(seed=st.integers(0, 2**32), months=st.integers(6, 18), ask=st.booleans())
def test_no_open_conflict_in_a_conflict_heavy_world(seed: int, months: int, ask: bool) -> None:
    state = replace(GROWN, save_meta=replace(GROWN.save_meta, master_seed=seed))
    founder = state.founder_of(state.player.id)
    assert founder is not None
    seen = 0
    for month in range(months):
        if ask:
            for m in [x for x in state.market.matters if x.status == "conflicted"]:
                state = _act(state, SeekWaiver(founder, m.id, advance=month % 2 == 0), month + 1)
                assert open_conflicts(state.market, state.player.id, state.turn, SMALL) == []
        state = advance_turn(
            state, Decisions(), RngFactory(seed), solvent(SMALL), HEAVY, {}
        ).new_state
        assert open_conflicts(state.market, state.player.id, state.turn, SMALL) == []
        seen = sum(
            1 for m in state.market.matters if m.status in ("conflicted", "declined") or m.waiver
        )
    assert seen > 0  # the world really is conflict-heavy
