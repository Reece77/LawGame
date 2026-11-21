"""Recorded known misses of the balance targets (docs/balance-targets.md): the one list read by
tools/balance_runner.py (`make balance`, CI's nightly "balance" job) and by the nightly pytest
balance tests.

Ported from backend/tst/balance/known_misses.py @ 121d318a (Tech Startup Tycoon); changed:
Partner Track's own list (no TST misses), Reading and the verdicts kept as they are.

A known miss names its target, the milestone that owns the fix and a "worse than" bound on
the target's score. A miss within the bound prints KNOWN MISS (<owner>) and does not fail the
job; a miss beyond it, or a miss of any target not listed, still fails. Only Reece or the product
manager decides a row (CLAUDE.md section 9, rule 3); the rows below are Reece's (2026-11-21).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal, Protocol


@dataclass(frozen=True, slots=True)
class KnownMiss:
    target: str  # the Row.target it covers, e.g. "T2"
    owner: str  # the milestone that owns the fix, e.g. "M15"
    worse_than: float  # the miss stays known while the row's score is at most this
    reason: str


KNOWN_MISSES: Final[tuple[KnownMiss, ...]] = (
    # Recorded by Reece's decision on PT-M7 (via the product manager, 2026-11-21), each owned by
    # PT-M7b. PT-M7b removed the rows whose targets now pass (T5.standard, T5.hard,
    # T9.rocket, T9.heeded, T10.ratio) and carries the rest with its readings (seeds 1-10)
    # back to Reece: docs/tasks/PT-M7b-pressure-and-balance.md, "Decisions made".
    KnownMiss(
        target="T2",  # no strategy has the best score on more than 6 of 10 seeds
        owner="PT-M7b",
        # score: the most wins of one strategy; known while at most 9 of 10
        worse_than=9.0,
        reason="steady 9, boutique 1 (PT-M7b; PT-M7: steady 9, pyramid 1): with the card, "
        "difficulty, crisis, forecast, hours policy and December comp rounds steady still grows "
        "with its demand and survives 9 of 10; for Reece",
    ),
    KnownMiss(
        target="T3.lawyers",  # steady 100-250 lawyers in December 2015
        owner="PT-M7b",
        # score: minus the median lawyers; known while at least 45
        worse_than=-45.0,
        reason="50 (PT-M7b; PT-M7: 53): a lower card makes a firm poorer, not bigger (at a "
        "65% start steady dissolved on 9 of 10 seeds in its first year); for Reece",
    ),
    KnownMiss(
        target="T4.steady",  # steady PEP $0.5-1.2M in 2015
        owner="PT-M7b",
        # score: median PEP in $M; known while at most $5.0M
        worse_than=5.0,
        reason="$4.02M (PT-M7b; PT-M7: $4.07M): as T3.lawyers; for Reece",
    ),
    KnownMiss(
        target="T4.pyramid",  # pyramid PEP $0.7-1.6M in 2015
        owner="PT-M7b",
        worse_than=2.5,  # score: median PEP in $M
        reason="$3.19M (PT-M7b, above its bound: the hours policy bills more and its card is "
        "near the full card; at a 9500 card 6 of 10 pyramids dissolved in the crash, $0.00M; "
        "PT-M7: $1.80M); for Reece",
    ),
    KnownMiss(
        target="T8.corporate",  # corporate-heavy firms' 2009 revenue -30% to -10% on 2008
        owner="PT-M7b",
        # score: the median change; known while it is at most +5%
        worse_than=0.05,
        reason="-9.0% (PT-M7b; -11.1% at a 9500 card, which broke PT-M4's exodus guard; PT-M7: "
        "-1.3%): a stronger crisis discount pushes realisation under T7's 84%; for Reece",
    ),
    KnownMiss(
        target="T8.restructuring",  # restructuring-heavy firms' 2009 revenue -5% to +20%
        owner="PT-M7b",
        # score: the median change; known while at most +55%
        worse_than=0.55,
        reason="+31.1% on 2-3 runs (PT-M7b, restructuring beta -0.8, estate_mult 15; PT-M7: "
        "+40.7% on 3): the qualifying firms are small ones that caught an estate; for Reece",
    ),
)

Verdict = Literal["ok", "printed", "known", "fail"]


@dataclass(frozen=True, slots=True)
class Reading:
    """A target a plain test asserts, judged like a report Row (M43a: M13, M13b, M22)."""

    target: str
    ok: bool
    score: float
    detail: str = ""


class _Judged(Protocol):
    @property
    def target(self) -> str: ...
    @property
    def ok(self) -> bool | None: ...
    @property
    def score(self) -> float | None: ...


def known_miss(target: str) -> KnownMiss | None:
    return next((k for k in KNOWN_MISSES if k.target == target), None)


def verdict(row: _Judged) -> Verdict:
    """ok, printed only, a known miss within its bound, or a failure."""
    if row.ok is None:
        return "printed"
    if row.ok:
        return "ok"
    known = known_miss(row.target)
    if known is not None and row.score is not None and row.score <= known.worse_than:
        return "known"
    return "fail"
