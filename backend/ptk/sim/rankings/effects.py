"""What the rankings do (spec 12.3): directory bands raise appeal (spec 7.1) and associate
recruiting in their practice for the year; a top Best places to work place raises campus
appeal for the year."""

from __future__ import annotations

from ptk.sim.data_models import Balance
from ptk.sim.state import GameState

YEAR = 12  # tunable-exempt: calendar


def band_of(state: GameState, firm_id: int, practice: str) -> int | None:
    return state.standing.rankings.band(firm_id, practice)


def appeal_bonus(state: GameState, firm_id: int, practice: str, balance: Balance) -> float:
    band = band_of(state, firm_id, practice)
    return 0.0 if band is None else balance.rankings.directory.appeal_bonus[band - 1]


def recruiting_term(
    state: GameState, firm_id: int, role: str | None, campus: bool, balance: Balance
) -> float:
    """Offer-score points: the band in the candidate's practice, and for a campus offer a top
    Best places to work place in the survey's year."""
    rb = balance.rankings
    points = 0.0
    if role is not None:
        band = band_of(state, firm_id, role)
        if band is not None:
            points += rb.directory.recruit_bonus[band - 1]
    if campus:
        rk = state.standing.rankings
        published = rk.published_turn("places")
        if published is not None and state.turn < published + YEAR:
            place = next((r.place for r in rk.places if r.firm_id == firm_id), None)
            if place is not None and place <= rb.places.top:
                points += rb.places.campus_bonus
    return points
