"""PT-M9's acceptance runs (run with -s to see the printed readings).

1. A 100-lawyer firm (PT-M8's stage-3 led firm) with every area that can be automated given to
   its owner plays a year with no player action beyond one-offs (approving each proposal),
   with a digest each month and no area past its limits. Knowledge and AI is the one area that
   cannot be automated (PT-M14).
2. `steady_automated` against steady: 2015 revenue and December 2015 PEP, the medians of
   seeds 1-40, within 20% (printed; nightly).
"""

from __future__ import annotations

import statistics

import pytest

from ptk.balance.report import play
from ptk.balance.seeds import SEEDS as BALANCE_SEEDS
from ptk.sim.data_models import Balance, GameData
from ptk.sim.decisions import Decisions
from ptk.sim.ledger import apply_entries
from ptk.sim.rng import RngFactory
from ptk.sim.turn import advance_turn
from tests.automation_support import approve_all, automated_firm
from tests.seats_support import funded, steady

SEEDS = BALANCE_SEEDS  # PT-M18: seeds 1-40 (CLAUDE.md 12.1)
BAND = 0.20  # tunable-exempt: the brief's "within 20%"
FINAL_YEAR = 2015
ACTED = ("decision", "mistake", "event")


def test_a_100_lawyer_firm_runs_a_year_on_its_owners(data: GameData, balance: Balance) -> None:
    b = steady(balance)
    state = automated_firm(data, b, lawyers=100)
    firm = state.player.id
    areas = {(o.area, o.slot) for o in state.automation.owners}
    assert {a for a, _ in areas} == set(b.automation.areas) - {"knowledge"}
    balances = funded(state)
    rng = RngFactory(state.save_meta.master_seed)
    approvals = decisions = 0
    for _ in range(12):
        state, balances, n = approve_all(state, data, b, balances)
        approvals += n
        r = advance_turn(state, Decisions(), rng, b, data, balances, answer_critical=True)
        balances = dict(apply_entries(balances, r.ledger_entries))
        state = r.new_state
        digests = [i for i in r.log_items if i.kind == "automation_digest"]
        assert len(digests) == 1, "a digest every month"
        owners = {(o.area, o.slot): o for o in state.automation.owners}
        month: dict[tuple[str, int], int] = {}
        for d in r.area_decisions:
            if d.kind not in ACTED:
                continue
            decisions += 1
            o = owners.get((d.area, d.slot))
            if o is None:
                continue  # the owner left this month and the area came back
            assert d.commitment_cents == 0 or d.commitment_cents < o.limit_cents
            month[(d.area, d.slot)] = month.get((d.area, d.slot), 0) + d.commitment_cents
        for key, total in month.items():
            assert total <= owners[key].monthly_cents
    assert not state.ended
    assert decisions > 0
    print(
        f"\n100-lawyer automated year: {decisions} owner decisions, {approvals} one-offs and "
        f"proposals approved, {len(state.automation.owners)} areas automated at the end "
        f"(firm {firm})"
    )


@pytest.mark.nightly
@pytest.mark.xfail(
    strict=False,
    reason="PT-M18 (the product manager's decisions, Reece, 2026-11-24 and 2026-11-25: "
    "non-strict, seed variance under rule 4): automated steady's delegated hiring grows the "
    "firm more slowly than steady's own growth rule. Revenue / PEP gaps, main 04efa78: seeds "
    "1-10 -21.5% / +9.1% (fails), seeds 11-40 -18.6% / -11.5% (passes); PT-M12's twenty "
    "practices: seeds 1-10 -34.3% / -17.7%, seeds 11-40 -31.5% / -2.1% (docs/tasks/PT-M12-"
    "all-twenty-practices.md). Earlier: PT-M7c seeds 1-10 +4.2% / +31.0%, seeds 11-40 "
    "-41.8% / -21.5%",
)
def test_steady_automated_is_within_20_percent_of_steady() -> None:
    from concurrent.futures import ProcessPoolExecutor

    jobs = [(s, seed) for s in ("steady", "steady-automated") for seed in SEEDS]
    with ProcessPoolExecutor() as pool:
        results = list(pool.map(play, [j[0] for j in jobs], [j[1] for j in jobs]))

    def medians(name: str) -> tuple[float, float]:
        runs = [r for r in results if r.strategy == name]
        revenue = statistics.median(r.year_revenue(FINAL_YEAR) for r in runs)
        peps = []
        for r in runs:
            d = r.december(FINAL_YEAR)
            peps.append(0 if r.dissolved or d is None or d.pep_cents is None else d.pep_cents)
        return revenue, statistics.median(peps)

    rev, pep = medians("steady")
    arev, apep = medians("steady-automated")
    print(
        f"\nsteady 2015 revenue ${rev / 1e8:.2f}M, PEP ${pep / 1e8:.2f}M; steady_automated "
        f"${arev / 1e8:.2f}M ({arev / rev - 1:+.1%}), PEP ${apep / 1e8:.2f}M "
        f"({apep / pep - 1:+.1%}) (medians, seeds 1-40)"
    )
    assert abs(arev / rev - 1) <= BAND
    assert abs(apep / pep - 1) <= BAND
