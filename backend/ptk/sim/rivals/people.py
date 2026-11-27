"""Rival key people (ADR PT-0008 3; ADR PT-0013): generation, real notables, lookups, moves.

A key person is generated like any lawyer (`generate_person`, stream `rival_people`, key
`(*rival_key, n)` where n counts the rival's key people ever made), so they are scoutable and
poachable with the engine's own rules. They are generated **on demand** from their `Member`
record (`person_of`), which is a pure function of the seed and those keys, so the state holds
no rival people until the player's firm meets one. A real notable (notables.yaml) is a generated
person
with the notable's practice and level, a current ability drawn inside the range of their
public standing (balance `rivals.standing_ca`), an age from their career-start year, no
negative tags, and `real` set. With `world.real_people` off the generated name stays: the
draws are the same, so play is identical apart from names (ADR PT-0013).

Rival people's skills do not grow while they are at a rival (only the player's people have
months of work); they age, are promoted by class year, retire (real people by their year,
then everyone by `rivals.retire_age`) and move.
"""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np

from ptk.sim.calendar import MONTHS_PER_YEAR, YearMonth, ym_to_turn
from ptk.sim.data_models import Balance, GameData
from ptk.sim.fastcopy import replace
from ptk.sim.people.formulas import current_ability
from ptk.sim.people.generator import _rescale_primaries, generate_person
from ptk.sim.people.models import Person, Skills
from ptk.sim.rivals.data import NotableDef
from ptk.sim.rivals.models import Member, MemberKind, RivalFirm, RivalsState
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState

JURISDICTION = "us_ny"  # tunable-exempt: v1's one bar (every modelled lawyer is admitted in NY)
ASSOCIATE_LEVELS = ("associate_5", "associate_6", "associate_7", "senior_associate")
STANDING_ORDER = {"elite": 0, "leading": 1, "strong": 2}  # tunable-exempt: sort order


def rival_people_stream(
    rng: RngFactory, turn: int, key: tuple[int, ...], n: int
) -> np.random.Generator:
    """Stream `rival_people`: a rival's n-th key person (one call site)."""
    return rng.stream(turn, "rival_people", *key, n)


def make_person(
    rng: RngFactory,
    turn: int,
    gen_key: tuple[int, ...],
    hq: str,
    n: int,
    person_id: int,
    practice: str,
    level: str,
    data: GameData,
    balance: Balance,
    notable: NotableDef | None = None,
    real_names: bool = True,
    start: YearMonth = (2005, 1),
) -> Person:
    gen = rival_people_stream(rng, turn, gen_key, n)
    person = generate_person(
        gen,
        data,
        balance,
        turn,
        data.practice_role(practice),
        level,
        person_id=person_id,
        city=hq,
        jurisdiction=JURISDICTION,
    )
    if notable is None:
        return person
    band = balance.rivals.standing_ca[notable.standing]
    target = float(gen.uniform(band.lo, band.hi))
    role = data.practice_role(practice)
    raw = _rescale_primaries(person.skills.as_dict(), role, target)
    skills = Skills.build(data.skill_keys, raw)
    ca = current_ability(skills.as_dict(), role.primary, role.secondary)
    month = int(gen.integers(1, MONTHS_PER_YEAR + 1))
    birth_year = notable.career_start - balance.rivals.career_start_age
    negative = {t.key for t in data.tags if t.negative}
    fam = person.familiarity.updated(
        {practice: max(person.familiarity[practice], balance.rivals.notable_familiarity)}
    )
    return replace(
        person,
        first_name=notable.first_name if real_names else person.first_name,
        last_name=notable.last_name if real_names else person.last_name,
        birth_turn=ym_to_turn(birth_year, month, start),
        skills=skills,
        potential_ability=max(person.potential_ability, ca),
        familiarity=fam,
        familiarity_peak=fam,
        tags=tuple(t for t in person.tags if t not in negative),
        real=True,
    )


def books(total_cents: float, n: int, pareto: float) -> list[int]:
    """Key partners' books: total split by rank^-a (the first is the biggest)."""
    if n <= 0:
        return []
    weights = [(i + 1) ** -pareto for i in range(n)]
    s = sum(weights)
    return [round(total_cents * w / s) for w in weights]


