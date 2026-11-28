"""The event director (TST formulas.md 16.1, 16.6, 23.3; ADR-0005): phase 12 decides how many
events next month brings, which templates, about whom, and how severe. Stream `events`, key
(turn,). Draw order: the count; the matter draws (per open case matter by id); one uniform draw
per pick; then one tone draw per queued event in queue order (follow-ups and engine events,
storyline steps, the crisis, then picks).

Follow-ups, engine-queued events and due storyline steps are queued first and always arrive;
the drawn count fills whatever slots remain.

Ported from backend/tst/sim/events/director.py @ 02fba2aa (Tech Startup Tycoon); changed:
targets are people, a practice group, a client, a matter and a practice; matter and client
cooldowns beside TST's template and person cooldowns; a restricted template never names a
person flagged real (ADR PT-0013); engine-queued events (`queue_engine_event`) for later
milestones; read-only text requests (spec 15's kinds); no press, persona or public names.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np
from simcore.kernel.calendar import turn_to_ym
from simcore.kernel.money import Cents

from ptk.sim.data_models import Balance, GameData
from ptk.sim.events.data import TRIGGERS, EventTemplate, Severity
from ptk.sim.events.formulas import candidate_weight, cash_base_cents, severity_for
from ptk.sim.events.models import (
    EventRequest,
    GameEvent,
    QueuedEvent,
    Storyline,
    TextRequest,
    Tone,
    with_event,
    with_queued,
    with_storyline,
)
from ptk.sim.events.render import placeholder_names, render
from ptk.sim.events.triggers import TriggerHit, crisis_hits, matter_draws, triggers
from ptk.sim.org.rules import org_view
from ptk.sim.state import GameState
from ptk.sim.streams import RngFactory

BP = 10_000  # tunable-exempt: basis-point scale
PAIR = 2  # tunable-exempt: two people


@dataclass(frozen=True, slots=True)
class Targets:
    """What one event is about (from a trigger hit, a storyline or a queued event)."""

    person_ids: tuple[int, ...] = ()
    unit_id: int | None = None
    client_id: int | None = None
    matter_id: int | None = None
    practice: str | None = None
    months: int | None = None
    amount_cents: int | None = None


@dataclass(frozen=True, slots=True)
class Candidate:
    template: EventTemplate
    hit: TriggerHit
    targets: Targets
    severity: Severity
    weight: float


def _targets(hit: TriggerHit) -> Targets:
    return Targets(
        hit.person_ids,
        hit.unit_id,
        hit.client_id,
        hit.matter_id,
        hit.practice,
        hit.months,
        hit.amount_cents,
    )


def names_real(state: GameState, person_ids: tuple[int, ...]) -> bool:
    """Whether any of the people is a real lawyer (ADR PT-0013)."""
    ids = set(person_ids)
    return any(p.real for p in state.people if p.id in ids)


def resolve(state: GameState, template: EventTemplate, base: Targets) -> Targets | None:
    """Fill in what the template names and the trigger did not; None if it cannot be named
    (no second person, no client, no matter, no court)."""
    needs = template.needs()
    fid = state.player.id
    matter = state.market.matter(base.matter_id) if base.matter_id is not None else None
    if "matter" in needs and matter is None:
        return None
    client_id = base.client_id
    if client_id is None and matter is not None:
        client_id = matter.client_id
    if ("client" in needs or "gc" in needs) and client_id is None:
        return None
    practice = base.practice or (matter.practice if matter is not None else None)
    if "practice" in needs and practice is None:
        return None
    if "court" in needs and (matter is None or matter.court is None):
        return None
    unit_id = base.unit_id
    if unit_id is None and base.person_ids and "unit" in needs:
        unit_id = org_view(state, fid).unit_of.get(base.person_ids[0])
    if "other" in needs and len(base.person_ids) < PAIR:
        return None
    if "person" in needs and not base.person_ids:
        return None
    founder = state.founder_of(fid)
    if "pair" in needs and len(base.person_ids) < PAIR and founder is None:
        return None
    if "pair" in needs and len(base.person_ids) < PAIR and base.person_ids == (founder,):
        return None
    if "months" in needs and base.months is None:
        return None
    return replace(base, client_id=client_id, practice=practice, unit_id=unit_id)


def eligible_targets(state: GameState, event: GameEvent) -> tuple[str, ...]:
    """The request's eligible list (TST 16.3): the trigger's people and pair, its unit, the
    firm, its client and matter, and the partnership."""
    fid = event.firm_id
    founder = state.founder_of(fid)
    out = [f"person:{p}" for p in event.person_ids]
    if len(event.person_ids) >= PAIR:
        a, b = sorted(event.person_ids[:PAIR])
        out.append(f"pair:{a}-{b}")
    elif event.person_ids and founder is not None and event.person_ids[0] != founder:
        a, b = sorted((founder, event.person_ids[0]))
        out.append(f"pair:{a}-{b}")
    if event.unit_id is not None:
        out.append(f"unit:{event.unit_id}")
    out.append(f"firm:{fid}")
    if event.client_id is not None:
        out.append(f"client:{event.client_id}")
    if event.matter_id is not None:
        out.append(f"matter:{event.matter_id}")
    out.append("partnership")
    return tuple(out)


def _recent(state: GameState, next_month: int, turns: int) -> list[GameEvent]:
    fid = state.player.id
    return [e for e in state.events.events if e.firm_id == fid and e.turn > next_month - turns]


def candidates(
    state: GameState, hits: list[TriggerHit], balance: Balance, data: GameData
) -> list[Candidate]:
    """Every (template, hit) with its severity and 16.1 weight, in template-file order, then
    hit order. Zero weights are kept out."""
    ev = balance.events
    fid = state.player.id
    next_month = state.turn + 1
    recent_templates = {
        e.template_id for e in _recent(state, next_month, ev.template_cooldown_turns)
    }
    recent_people = {
        p for e in _recent(state, next_month, ev.person_cooldown_turns) for p in e.person_ids
    }
    recent_matters = {
        e.matter_id for e in _recent(state, next_month, ev.matter_cooldown_turns) if e.matter_id
    }
    recent_clients = {
        e.client_id for e in _recent(state, next_month, ev.client_cooldown_turns) if e.client_id
    }
    last_month = {
        e.category for e in state.events.events if e.firm_id == fid and e.turn == state.turn
    }
    critical_ok = not any(
        e.severity == "critical" for e in _recent(state, next_month, ev.critical_gap_turns)
    )
    active = [s for s in state.events.storylines if s.firm_id == fid and s.status == "active"]
    out: list[Candidate] = []
    for template in data.event_templates:
        if template.trigger not in (*TRIGGERS, "smoking_gun", "judge_ruling"):
            continue
        story = template.storyline
        if story is not None and (
            len(active) >= ev.max_storylines or any(s.key == story.key for s in active)
        ):
            continue
        for hit in hits:
            if hit.trigger != template.trigger:
                continue
            if template.restricted and names_real(state, hit.person_ids):
                continue  # ADR PT-0013: never about a real person
            severity = severity_for(
                hit.strength,
                template.severities,
                critical_ok=hit.critical_ok and critical_ok,
                events=ev,
            )
            if severity is None:
                continue
            targets = resolve(state, template, _targets(hit))
            if targets is None:
                continue
            blocked = (
                template.id in recent_templates
                or bool(set(hit.person_ids) & recent_people)
                or (targets.matter_id is not None and targets.matter_id in recent_matters)
                or (targets.client_id is not None and targets.client_id in recent_clients)
            )
            weight = candidate_weight(
                template.weight,
                hit.strength,
                category_used_last_month=template.category in last_month,
                blocked=blocked,
                events=ev,
            )
            if weight > 0:
                out.append(Candidate(template, hit, targets, severity, weight))
    return out


def fill_candidates(
    state: GameState, hits: list[TriggerHit], balance: Balance, data: GameData
) -> list[Candidate]:
    """Quiet-month templates as fill for a month whose triggered candidates are all in
    cooldown (TST 16.1): minor severity only, same cooldowns and weights; none when quiet_month
    already holds."""
    if any(h.trigger == "quiet_month" for h in hits):
        return []
    quiet = TriggerHit("quiet_month", balance.events.fixed("quiet_month"))
    return [
        replace(c, severity="minor")
        for c in candidates(state, [quiet], balance, data)
        if "minor" in c.template.severities
    ]


def draw_count(gen: np.random.Generator, balance: Balance) -> int:
    u = float(gen.random())
    total = 0.0
    for n, w in enumerate(balance.events.count_weights):
        total += w
        if u < total:
            return n
    return len(balance.events.count_weights) - 1


def pick(
    gen: np.random.Generator,
    pool: list[Candidate],
    slots: int,
    fill: list[Candidate] | None = None,
) -> list[Candidate]:
    """Draw without replacement by weight; a pick removes its template, anyone, any matter and
    any client it names, other starts of its storyline and, if critical, every other critical
    candidate. When the triggered candidates run out and slots remain, the quiet-month `fill`
    candidates take over (TST 16.1)."""
    chosen: list[Candidate] = []
    for _ in range(slots):
        total = sum(c.weight for c in pool)
        if total <= 0 and fill:
            used = {c.template.id for c in chosen}
            pool, fill = [c for c in fill if c.template.id not in used], None
            total = sum(c.weight for c in pool)
        if total <= 0:
            break
        u = float(gen.random()) * total
        acc = 0.0
        choice = pool[-1]
        for c in pool:
            acc += c.weight
            if u < acc:
                choice = c
                break
        chosen.append(choice)
        story = choice.template.storyline
        people = set(choice.hit.person_ids)
        matter, client = choice.targets.matter_id, choice.targets.client_id
        pool = [
            c
            for c in pool
            if c.template.id != choice.template.id
            and not (people & set(c.hit.person_ids))
            and not (matter is not None and c.targets.matter_id == matter)
            and not (client is not None and c.targets.client_id == client)
            and not (story and c.template.storyline and c.template.storyline.key == story.key)
            and not (choice.severity == "critical" and c.severity == "critical")
        ]
    return chosen


def _crisis(
    state: GameState, hits: list[TriggerHit], data: GameData
) -> tuple[EventTemplate, TriggerHit, Targets] | None:
    """The first crisis hit with a critical template that can name its targets (23.3)."""
    for hit in hits:
        for template in data.event_templates:
            if template.trigger != hit.trigger or not template.is_critical:
                continue
            if template.restricted and names_real(state, hit.person_ids):
                continue
            targets = resolve(state, template, _targets(hit))
            if targets is not None:
                return template, hit, targets
    return None


def forced_severity(template: EventTemplate) -> Severity:
    """A scheduled event's severity: its highest non-critical one, else critical (an
    engine-queued critical template)."""
    usable = [s for s in template.severities if s != "critical"]
    return usable[-1] if usable else template.severities[0]


def monthly_fees_cents(state: GameState, firm_id: int) -> Cents:
    """Standard value of last month's hours by the firm's people (the cash base's revenue)."""
    staff = set(state.staff_ids(firm_id))
    return sum(h.value_cents for h in state.market.hours if h.person_id in staff)


def queue_engine_event(
    state: GameState,
    template_id: str,
    due_turn: int,
    *,
    person_ids: tuple[int, ...] = (),
    client_id: int | None = None,
    matter_id: int | None = None,
    practice: str | None = None,
) -> GameState:
    """Queue an engine event (a later milestone's: a partner group's resignation letter, a
    covenant breach, a trust-account shortfall) for the player firm; the director shows it in
    `due_turn`. Its template must be one of ENGINE_QUEUED's."""
    es = state.events
    queued = QueuedEvent(
        id=es.next_queued_id,
        firm_id=state.player.id,
        template_id=template_id,
        due_turn=due_turn,
        source_event_id=None,
        person_ids=person_ids,
        client_id=client_id,
        matter_id=matter_id,
        practice=practice,
    )
    return replace(state, events=with_queued(es, queued))


type _Queued = tuple[
    EventTemplate, Targets, Severity, float, str, Storyline | None, QueuedEvent | None
]


def direct(
    state: GameState,
    start: GameState,
    rng: RngFactory,
    balance: Balance,
    data: GameData,
    cash: Cents,
) -> tuple[GameState, tuple[EventRequest, ...]]:
    """Phase 12: next month's events for the player (16.1), as pending GameEvents."""
    if state.ended or not data.event_templates:
        return state, ()
    ev = balance.events
    fid = state.player.id
    next_month = state.turn + 1
    staff_ids = set(state.staff_ids(fid))
    es = state.events
    # Storylines end when their people leave (16.6).
    for story in es.storylines:
        if story.status == "active" and any(p not in staff_ids for p in story.person_ids):
            es = with_storyline(es, replace(story, status="ended", ended_turn=state.turn))
    state = replace(state, events=es)

    queue: list[_Queued] = []
    critical_free = not any(
        e.severity == "critical" for e in _recent(state, next_month, ev.critical_gap_turns)
    )
    for q in state.events.queued:
        if q.firm_id == fid and not q.done and q.due_turn <= next_month:
            template = data.event_template(q.template_id)
            severity = forced_severity(template)
            if severity == "critical":
                critical_free = False
            targets = Targets(q.person_ids, q.unit_id, q.client_id, q.matter_id, q.practice)
            queue.append((template, targets, severity, 1.0, template.trigger, None, q))
    for story in state.events.storylines:
        if (
            story.firm_id == fid
            and story.status == "active"
            and story.next_template
            and story.next_turn is not None
            and story.next_turn <= next_month
        ):
            template = data.event_template(story.next_template)
            crisis = template.is_critical and critical_free
            critical_free = critical_free and not crisis
            targets = Targets(
                story.person_ids, story.unit_id, story.client_id, story.matter_id, story.practice
            )
            step: Severity = "critical" if crisis else forced_severity(template)
            if step == "critical" and not crisis:
                step = "major"  # the critical slot is taken: the step arrives as major
            queue.append((template, targets, step, 1.0, "storyline", story, None))

    gen = rng.stream(state.turn, "events")
    count = draw_count(gen, balance)
    crises = crisis_hits(state, balance, data) if critical_free else []
    crisis_found = _crisis(state, crises, data)
    if crisis_found is not None:
        template, hit, targets = crisis_found
        queue.append((template, targets, "critical", hit.strength, hit.trigger, None, None))
        critical_free = False
    hits = triggers(state, start, balance, data) + matter_draws(state, gen, balance, data)
    pool = candidates(state, hits, balance, data)
    if not critical_free:  # this month's critical slot is taken
        pool = [c for c in pool if c.severity != "critical"]
    fill = fill_candidates(state, hits, balance, data)
    for c in pick(gen, pool, max(0, count - len(queue)), fill):
        queue.append((c.template, c.targets, c.severity, c.hit.strength, c.hit.trigger, None, None))

    base = cash_base_cents(cash, monthly_fees_cents(state, fid), ev)
    requests: list[EventRequest] = []
    for template, targets, severity, strength, trigger, thread, queued in queue:
        tone: Tone = "light" if int(gen.integers(0, BP)) < ev.light_tone_chance_bp else "grounded"
        es = state.events
        event_id = es.next_event_id
        names = placeholder_names(
            state,
            data,
            fid,
            person_ids=targets.person_ids,
            unit_id=targets.unit_id,
            client_id=targets.client_id,
            matter_id=targets.matter_id,
            practice=targets.practice,
            months=targets.months,
            amount_cents=targets.amount_cents,
        )
        storyline_id = None
        spec = template.storyline
        if spec is not None and thread is None:  # step 1 opens a storyline
            thread = Storyline(
                id=es.next_storyline_id,
                firm_id=fid,
                key=spec.key,
                title=render(spec.title or spec.key, names),
                step=spec.step,
                started_turn=next_month,
                summary=render(spec.summary, names),
                person_ids=targets.person_ids,
                unit_id=targets.unit_id,
                client_id=targets.client_id,
                matter_id=targets.matter_id,
                practice=targets.practice,
            )
        if spec is not None and thread is not None:
            storyline_id = thread.id
            last = spec.next_template is None
            es = with_storyline(
                es,
                replace(
                    thread,
                    step=spec.step,
                    summary=render(spec.summary, names),
                    next_turn=None if last else next_month + (spec.next_after_turns or 0),
                    next_template=spec.next_template,
                ),
            )
        if queued is not None:
            es = with_queued(es, replace(queued, done=True))
        event = GameEvent(
            id=event_id,
            firm_id=fid,
            turn=next_month,
            template_id=template.id,
            category=template.category,
            severity=severity,
            trigger=trigger,
            strength=strength,
            person_ids=targets.person_ids,
            unit_id=targets.unit_id,
            client_id=targets.client_id,
            matter_id=targets.matter_id,
            practice=targets.practice,
            months=targets.months,
            amount_cents=targets.amount_cents,
            cash_base_cents=base,
            tone=tone,
            storyline_id=storyline_id,
        )
        state = replace(state, events=with_event(es, event))
        requests.append(
            EventRequest(
                event_id=event_id,
                firm_id=fid,
                turn=next_month,
                template_id=template.id,
                severity=severity,
                tone=tone,
                targets=eligible_targets(state, event),
                storyline_id=storyline_id,
            )
        )
    return state, tuple(requests)


def text_requests(state: GameState, balance: Balance) -> tuple[TextRequest, ...]:
    """Phase 12's read-only texts for the month just played (spec 15): the legal headlines
    every month; a briefing on each large new matter (largest first, up to briefs_per_month);
    a pitch letter to each new client (up to pitch_letters_per_month); the partners' memo in
    memo_months; the year-end letter to the partners."""
    if state.ended:
        return ()
    cfg = balance.events.texts
    fid = state.player.id
    turn = state.turn
    month = turn_to_ym(turn, state.save_meta.start_ym)[1]
    out = [TextRequest("headlines", fid, turn)]
    new = sorted(
        (
            m
            for m in state.market.open_matters(fid)
            if m.opened_turn == turn and m.expected_fees_cents >= cfg.brief_min_cents
        ),
        key=lambda m: (-m.expected_fees_cents, m.id),
    )
    out += [TextRequest("matter_brief", fid, turn, m.id) for m in new[: cfg.briefs_per_month]]
    clients = sorted(
        r.client_id
        for r in state.market.relationships
        if r.firm_id == fid and r.since_turn == turn and turn > 0
    )
    letters = clients[: cfg.pitch_letters_per_month]
    out += [TextRequest("pitch_letter", fid, turn, c) for c in letters]
    if month in cfg.memo_months:
        out.append(TextRequest("partner_memo", fid, turn))
    if month == cfg.year_end_month:
        out.append(TextRequest("year_end_letter", fid, turn))
    return tuple(out)
