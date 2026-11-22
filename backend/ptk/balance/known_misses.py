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
    # brief's "Decisions made".
    KnownMiss(
        target="T2",  # no strategy has the best score on more than 6 of 10 seeds
        owner="PT-M18",
        # score: the most wins of one strategy; known while at most 9 of 10
        worse_than=9.0,
        reason="steady 9, boutique 1 (PT-M7b; PT-M7: steady 9, pyramid 1): the measure is "
        "unchanged and the miss moves to PT-M18 (Reece, 2026-11-22)",
    ),
    KnownMiss(
        target="T3.lawyers",  # steady 100-250 lawyers in December 2015
        owner="PT-M16",
        # score: minus the median lawyers; known while at least 45
        worse_than=-45.0,
        reason="50 (PT-M7b; PT-M7: 53): a lower card makes a firm poorer, not bigger; the band "
        "is unchanged and the miss moves to PT-M16's reputation that gates the card (Reece, "
        "2026-11-22)",
    ),
    KnownMiss(
        target="T4.steady",  # steady PEP $0.5-1.2M in 2015
        owner="PT-M16",
        # score: median PEP in $M; known while at most $5.0M
        worse_than=5.0,
        reason="$4.02M (PT-M7b; PT-M7: $4.07M): as T3.lawyers, to PT-M16 (Reece, 2026-11-22)",
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
