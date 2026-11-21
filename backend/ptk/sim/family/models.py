"""PT-M17's family state (spec 2.4; TST formulas.md 45.1-45.3, 45.6): the player's own
generated family. Members are people (`GameState.people`) with no employment until a child
joins a firm; their skills, potential and hidden traits are hidden as for anyone. These
records hold public facts only: relations, closeness, education, the relationship.

Ported from backend/tst/sim/family/models.py @ 121d318a (Tech Startup Tycoon); changed: no
shares, trust holders, seats or dynasty generations (dynasty mode is v3); education is
school and law school; a child in the firm is a lawyer at the firm; estate planning is a
trust that holds personal investments and gifts to heirs.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Final

PARTNER: Final = "partner"
CHILD: Final = "child"
EX_PARTNER: Final = "ex_partner"
RELATIONS: Final = (PARTNER, CHILD, EX_PARTNER)


@dataclass(frozen=True, slots=True)
class FamilyMember:
    """One member of the player's family (TST 45.1). `parent_ids`: a child's parents."""

    person_id: int
    relation: str  # RELATIONS
    member_index: int  # stream family's key (head_id, member_index)
    head_id: int  # the family head when the member joined
    joined_turn: int
    parent_ids: tuple[int, ...] = ()
    closeness: float = 0.0
    school: str | None = None  # config.SCHOOLS, chosen at 12
    law_school: str | None = None  # config.LAW_SCHOOLS, chosen at 18
    milestones: tuple[int, ...] = ()  # ages whose milestone has passed
    mentored: bool = False
    joined_firm_turn: int | None = None  # a child who joined the firm as an associate
    seen_level: str | None = None  # their level when last seen (promotions: nepotism)
    left_turn: int | None = None  # an ex-partner's divorce month


@dataclass(frozen=True, slots=True)
class FamilyNote:
    turn: int
    kind: str
    text: str


@dataclass(frozen=True, slots=True)
class Family:
    """The player's family. `id` is the first head's person id; `head_id` the current head
    (the founder). A successor who is not the founder's child plays without the family."""

    id: int
    setting: str  # config.SETTINGS, never "none" (no record then)
    head_id: int
    created_turn: int
    family_time: int = 0
    relationship: float = 0.0  # 0-100 with the head's partner (TST 45.2)
    partner_since: int | None = None
    married: bool = False
    low_months: int = 0
    next_index: int = 0
    lifetime_gifts_cents: int = 0  # gifts to heirs (TST 45.6)
    estate_tax_cents: int = 0
    trust_turn: int | None = None
    step_back_open: bool = False  # a health event asks the head to step back (TST 45.5)
    notes: tuple[FamilyNote, ...] = ()


@dataclass(frozen=True, slots=True)
class FamilyState:
    family: Family | None = None
    members: tuple[FamilyMember, ...] = ()  # by person id

    def member(self, person_id: int) -> FamilyMember | None:
        return next((m for m in self.members if m.person_id == person_id), None)


EMPTY_FAMILY: Final = FamilyState()


def with_member(fs: FamilyState, m: FamilyMember) -> FamilyState:
    rest = [x for x in fs.members if x.person_id != m.person_id]
    return replace(fs, members=tuple(sorted([*rest, m], key=lambda x: x.person_id)))


def with_family_record(fs: FamilyState, family: Family) -> FamilyState:
    return replace(fs, family=family)


def note(family: Family, turn: int, kind: str, text: str, keep: int) -> Family:
    return replace(family, notes=(*family.notes, FamilyNote(turn, kind, text))[-keep:])
