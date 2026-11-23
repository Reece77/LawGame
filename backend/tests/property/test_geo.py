"""PT-M11 properties: leases balance and clear; no lawyer leads a matter where they are not
admitted; the offices' P&Ls sum to the firm's."""

from __future__ import annotations

from dataclasses import replace
from functools import cache

from hypothesis import given, settings
from hypothesis import strategies as st

from ptk.loader import load_balance, load_game_data
from ptk.sim.data_models import Balance, GameData
from ptk.sim.decisions import Decisions
from ptk.sim.geo.admissions import may_lead
from ptk.sim.geo.models import Office
from ptk.sim.geo.offices import closing_entries, month_entries, office_pnl, signing_entries
from ptk.sim.ledger import LEASES, PPE, RIGHT_OF_USE, apply_entries
from ptk.sim.matters.models import Matter
from ptk.sim.matters.staffing import staff_matter
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState, with_people
from ptk.sim.turn import advance_turn
from tests.conftest import DATA_DIR
from tests.geo_support import london_game
from tests.matters_support import solvent


@cache
def _loaded() -> tuple[GameData, Balance]:
    return load_game_data(DATA_DIR), load_balance(DATA_DIR)


@cache
def _london(seed: int) -> GameState:
    data, balance = _loaded()
    return london_game(data, balance, seed).state


@settings(max_examples=60, deadline=None)
@given(
    rent=st.integers(1, 10_000_000),
    term=st.integers(1, 180),
    fit_out=st.integers(0, 50_000_000),
    close_after=st.integers(0, 200),
)
def test_a_lease_balances_and_clears(rent: int, term: int, fit_out: int, close_after: int) -> None:
    _, balance = _loaded()
    office = Office(1, 1, "london", 10, 0, "team_lift", term, rent, fit_out, 0)
    entries = list(signing_entries(office, 0))
    months = min(close_after, term)
    for t in range(months):
        entries += month_entries(office, t)
    if months < term:
        entries += closing_entries(office, months, balance)
    for e in entries:
        assert sum(ln.amount for ln in e.lines) == 0
    b = dict(apply_entries({}, entries))
    assert b.get((1, LEASES), 0) == 0
    assert b.get((1, RIGHT_OF_USE), 0) == 0
    assert b.get((1, PPE), 0) == 0


KINDS = (("deal", None), ("case", "sdny"), ("case", "ddel"), ("case", "ew_commercial"), ("case", "icc"))


@settings(max_examples=40, deadline=None)
@given(
    seed=st.integers(1, 3),
    london=st.booleans(),
    kind=st.sampled_from(KINDS),
    practice=st.sampled_from(("corporate_ma", "commercial_litigation", "banking_finance")),
    grants=st.lists(st.sampled_from(("us_ny", "ew", "ew_rfl", "us_de")), max_size=6),
    seed_people=st.integers(0, 10_000),
)
def test_no_lawyer_leads_a_matter_where_they_are_not_admitted(
    seed: int,
    london: bool,
    kind: tuple[str, str | None],
    practice: str,
    grants: list[str],
    seed_people: int,
) -> None:
    data, balance = _loaded()
    state = _london(seed)
    staff = [state.person(pid) for pid in state.staff_ids(1)]
    # scatter admissions over the firm's people (and strip some)
    people = []
    for i, p in enumerate(staff):
        g = grants[(i + seed_people) % len(grants)] if grants else None
        bars = set(p.bar_admissions)
        if g is not None and (i + seed_people) % 3 == 0:
            bars.discard(g)
        elif g is not None:
            bars.add(g)
        people.append(replace(p, bar_admissions=tuple(sorted(bars))))
    state = with_people(state, people)
    client = next(c for c in state.market.clients if (c.city == "london") == london)
    matter = Matter(
        id=state.market.next_matter_id,
        firm_id=1,
        client_id=client.id,
        practice=practice,
        kind_key="x",
        kind=kind[0],
        name="m",
        opened_turn=state.turn,
        planned_months=6,
        expected_fees_cents=50_000_000,
        hours_needed_tenths=5_000,
        court=kind[1],
    )
    staffed = staff_matter(state, matter, data, balance)
    if staffed.lead_id is not None:
        assert may_lead(state, state.person(staffed.lead_id), staffed, data)


@settings(max_examples=3, deadline=None)
@given(seed=st.integers(1, 50))
def test_played_months_keep_leads_admitted_and_pnls_summed(seed: int) -> None:
    data, balance = _loaded()
    state = london_game(data, balance, seed).state
    for _ in range(6):
        result = advance_turn(state, Decisions(), RngFactory(seed), solvent(balance), data, {})
        state = result.new_state
        for m in state.market.open_matters(1):
            if m.lead_id is not None and m.auto_staff:
                assert may_lead(state, state.person(m.lead_id), m, data)
        entries = [e for e in result.ledger_entries if e.firm_id == 1]
        types = {a.code: a.type for a in data.accounts}
        firm = -sum(
            ln.amount for e in entries for ln in e.lines if types[ln.account] in ("income", "expense")
        )
        assert sum(office_pnl(entries, 1, data).values()) == firm
