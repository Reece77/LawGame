"""PT-M13's streams (ADR PT-0016 8; PT-0012 ids 130-139): one call site each."""

from __future__ import annotations

import numpy as np

from ptk.sim.streams import RngFactory

SETUP_TURN = 0  # tunable-exempt: a firm's fixed hidden values are drawn at turn 0


def target(rng: RngFactory, rival_key: tuple[int, ...]) -> np.random.Generator:
    return rng.stream(SETUP_TURN, "merger_target", *rival_key)


def book(rng: RngFactory, turn: int, deal_id: int) -> np.random.Generator:
    return rng.stream(turn, "merger_book", deal_id)


def answer(rng: RngFactory, turn: int, deal_id: int, round_: int) -> np.random.Generator:
    return rng.stream(turn, "merger_answer", deal_id, round_)


def clear(rng: RngFactory, turn: int, deal_id: int) -> np.random.Generator:
    return rng.stream(turn, "merger_clear", deal_id)


def people(rng: RngFactory, turn: int, deal_id: int, n: int) -> np.random.Generator:
    return rng.stream(turn, "merger_people", deal_id, n)


def integration(rng: RngFactory, turn: int, deal_id: int, client_id: int) -> np.random.Generator:
    return rng.stream(turn, "integration", deal_id, client_id)


def rival_merger(rng: RngFactory, turn: int, *key: int) -> np.random.Generator:
    return rng.stream(turn, "rival_merger", *key)


def verein(rng: RngFactory, turn: int, verein_id: int, member_firm_id: int) -> np.random.Generator:
    return rng.stream(turn, "verein", verein_id, member_firm_id)
