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
    # T3.lawyers, T3.revenue and T4.steady are PT-M18's with PT-M7c's readings. PT-M18
    # (decision 10, 2026-11-27): T2 passes on seeds 1-40 and its row goes; T4.steady's row
    # returns bounded at its 40-seed reading (decision 12). The product manager (2026-11-27):
    # T3.lawyers, T4.steady, T6.partners and T13 carried to v3 (PT-M23), each bounded at its
    # 40-seed reading; T14 passes and its row goes.
    KnownMiss(
        target="T3.lawyers",  # steady 100-250 lawyers in December 2015
        owner="PT-M23",
        # score: minus the median lawyers; PT-M18 (CLAUDE.md 12.5): bounded at the 40-seed
        # reading, 73.5
        worse_than=-73.5,
        reason="PT-M18 (the product manager's decision, 2026-11-27: carried to v3"
        "): 73.5 on seeds 1-40 (66.5 at PT-M18's baseline; revenue "
        "$70.6M is inside T3's band). Steady grows by its utilisation rule; growth to 100-250 "
        "is v3's (a follow-up in docs/tasks/PT-M18-v2-balance.md). Earlier: 60.0 on PT-M7c's "
        "client tiers (Reece, 2026-11-24)",
    ),
    KnownMiss(
        target="T4.steady",  # steady PEP $0.5-1.2M in 2015
        owner="PT-M23",
        # score: median PEP in $M; PT-M18 (CLAUDE.md 12.5): bounded at the 40-seed reading,
        # $1.3168M
        worse_than=1.317,
        reason="PT-M18 (the product manager's decision, 2026-11-27: carried to v3"
        "; T14 keeps its claim rate): seeds 1-40 $1.65M at baseline, "
        "$1.19M with steady at the dossier's 2.5 lawyers per equity partner (decision 10), "
        "$1.32M once risk.claims.from_error_bp 1070 brings T14 back to 1.50 (decision 11); "
        "no key holds both (decision 12)",
    ),
    KnownMiss(
        target="PT-M14.fixed_fees",  # ai-fixed earns more PEP 2026-2030 than ai-hourly, 70%
        owner="PT-M23",
        # score: minus the share of seeds where ai-fixed wins; PT-M18 (CLAUDE.md 12.5): bounded
        # at the 40-seed reading, 24 of 40
        worse_than=-0.6,
        reason="PT-M18 (the product manager, 2026-11-27: kept, bound at the reading): 24 of "
        "seeds 1-40 on PT-M18 (4d91fac; tools/tech_readings.py --criterion3); earlier 4/10 "
        "and 9/30 with price acceptance at 110% (Reece's decision, 2026-11-23)",
    ),
    KnownMiss(
        target="T6.partners",  # steady's Sept 2006 class: 8-15% equity partners by Dec 2015
        owner="PT-M23",
        # score: minus the share; PT-M18 (CLAUDE.md 12.5): bounded at the 40-seed reading, 0%
        worse_than=-0.0,
        reason="PT-M18 (the product manager's decision, 2026-11-27: carried to v3"
        "): 0.0% on seeds 1-40 (1.9% at the baseline). The class is 0-2 "
        "people a seed and almost all leave before year 8 (22% attrition leaves about 13%); "
        "admitting one partner every December changes nothing (decision 9)",
    ),
    KnownMiss(
        target="T13",  # partners lost within 24 months of a merger: 10-20% (PT-M13)
        owner="PT-M23",
        # score: the median share lost; PT-M18 (CLAUDE.md 12.5): bounded at the 40-seed
        # reading, 23.1%
        worse_than=0.232,
        reason="PT-M18 (the product manager's decision, 2026-11-27: carried to v3"
        "): 23.1% on seeds 1-40 (23 merged); with every integration "
        "effect at 0 it reads 21.7%, so the loss is partners' ordinary flight over 24 months, "
        "not the merger (flight_mult 0.8 -> 0.4: 23.3%). Earlier: 28.0% and 23.9% on PT-M12's "
        "branch (Reece, 2026-11-25)",
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
