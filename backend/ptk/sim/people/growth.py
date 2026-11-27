"""Monthly skill growth, learning and practice familiarity (spec 5.3; turn phase 8).

Ported from backend/tst/sim/people/growth.py @ 02fba2aa (Tech Startup Tycoon); changed:
the growth term is multiplied by learn(h) from the person's month of work (ADR PT-0006
section 4); practice familiarity grows with hours in each practice and decays without them
(spec 5.3); every person grows in their own role (no founder best fit).

Applies to everyone with an active or notice employment, founding partners included. Age
is derived from birth_turn, so aging needs no update. Noise is multiplicative on the growth
term and comes from stream `growth` keyed by person id: one Normal(0, noise_rel_sd) draw per
role skill (primary and secondary), in skills.yaml order. Skills outside the role draw
nothing and change only by -d(age). Familiarity draws nothing.
"""

from __future__ import annotations

from ptk.sim.data_models import Balance, GameData, band_value
from ptk.sim.fastcopy import replace
from ptk.sim.people.formulas import familiarity_after, growth_base, learn_factor
from ptk.sim.people.models import Familiarity, Person, Skills, WorkMonth, role_ability
from ptk.sim.rng import RngFactory


def grow_skills(
    person: Person,
    turn: int,
    rng: RngFactory,
    data: GameData,
    balance: Balance,
    work: WorkMonth,
    mentoring: float = 1.0,
) -> Person:
    """One month of growth: role skills grow toward PA at learn(h), every skill declines
    with age. `mentoring` is TST 13.5's M_growth (1 until PT-M2)."""
    return replace(person, skills=_grown_skills(person, turn, rng, data, balance, work, mentoring))


def _grown_skills(
    person: Person,
    turn: int,
    rng: RngFactory,
    data: GameData,
    balance: Balance,
    work: WorkMonth,
    mentoring: float,
) -> Skills:
    growth = balance.growth
    role = data.role(person.role)
    in_role = set(role.skills)
    ca = role_ability(person.skills, role)
    age = person.age(turn)
    professionalism = person.personality["professionalism"]
    learn = learn_factor(work.total_tenths, work.substantive_tenths, growth)
    gen = rng.stream(turn, "growth", person.id)

    current = person.skills.as_dict()
    decline = band_value(growth.decline, age)  # growth_delta for a skill outside the role
    # PT-M18 (T12): growth_delta's terms that do not depend on the skill, once (the same
    # operations in the same order: identical values), and the role skills' noise as one
    # array (the same values as one draw at a time, in skills.yaml order)
    base = growth_base(age, ca, person.potential_ability, professionalism, growth)
    keys = [k for k in data.skill_keys if k in in_role]
    noises = dict(
        zip(keys, gen.normal(0.0, growth.noise_rel_sd, size=len(keys)).tolist(), strict=True)
    )
    changes = {}
    for key in data.skill_keys:
        if key not in in_role:
            changes[key] = current[key] - decline
            continue
        delta = base * max(0.0, 1 + noises[key]) * mentoring * learn - decline
        changes[key] = current[key] + delta
    return person.skills.updated(changes)  # updated() clamps


def grow_familiarity(person: Person, data: GameData, balance: Balance, work: WorkMonth) -> Person:
    """Familiarity in every practice: up with hours worked there, down without (spec 5.3)."""
    familiarity, peak = _grown_familiarity(person, data, balance, work)
    return replace(person, familiarity=familiarity, familiarity_peak=peak)


def _grown_familiarity(
    person: Person, data: GameData, balance: Balance, work: WorkMonth
) -> tuple[Familiarity, Familiarity]:
    fam = balance.familiarity
    # PT-M12 (T12, rule 6): dict lookups, not AttrSet's linear scan, for twenty practices
    current = person.familiarity.as_dict()
    peaks = person.familiarity_peak.as_dict()
    values = {
        key: familiarity_after(current[key], peaks[key], work.tenths_in(key), fam)
        for key in data.practice_keys
    }
    familiarity = person.familiarity.updated(values)
    after = familiarity.as_dict()
    rises = {k: v for k, v in after.items() if v > peaks[k]}  # usually none, or the home one
    peak = person.familiarity_peak.updated(rises) if rises else person.familiarity_peak
    return familiarity, peak


def grow_person(
    person: Person,
    turn: int,
    rng: RngFactory,
    data: GameData,
    balance: Balance,
    work: WorkMonth,
    mentoring: float = 1.0,
) -> Person:
    # PT-M18 (T12): one copy of the person (skills and familiarity are independent)
    skills = _grown_skills(person, turn, rng, data, balance, work, mentoring)
    familiarity, peak = _grown_familiarity(person, data, balance, work)
    return replace(person, skills=skills, familiarity=familiarity, familiarity_peak=peak)
