"""Event effects as plain words and numbers (TST formulas.md 23.2): "Priya Shah's morale +5",
"costs $8,000", "Acme Corp relationship +4", "+10% hours still needed on Project Atlas". Values
are what the choice applies; caps and trigger strengths are never shown, and a case's merits
are described only in words (hidden value, CLAUDE.md section 10).

Ported from backend/tst/sim/events/describe.py @ 02fba2aa (Tech Startup Tycoon); changed: law
effects; no loan, press or industry step texts.
"""

from __future__ import annotations

from ptk.sim.data_models import Balance
from ptk.sim.events.data import STAT_LABELS
from ptk.sim.events.models import Effect, EventChoice, GameEvent, Modifier
from ptk.sim.events.render import full_name
from ptk.sim.state import GameState

CENTS_PER_DOLLAR = 100  # tunable-exempt: unit conversion
PCT = 100  # tunable-exempt: percent
MINUS = chr(0x2212)  # tunable-exempt: a real minus sign
DO_NOTHING = "Do nothing: no effect"
WHOLE = 0.05  # tunable-exempt: display rounding, shown without decimals below this
PAIR = 2  # tunable-exempt: two people


def signed(x: float) -> str:
    """+5, -10, +2.5: whole numbers without decimals, others to one decimal place."""
    whole = abs(x - round(x)) < WHOLE
    text = f"{abs(x):.0f}" if whole else f"{abs(x):.1f}"
    return f"{'+' if x >= 0 else MINUS}{text}"


def dollars(cents: float) -> str:
    return f"${round(abs(cents) / CENTS_PER_DOLLAR):,}"


def person_label(state: GameState, person_id: int) -> str:
    person = next((p for p in state.people if p.id == person_id), None)
    return full_name(person) if person else "someone who has left"


def who(state: GameState, target: str) -> str:
    """A target as words: a person's name, a practice group, a pair, a client, a matter, or
    everyone."""
    kind, _, rest = target.partition(":")
    ids = [int(x) for x in rest.split("-") if x.isdigit()]
    if kind == "person" and ids:
        return person_label(state, ids[0])
    if kind == "unit" and ids:
        unit = state.org.unit(ids[0])
        return unit.name if unit else "the group"
    if kind == "pair" and len(ids) == PAIR:
        return f"{person_label(state, ids[0])} and {person_label(state, ids[1])}"
    if kind == "client" and ids:
        try:
            return state.market.client(ids[0]).name
        except KeyError:
            return "the client"
    if kind == "matter" and ids:
        matter = state.market.matter(ids[0])
        return matter.name if matter else "the matter"
    return "everyone"


def _possessive(name: str) -> str:
    if name == "everyone":
        return "Everyone's"
    return f"{name}'" if name.endswith("s") else f"{name}'s"


def modifier_text(state: GameState, stat: str, target: str, value_pct: float, months: int) -> str:
    """'+5% morale target for Priya Shah for 6 months'."""
    name = who(state, target)
    label = STAT_LABELS.get(stat, stat.replace("_", " "))
    span = f"{months} month{'s' if months != 1 else ''}"
    place = " across the firm" if target.startswith("firm") else f" for {name}"
    return f"{signed(value_pct)}% {label}{place} for {span}"


def running_text(state: GameState, m: Modifier) -> str:
    return modifier_text(state, m.stat, m.target, m.value_pct, m.end_turn - state.turn)


def _merits_words(value: float, balance: Balance, severity: str) -> str:
    share = abs(value) / balance.events.cap("merits_shift", severity)
    size = (
        "a little"
        if share <= balance.events.effect_size_bounds.lo
        else ("considerably" if share > balance.events.effect_size_bounds.hi else "somewhat")
    )
    return f"{'strengthens' if value > 0 else 'weakens'} the case {size}"


def effect_text(state: GameState, event: GameEvent, effect: Effect, balance: Balance) -> str:
    v = effect.value
    name = who(state, effect.target)
    match effect.type:
        case "morale_delta":
            return f"{_possessive(name)} morale {signed(v)}"
        case "strain_delta":
            return f"{_possessive(name)} strain {signed(v)}"
        case "relationship_delta":
            return f"{name} relationship {signed(v)}"
        case "pair_delta":
            return f"{name} get on {'better' if v > 0 else 'worse'} ({signed(v)})"
        case "cash_delta":
            return f"{'brings in' if v > 0 else 'costs'} {dollars(v)}"
        case "reputation_delta":
            return f"{signed(v)} reputation"
        case "confidence_delta":
            return f"{signed(v)} partners' confidence in you"
        case "hours_pct":
            return f"{signed(v)}% hours still needed on {name}"
        case "wip_writedown":
            return f"writes off {v:g}% of {_possessive(name)} unbilled time"
        case "merits_shift":
            return f"{name}: {_merits_words(v, balance, event.severity)}"
        case "growth_boost":
            return f"{signed(v)} skill points for {name}"
        case "reveal_tag":
            return f"you learn more about {name}"
        case "salary_change":
            return f"{signed(v)}% raise for {name}"
        case "resign":
            return f"{name} leaves"
        case "retain":
            return f"{name} stays: their notice is withdrawn"
        case "follow_up":
            return "a follow-up decision comes next month"
        case "modifier":
            return modifier_text(state, effect.stat, effect.target, v, effect.months)
    return effect.type.replace("_", " ")


def choice_texts(
    state: GameState, event: GameEvent, choice: EventChoice, balance: Balance
) -> list[str]:
    if not choice.effects:
        return [DO_NOTHING] if choice.do_nothing else []
    return [effect_text(state, event, e, balance) for e in choice.effects]
