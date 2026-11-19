"""Strain and burnout for every person (spec 5.6; ADR PT-0006 section 3).

Strain is TST 32.1's founder stress generalised to everyone. A generated person starts
with a strain drawn from stream `strain` keyed by person id; founding partners start at
strain.founder_start.
"""

from __future__ import annotations

from ptk.sim.data_models import Balance
from ptk.sim.rng import RngFactory


def initial_strain(rng: RngFactory, turn: int, person_id: int, balance: Balance) -> float:
    """Uniform in people.initial_strain (stream `strain`, key `(person_id,)`)."""
    span = balance.people.initial_strain
    return float(rng.stream(turn, "strain", person_id).uniform(span.lo, span.hi))
