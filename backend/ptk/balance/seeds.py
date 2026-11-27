"""The balance seeds (PT-M18 sub-task 1; CLAUDE.md section 12, rule 1: Reece, 2026-11-25).

From PT-M18 every target and guard is judged on seeds 1-40, with thresholds written as shares
of seeds: "6 of 10" becomes at most 60% of them, "9 of 10" at least 90%; a median stays a
median. The runner, the nightly tests and the readings tools all read `SEEDS` from here.
"""

from __future__ import annotations

import math
from typing import Final

SEEDS: Final = tuple(range(1, 41))
_EPS: Final = 1e-9  # a share times a count that should be whole (0.6 x 40) stays whole


def at_least(share: float, n: int) -> int:
    """The fewest of n seeds that make at least `share` of them (90% of 40: 36)."""
    return math.ceil(share * n - _EPS)


def at_most(share: float, n: int) -> int:
    """The most of n seeds that stay within `share` of them (60% of 40: 24)."""
    return math.floor(share * n + _EPS)
