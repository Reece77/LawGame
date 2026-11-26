"""Strain and burnout for every person (spec 5.6; ADR PT-0006 section 3).

Strain is TST 32.1's founder stress generalised to everyone. A generated person starts
with a strain drawn from stream `strain` keyed by person id; founding partners start at
strain.founder_start.
"""

from __future__ import annotations

from typing import Final

from ptk.sim.calendar import MONTHS_PER_YEAR
from ptk.sim.data_models import Balance
from ptk.sim.fastcopy import replace
from ptk.sim.people.formulas import clamp_strain, strain_delta
from ptk.sim.people.models import Person, WorkMonth
from ptk.sim.rng import RngFactory

TENTHS_PER_HOUR: Final = 10  # tunable-exempt: hours are integer tenths (ADR PT-0005)
REAL_STRAIN_MARGIN: Final = 1.0  # tunable-exempt: a real person's strain stays below burnout


def initial_strain(rng: RngFactory, turn: int, person_id: int, balance: Balance) -> float:
    """Uniform in people.initial_strain (stream `strain`, key `(person_id,)`)."""
    span = balance.people.initial_strain
    return float(rng.stream(turn, "strain", person_id).uniform(span.lo, span.hi))


def monthly_capacity_tenths(person: Person, balance: Balance) -> float:
    """The level's yearly capacity in tenths, a twelfth a month, times 0.7 in burnout."""
    level = balance.people.levels[person.level]
    capacity = level.capacity_hours * TENTHS_PER_HOUR / MONTHS_PER_YEAR
    return capacity * (balance.strain.burnout_capacity if person.burnt_out else 1.0)


def strain_month(
    person: Person, turn: int, work: WorkMonth, balance: Balance, gain_factor: float = 1.0
) -> Person:
    """One month of strain and burnout (spec 5.6). Burnout starts at strain.burnout_at and
    lasts until strain falls below strain.burnout_exit; a founding partner is no different.
    `gain_factor` (PT-M6): event modifiers on how fast strain builds scale a month's gain."""
    cfg = balance.strain
    delta = strain_delta(
        hours_tenths=work.total_tenths,
        capacity_tenths=monthly_capacity_tenths(person, balance),
        stamina=person.skills["stamina"],
        burnout_risk=person.hidden["burnout_risk"],
        grinder="grinder" in person.tags,
        rest=work.rest,
        strain=cfg,
    )
    if delta > 0:
        delta *= gain_factor
    value = clamp_strain(person.strain + delta)
    if person.real:  # ADR PT-0013 (PT-M5): no burnout collapse for a real person
        value = min(value, cfg.burnout_at - REAL_STRAIN_MARGIN)
    since, last = person.burnout_since, person.last_burnout_turn
    if since is None and value >= cfg.burnout_at:
        since = last = turn
    elif since is not None and value < cfg.burnout_exit:
        since = None
    return replace(person, strain=value, burnout_since=since, last_burnout_turn=last)


def burnout_effects_active(person: Person, turn: int, balance: Balance) -> bool:
    """Error chance and resignation chance are doubled for burnout_effect_months from the
    start of the latest burnout (spec 5.6; used by PT-M1b and PT-M3a)."""
    last = person.last_burnout_turn
    return last is not None and turn - last < balance.strain.burnout_effect_months
