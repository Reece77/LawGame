"""Quarterly reports with a voice, the partners' meeting and the executive committee's
December (TST formulas.md 24.3, 27.2, 14.6; spec 9.2-9.3; PT-M8).

Ported from backend/tst/sim/org/reports.py and voices.py @ 121d318a (Tech Startup Tycoon);
changed: Partner Track's chiefs report (seat_data.REPORTING_SEATS) through PT-M6's read-only
texts (a `seat_report` text request per holder, written after the turn by the LLM within the
budget or by `report_text`'s template), so a replay copies the stored words; the voice comes
from the holder's REVEALED personality midpoints and revealed tags only (never true values:
ADR-0005); the board meeting is the quarterly partners' meeting, reporting the committee's
mean confidence as a mood (a warning below `seats.exco.warn_confidence`); December holds the
exco_elected term's vote and, when the committee is elected, its election.

Facts a report gives: what the holder did under authority this quarter (their decisions'
texts), what they are pitching and their record, one concern tied to a number, and their
function's numbers. No seat score, true skill, quality draw or pitch probability.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Final

from simcore.kernel.calendar import turn_to_ym
from simcore.kernel.money import format_money

from ptk.sim.data_models import Balance, GameData
from ptk.sim.events.models import TextRequest
from ptk.sim.log import LogItem, inbox_item
from ptk.sim.org.seat_data import REPORTING_SEATS
from ptk.sim.org.seat_models import EXCO
from ptk.sim.org.seats import (
    exco_elected,
    exco_max,
    in_play,
    managing_partner,
    seat_def,
    seated_holder,
    set_holder,
    slots,
    with_firm_leadership,
)
from ptk.sim.people.reveal import revealed_range
from ptk.sim.state import GameState

QUARTER: Final = 3  # tunable-exempt: calendar
DECEMBER: Final = 12  # tunable-exempt: calendar
NEUTRAL: Final = 10.0  # tunable-exempt: the attribute scale's midpoint
VOICE_HIGH: Final = 13.0  # tunable-exempt: a displayed trait this high colours the voice
VOICE_LOW: Final = 8.0  # tunable-exempt: and this low


def is_quarter_end(state: GameState) -> bool:
    return turn_to_ym(state.turn, state.save_meta.start_ym)[1] % QUARTER == 0


def _name(state: GameState, pid: int) -> str:
    p = state.person(pid)
    return f"{p.first_name} {p.last_name}"


# --- The voice (revealed personality only) -----------------------------------------------------


def shown_trait(state: GameState, firm_id: int, pid: int, key: str) -> float:
    reveal = state.reveal(firm_id, pid)
    if reveal is None:
        return NEUTRAL
    lo, hi = revealed_range(state.person(pid), reveal, key)
    return (lo + hi) / 2


def voice(state: GameState, firm_id: int, pid: int) -> str:
    """A voice from what the firm has seen: blunt, driven, cautious, warm or measured."""
    ambition = shown_trait(state, firm_id, pid, "ambition")
    temperament = shown_trait(state, firm_id, pid, "temperament")
    sociability = shown_trait(state, firm_id, pid, "sociability")
    risk = shown_trait(state, firm_id, pid, "risk_appetite")
    if ambition >= VOICE_HIGH and temperament <= VOICE_LOW:
        return "blunt"
    if ambition >= VOICE_HIGH:
        return "driven"
    if risk <= VOICE_LOW:
        return "cautious"
    if sociability >= VOICE_HIGH:
        return "warm"
    return "measured"


OPENERS: Final = {
    "blunt": "I'll keep this short.",
    "driven": "We can do more, and here is how.",
    "cautious": "A careful quarter, and I would keep it that way.",
    "warm": "Thank you all for the quarter's work.",
    "measured": "Here is where things stand.",
}


def revealed_tags(state: GameState, firm_id: int, pid: int) -> tuple[str, ...]:
    reveal = state.reveal(firm_id, pid)
    return tuple(t for t, _ in reveal.revealed_tags) if reveal is not None else ()


# --- Report facts -------------------------------------------------------------------------------


def _numbers(state: GameState, firm_id: int, seat: str, b: Balance) -> tuple[str, str]:
    """(the function's numbers, a concern tied to a number)."""
    if seat == "cfo":
        wip = sum(
            e.wip_cents for e in state.billing.engagements if e.firm_id == firm_id and not e.closed
        )
        return f"Unbilled time stands at {format_money(wip)}.", (
            "Unbilled time is building up." if wip > 0 else "Nothing worries me on the books."
        )
    if seat == "general_counsel":
        held = sum(
            1 for m in state.market.matters if m.firm_id == firm_id and m.status == "conflicted"
        )
        return f"{held} instructions are held for conflicts.", (
            f"{held} clients are waiting on conflict decisions."
            if held
            else "No conflicts are pending."
        )
    if seat == "cmo":
        rfps = sum(1 for r in state.rivals.rfps if r.status == "open" and r.player_invited)
        return f"{rfps} RFPs are open to us.", (
            "RFPs are open that we have not pitched." if rfps else "No RFPs are open to us."
        )
    if seat == "chro":
        from ptk.sim.data_models import SCALE_LEVELS

        assoc = [
            e.person_id
            for e in state.staff(firm_id)
            if state.person(e.person_id).level in SCALE_LEVELS
        ]
        morale = [m for p in assoc if (m := state.person_state(p).morale) is not None]
        avg = sum(morale) / len(morale) if morale else 0.0
        return f"{len(assoc)} associates; their morale averages {avg:.0f}.", (
            "Associate morale is low." if morale and avg < 50 else "The associates are holding up."
        )
    if seat == "pricing_director":
        firm = state.firm(firm_id)
        return (
            f"Our rate card stands at {firm.rate_index:.2f}x the 2005 cards.",
            "Clients push back on every rise.",
        )
    heads = len(state.staff(firm_id))
    return f"{heads} people on the books.", "Space and support are stretched."


def report_facts(
    state: GameState, turn: int, firm_id: int, pid: int, data: GameData, b: Balance
) -> tuple[str, list[str]]:
    """(title, facts) of a holder's quarterly report; facts are engine-supplied and shown."""
    from ptk.sim.org.pitches import record

    seats = [h for h in state.leadership.seats_of(pid) if h.seat in REPORTING_SEATS]
    seat_key = seats[0].seat if seats else "coo"
    seat = seat_def(data, seat_key)
    title = f"{seat.short} quarterly report: {_name(state, pid)}"
    since = turn - QUARTER + 1
    did = [d.text for d in state.leadership.decisions if d.person_id == pid and d.turn >= since]
    facts = [f"Seat: {seat.label}. Voice: {voice(state, firm_id, pid)}."]
    tags = revealed_tags(state, firm_id, pid)
    if tags:
        facts.append(f"Known for: {', '.join(t.replace('_', ' ') for t in tags)}.")
    if did:
        facts.append("What I did: " + "; ".join(did[:4]) + ".")
    else:
        facts.append("What I did: nothing under authority this quarter.")
    pending = [p for p in state.leadership.pitches if p.person_id == pid and p.status == "pending"]
    hits, misses = record(state, pid)
    if pending:
        facts.append(f"What I'm pitching: {pending[0].title}.")
    else:
        facts.append("What I'm pitching: nothing this quarter.")
    if hits or misses:
        facts.append(f"My pitches so far: {hits} hit, {misses} missed.")
    numbers, concern = _numbers(state, firm_id, seat_key, b)
    facts.append(f"What worries me: {concern}")
    facts.append(f"The numbers: {numbers}")
    return title, facts


def report_text(
    state: GameState, turn: int, firm_id: int, pid: int, data: GameData, b: Balance
) -> tuple[str, str, list[str]]:
    """(title, template text, facts): the offline report in the holder's voice."""
    title, facts = report_facts(state, turn, firm_id, pid, data, b)
    opener = OPENERS[voice(state, firm_id, pid)]
    body = [opener, *(f.split(": ", 1)[1] if ": " in f else f for f in facts[1:])]
    return title, " ".join(body), facts


def report_requests(state: GameState, b: Balance, data: GameData) -> tuple[TextRequest, ...]:
    """Phase 12 of a quarter's last month: one `seat_report` per chief seat holder."""
    if state.ended or not state.firms or not is_quarter_end(state):
        return ()
    firm = state.player.id
    out = []
    for key in sorted(REPORTING_SEATS):
        seat = seat_def(data, key)
        if not in_play(state, firm, seat):
            continue
        pid = seated_holder(state, firm, seat, 0, b)
        if pid is not None:
            out.append(TextRequest("seat_report", firm, state.turn, pid))
    return tuple(sorted(out, key=lambda r: r.ref_id or 0))


# --- The partners' meeting and the committee's December ------------------------------------------


def _confidences(state: GameState, firm: int, people: list[int]) -> list[float]:
    fp = state.partnership.of(firm)
    if fp is None:
        return []
    return [p.confidence for pid in people if (p := fp.partner(pid)) is not None]


def members(state: GameState, firm: int, b: Balance, data: GameData) -> list[int]:
    seat = seat_def(data, EXCO)
    return [
        pid
        for s in slots(state, firm, seat, b)
        if (pid := seated_holder(state, firm, seat, s, b)) is not None
    ]


def partners_meeting(
    state: GameState, b: Balance, data: GameData
) -> tuple[GameState, list[LogItem]]:
    """A quarter's last month, from the committee's stage: its mean confidence as a mood."""
    if state.ended or not state.firms or not is_quarter_end(state):
        return state, []
    firm = state.player.id
    if not in_play(state, firm, seat_def(data, EXCO)):
        return state, []
    who = members(state, firm, b, data)
    values = _confidences(state, firm, who)
    cfg = b.seats.exco
    if not values:
        mood, detail = (
            "missing",
            "The executive committee has no members: appoint them on the Org screen.",
        )
    else:
        mean = sum(values) / len(values)
        if mean >= cfg.uneasy_confidence:
            mood, detail = "behind you", "The committee backs the firm's direction."
        elif mean >= cfg.warn_confidence:
            mood, detail = "uneasy", "The committee has doubts; results this quarter matter."
        else:
            mood, detail = (
                "restless",
                "Warning: the committee's confidence is low. Partners talk of a change at the top.",
            )
    record = state.leadership.firm(firm)
    state = with_firm_leadership(state, replace(record, last_meeting_turn=state.turn))
    return state, [
        inbox_item(state.turn, firm, "partners_meeting", link_kind="org", mood=mood, detail=detail)
    ]


def december(state: GameState, b: Balance, data: GameData) -> tuple[GameState, list[LogItem]]:
    """The December vote on a proposed exco_elected term, then the committee's election."""
    logs: list[LogItem] = []
    if state.ended or not state.firms:
        return state, logs
    if turn_to_ym(state.turn, state.save_meta.start_ym)[1] != DECEMBER:
        return state, logs
    firm = state.player.id
    record = state.leadership.firm(firm)
    fp = state.partnership.of(firm)
    if record.exco_proposed is not None:
        equity = [p.confidence for p in fp.equity_partners if p.person_id != fp.mp_id] if fp else []
        mean = sum(equity) / len(equity) if equity else 100.0
        passed = mean >= b.seats.exco.term_pass_confidence
        mode = "elected" if record.exco_proposed else "appointed by the MP"
        record = replace(
            record,
            exco_elected=record.exco_proposed if passed else record.exco_elected,
            exco_proposed=None,
        )
        state = with_firm_leadership(state, record)
        logs.append(
            inbox_item(
                state.turn,
                firm,
                "exco_term",
                link_kind="partnership",
                result="passes" if passed else "fails",
                detail=f"The partners voted on an executive committee {mode}.",
            )
        )
    seat = seat_def(data, EXCO)
    if not in_play(state, firm, seat) or not exco_elected(state, firm, b, data) or fp is None:
        return state, logs
    mp = managing_partner(state, firm)
    ranked = sorted(
        (
            p
            for p in fp.equity_partners
            if p.person_id != mp and state.employer_of(p.person_id) == firm
        ),
        key=lambda p: (-p.points, -state.person(p.person_id).book_cents, p.person_id),
    )
    chosen = [p.person_id for p in ranked[: exco_max(state, firm, b)]]
    for s in range(1, max(seat_slot_count(state), exco_max(state, firm, b)) + 1):
        state = set_holder(state, firm, EXCO, s, chosen[s - 1] if s <= len(chosen) else None)
    if chosen:
        names = ", ".join(_name(state, pid) for pid in chosen)
        logs.append(inbox_item(state.turn, firm, "exco_elected", link_kind="org", names=names))
    return state, logs


def seat_slot_count(state: GameState) -> int:
    return max((h.slot for h in state.leadership.holders if h.seat == EXCO), default=0)
