"""Persona (spec 2.3; TST formulas.md 32.4): four public traits, 0-100, raised by the firm's
choices and drifting back toward `persona.start`. Effects apply at `persona.effect_at` or
more, in Partner Track's units: partner confidence (a monthly nudge through
`interfaces.confidence_change`) and recruiting (an offer-score term; a resignation factor).

Ported from backend/tst/sim/founder/persona.py @ 121d318a (Tech Startup Tycoon); changed:
spec 2.3's sources (de-equitisations, hostile laterals and layoffs; pro bono, raises and comp
fairness; new practices; guarantees, revolver leverage and covenant breaches), read from the
month's records in phase 10; TST's effects mapped to partner confidence and recruiting.
"""

from __future__ import annotations

from dataclasses import replace

from ptk.sim.calendar import turn_to_ym
from ptk.sim.data_models import Balance
from ptk.sim.founder.config import SOURCES, TRAITS
from ptk.sim.founder.models import FounderLife

TRAIT_MAX = 100.0  # tunable-exempt: traits are 0-100

SOURCE_WORDS: dict[str, str] = {
    "new_practice": "opened a new practice",
    "first_region": "opened a new region",
    "early_ai": "adopted AI early",
    "deequitisation": "de-equitised a partner",
    "hostile_lateral": "hired a partner from a rival",
    "layoffs": "layoffs",
    "pro_bono": "a year of pro bono",
    "raises": "raises across the firm",
    "comp_fairness": "a fair comp round",
    "guarantee": "guaranteed a partner's pay",
    "revolver_leverage": "leaned on the revolver",
    "covenant_breach": "breached a bank covenant",
    "broken_claim": "broke a public claim",
}

PUBLIC_WORDS: dict[str, str] = {
    "visionary": "a visionary",
    "ruthless": "ruthless",
    "beloved": "well liked",
    "reckless": "reckless",
}
UNKNOWN_WORDS = "little known in the profession"


def new_life(person_id: int, turn: int, balance: Balance) -> FounderLife:
    s = balance.founder_life.persona.start
    return FounderLife(person_id, s, s, s, s, since_turn=turn)


def heir_life(
    person_id: int, parent: FounderLife | None, turn: int, balance: Balance
) -> FounderLife:
    """TST 45.5: a successor's persona starts at `start` plus `heir_share` of the old player's
    (their own reputation is new; some of the firm's carries over)."""
    pb = balance.founder_life.persona
    life = new_life(person_id, turn, balance)
    if parent is None:
        return life
    values = {t: pb.start + pb.heir_share * (parent.trait(t) - pb.start) for t in TRAITS}
    return _with_traits(life, values)


def _with_traits(life: FounderLife, values: dict[str, float]) -> FounderLife:
    return replace(
        life,
        visionary=values.get("visionary", life.visionary),
        ruthless=values.get("ruthless", life.ruthless),
        beloved=values.get("beloved", life.beloved),
        reckless=values.get("reckless", life.reckless),
    )


def raise_trait(
    life: FounderLife, trait: str, value: float, why: str, turn: int, balance: Balance
) -> FounderLife:
    if trait not in TRAITS or not value:
        return life
    old = life.trait(trait)
    new = max(0.0, min(TRAIT_MAX, old + value))
    causes = (*life.causes, (turn, trait, new - old, why))[-balance.founder_life.persona.history :]
    return _with_traits(replace(life, causes=causes), {trait: new})


def apply_source(
    life: FounderLife, source: str, turn: int, balance: Balance, n: float = 1
) -> FounderLife:
    trait = SOURCES[source]
    points = balance.founder_life.persona.sources[source] * n
    return raise_trait(life, trait, points, SOURCE_WORDS[source], turn, balance)


def leverage(
    life: FounderLife, turn: int, start_ym: tuple[int, int], balance: Balance
) -> FounderLife:
    """revolver_leverage: its points, at most `leverage_year_cap` a calendar year."""
    pb = balance.founder_life.persona
    year = turn_to_ym(turn, start_ym)[0]
    used = life.leverage_points if life.leverage_year == year else 0.0
    gain = min(pb.sources["revolver_leverage"], max(0.0, pb.leverage_year_cap - used))
    if gain <= 0:
        return replace(life, leverage_year=year, leverage_points=used)
    life = raise_trait(life, "reckless", gain, SOURCE_WORDS["revolver_leverage"], turn, balance)
    return replace(life, leverage_year=year, leverage_points=used + gain)


def drift(life: FounderLife, balance: Balance) -> FounderLife:
    pb = balance.founder_life.persona
    moved = {}
    for trait in TRAITS:
        value = life.trait(trait)
        gap = pb.start - value
        if gap:
            moved[trait] = value + max(-pb.drift, min(pb.drift, gap))
    return _with_traits(life, moved) if moved else life


def strong(life: FounderLife | None, trait: str, balance: Balance) -> bool:
    return life is not None and life.trait(trait) >= balance.founder_life.persona.effect_at


def confidence_points(life: FounderLife | None, balance: Balance) -> float:
    """A month's nudge to every partner's confidence in the MP from the MP's persona."""
    pb = balance.founder_life.persona
    points = 0.0
    if strong(life, "ruthless", balance):
        points += pb.ruthless_confidence
    if strong(life, "beloved", balance):
        points += pb.beloved_confidence
    if strong(life, "reckless", balance):
        points += pb.reckless_confidence
    return points


def recruiting_points(life: FounderLife | None, balance: Balance) -> float:
    """Visionary: an offer-score term for every hire (TST's +0.03 hiring appeal)."""
    return (
        balance.founder_life.persona.visionary_recruiting
        if strong(life, "visionary", balance)
        else 0.0
    )


def resign_mult(life: FounderLife | None, balance: Balance) -> float:
    """Beloved: resignation chance x `beloved_resign` (TST's x0.9)."""
    return balance.founder_life.persona.beloved_resign if strong(life, "beloved", balance) else 1.0


def top_trait(life: FounderLife) -> str:
    """The strongest trait; ties go to the first in TRAITS order."""
    return max(TRAITS, key=lambda t: (life.trait(t), -TRAITS.index(t)))


def public_words(life: FounderLife | None, balance: Balance) -> str:
    if life is None:
        return UNKNOWN_WORDS
    top = top_trait(life)
    return (
        PUBLIC_WORDS[top] if life.trait(top) > balance.founder_life.persona.start else UNKNOWN_WORDS
    )
