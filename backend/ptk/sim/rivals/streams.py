"""The one call site of each PT-M5 stream used from more than one place (ADR-0013: one
stream per use; tests/unit/test_rng_call_sites.py). Keys as ADR PT-0012's table."""

from __future__ import annotations

import numpy as np

from ptk.sim.rng import RngFactory


def rival_gen(rng: RngFactory, turn: int, *key: int) -> np.random.Generator:
    """A generated firm's making at turn 0 (GENERATED_KEY, n) or a boutique's founding month
    (BOUTIQUE_KEY, n)."""
    return rng.stream(turn, "rival_gen", *key)


def rival_fate(rng: RngFactory, turn: int, key: tuple[int, ...]) -> np.random.Generator:
    """A rival's month of fate: the collapse hazard's roll, then a collapse's scatter."""
    return rng.stream(turn, "rival_fate", *key)


def rfp(rng: RngFactory, turn: int, tag: int, ident: int) -> np.random.Generator:
    """(0, client_id): a client's monthly RFP roll; (1, rfp_id): an RFP's award."""
    return rng.stream(turn, "rfp", tag, ident)


def real_swap(rng: RngFactory, turn: int, tag: int, index: int) -> np.random.Generator:
    """(1, judge index): a real judge's generated name when real people are off; (2, judge
    index): the generated judge who succeeds them."""
    return rng.stream(turn, "real_swap", tag, index)
