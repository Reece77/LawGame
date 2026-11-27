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
    # PT-M18 sub-task 3 (2026-11-27): T3.revenue, T5.standard and T8.corporate pass on seeds 1-40
    # (nightly run 45952995537: $70.91M, 15.0%, -12.2%) and their rows are removed.
    # Recorded by Reece's decision on PT-M7 (via the product manager, 2026-11-21) and re-owned
    # by Reece's decisions on PT-M7b's targets (2026-11-22, docs/tasks/PT-M10-history-to-2025.md
    # sub-task 0): T2 moves to PT-M18; T3 lawyers and T4 steady to PT-M16 (reputation that
    # gates the card); T8 corporate's -9% is accepted as noise. PT-M10's readings are in its
    # brief's "Decisions made". PT-M7c (2026-11-23) removes T2 (steady 6, pyramid 4 on seeds 1-10)
    # and takes over T3.lawyers, T4.steady and T4.pyramid with its readings. Reece (2026-11-24,
    # after the client tiers): T1 (10/10) and T4.pyramid ($0.98M) pass and their rows go;
    # T3.lawyers, T3.revenue and T4.steady are PT-M18's with PT-M7c's readings.
    KnownMiss(
        target="T3.lawyers",  # steady 100-250 lawyers in December 2015
        owner="PT-M18",
        # score: minus the median lawyers; known while at least 45
        worse_than=-45.0,
        reason="60.0 on PT-M7c's client tiers (before the tiers 46.0, main 60.0); seeds 11-40 "
        "71.5 (before 72.5): growth to 100-250 is expected from PT-M12 (practices) and PT-M13 "
        "(mergers) (Reece, 2026-11-24)",
    ),
    KnownMiss(
        target="T4.steady",  # steady PEP $0.5-1.2M in 2015
        owner="PT-M18",
        # score: median PEP in $M; known while at most $5.0M
        worse_than=5.0,
        reason="$1.31M on PT-M7c's client tiers (before the tiers $2.72M, main $4.37M); seeds "
        "11-40 $1.65M (before $3.09M): steady's large clients at a top-decile card "
        "(Reece, 2026-11-24)",
    ),
    KnownMiss(
        target="PT-M14.fixed_fees",  # ai-fixed earns more PEP 2026-2030 than ai-hourly, 7 of 10
        owner="PT-M18",
        # score: minus the seeds of 10 where ai-fixed wins; known while at least 3 of 10
        worse_than=-3.0,
        reason="4/10 on seeds 1-10 (4 of the 6 with products) and 9/30 on seeds 11-40 (9 of "
        "the 16 with products) with price acceptance at 110% (Reece's decision, 2026-11-23); "
        "the product manager authorised the row (tools/tech_readings.py; PT-M14's brief)",
    ),
    KnownMiss(
        target="T2",  # no strategy has the best founder's earnings on more than 6 of 10 seeds
        owner="PT-M18",
        # score: the most wins any strategy has, as a share of the seeds (PT-M18: 9 of 10
        # read as 90%); known while at most 90%
        worse_than=0.9,
        reason="PT-M15 (authorised by the product manager, Reece, 2026-11-25): steady wins 9 "
        "of seeds 1-10 on the branch (main 5); seeds 11-40 steady 16/30 on the branch, 19/30 "
        "on main (a miss on main too: the cause predates PT-M15). PT-M12 (the product "
        "manager's decision, 2026-11-25: this row covers it, bound unchanged): steady 8 of "
        "seeds 1-10 (main 9), 21/30 on seeds 11-40 (main 16/30)",
    ),
    KnownMiss(
        target="T13",  # partners lost within 24 months of a merger: 10-20% (PT-M13)
        owner="PT-M18",
        # score: the median share lost; known while at most 28% (seeds 1-10's 27.98%: bounded
        # at the reading, CLAUDE.md 12.5)
        worse_than=0.28,
        reason="PT-M12 (authorised by the product manager, Reece, 2026-11-25): 28.0% on seeds "
        "1-10 and 23.9% on 11-40 on PT-M12's branch (main 04efa78: 12.8% and 18.8%). The "
        "targeted fix (subordination only in a practice both firms had, contested_min_share "
        "10%) does not move it: no merged partner is subordinated in these runs",
    ),
    KnownMiss(
        target="T14",  # steady's claim notices a 100 lawyer-years 2006-2015: 1.5-5.0 (PT-M15)
        owner="PT-M18",
        # score: minus the median; known while the median is at least 1.495 (seeds 1-10's
        # 1.4951: bounded at the reading, CLAUDE.md 12.5)
        worse_than=-1.495,
        reason="PT-M12 (authorised by the product manager, Reece, 2026-11-25): 1.495 on seeds "
        "1-10 and 1.497 on 11-40 on PT-M12's branch (main 04efa78: 1.717 and 1.998). The v2 "
        "practices' claim weights (risk-and-ethics.md s2a) do not move it: steady's escaped "
        "errors fall in v1's practices; its larger firm (lawyer-years) lowers the rate",
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
