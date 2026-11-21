"""Influence as bar politics (spec 2.3; TST formulas.md 32.5): the bar association, its
committees and its offices.

Ported from backend/tst/sim/founder/influence.py @ 121d318a (Tech Startup Tycoon); changed:
one influence for the player (the profession, not a region's regulators); it rises with a
committee seat (energy each month) and the firm's spend on bar politics (account 6950,
`rate x sqrt(spend / unit)` as TST's lobbying), decays `decay` a month, capped; with enough
influence the player may stand for bar office (elected each `office_month`, stream
`founder_life` keyed (2, person_id)); in office it grows and counts toward legacy. Effects:
recruiting (the firm's standing) and partner confidence, in proportion to influence. No
hidden scandal risk: the brief's bar politics carries none (see the brief's decisions).
"""

from __future__ import annotations

from dataclasses import replace
from typing import Final

import numpy as np

from ptk.sim.calendar import MONTHS_PER_YEAR, turn_to_ym
from ptk.sim.data_models import Balance
from ptk.sim.founder.models import FounderLife
from ptk.sim.founder.streams import BAR_ELECTION, life_stream
from ptk.sim.rng import RngFactory

INFLUENCE_MAX: Final = 100.0  # tunable-exempt: influence is 0-100
CENTS_A_DOLLAR: Final = 100  # tunable-exempt: cents in a dollar


def office_stream(rng: RngFactory, turn: int, person_id: int) -> np.random.Generator:
    return life_stream(rng, turn, BAR_ELECTION, person_id)


def in_office(life: FounderLife, turn: int) -> bool:
    return life.office_until_turn is not None and turn < life.office_until_turn


def month(life: FounderLife, turn: int, balance: Balance) -> FounderLife:
    """A month of bar politics: committee and spend raise influence; it decays."""
    ib = balance.founder_life.influence
    gain = ib.committee if life.committee else 0.0
    if life.bar_spend_cents > 0:
        # money-exact: ratio
        gain += ib.rate * (life.bar_spend_cents / CENTS_A_DOLLAR / ib.unit_dollars) ** 0.5
    if in_office(life, turn):
        gain += ib.office_bonus
    value = life.influence * (1 - ib.decay) + gain
    return replace(life, influence=max(0.0, min(ib.cap, value)))


def election(
    life: FounderLife, turn: int, start_ym: tuple[int, int], rng: RngFactory, balance: Balance
) -> tuple[FounderLife, bool | None]:
    """The bar's election month: a standing candidate with influence of at least `office_at`
    wins outright from `office_win_at`, else with chance (I - at) / (win_at - at). Returns
    the life and the result (None: no election for them this month)."""
    ib = balance.founder_life.influence
    if turn_to_ym(turn, start_ym)[1] != ib.office_month or not life.standing:
        return life, None
    life = replace(life, standing=False)
    if life.influence < ib.office_at or in_office(life, turn):
        return life, False
    span = max(ib.office_win_at - ib.office_at, 1e-9)
    chance = min(1.0, (life.influence - ib.office_at) / span)
    won = float(office_stream(rng, turn, life.person_id).random()) < chance
    if not won:
        return life, False
    until = turn + ib.office_years * MONTHS_PER_YEAR
    return replace(life, office_until_turn=until, office_turns=(*life.office_turns, turn)), True


def recruiting_points(life: FounderLife | None, balance: Balance) -> float:
    if life is None:
        return 0.0
    return balance.founder_life.influence.recruiting * life.influence / INFLUENCE_MAX


def confidence_points(life: FounderLife | None, balance: Balance) -> float:
    if life is None:
        return 0.0
    return balance.founder_life.influence.confidence * life.influence / INFLUENCE_MAX


def office_years(life: FounderLife, turn: int, balance: Balance) -> float:
    """Years served in bar office so far (legacy)."""
    years = 0.0
    span = balance.founder_life.influence.office_years * MONTHS_PER_YEAR
    for t in life.office_turns:
        years += min(span, max(0, turn - t)) / MONTHS_PER_YEAR
    return years
