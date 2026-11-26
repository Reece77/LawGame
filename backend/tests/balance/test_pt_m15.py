"""PT-M15's acceptance runs (run with -s to see the printed readings; nightly).

1. T14 (proposed, docs/balance-targets.md): steady's claim notices per 100 lawyer-years,
   2006-2015, median over seeds 1-10, within the band (the dossier's 2-4 notices a 100 lawyers
   a year, widened for a small firm's sampling).
2. Premiums: steady's premium per lawyer in December 2015, median, within the dossier's band
   ($5,000-$10,000 a lawyer a year).
3. `cowboy` has at least twice steady's claims and disciplinary cases over 2005-2015 on at least
   8 of 10 seeds, and lower PEP in December 2015 on at least 6 of 10.
"""

from __future__ import annotations

import statistics
from concurrent.futures import ProcessPoolExecutor
from functools import cache

import pytest

from ptk.balance.known_misses import Reading, verdict
from ptk.balance.risk import RiskRun, risk_run

SEEDS = range(1, 11)
T14_BAND = (1.5, 5.0)  # tunable-exempt: T14's band, claim notices a 100 lawyer-years
PREMIUM_BAND = (500_000, 1_000_000)  # tunable-exempt: the dossier's $5k-$10k a lawyer a year
COWBOY_SEEDS = 8  # tunable-exempt: the brief's "at least 8 of 10"
PEP_SEEDS = 6  # tunable-exempt: the brief's "at least 6 of 10"
WORKERS = 4  # tunable-exempt
# PT-M18 (the product manager's decision, Reece, 2026-11-25: non-strict, main fails it on
# seeds 11-40): readings in docs/tasks/PT-M12-all-twenty-practices.md (decision 18)
COWBOY_PEP_REASON = (
    "PT-M18 (product manager, 2026-11-25): cowboy's lower PEP than steady, main 04efa78 7/10 "
    "on seeds 1-10 and 13/30 on 11-40 (fails); PT-M12's branch 5/10 and 12/30 "
    "(docs/tasks/PT-M12-all-twenty-practices.md, decision 18)"
)


def _one(args: tuple[str, int]) -> RiskRun:
    return risk_run(*args)


@cache
def _runs() -> dict[tuple[str, int], RiskRun]:
    jobs = [(s, seed) for s in ("steady", "cowboy") for seed in SEEDS]
    with ProcessPoolExecutor(WORKERS) as pool:
        return {(r.strategy, r.seed): r for r in pool.map(_one, jobs)}


@pytest.mark.nightly
def test_t14_claims_and_premiums_for_steady() -> None:
    runs = [_runs()[("steady", s)] for s in SEEDS]
    rates = [100 * r.claims_0615 / r.lawyer_years for r in runs if r.lawyer_years > 0]
    premiums = [r.premium_per_lawyer_cents for r in runs if not r.dissolved]
    for r in runs:
        print(
            f"\nT14 steady seed {r.seed}: {r.claims_0615} notices over {r.lawyer_years:.0f} "
            f"lawyer-years; premium ${r.premium_per_lawyer_cents / 100:,.0f} a lawyer"
        )
    median = statistics.median(rates)
    premium = statistics.median(premiums)
    print(f"\nT14: median {median:.2f} notices a 100 lawyer-years (band {T14_BAND})")
    print(f"Premium a lawyer (December 2015): median ${premium / 100:,.0f} (band $5k-$10k)")
    # PT-M12: a known miss within its row's bound (owner PT-M18) passes; worse fails
    reading = Reading("T14", T14_BAND[0] <= median <= T14_BAND[1], -median)
    assert verdict(reading) != "fail", f"T14 {median:.3f} outside {T14_BAND}"
    assert PREMIUM_BAND[0] <= premium <= PREMIUM_BAND[1]


def _cowboy_counts() -> tuple[int, int]:
    """(seeds where cowboy has at least twice steady's claims and cases, seeds where its PEP is
    lower), seeds 1-10."""
    more = lower = 0
    for seed in SEEDS:
        s, c = _runs()[("steady", seed)], _runs()[("cowboy", seed)]
        twice = c.claims + c.cases >= 2 * max(1, s.claims + s.cases)
        less = c.pep_cents < s.pep_cents
        more += twice
        lower += less
        print(
            f"\ncowboy seed {seed}: claims+cases {c.claims}+{c.cases} vs steady "
            f"{s.claims}+{s.cases} ({'2x' if twice else 'under 2x'}); PEP "
            f"${c.pep_cents / 100:,.0f} vs ${s.pep_cents / 100:,.0f}"
        )
    print(
        f"\ncowboy: 2x on {more} of 10 (>= {COWBOY_SEEDS}); lower PEP on {lower} (>= {PEP_SEEDS})"
    )
    return more, lower


@pytest.mark.nightly
def test_cowboy_pays_for_its_corners() -> None:
    more, _ = _cowboy_counts()
    assert more >= COWBOY_SEEDS


@pytest.mark.nightly
@pytest.mark.xfail(
    strict=False,
    reason=COWBOY_PEP_REASON,
)
def test_cowboy_earns_less_than_steady() -> None:
    _, lower = _cowboy_counts()
    assert lower >= PEP_SEEDS
