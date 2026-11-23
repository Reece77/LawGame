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
        "events": 6,  # (): the event director's month: count, matter draws, picks, tones (PT-M6)
        "founder": 7,  # (founder_index,): a founding partner's build; 0 = the player's
        "growth": 8,  # (person_id,): monthly growth noise
        "reveal": 9,  # (observer_firm_id, person_id): reveal record offsets
        "tags": 10,  # (person_id,): monthly tag reveals of employees (PT-M1b)
        "resign": 11,  # (person_id,): the monthly resignation roll (PT-M1b)
        "actions": 13,  # (seq,): randomness inside a player action (ADR-0014; PT-M1b)
        "delegate": 14,  # (person_id, n): a delegate's nth hiring request this turn (PT-M2)
        "partnership": 17,  # (purpose, id): up or out, the comp round (PT-M4; TST's board)
        "poach": 19,  # (person_id,): a partner's month: approach, decision, clients (PT-M4)
        "demand": 20,  # (region, practice_index): monthly legal demand noise (PT-M3a)
        "intake": 21,  # (client_id,): a client's new instructions this month (PT-M3a)
        "matter": 22,  # (matter_id,): a matter's month: judge, progress, errors, outcome (PT-M3a)
        "billing": 23,  # (purpose, id): terms, bills, clients, disputes (PT-M3b; ADR PT-0012)
        "conflict": 24,  # (matter_id,): a hidden conflict surfacing (PT-M3a)
        "rfp": 25,  # (0, client_id) an RFP's opening roll; (1, rfp_id) its award (PT-M5)
        "rival_firm": 26,  # (*rival_key,): a rival firm's month: demand shock, decisions (PT-M5)
        "lateral": 27,  # (person_id,): a lateral offer's answer, portability, arrivals (PT-M4)
        "vote": 28,  # (vote_id, person_id): each partner's vote noise (PT-M4)
        "strain": 29,  # (person_id,): a generated person's starting strain (PT-M1a)
        "campus": 30,  # (year, school_tier_index, search_id): a campus pool (PT-M1b)
        "client_gen": 31,  # (client_index,): a client, its panel and its general counsel (PT-M3a)
        "judge_gen": 33,  # (court_index, n): the n-th generated judge of a court (PT-M3a)
        "book": 34,  # (founder_index,): the clients a founding partner's book came from (PT-M3a)
        "rival_gen": 35,  # (*rival_key,): a generated firm or a boutique's founding (PT-M5)
        "rival_people": 36,  # (*rival_key, n): a rival's n-th key person (PT-M5)
        "real_swap": 37,  # (kind, index): a real judge's generated name if real people are off
        "opposing": 38,  # (matter_id,): a case's opposing counsel (PT-M5)
        "rival_fate": 39,  # (*rival_key,): a rival's collapse hazard and scatter (PT-M5)
        "rival_poach": 40,  # (*rival_key, 0, made_turn): a rival's approach answered (PT-M5)
        "pro_bono": 41,  # (firm_id,): a month's named pro bono matter, its kind and size (PT-M7a)
        "seat_act": 45,  # (seat_index, firm_id, slot): a holder's month under authority (PT-M8)
        "pitch": 46,  # (firm_id, person_id): a holder's quarterly pitch: whether, which (PT-M8)
        "crisis": 42,  # (kind, id): a bill's crisis write-down request and its size (PT-M7b)
        "deal_collapse": 43,  # (matter_id,): a deal's crisis collapse in progress (PT-M7b)
        # PT-M17 (lane C, ids 50-59): the founder's life and family
        "founder_life": 50,  # (purpose, *key): retirement, a bar election, an annuity vote
        "family": 51,  # (head_id, index) a member; (head_id, 0, k) events; (pid, 1); (pid, 2, 0)
        "investments": 52,  # (person_id,): a player's month of investment returns
        "press": 70,  # (firm_id,): a broken claim's reminder wait (PT-M16, lane C's 70-79)
        # PT-M11 (lane B's range 100-109)
        "city_clients": 100,  # (city_index, n): a city's clients, made when a firm opens there
        "bar_exam": 101,  # (exam_id,): a bar exam's pass draw
        "office_team": 102,  # (office_id, n): an office's lifted or lateral team and its books
        "city_demand": 103,  # (city_index, practice_index): a city's monthly demand noise
        "trainees": 104,  # (contract_id, n): a training contract's trainee and their seats
        "press_rival": 71,  # (*rival_key, n): a rival MP's statement at a move, a jab (PT-M16)
        # PT-M9 (lane B, ids 60-64): automation
        "auto_quality": 60,  # (area_index, firm_id, slot): an area's month: q, then its draws
        "auto_events": 61,  # (event_id,): an owner's answer to a routine event: q
        # PT-M10 (lane A, ids 65-69): the seeded world after history (ptk.sim.macro_seed)
        "macro_seed": 65,  # (index_number,): an index's 2026-2034 path; (len(SERIES),) recessions
        "scale_seed": 66,  # (0,) the seeded rate rises; (1,) the salary scale's seeded steps
        # PT-M14 (lane C, ids 110-119): legal technology and AI (ptk.sim.tech)
        "tech_seed": 110,  # (era_index, 0) its strength's 2026+ target; (era_index, 1) the market's
        "tech_vote": 111,  # (era_index,): a rollout vote on an era this month, each partner's noise
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
