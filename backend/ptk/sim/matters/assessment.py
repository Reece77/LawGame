"""Early case assessment (PT-M7a; spec 7.6): a case's hidden merits revealed as a range.

The lead's assessment skill S = Σ w_k x skill_k (`assessment.skills`). The range's
half-width is `half_width` x (1 - `skill_slope` x (S - 10) / 10), never below
`min_half_width`; its centre is the true merits plus u x `centre_share` x half-width, u
uniform in [-1, 1] from the action's draw, so the range always holds the true merits. Only
the range (and words for it) reach the API; the merits never do (CLAUDE.md section 10).
"""

from __future__ import annotations

from typing import Final

from ptk.sim.data_models import Balance
from ptk.sim.people.models import Person

# Words for merits in logit points (upper bounds). tunable-exempt: display words, not rules.
MERITS_WORDS: Final = (
    (-1.0, "weak"),
    (-0.35, "leaning against us"),
    (0.35, "even"),
    (1.0, "favourable"),
    (float("inf"), "strong"),
)


def assessment_skill(lead: Person, balance: Balance) -> float:
    weights = balance.assessment.skills
    total = sum(weights.values())
    return sum(lead.skills[k] * w for k, w in weights.items()) / total


def half_width(lead: Person, balance: Balance) -> float:
    cfg = balance.assessment
    skill = assessment_skill(lead, balance)
    return max(cfg.min_half_width, cfg.half_width * (1.0 - cfg.skill_slope * (skill - 10.0) / 10.0))


def merits_range(merits: float, lead: Person, u: float, balance: Balance) -> tuple[float, float]:
    """(lo, hi) around the true merits; `u` is a uniform draw in [0, 1)."""
    half = half_width(lead, balance)
    centre = merits + (2.0 * u - 1.0) * balance.assessment.centre_share * half
    return centre - half, centre + half


def merits_word(value: float) -> str:
    return next(word for top, word in MERITS_WORDS if value < top)


def merits_words(lo: float, hi: float) -> str:
    """The range in words: "weak to even", or one word when both ends agree."""
    a, b = merits_word(lo), merits_word(hi)
    return a if a == b else f"{a} to {b}"
