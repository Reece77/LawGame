"""Up or out and the December vote (spec 5.5).

An associate is eligible at the agreement's track year (default 8); counsel are eligible too,
and income partners for equity. From the sponsor year (associate_6) each associate has a
sponsor: the player names one, or the partner in their practice with the best mentoring is
given in September. In December the player proposes candidates (equity, income, counsel or
not this year); admissions are votes counted in December's phase 1. In December's phase 10
every eligible associate who was not admitted, made counsel or deferred is told to move on:
they leave within `leave_months`, some for a client's in-house team (alumni, v2).
"""

from __future__ import annotations

from dataclasses import replace

from ptk.sim.data_models import SCALE_LEVELS, Balance, GameData
from ptk.sim.log import LogItem, inbox_item
from ptk.sim.partnership.common import firm_partnership, home_practice, name, put, ym
from ptk.sim.partnership.effects import PURPOSE_UP_OR_OUT, partnership_stream
from ptk.sim.partnership.models import (
    Departure,
    FirmPartnership,
    MovingOn,
    with_departure,
    with_moving_on,
    with_sponsor,
)
from ptk.sim.state import GameState, with_employment
from ptk.sim.streams import RngFactory

SENIOR = "senior_associate"
COUNSEL = "counsel"
INCOME = "income_partner"
SENIOR_CLASS = 9  # tunable-exempt: a senior associate is past class year 8


def class_year(level: str) -> int | None:
    if level == SENIOR:
        return SENIOR_CLASS
    if level in SCALE_LEVELS:
        return SCALE_LEVELS.index(level) + 1
    return None


def eligible(state: GameState, fp: FirmPartnership, person_id: int, balance: Balance) -> bool:
    person = state.person(person_id)
    if fp.partner(person_id) is not None and fp.partner(person_id).equity:  # type: ignore[union-attr]
        return False
    if person.level in (COUNSEL, INCOME):
        return True
    year = class_year(person.level)
    return year is not None and year >= fp.agreement.track_years


def tracks_for(state: GameState, fp: FirmPartnership, person_id: int) -> tuple[str, ...]:
    level = state.person(person_id).level
    if level == INCOME:
        return ("equity", "not_this_year")
    tracks = ["equity"]
    if fp.agreement.two_tier:
        tracks.append("income")
    if level != COUNSEL:
        tracks.append("counsel")
    tracks.append("not_this_year")
    return tuple(tracks)


def default_sponsor(
    state: GameState, fp: FirmPartnership, person_id: int, data: GameData
) -> int | None:
    practice = home_practice(state.person(person_id), data)
    best: tuple[float, int] | None = None
    for p in fp.equity_partners:
        person = state.person(p.person_id)
        if home_practice(person, data) != practice:
            continue
        key = (-person.skills["mentoring"], p.person_id)
        if best is None or key < best:
            best = key
    return best[1] if best else fp.mp_id


def sponsored_levels(balance: Balance) -> frozenset[str]:
    start = SCALE_LEVELS.index(balance.partnership.up_or_out.sponsor_from)
    return frozenset((*SCALE_LEVELS[start:], SENIOR, COUNSEL))


def assign_sponsors(state: GameState, balance: Balance, data: GameData) -> GameState:
    """September: associates from the sponsor year without one are given a sponsor."""
    if ym(state)[1] != balance.people.class_year_month:
        return state
    levels = sponsored_levels(balance)
    for fp in state.partnership.firms:
        for e in state.staff(fp.firm_id):
            person = state.person(e.person_id)
            if person.level not in levels or fp.sponsor_of(person.id) is not None:
                continue
            sponsor = default_sponsor(state, fp, person.id, data)
            if sponsor is not None:
                fp = with_sponsor(fp, person.id, sponsor)
        state = put(state, fp)
    return state


def december(
    state: GameState, rng: RngFactory, balance: Balance
) -> tuple[GameState, tuple[LogItem, ...]]:
    """December's phase 10: eligible associates not admitted, made counsel or deferred are
    told to move on; this year's candidacies close."""
    if ym(state)[1] != 12:  # tunable-exempt: the December vote
        return state, ()
    cfg = balance.partnership.up_or_out
    logs: list[LogItem] = []
    year = ym(state)[0]
    for fp0 in state.partnership.firms:
        fp = fp0
        for e in state.staff(fp.firm_id):
            person = state.person(e.person_id)
            if e.status != "active" or class_year(person.level) is None:
                continue
            if not eligible(state, fp, person.id, balance):
                continue
            cand = fp.candidacy(person.id)
            if cand is not None and cand.year == year and cand.track == "not_this_year":
                continue
            if any(m.person_id == person.id for m in fp.moving_on):
                continue
            gen = partnership_stream(rng, state.turn, PURPOSE_UP_OR_OUT, person.id)
            leave = state.turn + int(gen.integers(1, cfg.leave_months + 1))
            in_house = int(gen.integers(0, 10_000)) < cfg.in_house_bp  # tunable-exempt: a bp roll
            fp = with_moving_on(fp, MovingOn(person.id, fp.firm_id, state.turn, leave, in_house))
            logs.append(
                inbox_item(
                    state.turn,
                    fp.firm_id,
                    "told_to_move_on",
                    link_kind="person",
                    link_id=person.id,
                    name=name(person),
                )
            )
        fp = replace(fp, candidacies=tuple(c for c in fp.candidacies if c.year != year))
        state = put(state, fp)
    return state, tuple(logs)


def moving_on_month(state: GameState, data: GameData) -> tuple[GameState, tuple[LogItem, ...]]:
    """Phase 8: associates told to move on leave at their month, unless made counsel or a
    partner in the meantime."""
    logs: list[LogItem] = []
    for fp0 in state.partnership.firms:
        fp = firm_partnership(state, fp0.firm_id)
        keep: list[MovingOn] = []
        for m in fp.moving_on:
            person = state.person(m.person_id)
            e = state.employment_of(m.person_id)
            if e is None or e.status != "active" or class_year(person.level) is None:
                continue  # gone already, or made counsel or partner
            if m.leave_turn > state.turn:
                keep.append(m)
                continue
            state = with_employment(
                state, replace(e, status="notice", end_turn=state.turn + 1, end_reason="resigned")
            )
            fp = with_departure(
                fp,
                Departure(
                    person_id=m.person_id,
                    firm_id=fp.firm_id,
                    turn=state.turn,
                    leave_turn=state.turn + 1,
                    practice=home_practice(person, data),
                    reason="up_or_out",
                    equity=False,
                    suitor_key="in_house" if m.in_house else None,
                    suitor_name="a client's in-house team" if m.in_house else None,
                    suitor_firm_id=None,
                    book_cents=0,
                ),
            )
            logs.append(
                inbox_item(
                    state.turn,
                    fp.firm_id,
                    "moved_on",
                    link_kind="person",
                    link_id=m.person_id,
                    name=name(person),
                    destination="a client's in-house team" if m.in_house else "another firm",
                )
            )
        state = put(state, replace(fp, moving_on=tuple(keep)))
    return state, tuple(logs)
