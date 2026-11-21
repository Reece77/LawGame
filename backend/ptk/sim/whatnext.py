"""What next and Getting started: the Overview's guidance (PT-M7; TST M29's §42.2 and §42.3,
re-made for the law firm).

Pure and read-only: built from the state the player can see (no hidden values, no energy, no
randomness). **What next** is a short list of what needs the managing partner now, the most
urgent first: a critical decision waiting, the bank's warnings, open settlement offers, rivals'
approaches to partners, December's partnership candidates, RFPs to pitch, then capacity (busy
people to hire for, or idle people to find work for). **Getting started** is the guided first
year: six steps, each ticked from state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from ptk.sim.calendar import turn_to_ym
from ptk.sim.data_models import Balance, GameData
from ptk.sim.matters.models import PRO_BONO_CLIENT_ID
from ptk.sim.partnership.careers import eligible
from ptk.sim.state import GameState

MAX_ITEMS: Final = 5  # tunable-exempt: the panel's length (TST 42.3)
DECEMBER: Final = 12  # tunable-exempt: the December vote
NOVEMBER: Final = 11  # tunable-exempt: a month's warning of it
BUSY_BP: Final = 9000  # tunable-exempt: a guidance threshold, not a rule (utilisation)
IDLE_BP: Final = 6500  # tunable-exempt: a guidance threshold, not a rule
WARNINGS: Final = (
    "cfo_forecast",  # PT-M7b
    "cfo_warning",
    "covenant_breach",
    "revolver_called",
    "insolvent",
)


@dataclass(frozen=True, slots=True)
class Item:
    key: str
    text: str
    link_kind: str  # event, finance, matter, partnership, market, recruitment, clients
    link_id: int | None = None


@dataclass(frozen=True, slots=True)
class Step:
    key: str
    text: str
    done: bool
    link_kind: str


def what_next(
    state: GameState,
    recent: tuple[str, ...],
    utilisation_bp: int | None,
    data: GameData,
    balance: Balance,
) -> list[Item]:
    """At most MAX_ITEMS lines. `recent` is last month's inbox template ids (the bank's
    warnings come through it); `utilisation_bp` last month's utilisation."""
    firm = state.player.id
    items: list[Item] = []
    for e in state.events.events:
        if e.firm_id == firm and e.severity == "critical" and e.status == "open":
            items.append(
                Item(
                    "critical",
                    f"A critical decision waits: {e.title or 'untitled'}.",
                    "event",
                    e.id,
                )
            )
            break
    warned = next((t for t in WARNINGS if t in recent), None)
    if warned is not None:
        items.append(
            Item("bank", "The bank has written about the revolver: read it on Finance.", "finance")
        )
    for m in state.market.open_matters(firm):
        if m.settlement is not None:
            items.append(
                Item("settlement", f"A settlement offer is open on {m.name}.", "matter", m.id)
            )
            break
    fp = state.partnership.of(firm)
    if fp is not None:
        if any(a.status == "open" for a in fp.approaches):
            items.append(
                Item("approach", "A rival is courting one of your partners.", "partnership")
            )
        month = turn_to_ym(state.turn, state.save_meta.start_ym)[1]
        if month in (NOVEMBER, DECEMBER):
            n = sum(1 for pid in state.staff_ids(firm) if eligible(state, fp, pid, balance))
            if n:
                when = "this month" if month == DECEMBER else "in December"
                items.append(
                    Item(
                        "vote",
                        f"{n} partnership candidate{'s' if n > 1 else ''} to decide {when}.",
                        "partnership",
                    )
                )
    rfps = [
        r for r in state.rivals.rfps if r.status == "open" and r.player_invited and r.pitch is None
    ]
    if rfps:
        items.append(
            Item("rfp", f"{len(rfps)} RFP{'s' if len(rfps) > 1 else ''} to pitch for.", "market")
        )
    if utilisation_bp is not None and utilisation_bp >= BUSY_BP:
        items.append(
            Item(
                "busy",
                "Your lawyers are stretched: hire, or the work goes elsewhere.",
                "recruitment",
            )
        )
    elif utilisation_bp is not None and utilisation_bp < IDLE_BP:
        items.append(
            Item("idle", "Capacity is idle: pitch, or introduce colleagues to clients.", "clients")
        )
    return items[:MAX_ITEMS]


def getting_started(state: GameState, data: GameData, balance: Balance) -> list[Step]:
    """The guided first year: each step is done when the state shows it."""
    firm = state.player.id
    staffed = any(
        m.firm_id == firm and not m.auto_staff and m.client_id != PRO_BONO_CLIENT_ID
        for m in state.market.matters
    )
    hired = any(o.firm_id == firm and o.status == "accepted" for o in state.offers) or any(
        s.firm_id == firm and s.channel == "campus" for s in state.searches
    )
    bd = any(r.pitch is not None for r in state.rivals.rfps) or any(
        r.firm_id == firm and r.intro_turns for r in state.market.relationships
    )
    collected = any(m.firm_id == firm and m.collected_cents > 0 for m in state.billing.months)
    fp = state.partnership.of(firm)
    voted = fp is not None and (
        bool(fp.candidacies) or any(v.kind == "admission" for v in fp.votes)
    )
    policy = state.player.rate_rise_bp is not None or state.player.pro_bono_credit_hours is not None
    return [
        Step("staff", "Staff a matter yourself from its staffing board.", staffed, "matters"),
        Step(
            "hire",
            "Hire: register for the campus season or make a lateral offer.",
            hired,
            "recruitment",
        ),
        Step("bd", "Win work: pitch an RFP or introduce a colleague to a client.", bd, "clients"),
        Step(
            "collect",
            "Bill and collect: see your first fees come in on Finance.",
            collected,
            "finance",
        ),
        Step("policy", "Set the firm's rate rise or pro bono policy on Org.", policy, "org"),
        Step("vote", "Hold your first December partnership decision.", voted, "partnership"),
    ]
