"""Stream `founder_life` (id 50, ADR PT-0012): this package's one call site.

Keys `(purpose, *key)`: `(1, person_id)` a retiring partner's departure (PT-M4's `depart`
draws its clients with it), `(2, person_id)` a bar election, `(3, n)` the n-th partner's vote
on the agreement's annuity term (`n` their place by person id)."""

from __future__ import annotations

from typing import Final

import numpy as np

from ptk.sim.rng import RngFactory

RETIREMENT: Final = 1
BAR_ELECTION: Final = 2
ANNUITY_VOTE: Final = 3


def life_stream(rng: RngFactory, turn: int, purpose: int, *key: int) -> np.random.Generator:
    return rng.stream(turn, "founder_life", purpose, *key)
