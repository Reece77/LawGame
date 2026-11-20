"""The context builder (TST formulas.md 16.5; ADR-0005 section 4): an allowlist of what the
player could plausibly know, never true attributes, potential, hidden traits, hidden tags or
numbers the API would not show. People are described by name, practice, level, tenure, morale
and strain (shown for the firm's own people), and their skills as words from the firm's
displayed ranges; tags only once noticed; interests only once the profile is known. Matters by
their public facts (name, client, practice, kind, phase, months open, the team's caught errors
and missed deadlines, budget and hours): never a case's merits, opposing counsel's quality, an
escaped error or a hidden conflict. Clients by name, sector and the firm's relationship score;
their general counsel by name only (a GC's personality is hidden). Never a partner's
portability or a judge's traits. Everything is built from these fields and nothing else.

Ported from backend/tst/events/context.py @ 02fba2aa (Tech Startup Tycoon); changed: legal
state; the real-person rule in the system prompt (ADR PT-0013); spec 15's text kinds.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from ptk.events.validator import allowed_effects
from ptk.sim.data_models import Balance, GameData
from ptk.sim.events.data import EFFECT_TARGETS, MODIFIER_STATS, EventTemplate
from ptk.sim.events.formulas import effect_cap
from ptk.sim.events.models import GameEvent
from ptk.sim.events.render import full_name
from ptk.sim.people.reveal import revealed_range
from ptk.sim.state import GameState

STRONG_AT, WEAK_AT = 14, 6  # tunable-exempt: words for displayed 1-20 ranges
CENTS_PER_DOLLAR = 100  # tunable-exempt: unit conversion
TENTHS = 10  # tunable-exempt: hours are integer tenths (ADR PT-0005)

SYSTEM = (
    "You write events for a single-player business game about running a law firm that "
    "began in January 2005 in New York. The engine has already decided that this event "
    "happens, who it is about, how serious it is and which effects are allowed. You write the "
    "words: a short title, a body of at most {body_words} words in the second person "
    "addressed to the founding partner, and two or three choices. Each choice may carry up to "
    "three effects, chosen only from the allowed effects, aimed only at the listed targets, "
    "with values within the caps (cash in dollars; negative is a cost). The first choice is "
    "what happens if the player does not answer, so make it the reasonable default. Never "
    "invent people, firms, clients, cases or numbers that are not in the context. Use names, "
    "not pronouns, for people. Tone: {tone}. Return only the JSON object."
)
GROUNDED = "grounded professional realism"
LIGHT = "grounded, with a light or gently satirical touch this time"
REAL_RULE = (
    " Some people in the context are marked real: they are real lawyers in their "
    "professional role. For them write about business and procedural matters only: no "
    "misconduct, no private life, no health and no real-world controversies, and never make "
    "them resign or reveal anything about their character."
)


@dataclass(frozen=True, slots=True)
class Kpis:
    """The firm numbers the player sees on the Overview."""

    cash_cents: int
    headcount: int
    lawyers: int
    open_matters: int
    monthly_fees_cents: int  # standard value of last month's hours


def person_context(
    state: GameState, firm_id: int, person_id: int, data: GameData
) -> dict[str, Any]:
    """One person as the firm sees them (the API's own-firm view, in words)."""
    person = state.person(person_id)
    employment = state.employment_of(person_id)
    reveal = state.reveal(firm_id, person_id)
    out: dict[str, Any] = {
        "name": full_name(person),
        "practice": data.role(person.role).label,
        "level": person.level.replace("_", " "),
    }
    if person.real:
        out["real"] = True
    if employment is not None and employment.firm_id == firm_id:
        out["tenure_months"] = state.turn - employment.start_turn
        ps = state.person_state(person_id)
        if ps.morale is not None:
            out["morale"] = round(ps.morale)
        out["strain"] = round(person.strain)
    if reveal is not None:
        labels = {s.key: s.label for s in data.skills}
        strong, weak = [], []
        for skill in data.skill_keys:
            lo, hi = revealed_range(person, reveal, skill)
            mid = (lo + hi) / 2
            label = labels[skill].lower()
            if mid >= STRONG_AT:
                strong.append(label)
            elif mid <= WEAK_AT and hi - lo <= WEAK_AT:
                weak.append(label)
        if strong:
            out["strong_at"] = strong
        if weak:
            out["weak_at"] = weak
        tags = {t.key: t.label for t in data.tags}
        noticed = [tags[t] for t, _ in reveal.revealed_tags]
        if noticed:
            out["noticed"] = noticed
        if reveal.profile_revealed_turn is not None:
            out["interests"] = list(person.interests)
    return out


def matter_context(state: GameState, matter_id: int, data: GameData) -> dict[str, Any] | None:
    """A matter's public facts (what the Matters screen shows)."""
    m = state.market.matter(matter_id)
    if m is None:
        return None
    kind = data.market.kinds[m.kind]
    phase = kind.phases[min(m.phase_index, len(kind.phases) - 1)].key
    out: dict[str, Any] = {
        "name": m.name,
        "client": state.market.client(m.client_id).name,
        "practice": data.practice(m.practice).label,
        "kind": m.kind,
        "phase": phase if m.is_open else None,
        "status": m.status,
        "months_open": state.turn - m.opened_turn,
        "planned_months": m.planned_months,
        "expected_fees_dollars": m.expected_fees_cents // CENTS_PER_DOLLAR,
        "budget_hours": m.hours_needed_tenths // TENTHS,
        "worked_hours": m.worked_tenths // TENTHS,
        "critical": m.critical,
        "errors_caught": m.errors_caught,
        "missed_deadlines": m.missed_deadlines,
    }
    if m.outcome is not None:
        out["outcome"] = m.outcome
    if m.court is not None:
        out["court"] = data.courts.court(m.court).label
    if m.adverse_name:
        out["adverse"] = m.adverse_name
    return out


def client_context(state: GameState, firm_id: int, client_id: int) -> dict[str, Any]:
    client = state.market.client(client_id)
    rel = state.market.relationship(client_id, firm_id)
    out: dict[str, Any] = {
        "name": client.name,
        "sector": client.sector.replace("_", " "),
        "general_counsel": f"{client.gc.first_name} {client.gc.last_name}",
    }
    if rel is not None:
        out["relationship_score"] = round(rel.score)
        out["fees_12m_dollars"] = rel.fees_12m // CENTS_PER_DOLLAR
    return out


def facts(state: GameState, event: GameEvent, data: GameData) -> list[str]:
    """The situation in plain words, from values the player can see (16.5)."""
    out: list[str] = []
    for pid in event.person_ids:
        person = state.person(pid)
        name = full_name(person)
        ps = state.person_state(pid)
        if ps.morale is not None:
            out.append(f"{name}'s morale is {round(ps.morale)} out of 100.")
        out.append(f"{name}'s strain is {round(person.strain)} out of 100.")
    if event.client_id is not None:
        rel = state.market.relationship(event.client_id, event.firm_id)
        name = state.market.client(event.client_id).name
        if rel is not None:
            out.append(f"The firm's relationship with {name} is {round(rel.score)} out of 100.")
    if event.matter_id is not None:
        m = state.market.matter(event.matter_id)
        if m is not None:
            out.append(
                f"{m.name} has used {m.worked_tenths // TENTHS} of "
                f"{m.hours_needed_tenths // TENTHS} budgeted hours."
            )
    if event.practice is not None:
        out.append(f"The practice involved is {data.practice(event.practice).label}.")
    if event.amount_cents is not None:
        out.append(f"The sum involved is ${event.amount_cents // CENTS_PER_DOLLAR:,}.")
    return out


def build_prompt(
    state: GameState,
    event: GameEvent,
    template: EventTemplate,
    targets: tuple[str, ...],
    kpis: Kpis,
    balance: Balance,
    data: GameData,
) -> tuple[str, str]:
    """(system, user) for one event. The user message is JSON built from the allowlist."""
    ev = balance.events
    fid = event.firm_id
    firm = state.firm(fid)
    people = []
    for target in targets:
        kind, _, rest = target.partition(":")
        if kind == "person" and rest.isdigit():
            people.append({"target": target, **person_context(state, fid, int(rest), data)})
    allowed = []
    for effect in allowed_effects(template, event.severity, targets):
        cap = effect_cap(effect, event.severity, ev, event.cash_base_cents, gain=False)
        entry: dict[str, Any] = {"type": effect, "targets": list(EFFECT_TARGETS[effect])}
        if effect == "cash_delta":
            entry["max_cost_dollars"] = round(cap / CENTS_PER_DOLLAR)
            entry["max_gain_dollars"] = round(cap * ev.cash_gain_share / CENTS_PER_DOLLAR)
        elif effect == "modifier":
            entry["max_percent"] = cap
            entry["max_months"] = ev.max_months(event.severity)
            entry["stats"] = {s: list(MODIFIER_STATS[s]) for s in sorted(template.modifier_stats())}
        elif cap:
            entry["max"] = cap
        allowed.append(entry)
    recent = [
        f"{e.title} (chose: {c.label})" if (c := e.choice(e.chosen or "")) else e.title
        for e in sorted(state.events.events, key=lambda e: -e.id)
        if e.firm_id == fid and e.id != event.id and e.title
    ][: ev.recent_summaries]
    stories = [
        {"title": s.title, "summary": s.summary}
        for s in state.events.storylines
        if s.firm_id == fid and s.status == "active"
    ]
    story = state.events.storyline(event.storyline_id) if event.storyline_id is not None else None
    context: dict[str, Any] = {
        "firm": {
            "name": firm.name,
            "cash_dollars": kpis.cash_cents // CENTS_PER_DOLLAR,
            "headcount": kpis.headcount,
            "lawyers": kpis.lawyers,
            "open_matters": kpis.open_matters,
            "monthly_fees_dollars": kpis.monthly_fees_cents // CENTS_PER_DOLLAR,
        },
        "category": event.category,
        "severity": event.severity,
        "situation": facts(state, event, data),
        "people": people,
        "client": client_context(state, fid, event.client_id)
        if event.client_id is not None
        else None,
        "matter": matter_context(state, event.matter_id, data)
        if event.matter_id is not None
        else None,
        "eligible_targets": list(targets),
        "allowed_effects": allowed,
        "recent_events": recent,
        "active_storylines": stories,
        "this_storyline": {"title": story.title, "summary": story.summary} if story else None,
        "template_idea": {"title": template.title, "body": " ".join(template.body.split())},
    }
    system = SYSTEM.format(
        body_words=ev.body_words, tone=LIGHT if event.tone == "light" else GROUNDED
    )
    if any(p.get("real") for p in people):
        system += REAL_RULE
    if story is not None:
        system += (
            " This event is a step in an ongoing storyline: continue it, and write a new "
            f"storyline_summary of at most {ev.summary_words} words."
        )
    else:
        system += " Leave storyline_summary empty."
    return system, json.dumps(context, indent=1, sort_keys=True)


ASKS = {
    "headlines": "Write two or three one-line legal-press headlines about this month in the "
    "New York legal market, one per line, no numbering. Use only these facts.",
    "matter_brief": "Write a short internal briefing (at most 120 words) for the partners on "
    "this new matter: the client, the work, the team and what to watch. Use only these "
    "facts; keep every name and number as given.",
    "pitch_letter": "Write a short pitch letter (at most 120 words) from the founding partner "
    "to this new client's general counsel, thanking them for the instruction and offering the "
    "firm's wider help. Use only these facts; no fee promises.",
    "partner_memo": "Write a memo (at most 150 words) from the managing partner to the "
    "partners on the firm's half year: fees, people and what comes next. Use only these "
    "facts; keep every number as given.",
    "year_end_letter": "Write the managing partner's year-end letter to the partners (at most "
    "180 words): the year's work, the people, thanks and the year ahead. Use only these "
    "facts; keep every number as given.",
}


def text_prompt(kind: str, lines: list[str], firm_name: str) -> tuple[str, str]:
    """Read-only text (16.8): the facts to write from, as plain lines."""
    system = (
        f"You write short professional text for {firm_name}, a law firm in a business game. "
        "Grounded, plain English. Real lawyers appear only in their professional role."
    )
    return system, ASKS[kind] + "\n\n" + "\n".join(f"- {line}" for line in lines)
