"""Partner Track's stream table (ADR PT-0012, ADR PT-0019; SC-0002).

Ids 1-19 are sim-core's core streams with TST's names and meanings (`simcore.kernel.rng`):
PT draws on people_gen 1, hiring 2, morale 3, events 6, founder 7, growth 8, reveal 9, tags 10,
resign 11, actions 13, delegate 14 and poach 19 with the meanings ADR PT-0012 gives them, and
names core stream 17 (`governance`) `partnership`, as TST names it `board`. 99 `misc` is for
tests. PT's own rows below are registered with `StreamTable.build`; the table is append-only:
never renumber or reuse an id, it is part of every draw. A stream is added by the milestone
that first draws on it, here and in ADR PT-0012's table.

`RngFactory` is sim-core's, bound to PT's table. PT keeps refusing negative turns and keys at
its own boundary (sim-core accepts them for TST ADR-0024; PT has no month before turn 0).
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Final

import numpy as np
from simcore.kernel import rng as core_rng
from simcore.kernel.errors import InvalidSeedError
from simcore.kernel.rng import StreamTable

# name -> id: Partner Track's own rows (20-98, 100-199), with the key each draw passes.
OWN_ROWS: Final[Mapping[str, int]] = MappingProxyType(
    {
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
        "macro_seed": 65,  # (series_key,): an index's 2026-2034 path; (12,) recessions (PT-M12)
        "scale_seed": 66,  # (0,) the seeded rate rises; (1,) the salary scale's seeded steps
        # PT-M14 (lane C, ids 110-119): legal technology and AI (ptk.sim.tech)
        "tech_seed": 110,  # (era_index, 0) its strength's 2026+ target; (era_index, 1) the market's
        "tech_vote": 111,  # (era_index,): a rollout vote on an era this month, each partner's noise
        # PT-M12 (lane A, ids 120-129): the twenty practices
        "funding": 120,  # (matter_id,): a funder's terms for a contingency case, at its opening
        "practice_team": 121,  # (practice_index, n): a team entering a practice, its n-th person
        # PT-M15 (lane C, ids 140-149): risk and ethics (ptk.sim.risk; ADR PT-0017)
        "risk_claim": 140,  # (1, matter_id, n) an escape's claim; (2, matter_id, 0) a grievance
        "risk_case": 141,  # (claim_id,): a claim's month: drop, offer, stage length, trial
        "discipline": 142,  # (firm_id,): the month's disciplinary rolls, by person id
        "discipline_case": 143,  # (case_id,): a case's month: stage length, then the outcome
        "regulator": 144,  # (purpose, id): (1, firm_id) inquiries opened; (2, inquiry_id) its month
        "trust": 145,  # (firm_id,): the month's client-account errors and misuse
        "audit": 146,  # (bill_id,): a client's e-billing audit of a new bill
        "arbitration": 147,  # (2, arbitration_id): the award (the filing is the hold's action draw)
        # PT-M13 (lane B, ids 130-139): mergers and the verein (ptk.sim.mergers; ADR PT-0016)
        "merger_target": 130,  # (*rival_key,) at turn 0: a firm's fixed hidden values
        "merger_book": 131,  # (deal_id,): a deal's client book, drawn when talks open
        "merger_answer": 132,  # (deal_id, round): the other side's answer, each partner's noise
        "merger_clear": 133,  # (deal_id,): clearance's waiver draws, in conflict order
        "merger_people": 134,  # (deal_id, n): the n-th materialised lawyer at closing
        "integration": 135,  # (deal_id, client_id): a book client's balk at the merged card
        "rival_merger": 136,  # (0,) a month's approach to the player; (1,) a free-play merger
        "verein": 137,  # (verein_id, member_firm_id): a member's quarterly introduction
    }
)

ALIASES: Final[Mapping[str, str]] = MappingProxyType({"partnership": "governance"})

TABLE: Final = StreamTable.build(OWN_ROWS, aliases=ALIASES)
# Every name PT's factory accepts (core rows, PT's rows, the alias), by id.
STREAM_IDS: Final = TABLE.ids
MAX_SEED: Final = core_rng.MAX_SEED


class RngFactory(core_rng.RngFactory):
    """sim-core's factory with Partner Track's table; turns and keys from 0 only."""

    __slots__ = ()

    def __init__(self, master_seed: int) -> None:
        super().__init__(master_seed, TABLE)

    def stream(self, turn: int, name: str, *key: int) -> np.random.Generator:
        if turn < 0:
            raise InvalidSeedError(f"turn must be >= 0 for an RNG stream, got {turn}")
        for part in key:
            if isinstance(part, bool) or not isinstance(part, int) or part < 0:
                raise InvalidSeedError(f"stream keys must be non-negative ints, got {key!r}")
        return super().stream(turn, name, *key)
