"""The event service (TST formulas.md 16.5; ADR-0005): after a turn commits, each pending event
gets its words and validated choices, from the LLM if the budget allows, else from its
template; a draft rejected twice also falls back to the template. Read-only texts (16.8) are
written the same way. Nothing here touches the turn's RNG or the clock-free sim; the stored
results are what a replay copies, so a replay never calls an adapter.

Ported from backend/tst/events/service.py @ 02fba2aa (Tech Startup Tycoon); changed: Partner
Track's KPIs and text kinds (spec 15: headlines, matter briefings, pitch letters, partner
memos, the year-end letter); the real-person rule passed to the validator (ADR PT-0013); no
lender, public or press special cases.
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from typing import cast

from ptk.events.context import Kpis, build_prompt, matter_context, text_prompt
from ptk.events.drafts import real_targets, template_draft
from ptk.events.validator import Rejection, ValidatedEvent, validate_event
from ptk.llm.base import CallRecord, Completion, EventPrompt, LLMAdapter, TextKind, TextPrompt
from ptk.llm.settings import LLMSettings
from ptk.sim.calendar import format_turn, turn_to_ym
from ptk.sim.data_models import Balance, GameData
from ptk.sim.events.director import eligible_targets
from ptk.sim.events.models import GameEvent, with_event, with_storyline
from ptk.sim.events.render import full_name
from ptk.sim.state import GameState

log = logging.getLogger(__name__)

RETRY = (
    "Your previous draft was rejected ({reason}). Write it again: two or three choices, "
    "only the allowed effects, only the eligible targets, values within the caps."
)
CENTS_PER_DOLLAR = 100  # tunable-exempt: unit conversion
ATTEMPTS = 2  # tunable-exempt: one retry (ADR-0005 section 3)
TEXT_TITLES = {
    "headlines": "Legal news",
    "matter_brief": "Matter briefing",
    "pitch_letter": "Letter to a new client",
    "partner_memo": "Memo to the partners",
    "year_end_letter": "Year-end letter to the partners",
}


@dataclass
class Writer:
    """One batch of writing: the adapter, the prices, a budget check and what was spent."""

    adapter: LLMAdapter
    settings: LLMSettings
    budget_left: Callable[[], float]  # cents left this calendar month
    debug: bool = False
    records: list[CallRecord] = field(default_factory=list)
    spent_cents: float = 0.0
    claude_events: int = 0
    rejected: int = 0
    event_cents: float = 0.0

    @property
    def live(self) -> bool:
        """An adapter that calls a model (Claude, or the mock standing in for it)."""
        return self.adapter.name != "template"

    def can_spend(self) -> bool:
        return self.budget_left() - self.spent_cents > 0

    def record(self, purpose: str, prompt: str, completion: Completion, outcome: str) -> float:
        usage = completion.usage
        cost = (
            self.settings.cost_cents(usage.model, usage.input_tokens, usage.output_tokens)
            if usage
            else 0.0
        )
        self.spent_cents += cost
        self.records.append(
            CallRecord(
                purpose=purpose,
                model=usage.model if usage else self.adapter.name,
                prompt_hash=hashlib.sha256(prompt.encode()).hexdigest()[:16],
                input_tokens=usage.input_tokens if usage else 0,
                output_tokens=usage.output_tokens if usage else 0,
                cost_cents=cost,
                latency_ms=completion.latency_ms,
                outcome=outcome,
                prompt=prompt if self.debug else None,
                response=str(completion.content) if self.debug else None,
            )
        )
        return cost


def kpis_of(state: GameState, cash_cents: int, data: GameData) -> Kpis:
    from ptk.sim.events.director import monthly_fees_cents
    from ptk.sim.org.rules import lawyer_count

    fid = state.player.id
    return Kpis(
        cash_cents=cash_cents,
        headcount=len(state.staff_ids(fid)),
        lawyers=lawyer_count(state, fid, data),
        open_matters=len(state.market.open_matters(fid)),
        monthly_fees_cents=monthly_fees_cents(state, fid),
    )


def write_event(
    state: GameState,
    event: GameEvent,
    kpis: Kpis,
    writer: Writer,
    balance: Balance,
    data: GameData,
) -> GameState:
    """Give one pending event its words and choices; status becomes "open"."""
    template = data.event_template(event.template_id)
    targets = eligible_targets(state, event)
    fallback = template_draft(state, event, template, balance, data)
    real = real_targets(state, event)

    def check(draft: object) -> ValidatedEvent | Rejection:
        return validate_event(
            draft,
            template=template,
            severity=event.severity,
            targets=targets,
            cash_base_cents=event.cash_base_cents,
            events=balance.events,
            real_targets=real,
        )

    result: ValidatedEvent | Rejection = Rejection("not written")
    source = "template"
    story = event.storyline_id is not None and template.trigger == "storyline"
    purpose = "story" if story else "event"
    if writer.live and writer.can_spend():
        system, user = build_prompt(state, event, template, targets, kpis, balance, data)
        prompt = EventPrompt(event.id, "story" if story else "events", system, user, fallback)
        for attempt in range(ATTEMPTS):
            completion = writer.adapter.generate_event(prompt)
            result = (
                check(completion.content)
                if completion.content is not None
                else Rejection(completion.error or "no draft")
            )
            outcome = "ok" if isinstance(result, ValidatedEvent) else "rejected"
            cost = writer.record(purpose, system + "\n" + user, completion, outcome)
            writer.event_cents += cost
            if isinstance(result, ValidatedEvent):
                source = writer.adapter.name
                writer.claude_events += 1
                break
            log.info(
                "Event %s draft rejected (%s), attempt %d", event.id, result.reason, attempt + 1
            )
            if not writer.can_spend():
                break
            prompt = replace(prompt, retry_note=RETRY.format(reason=result.reason))
        else:
            writer.rejected += 1
    elif writer.live:
        log.info("LLM budget reached: event %s from its template", event.id)
        writer.records.append(CallRecord(purpose, "template", "", outcome="budget"))
    if not isinstance(result, ValidatedEvent):
        result = check(fallback)
        source = "template"
        if not isinstance(result, ValidatedEvent):  # templates are checked at load
            raise RuntimeError(f"template {template.id} failed validation: {result.reason}")
    es = with_event(
        state.events,
        replace(
            event,
            status="open",
            title=result.title,
            body=result.body,
            choices=result.choices,
            source=source,
        ),
    )
    if event.storyline_id is not None and result.summary and source != "template":
        thread = es.storyline(event.storyline_id)
        if thread is not None:
            es = with_storyline(es, replace(thread, summary=result.summary))
    return replace(state, events=es)


def fallback_text(
    state: GameState, kind: str, turn: int, ref_id: int | None, kpis: Kpis, data: GameData
) -> tuple[str, list[str]]:
    """(template text, facts) for a read-only text (16.8)."""
    firm = state.player
    fid = firm.id
    date = format_turn(turn, state.save_meta.start_ym)
    if kind == "headlines":
        lines: list[str] = []
        for row in state.market.matters:
            if row.firm_id != fid or not row.critical:
                continue
            who = state.market.client(row.client_id).name
            if row.opened_turn == turn:
                lines.append(f"{who} turns to {firm.name} for {row.name}")
            if row.closed_turn == turn and row.outcome in ("won", "closed"):
                lines.append(f"{firm.name} delivers for {who} on {row.name}")
            if row.closed_turn == turn and row.outcome in ("lost", "collapsed"):
                lines.append(f"Setback for {who} as {row.name} ends badly")
        facts = lines[:3] or [f"A quiet month in the New York legal market ({date})."]
        text = "\n".join(lines[:3]) or "Quiet month for New York's law firms"
        return text, facts
    if kind == "matter_brief" and ref_id is not None:
        m = state.market.matter(ref_id)
        ctx = matter_context(state, ref_id, data) if m is not None else None
        if m is None or ctx is None:
            return "", []
        lead = full_name(state.person(m.lead_id)) if m.lead_id is not None else "no lead yet"
        facts = [
            f"Matter: {ctx['name']} for {ctx['client']} ({ctx['practice']}, {ctx['kind']}).",
            f"Expected fees ${ctx['expected_fees_dollars']:,} over {ctx['planned_months']} months.",
            f"Budget {ctx['budget_hours']:,} hours; lead partner {lead}.",
        ]
        if m.critical:
            facts.append("The client treats this as a critical matter.")
        return " ".join(facts), facts
    if kind == "pitch_letter" and ref_id is not None:
        client = state.market.client(ref_id)
        gc = f"{client.gc.first_name} {client.gc.last_name}"
        facts = [f"{client.name} has instructed {firm.name} for the first time.", f"GC: {gc}."]
        text = (
            f"Dear {gc}, thank you for instructing {firm.name}. We are glad to be working with "
            f"{client.name}, and we would welcome the chance to help across the firm's "
            "practices whenever it is useful."
        )
        return text, facts
    year = turn_to_ym(turn, state.save_meta.start_ym)[0]
    facts = [
        f"{firm.name} has {kpis.headcount} people, {kpis.lawyers} of them lawyers.",
        f"Open matters: {kpis.open_matters}.",
        f"Cash at month end: ${kpis.cash_cents // CENTS_PER_DOLLAR:,}.",
        f"Last month's work at standard rates: ${kpis.monthly_fees_cents // CENTS_PER_DOLLAR:,}.",
    ]
    if kind == "year_end_letter":
        text = (
            f"Partners, {year} is done. " + " ".join(facts) + " Thank you for the year's work; "
            "the year ahead asks as much of us again."
        )
        return text, facts
    return "Partners, a short note on where the firm stands. " + " ".join(facts), facts


def write_text(
    state: GameState,
    kind: str,
    turn: int,
    ref_id: int | None,
    writer: Writer,
    kpis: Kpis,
    data: GameData,
) -> tuple[str, str]:
    """(text, source) for one read-only text."""
    fallback, facts = fallback_text(state, kind, turn, ref_id, kpis, data)
    if not fallback or not writer.live or not writer.can_spend():
        return fallback, "template"
    system, user = text_prompt(kind, facts, state.player.name)
    # TST's TextKind (llm/base.py, AS IS) does not list Partner Track's kinds yet (follow-up).
    prompt = TextPrompt(cast(TextKind, kind), system, user, fallback)
    completion = writer.adapter.generate_text(prompt)
    text = completion.content if isinstance(completion.content, str) else None
    ok = bool(text and text.strip())
    writer.record(kind, system + "\n" + user, completion, "ok" if ok else "rejected")
    return (text.strip(), writer.adapter.name) if ok and text else (fallback, "template")


def write_pending_events(
    state: GameState, cash_cents: int, writer: Writer, balance: Balance, data: GameData
) -> GameState:
    """Every pending event of the state written, in id order (what `write_pending` does to a
    save; in-memory runs and replays use it with the same adapter)."""
    kpis = kpis_of(state, cash_cents, data)
    for event in [e for e in state.events.events if e.status == "pending"]:
        state = write_event(state, event, kpis, writer, balance, data)
    return state
