"""Recorded known misses of the balance targets (docs/balance-targets.md): the one list read by
tools/balance_runner.py (`make balance`, CI's nightly "balance" job) and by the nightly pytest
balance tests.

Ported from backend/tst/balance/known_misses.py @ 121d318a (Tech Startup Tycoon); changed:
Partner Track's own list (no TST misses), Reading and the verdicts kept as they are.

A known miss names its target, the milestone that owns the fix and a "worse than" bound on
the target's score. A miss within the bound prints KNOWN MISS (<owner>) and does not fail the
job; a miss beyond it, or a miss of any target not listed, still fails. Only Reece or the product
manager decides a row (CLAUDE.md section 9, rule 3); the rows below are Reece's (2026-11-21,
re-owned 2026-11-22).
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
    # Recorded by Reece's decision on PT-M7 (via the product manager, 2026-11-21) and re-owned
    # by Reece's decisions on PT-M7b's targets (2026-11-22, docs/tasks/PT-M10-history-to-2025.md
    # sub-task 0): T2 moves to PT-M18; T3 lawyers and T4 steady to PT-M16 (reputation that
    # gates the card); T8 corporate's -9% is accepted as noise. PT-M10's readings are in its
    # brief's "Decisions made". PT-M7c (2026-11-23) removes T2 (steady 6, pyramid 4 on seeds 1-10)
    # and takes over T3.lawyers, T4.steady and T4.pyramid with its readings.
    KnownMiss(
        target="T3.lawyers",  # steady 100-250 lawyers in December 2015
        owner="Reece (PT-M7c decision 5)",
        # score: minus the median lawyers; known while at least 45
        worse_than=-45.0,
        reason="46.0 on PT-M7c seeds 1-10 (main 55.0); seeds 11-40 83.5 (main 56): steady's "
        "30% a year is already faster than real young firms (docs/research/firm-economics.md); "
        "the band and the rate card are Reece's (PT-M7c's brief, decision 5)",
    ),
    KnownMiss(
        target="T4.steady",  # steady PEP $0.5-1.2M in 2015
        owner="Reece (PT-M7c decision 5)",
        # score: median PEP in $M; known while at most $5.0M
        worse_than=5.0,
        reason="$2.72M on PT-M7c (main $3.39M; seeds 11-40 $3.01M, main $3.90M): leverage fixed "
        "(a December admission keeps its budget); RPL +83% on the Second Hundred is the rate "
        "card, a design question for Reece (PT-M7c's brief, decision 5)",
    ),
    KnownMiss(
        target="T1",  # do-nothing fails on at least 9 of 10 seeds
        owner="PT-M18",
        # score: minus the seeds where do-nothing fails; known while at least 8 of 10 fail
        worse_than=-8.0,
        reason="8/10 on PT-M16 (main 9/10): seed variance, rule 4 (the product manager, "
        "2026-11-22, PR #22): seeds 11-40 main 26/30, PT-M16 28/30; all 40 main 35/40, "
        "PT-M16 36/40",
    ),
    KnownMiss(
        target="T4.pyramid",  # pyramid PEP $0.7-1.6M in 2015
        owner="Reece (PT-M7c decision 5)",
        worse_than=3.5,  # score: median PEP in $M; known while at most $3.5M
        reason="$1.65M on PT-M7c (main $2.36M; seeds 11-40 $2.07M, main $3.46M): $0.05M above "
        "its band after the admission fix; the rest is the rate card (PT-M7c's brief, decision 5)",
    ),
    KnownMiss(
        target="T8.corporate",  # corporate-heavy firms' 2009 revenue -30% to -10% on 2008
        owner="accepted (Reece, 2026-11-22)",
        # score: the median change; known while it is at most -5% (a fall within noise of -10%)
        worse_than=-0.05,
        reason="-9.0% (PT-M7b; -11.1% at a 9500 card): accepted as noise by Reece "
        "(2026-11-22; docs/balance-targets.md)",
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
