"""Hiring rules shared by actions, turn phases and previews (TST formulas.md 7; spec 5.7).

Ported from backend/tst/sim/hiring/rules.py @ 02fba2aa (Tech Startup Tycoon); changed: no
option pool, equity or mission; the fit term counts interests the candidate's home practice
favours; the firm's prestige term (0 until PT-M5/PT-M16); the campus calendar; the offer
dialog's hint reads the firm's revealed ranges only.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction

from ptk.sim.calendar import turn_to_ym
from ptk.sim.data_models import Balance, GameData
from ptk.sim.hiring.formulas import HintBand, hint_band, is_lowball, offer_score, pitch
from ptk.sim.hiring.models import Candidate
from ptk.sim.people.models import Person
from ptk.sim.people.reveal import revealed_range
from ptk.sim.state import GameState

RECRUITING = "recruiting"
RISK_APPETITE = "risk_appetite"


def favoured_interests(person: Person, data: GameData, balance: Balance) -> int:
    """How many of the person's interests their home role favours (interest weight at least
    morale.interest_weight_from): offer fit and the interesting-work term (spec 5.3)."""
    weights = data.role(person.role).interest_weights
    return sum(
        1 for i in person.interests if weights.get(i, 1) >= balance.morale.interest_weight_from
    )


def offer_pitch(state: GameState, actor_id: int, balance: Balance) -> float:
    """The pitch from the true recruiting skill of whoever made the offer (TST 7, M2)."""
    return pitch(state.person(actor_id).skills[RECRUITING], balance.hiring)


def prestige(state: GameState, firm_id: int, balance: Balance) -> float:
    """The firm's prestige term in offer scores: a constant until PT-M5 and PT-M16."""
    return balance.hiring.prestige_term


def floor_cents(ask_cents: int, balance: Balance) -> int:
    """Lowest salary that is not an automatic decline: ceil(ask x lowball_ratio)."""
    return math.ceil(Fraction(ask_cents) * Fraction(str(balance.hiring.lowball_ratio)))


# --- The campus calendar (spec 5.7, ADR PT-0002 section 3) -----------------------------------


def month_of(state: GameState) -> int:
    return turn_to_ym(state.turn, state.save_meta.start_ym)[1]


def campus_registration_open(state: GameState, balance: Balance) -> bool:
    months = balance.campus.register_months
    return months.lo <= month_of(state) <= months.hi


def campus_offers_open(state: GameState, balance: Balance) -> bool:
    return month_of(state) == balance.campus.offer_month


def campus_start_turn(turn: int, start_ym: tuple[int, int], balance: Balance) -> int:
    """The turn of the class's start: start_month of the year after `turn`'s year."""
    month = turn_to_ym(turn, start_ym)[1]
    return turn + (12 - month) + balance.campus.start_month  # tunable-exempt: months a year


def offer_allowed(state: GameState, candidate: Candidate, balance: Balance) -> bool:
    return candidate.channel != "campus" or campus_offers_open(state, balance)


# --- The offer dialog's hint -------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class OfferPreview:
    hint: HintBand
    ratio: float  # offered salary / ask
    floor_cents: int
    ask_cents: int


def offer_preview(
    state: GameState,
    candidate: Candidate,
    salary_cents: int,
    balance: Balance,
    data: GameData,
    actor_id: int | None = None,
) -> OfferPreview:
    """The hint, from what the firm knows (TST 7): R exactly; fit counts favoured interests
    only once interests are revealed; risk appetite at the midpoint of its displayed range;
    the pitch of the offer maker (usually the player's founding partner, known exactly).
    Nothing is drawn or saved."""
    person = state.person(candidate.person_id)
    ask = candidate.ask_cents
    # money-exact: ratio
    ratio = salary_cents / ask if ask else 0.0
    reveal = state.reveal(candidate.firm_id, person.id)
    if reveal is None:  # every candidate gets a knowledge record when generated
        raise RuntimeError(f"firm {candidate.firm_id} has no knowledge of {person.id}")
    fit = 0 if reveal.profile_revealed_turn is None else favoured_interests(person, data, balance)
    lo, hi = revealed_range(person, reveal, RISK_APPETITE)
    score = offer_score(
        ratio=ratio,
        matching_interests=fit,
        risk_appetite=(lo + hi) / 2,
        offer=balance.hiring.offer,
        prestige=prestige(state, candidate.firm_id, balance),
        pitch=0.0 if actor_id is None else offer_pitch(state, actor_id, balance),
    )
    hint: HintBand = (
        "unlikely" if is_lowball(ratio, balance.hiring) else hint_band(score, balance.hiring)
    )
    return OfferPreview(
        hint=hint, ratio=ratio, floor_cents=floor_cents(ask, balance), ask_cents=ask
    )
