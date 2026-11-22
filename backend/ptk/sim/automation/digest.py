"""The monthly digest (spec 9.4; TST formulas.md 40.4) and the areas' KPIs.

Ported from backend/tst/sim/automation/digest.py and kpis.py @ 80a38079 (Tech Startup
Tycoon); changed: Partner Track's areas and KPIs; the digest is one inbox item at month end
(phase 12) whose body lists each automated area's owner, what they did (a count and up to
three lines), money committed against the monthly limit, decisions near a limit, proposals
waiting and the owner's own note; it links to the Automation screen's digest for the month,
which shows every line with its links (`digest_view`). The opening paragraph is a template
(an LLM voice is a follow-up). Items produced by automated areas carry `in_digest`, and the
inbox's default view leaves them out.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from ptk.sim.automation import owners
from ptk.sim.automation.models import AreaDecision, AreaOwner
from ptk.sim.calendar import format_turn
from ptk.sim.data_models import Balance, GameData
from ptk.sim.log import LogItem, inbox_item
from ptk.sim.state import GameState

LINES_SHOWN: Final = 3  # tunable-exempt: lines per area in the inbox body (TST 40.4)
BP: Final = 10_000  # tunable-exempt
ACTED: Final = frozenset({"decision", "mistake", "event"})


@dataclass(frozen=True, slots=True)
class AreaMonth:
    owner: AreaOwner
    lines: tuple[AreaDecision, ...]
    committed_cents: int
    near_limit: tuple[AreaDecision, ...]
    proposals_waiting: int
    note: str


def month_lines(state: GameState, turn: int, firm_id: int) -> tuple[AreaDecision, ...]:
    return tuple(d for d in state.automation.decisions if d.turn == turn and d.firm_id == firm_id)


def near(d: AreaDecision, o: AreaOwner, b: Balance) -> bool:
    return (
        d.commitment_cents > 0
        and d.commitment_cents * BP >= b.automation.near_limit_bp * o.limit_cents
    )


def area_months(state: GameState, turn: int, b: Balance) -> tuple[AreaMonth, ...]:
    firm = state.player.id
    lines = month_lines(state, turn, firm)
    pending = state.automation.pending(firm)
    out = []
    for o in state.automation.owners:
        if o.firm_id != firm:
            continue
        mine = tuple(d for d in lines if (d.area, d.slot) == o.key)
        committed = sum(d.commitment_cents for d in mine if d.kind in ACTED)
        waiting = sum(1 for p in pending if (p.area, p.slot) == o.key)
        out.append(
            AreaMonth(
                owner=o,
                lines=mine,
                committed_cents=committed,
                near_limit=tuple(d for d in mine if d.kind in ACTED and near(d, o, b)),
                proposals_waiting=waiting,
                note=owner_note(state, o, mine, waiting),
            )
        )
    return tuple(out)


def owner_note(
    state: GameState, o: AreaOwner, lines: tuple[AreaDecision, ...], waiting: int
) -> str:
    """The owner's own words for the month, from what they did (displayed facts only)."""
    acted = sum(1 for d in lines if d.kind in ACTED)
    proposed = sum(1 for d in lines if d.kind == "proposal")
    parts = []
    if acted:
        parts.append(f"I took {acted} decision{'s' if acted != 1 else ''}")
    elif not proposed:
        parts.append("Nothing needed doing")
    if proposed:
        parts.append(f"I have put {proposed} to you for approval")
    if waiting and not proposed:
        many = waiting != 1
        parts.append(f"{waiting} proposal{'s' if many else ''} wait{'' if many else 's'} for you")
    if any(d.kind == "over_budget" for d in lines):
        parts.append("I reached this month's limit, so the rest waits")
    if any(d.kind == "stretched" for d in lines):
        parts.append("I have more on my plate than I can do well")
    return "; ".join(parts) + "."


def _label(state: GameState, o: AreaOwner, b: Balance) -> str:
    label = owners.area_def(b, o.area).label
    if o.slot:
        unit = state.org.unit(o.slot)
        if unit is not None:
            label = f"{label}: {unit.name}"
    return label


