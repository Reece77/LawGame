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
    # Recorded by Reece's decision on PT-M7 (via the product manager, 2026-11-21): every
    # miss is PT-M7b's (docs/tasks/PT-M7b-pressure-and-balance.md). PT-M7's readings, seeds 1-10.
    KnownMiss(
        target="T2",  # no strategy has the best score on more than 6 of 10 seeds
        owner="PT-M7b",
        # score: the most wins of one strategy; known while at most 9 of 10
        worse_than=9.0,
        reason="steady 9, pyramid 1 (PT-M7): steady grows, keeps leverage and rarely dissolves; "
        "PT-M7b's sub-tasks a-e give the other strategies' edges and steady's risks, then "
        "sub-task f re-reads T2 (its measure unchanged)",
    ),
    KnownMiss(
        target="T3.lawyers",  # steady 100-250 lawyers in December 2015
        owner="PT-M7b",
        # score: minus the median lawyers; known while at least 45
        worse_than=-45.0,
        reason="53 (PT-M7): a top New York card bills about $1.2M a lawyer, so T3's revenue "
        "comes with half its lawyers; PT-M7b sub-task a (a new firm's card at 65%)",
    ),
    KnownMiss(
        target="T4.steady",  # steady PEP $0.5-1.2M in 2015
        owner="PT-M7b",
        # score: median PEP in $M; known while at most $5.0M
        worse_than=5.0,
        reason="$4.07M (PT-M7): revenue per lawyer at the top card; PT-M7b sub-task a",
    ),
    KnownMiss(
        target="T4.pyramid",  # pyramid PEP $0.7-1.6M in 2015
        owner="PT-M7b",
        worse_than=2.5,  # score: median PEP in $M
        reason="$1.80M (PT-M7): as T4.steady; PT-M7b sub-task a",
    ),
    KnownMiss(
        target="T5.standard",  # steady dissolves on 5-20% of seeds at standard
        owner="PT-M7b",
        # score: minus the share dissolved; known while none or more dissolve (always)
        worse_than=0.0,
        reason="0% (PT-M7): difficulty only scales starting capital and steady never strains "
        "its revolver; PT-M7b sub-tasks b (difficulty teeth) and c (crisis discounts)",
    ),
    KnownMiss(
        target="T5.hard",  # steady dissolves on 20-45% of seeds at hard
        owner="PT-M7b",
        worse_than=0.0,  # score: minus the share dissolved
        reason="0% (PT-M7): as T5.standard; PT-M7b sub-task b",
    ),
    KnownMiss(
        target="T8.corporate",  # corporate-heavy firms' 2009 revenue -30% to -10% on 2008
        owner="PT-M7b",
        # score: the median change; known while it is at most +5%
        worse_than=0.05,
        reason="-1.3% (PT-M7): small firms stay capacity-bound through the crash; 2009's "
        "discounts and write-downs are not modelled; PT-M7b sub-task c",
    ),
    KnownMiss(
        target="T8.restructuring",  # restructuring-heavy firms' 2009 revenue -5% to +20%
        owner="PT-M7b",
        # score: the median change; known while at most +55%
        worse_than=0.55,
        reason="+40.7% on 3 runs (PT-M7); PT-M7b sub-task c brings 2009's growth under +20%",
    ),
    KnownMiss(
        target="T9.rocket",  # the lateral rocket dissolves on 3-6 of 10 seeds
        owner="PT-M7b",
        # score: seeds dissolved; known while at most 9 of 10
        worse_than=9.0,
        reason="8/10 (PT-M7): $600k of capital cannot carry a guaranteed lateral in year one; "
        "PT-M7b sub-task d (an earlier CFO warning, lateral guarantees tuned)",
    ),
    KnownMiss(
        target="T9.heeded",  # the heeded rocket dissolves on at most 1 of 10
        owner="PT-M7b",
        worse_than=7.0,  # score: seeds dissolved
        reason="6/10 (PT-M7): the warning comes too late; PT-M7b sub-task d",
    ),
    KnownMiss(
        target="T10.ratio",  # pyramid's associates burn out at least twice as often as steady's
        owner="PT-M7b",
        # score: minus the ratio; known while the ratio is at least 0.7x
        worse_than=-0.7,
        reason="0.88x (PT-M7): staffing plans at most 95% of capacity and strain starts above "
        "100%, so a 2,100-hour plan never strains; PT-M7b sub-task e (an hours policy)",
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
