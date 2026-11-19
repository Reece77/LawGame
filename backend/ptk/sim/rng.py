"""Derived, seeded random streams (ADR-0002, ADR-0013, ADR PT-0012).

Ported from tst/sim/rng.py @ 02fba2aa; changed: Partner Track's own STREAM_IDS table.

Each save stores one 64-bit master seed. A generator for a given turn and subsystem is
derived from it on demand, so no generator state is ever persisted, and adding a stream
never changes the draws of an existing one.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Final

import numpy as np

from ptk.sim.errors import InvalidSeedError, UnknownStreamError

# Append-only. Never renumber or reuse an id: that would change every save's outcomes.
# Ids 1-19 keep Tech Startup Tycoon's meanings for ported systems (ADR PT-0012); 20-98 are
# Partner Track's own; 99 is for tests. A stream is added by the milestone that first draws.
STREAM_IDS: Final = MappingProxyType(
    {
        "people_gen": 1,  # (search_id, n): generated people; search 0 = a scenario's staff
        "hiring": 2,  # (offer_id,): an offer's acceptance draw (PT-M1b)
        "morale": 3,  # (person_id,): monthly morale noise (PT-M1b)
        "founder": 7,  # (founder_index,): a founding partner's build; 0 = the player's
        "growth": 8,  # (person_id,): monthly growth noise
        "reveal": 9,  # (observer_firm_id, person_id): reveal record offsets
        "tags": 10,  # (person_id,): monthly tag reveals of employees (PT-M1b)
        "resign": 11,  # (person_id,): the monthly resignation roll (PT-M1b)
        "actions": 13,  # (seq,): randomness inside a player action (ADR-0014; PT-M1b)
        "delegate": 14,  # (person_id, n): a delegate's nth hiring request this turn (PT-M2)
        "strain": 29,  # (person_id,): a generated person's starting strain (PT-M1a)
        "campus": 30,  # (year, school_tier_index, search_id): a campus pool (PT-M1b)
        "misc": 99,  # tests only
    }
)

MAX_SEED: Final = 2**64 - 1


class RngFactory:
    """Hands out independent generators keyed by (turn, stream name, *entity keys).

    ADR-0013: every call site uses its own stream name, and draws that belong to one entity
    pass that entity's id as a key, so they do not depend on iteration order.
    """

    __slots__ = ("_master_seed",)

    def __init__(self, master_seed: int) -> None:
        if isinstance(master_seed, bool) or not isinstance(master_seed, int):
            raise InvalidSeedError(f"master seed must be an int, got {type(master_seed).__name__}")
        if not 0 <= master_seed <= MAX_SEED:
            raise InvalidSeedError(f"master seed must be in 0..2**64-1, got {master_seed}")
        self._master_seed = master_seed

    @property
    def master_seed(self) -> int:
        return self._master_seed

    def stream(self, turn: int, name: str, *key: int) -> np.random.Generator:
        if name not in STREAM_IDS:
            raise UnknownStreamError(f"unknown RNG stream {name!r}; add it to STREAM_IDS")
        if turn < 0:
            raise InvalidSeedError(f"turn must be >= 0 for an RNG stream, got {turn}")
        for part in key:
            if isinstance(part, bool) or not isinstance(part, int) or part < 0:
                raise InvalidSeedError(f"stream keys must be non-negative ints, got {key!r}")
        seq = np.random.SeedSequence(
            entropy=self._master_seed, spawn_key=(turn, STREAM_IDS[name], *key)
        )
        return np.random.Generator(np.random.PCG64(seq))