def digest_item(state: GameState, turn: int, b: Balance, data: GameData) -> LogItem | None:
    """Phase 12: the month's digest for the player's firm, when it has an automated area."""
    del data
    months = area_months(state, turn, b)
    if not months:
        return None
    month = format_turn(turn, state.save_meta.start_ym)
    paras = []
    acted_total = 0
    for m in months:
        o = m.owner
        p = state.person(o.person_id)
        acted = [d for d in m.lines if d.kind in ACTED or d.kind == "proposal"]
        acted_total += len(acted)
        head = f"{_label(state, o, b)} ({p.first_name} {p.last_name}): {len(acted)} this month"
        if m.committed_cents:
            head += f", ${m.committed_cents / 100:,.0f} committed of ${o.monthly_cents / 100:,.0f}"
        body = [head]
        body += [f"- {d.text}" for d in acted[:LINES_SHOWN]]
        if len(acted) > LINES_SHOWN:
            body.append(f"- and {len(acted) - LINES_SHOWN} more")
        for d in m.near_limit:
            body.append(f"- near the limit: {d.text}")
        body.append(f'"{m.note}"')
        paras.append("\n".join(body))
    opening = (
        f"Your people ran {len(months)} area{'s' if len(months) != 1 else ''} this month and "
        f"logged {acted_total} decision{'s' if acted_total != 1 else ''} and proposal"
        f"{'s' if acted_total != 1 else ''}."
    )
    return inbox_item(
        turn,
        state.player.id,
        "automation_digest",
        link_kind="automation",
        link_id=turn,
        month=month,
        summary="\n\n".join([opening, *paras]),
    )


def kpis(state: GameState, o: AreaOwner, b: Balance, data: GameData) -> tuple[tuple[str, int], ...]:
    """An area's two or three KPIs now, as the firm sees them (TST 40.4)."""
    from ptk.sim.ledger import REVOLVER  # noqa: F401  (named for the reader)
    from ptk.sim.org.authority import utilisation_bp

    firm = o.firm_id
    rule = owners.area_def(b, o.area).rule
    staff = state.staff(firm)
    lawyers = [
        e.person_id for e in staff if data.role(state.person(e.person_id).role).kind == "lawyer"
    ]
    if rule == "staffing":
        members = tuple(m.person_id for m in state.org.members if m.unit_id == o.slot)
        return (
            ("utilisation_bp", utilisation_bp(state, members, data, b) or 0),
            ("headcount", len(members)),
        )
    if rule in ("intake", "risk"):
        held = sum(
            1 for m in state.market.matters if m.firm_id == firm and m.status == "conflicted"
        )
        return (("held_instructions", held), ("checks_on", int(state.player.conflict_checks)))
    if rule == "billing":
        wip = sum(
            e.wip_cents for e in state.billing.engagements if e.firm_id == firm and not e.closed
        )
        return (("wip_cents", wip),)
    if rule == "pricing":
        return (("rate_rise_bp", state.player.rate_rise_bp or 0),)
    if rule == "bd":
        rfps = sum(1 for r in state.rivals.rfps if r.status == "open" and r.player_invited)
        return (
            ("open_rfps", rfps),
            ("clients", sum(1 for r in state.market.relationships if r.firm_id == firm)),
        )
    if rule == "hiring":
        plans = sum(1 for p in state.org.firm_plans(firm) if p.status == "active")
        return (("lawyers", len(lawyers)), ("open_plans", plans))
    if rule == "development":
        fp = state.partnership.of(firm)
        return (("sponsored", 0 if fp is None else len(fp.sponsors)),)
    if rule == "laterals":
        fp = state.partnership.of(firm)
        return (("partners", 0 if fp is None else len(fp.partners)),)
    if rule == "pro_bono":
        return (
            ("pro_bono_hours", round(state.player.pro_bono_avg_tenths * 12 / 10)),
        )  # tunable-exempt: a year, tenths
    if rule == "offices":
        return (("staff", len(staff)),)
    return ()
