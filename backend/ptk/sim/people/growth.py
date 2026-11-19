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

from dataclasses import replace

from ptk.sim.data_models import Balance, GameData, band_value
from ptk.sim.people.formulas import familiarity_after, growth_delta, learn_factor
from ptk.sim.people.models import Person, WorkMonth, role_ability
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
    changes = {}
    for key in data.skill_keys:
        if key not in in_role:
            changes[key] = current[key] - decline
            continue
        noise = float(gen.normal(0.0, growth.noise_rel_sd))
        delta = growth_delta(
            in_role=True,
            age=age,
            ca=ca,
            pa=person.potential_ability,
            professionalism=professionalism,
            growth=growth,
            noise=noise,
            mentoring=mentoring,
            learn=learn,
        )
        changes[key] = current[key] + delta
    return replace(person, skills=person.skills.updated(changes))  # updated() clamps


def grow_familiarity(person: Person, data: GameData, balance: Balance, work: WorkMonth) -> Person:
    """Familiarity in every practice: up with hours worked there, down without (spec 5.3)."""
    fam = balance.familiarity
    values = {
        key: familiarity_after(
            person.familiarity[key], person.familiarity_peak[key], work.tenths_in(key), fam
        )
        for key in data.practice_keys
    }
    familiarity = person.familiarity.updated(values)
    peak = person.familiarity_peak.updated(
        {k: max(person.familiarity_peak[k], familiarity[k]) for k in data.practice_keys}
    )
    return replace(person, familiarity=familiarity, familiarity_peak=peak)


def grow_person(
    person: Person,
    turn: int,
    rng: RngFactory,
    data: GameData,
    balance: Balance,
    work: WorkMonth,
    mentoring: float = 1.0,
) -> Person:
    grown = grow_skills(person, turn, rng, data, balance, work, mentoring)
    return grow_familiarity(grown, data, balance, work)
