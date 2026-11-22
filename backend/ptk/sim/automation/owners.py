"""Owners and eligibility (spec 9.4; TST formulas.md 40.1), area scores (40.3) and default
limits (40.2).

Ported from backend/tst/sim/automation/owners.py @ 80a38079 (Tech Startup Tycoon); changed: an
area's owner is its seat's holder (PT-M8), and an area whose seat is vacant cannot be automated
(the brief); the staffing area has one slot per practice group, owned by its leader once the
leader is eligible for the practice group leader's seat (from stage 2: a group's leader leads
before the seat's stage 3); the pro bono area is owned by any partner but the MP ("a pro bono
partner", spec 9.4); there are no area leads, CEOs or subsidiaries. True scores decide how well
an owner decides and are never shown: the player sees fit bands from displayed ranges only.
"""

from __future__ import annotations

from ptk.sim.automation.config import AreaDef
from ptk.sim.data_models import PARTNER_LEVELS, Balance, GameData
from ptk.sim.money import BP_DENOMINATOR, Cents
from ptk.sim.org.seat_models import EXCO, PGL
from ptk.sim.org.seats import (
    FitBand,
    displayed_score,
    fit_band,
    in_play,
    managing_partner,
    seated_holder,
    slots,
    true_score,
)
from ptk.sim.people.reveal import revealed_range
from ptk.sim.state import GameState

SINGLE = 0
NEUTRAL = 10.0  # tunable-exempt: the attribute scale's middle, for a person the firm cannot see


def area_keys(b: Balance) -> tuple[str, ...]:
    return tuple(b.automation.areas)


def area_def(b: Balance, area: str) -> AreaDef:
    return b.automation.areas[area]


def area_index(b: Balance, area: str) -> int:
    """The area's fixed index: its draws' key in stream `auto_quality` (ADR PT-0012)."""
    return area_keys(b).index(area)


def area_slots(state: GameState, firm_id: int, area: str, b: Balance) -> tuple[int, ...]:
    """Staffing: one slot per active practice group (its unit id); every other area: 0."""
    if area_def(b, area).seat == PGL:
        return tuple(
            u.id
            for u in state.org.firm_units(firm_id)
            if u.kind == "practice_group" and u.practice is not None
        )
    return (SINGLE,)


def _partner(state: GameState, firm_id: int, person_id: int) -> bool:
    e = state.employment_of(person_id)
    if e is None or e.firm_id != firm_id or e.status != "active":
        return False
    p = state.person(person_id)
    return p.level in PARTNER_LEVELS and person_id != managing_partner(state, firm_id)


def eligible_people(
    state: GameState, firm_id: int, area: str, slot: int, b: Balance, data: GameData
) -> tuple[int, ...]:
    """Who may own the area: its seat's holder (an executive committee member for lateral
    partners; any partner but the MP for pro bono). The founder never may (they are the
    player). Empty: the area cannot be automated."""
    a = area_def(b, area)
    if not a.available or not state.firm(firm_id).is_player:
        return ()
    if a.who == "partner":
        return tuple(
            e.person_id for e in state.staff(firm_id) if _partner(state, firm_id, e.person_id)
        )
    assert a.seat is not None
    seat = data.seat(a.seat)
    if seat.key == PGL:
        if slot not in area_slots(state, firm_id, area, b):
            return ()
        pid = seated_holder(state, firm_id, seat, slot, b)
        return () if pid is None else (pid,)
    if not in_play(state, firm_id, seat):
        return ()
    out = []
    for s in slots(state, firm_id, seat, b):
        pid = seated_holder(state, firm_id, seat, s, b)
        if pid is not None and pid not in out:
            out.append(pid)
    founder = state.founder_of(firm_id)
    return tuple(p for p in out if p != founder)


def may_own(
    state: GameState, firm_id: int, area: str, slot: int, person_id: int, b: Balance, data: GameData
) -> bool:
    return person_id in eligible_people(state, firm_id, area, slot, b, data)


def cant_automate(
    state: GameState, firm_id: int, area: str, slot: int, b: Balance, data: GameData
) -> str | None:
    """Why nobody can own the area yet, with how to fix it (TST 40.8), or None."""
    if eligible_people(state, firm_id, area, slot, b, data):
        return None
    a = area_def(b, area)
    if not a.available:
        return a.unavailable_reason or "not in the game yet"
    if a.who == "partner":
        return "needs a partner other than you"
    assert a.seat is not None
    seat = data.seat(a.seat)
    if seat.key == PGL:
        return "the group needs a leader who is an equity partner"
    if not in_play(state, firm_id, seat):
        return f"the {seat.label.lower()} seat opens at stage {seat.stage}"
    if seat.key == EXCO:
        return "appoint the executive committee"
    return f"fill the {seat.label.lower()} seat"


def true_area_score(
    state: GameState, area: str, person_id: int, b: Balance, data: GameData
) -> float:
    """s for the owner (TST 40.3): the seat score for a seat's area, the area's weights over
    true skills for a seatless one. Engine-only, never shown."""
    a = area_def(b, area)
    person = state.person(person_id)
    if a.seat is not None:
        return true_score(person, data.seat(a.seat))
    return sum(w * person.skills[k] for k, w in a.weights.items())


def shown_area_score(
    state: GameState, firm_id: int, area: str, person_id: int, b: Balance, data: GameData
) -> float:
    """The same from the firm's displayed ranges' midpoints: what the player can judge."""
    a = area_def(b, area)
    if a.seat is not None:
        return displayed_score(state, firm_id, person_id, data.seat(a.seat), b)
    reveal = state.reveal(firm_id, person_id)
    if reveal is None:
        return NEUTRAL
    person = state.person(person_id)
    total = 0.0
    for key, w in a.weights.items():
        lo, hi = revealed_range(person, reveal, key)
        total += w * (lo + hi) / 2
    return total


def area_fit(
    state: GameState, firm_id: int, area: str, person_id: int, b: Balance, data: GameData
) -> FitBand:
    return fit_band(shown_area_score(state, firm_id, area, person_id, b, data), b)


def default_limit(cash: Cents, b: Balance) -> int:
    """default_limit_bp of cash, rounded down to limit_round_cents, at least min_limit_cents
    (TST 40.2)."""
    ab = b.automation
    raw = max(0, cash) * ab.default_limit_bp // BP_DENOMINATOR
    return max(ab.min_limit_cents, raw // ab.limit_round_cents * ab.limit_round_cents)


def guardrails(area: str, b: Balance, data: GameData) -> tuple[tuple[str, str, int, int, int], ...]:
    """(key, label, default, min, max) of the area's guardrails: its seat's authority
    guardrails (PT-M8) when it runs the seat's rule, then its own."""
    a = area_def(b, area)
    out: list[tuple[str, str, int, int, int]] = []
    if a.seat_rule and a.seat is not None:
        out += [
            (g.key, g.label, g.default, g.min, g.max)
            for g in data.seat(a.seat).authority.guardrails
        ]
    out += [(g.key, g.label, g.default, g.min, g.max) for g in a.guardrails]
    return tuple(out)


def rail(
    owner_rails: tuple[tuple[str, int], ...], area: str, key: str, b: Balance, data: GameData
) -> int:
    """A guardrail's value: the player's setting, else its default."""
    for k, _label, default, _lo, _hi in guardrails(area, b, data):
        if k == key:
            return next((v for kk, v in owner_rails if kk == key), default)
    raise KeyError(f"area {area} has no guardrail {key!r}")
