"""Geography's steps in the turn (PT-M11), each a no-op for a firm with no other office, no
admission in progress and no trainee, so v1's months are unchanged:

- phase 1: trainees whose training contracts start this month join (`uk.trainees_join`);
- phase 4: each office city's demand, before intake (`markets.demand_month`); after staffing,
  pro hac vice for cases led outside the lead's admissions (`admissions.pro_hac_vice_month`);
- phase 6: the offices' leases and insurance (`offices.office_costs`);
- phase 8: bar exams' and motions' results (`admissions.exams_month`), then trainees' seats,
  second-year pay and qualification (`uk.trainees_month`).
"""

from __future__ import annotations

from ptk.sim.data_models import Balance, GameData
from ptk.sim.geo import admissions, markets, offices, uk
from ptk.sim.ledger import LedgerEntry
from ptk.sim.log import LogItem
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState

type Step = tuple[GameState, tuple[LedgerEntry, ...], tuple[LogItem, ...]]


def phase_one(state: GameState, rng: RngFactory, balance: Balance, data: GameData) -> Step:
    state, logs = uk.trainees_join(state, rng, balance, data)
    return state, (), logs


def before_intake(state: GameState, rng: RngFactory, balance: Balance, data: GameData) -> GameState:
    return markets.demand_month(state, rng, data, balance)


def after_staffing(state: GameState, data: GameData) -> Step:
    return admissions.pro_hac_vice_month(state, data)


def phase_six(state: GameState, balance: Balance, data: GameData) -> Step:
    state, entries = offices.office_costs(state, balance, data)
    return state, entries, ()


def phase_eight(state: GameState, rng: RngFactory, balance: Balance, data: GameData) -> Step:
    state, exam_logs = admissions.exams_month(state, rng, data)
    state, trainee_logs = uk.trainees_month(state, balance, data)
    return state, (), (*exam_logs, *trainee_logs)