# --- On-demand people (a pure function of the seed and the member's generation keys) -------

_MADE: dict[tuple[object, ...], Person] = {}
_MADE_MAX = 20_000  # tunable-exempt: a memo's size, not a game number


def generate(
    rng: RngFactory,
    m: Member,
    data: GameData,
    balance: Balance,
    real_names: bool,
    start: YearMonth,
) -> Person:
    """The member as generated (memoised: the same keys always give the same person)."""
    key = (rng.master_seed, m.gen_key, m.n, m.made_turn, m.person_id, m.practice, m.gen_level,
           m.gen_hq, m.notable, real_names, start, id(data), id(balance))  # fmt: skip
    made = _MADE.get(key)
    if made is None:
        notable = None
        if m.notable is not None:
            notable = next(x for x in data.rivals.people.notables if x.key == m.notable)
        made = make_person(
            rng, m.made_turn, m.gen_key, m.gen_hq, m.n, m.person_id, m.practice, m.gen_level,
            data, balance, notable=notable, real_names=real_names, start=start,
        )  # fmt: skip
        if len(_MADE) >= _MADE_MAX:
            _MADE.clear()
        _MADE[key] = made
    return made


def person_of(state: GameState, m: Member, data: GameData, balance: Balance) -> Person:
    """A key person as they are now."""
    if m.outside:
        return state.person(m.person_id)
    made = generate(
        RngFactory(state.save_meta.master_seed), m, data, balance, state.rivals.real_people,
        state.save_meta.start_ym,
    )  # fmt: skip
    return replace(made, level=m.level, book_cents=m.book_cents)


def find_person(
    state: GameState, person_id: int, data: GameData, balance: Balance
) -> Person | None:
    m = state.rivals.member(person_id)
    if m is not None:
        return person_of(state, m, data, balance)
    agent = next((a for a in state.rivals.free_agents if a.person_id == person_id), None)
    if agent is not None:
        return person_of(state, agent.member, data, balance)
    return next((q for q in state.people if q.id == person_id), None)


def key_people(
    state: GameState, firm_id: int, data: GameData, balance: Balance
) -> list[tuple[Member, Person]]:
    return [(m, person_of(state, m, data, balance)) for m in state.rivals.members_of(firm_id)]


def new_member(
    firm: RivalFirm,
    person_id: int,
    n: int,
    turn: int,
    practice: str,
    level: str,
    book_cents: int,
    notable: str | None = None,
) -> Member:
    return Member(
        person_id=person_id, firm_id=firm.id, kind=member_kind(level), practice=practice,
        book_cents=book_cents, since_turn=turn, level=level, gen_key=firm.rival_key,
        gen_hq=firm.hq, n=n, made_turn=turn, gen_level=level, notable=notable,
    )  # fmt: skip


def add_members(rivals: RivalsState, members: Iterable[Member]) -> RivalsState:
    new = list(members)
    if not new:
        return rivals
    ids = {m.person_id for m in new}
    kept = [m for m in rivals.members if m.person_id not in ids]
    merged = sorted([*kept, *new], key=lambda m: m.person_id)
    next_id = max([rivals.next_person_id, *(m.person_id + 1 for m in new)])
    return replace(rivals, members=tuple(merged), next_person_id=next_id)


def update_member(rivals: RivalsState, member: Member) -> RivalsState:
    return replace(
        rivals,
        members=tuple(member if m.person_id == member.person_id else m for m in rivals.members),
    )


def drop_member(rivals: RivalsState, person_id: int) -> RivalsState:
    """The person is no longer a key person of a rival."""
    return replace(rivals, members=tuple(m for m in rivals.members if m.person_id != person_id))


def move_member(rivals: RivalsState, person_id: int, firm_id: int, turn: int) -> RivalsState:
    members = tuple(
        replace(m, firm_id=firm_id, since_turn=turn) if m.person_id == person_id else m
        for m in rivals.members
    )
    return replace(rivals, members=members)


def member_kind(level: str) -> MemberKind:
    return "partner" if level in ("equity_partner", "income_partner", "counsel") else "associate"
