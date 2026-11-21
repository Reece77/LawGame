"""The legacy score (spec 2.5, 19; TST formulas.md 32.6), shown with its parts.

Ported from backend/tst/sim/founder/legacy.py @ 121d318a (Tech Startup Tycoon); changed:
the firm's part is `firm_points x log10(1 + the firm's best year's revenue / unit)` (Partner
Track has no company score); the name on the door adds `name_points`; the foundation's
lifetime grants as TST's; the persona as TST's (2 x (Visionary + Beloved) - (Ruthless +
Reckless)); the family adds points for each child who made partner and for a successor from
the family; bar office adds points a year served. No net-worth term (TST 37.5 is M26's).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from ptk.sim import dmath
from ptk.sim.data_models import Balance
from ptk.sim.family.models import CHILD
from ptk.sim.founder import influence
from ptk.sim.state import GameState

GIVING_POINTS: Final = 100  # TST 32.6's formula constant: points per decade of grants
GOOD_WEIGHT: Final = 2  # TST 32.6's formula constant: Visionary and Beloved count twice
CENTS_A_DOLLAR: Final = 100  # tunable-exempt: cents in a dollar


@dataclass(frozen=True, slots=True)
class Legacy:
    total: int
    firm: float
    name_on_door: float
    giving: float
    persona: float
    family: float
    bar: float
    grants_cents: int
    best_revenue_cents: int


def legacy_of(state: GameState, person_id: int, balance: Balance) -> Legacy:
    lb = balance.founder_life.legacy
    fl = state.founder_life
    life = fl.life(person_id)
    best = fl.best_revenue_cents
    # money-exact: ratio
    firm = lb.firm_points * dmath.log10(1 + best / CENTS_A_DOLLAR / lb.firm_unit_dollars)
    person = state.person(person_id)
    door = lb.name_points if person.last_name.lower() in state.player.name.lower() else 0.0
    foundation = fl.foundation(person_id)
    grants = foundation.grants_cents if foundation is not None else 0
    unit = balance.founder_life.foundation.legacy_unit_dollars * CENTS_A_DOLLAR
    # money-exact: ratio
    giving = GIVING_POINTS * dmath.log10(1 + grants / unit)
    start = balance.founder_life.persona.start
    v, r, b, k = (
        (life.visionary, life.ruthless, life.beloved, life.reckless)
        if life is not None
        else (start, start, start, start)
    )
    persona = GOOD_WEIGHT * (v + b) - (r + k)
    family = 0.0
    from ptk.sim.interfaces import partner_ids

    partners = set(partner_ids(state, state.player.id))
    for m in state.family.members:
        if m.relation == CHILD and person_id in m.parent_ids and m.person_id in partners:
            family += lb.child_partner_points
    for s in fl.successions:
        if s.founder_id == person_id and s.result in ("elected", "handed_over"):
            child = state.family.member(s.successor_id)
            if child is not None and child.relation == CHILD and person_id in child.parent_ids:
                family += lb.family_successor_points
    bar = (
        balance.founder_life.influence.legacy_per_year
        * influence.office_years(life, state.turn, balance)
        if life is not None
        else 0.0
    )
    total = round(firm + door + giving + persona + family + bar)
    return Legacy(total, firm, door, giving, persona, family, bar, grants, best)
