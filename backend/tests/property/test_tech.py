"""PT-M14 (property tests; ADR PT-0011 3, PT-0005): hours on each task equal base hours x the
firm's efficiency on it; efficiency and adoption stay in [0, 1]; a month with technology still
reconciles money with hours (every record's value is its tenths x its rate) and every entry
balances in integer cents.
"""

from __future__ import annotations

from dataclasses import replace

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from ptk.sim.billing.books import WIP_POSTED
from ptk.sim.calendar import ym_to_turn
from ptk.sim.data_models import Balance, GameData
from ptk.sim.decisions import Decisions
from ptk.sim.interfaces import tech_hours
from ptk.sim.ledger import WIP
from ptk.sim.matters.models import Matter
from ptk.sim.matters.progress import advance_phases
from ptk.sim.rng import RngFactory
from ptk.sim.tech import adoption as ad
from ptk.sim.tech import efficiency as ef
from ptk.sim.tech.models import EraAdoption, FirmTech, with_era, with_firm
from ptk.sim.turn import advance_turn
from tests.matters_support import game, grown_firm, solvent

PROPERTY = settings(
    max_examples=12, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
levels = st.lists(st.floats(0, 1), min_size=6, max_size=6)


def _adopt(state, data, values, year):  # type: ignore[no-untyped-def]
    firm = FirmTech(firm_id=state.player.id)
    for key, v in zip(data.legal_eras.keys, values, strict=True):
        firm = with_era(firm, EraAdoption(era=key, adoption=v, platform=True), data.legal_eras.keys)
    state = replace(state, tech=with_firm(state.tech, firm))
    return replace(state, turn=ym_to_turn(year, 6, state.save_meta.start_ym))


@PROPERTY
@given(values=levels, year=st.integers(2005, 2034), seed=st.integers(1, 1000))
def test_hours_on_each_task_are_base_times_efficiency(
    data: GameData, balance: Balance, values: list[float], year: int, seed: int
) -> None:
    """A phase worked at skill 10 completes after exactly its base hours on each task x the
    task's efficiency (Σ over the phase's task mix)."""
    state = _adopt(game(data, balance, seed), data, values, year)
    eff = ef.firm_efficiency(state, state.player.id, data)
    assert all(0.0 <= v <= 1.0 for v in eff.values())
    view = tech_hours(state, state.player.id, data, balance)
    kind = data.market.kinds["deal"]
    total_tenths = 100_000
    m = Matter(
        id=1,
        firm_id=state.player.id,
        client_id=1,
        practice="corporate_ma",
        kind_key="private_ma",
        kind="deal",
        name="x",
        opened_turn=0,
        planned_months=6,
        expected_fees_cents=1,
        hours_needed_tenths=total_tenths,
    )
    for i, phase in enumerate(kind.phases):
        weights = sum(phase.tasks.values())
        base = {t: phase.share * total_tenths / 10 * w / weights for t, w in phase.tasks.items()}
        needed = sum(base[t] * eff[t] for t in base)  # hours on each task = base x efficiency
        factor = view.factor(phase.tasks)
        assert needed == pytest.approx(phase.share * total_tenths / 10 * factor)
        # worked hours h at skill 10 make output h / factor: exactly `needed` finishes it
        start = replace(m, phase_index=i, phase_progress=0.0)
        done, _, finished = advance_phases(start, needed / factor * (1 - 1e-9), kind)
        assert done.phase_index == i
        done, _, finished = advance_phases(start, needed / factor * (1 + 1e-9), kind)
        assert finished == [phase.key]


@PROPERTY
@given(values=levels, seed=st.integers(1, 1000))
def test_adoption_and_money_stay_in_bounds_with_technology(
    data: GameData, balance: Balance, values: list[float], seed: int
) -> None:
    b = solvent(balance)
    state = _adopt(grown_firm(data, b, 12, seed), data, values, 2026)
    firm = state.tech.firm(state.player.id)
    assert firm is not None
    firm = replace(
        firm,
        training_hours=40,
        eras=tuple(replace(e, subscription_bp=10000, rolled_out=True) for e in firm.eras),
    )
    state = replace(state, tech=with_firm(state.tech, firm))
    result = advance_turn(state, Decisions(), RngFactory(seed), b, data, {})
    # PT-0005: money reconciles with hours: WIP posted is the month's hours at standard value
    records = result.new_state.market.hours
    posted = sum(
        line.amount
        for e in result.ledger_entries
        if e.firm_id == state.player.id and e.memo == WIP_POSTED
        for line in e.lines
        if line.account == WIP
    )
    assert posted == sum(r.value_cents for r in records)
    assert all(0 <= r.substantive_tenths <= r.tenths for r in records)
    for e in result.ledger_entries:
        assert sum(line.amount for line in e.lines) == 0
        assert all(isinstance(line.amount, int) for line in e.lines)
    after = result.new_state.tech.firm(state.player.id)
    assert after is not None
    assert all(0.0 <= e.adoption <= 1.0 for e in after.eras)
    _s2, entries, _ = ad.month(result.new_state, data, b)
    assert all(sum(x.amount for x in e.lines) == 0 for e in entries)
