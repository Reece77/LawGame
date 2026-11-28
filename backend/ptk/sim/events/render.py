"""Placeholder names for an event (TST formulas.md 16.4) and template rendering. Only what the
player can see: names, a practice group's name, a client's and its general counsel's names, a
matter's name, a practice's and a court's labels, a sum and a count of months.

Ported from backend/tst/sim/events/render.py @ 02fba2aa (Tech Startup Tycoon); changed: law
placeholders (client, gc, matter, practice, court) replace product, segment, rival and loan.
"""

from __future__ import annotations

from collections.abc import Mapping

from simcore.kernel.money import format_money

from ptk.sim.data_models import GameData
from ptk.sim.events.data import PLACEHOLDER_RE
from ptk.sim.people.models import Person
from ptk.sim.state import GameState

PARTNERSHIP = "the partnership"


def full_name(person: Person) -> str:
    return f"{person.first_name} {person.last_name}"


def placeholder_names(
    state: GameState,
    data: GameData,
    firm_id: int,
    *,
    person_ids: tuple[int, ...] = (),
    unit_id: int | None = None,
    client_id: int | None = None,
    matter_id: int | None = None,
    practice: str | None = None,
    months: int | None = None,
    amount_cents: int | None = None,
) -> dict[str, str]:
    firm = state.firm(firm_id)
    founder_id = state.founder_of(firm_id)
    names = {
        "firm": firm.name,
        "founder": full_name(state.person(founder_id)) if founder_id else "the founding partner",
        "partnership": PARTNERSHIP,
    }
    known = {p.id for p in state.people}
    people = [state.person(p) for p in person_ids if p in known]
    if people:
        names["person"] = full_name(people[0])
    if len(people) > 1:
        names["other"] = full_name(people[1])
    # The firm root has no unit row: its {unit} is the firm.
    unit = state.org.unit(unit_id) if unit_id is not None else None
    names["unit"] = unit.name if unit is not None else firm.name
    matter = state.market.matter(matter_id) if matter_id is not None else None
    if matter is not None:
        names["matter"] = matter.name
        client_id = client_id if client_id is not None else matter.client_id
        practice = practice or matter.practice
        if matter.court is not None:
            names["court"] = data.courts.court(matter.court).label
    if client_id is not None:
        client = state.market.client(client_id)
        names["client"] = client.name
        names["gc"] = f"{client.gc.first_name} {client.gc.last_name}"
    if practice is not None:
        names["practice"] = data.practice(practice).label
    if months is not None:
        names["months"] = str(months)
    if amount_cents is not None:
        names["amount"] = format_money(amount_cents)
    return names


def render(text: str, names: Mapping[str, str]) -> str:
    """Fill {placeholders}; an unknown one is left as written (templates are checked at load)."""
    return PLACEHOLDER_RE.sub(lambda m: names.get(m.group(1), m.group(0)), text)
