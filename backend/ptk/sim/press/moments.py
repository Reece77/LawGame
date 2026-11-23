"""Press moments and credibility (spec 12.2; TST formulas.md 29.1, 29.3; PT-M16).

Engine code raises a moment with `queue_moment`. The press month keeps at most
`press.max_per_quarter` a quarter and one a month, highest stakes first, and opens each kept
moment for the player to answer in the next month; the rest are skipped. An open moment the
player does not answer by the end of its month gets the press office's measured answer.

Tones (TST 29.1, in Partner Track's units): **bold** lifts reputation `bold_rep` x a x the
credibility factor in the moment's practice (every practice without one) and draws the named
rival's managing partner; if the firm's reputation there falls `backfire_drop` below the claim's
within `backfire_months`, credibility -`bold_backfire` x a. **Measured** lifts it `measured_rep`
x a x the factor. **Deflect** costs credibility `deflect_cred` x a.

Ported from backend/tst/sim/press/moments.py @ 80a3807 (Tech Startup Tycoon); changed: moments
are the press's own (the Press screen and an action answer them, not the event director);
reputation pulses instead of brand-target modifiers; audience by the firm's stage; backfires on
reputation (no share or earnings); ADR PT-0013's restricted moments never name a real person.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import Final

from ptk.sim.data_models import Balance, GameData
from ptk.sim.log import LogItem, inbox_item
from ptk.sim.press.config import MOMENT_TRIGGERS, REMINDER, RESTRICTED
from ptk.sim.press.models import PressMoment, PressState
from ptk.sim.reputation.formulas import apply_pulse, reputation
from ptk.sim.state import GameState

PCT: Final = 100.0  # tunable-exempt: the 0-100 scale
QUARTER: Final = 3  # tunable-exempt: calendar
TRIGGER_WORDS: Final[dict[str, str]] = {
    "collapse": "a collapse nearby",
    "layoffs": "the firm's layoffs",
    "verdict": "a big verdict",
    "merger": "a merger in the market",
    "lateral": "a lateral move",
    "ranking_day": "ranking day",
    "salary_scale": "the associate salary scale",
    "jab": "a rival's jab",
    "rivalry": "a rivalry",
    REMINDER: "a claim you made",
}


def press_of(state: GameState) -> PressState:
    return state.standing.press


def with_press(state: GameState, press: PressState) -> GameState:
    return replace(state, standing=replace(state.standing, press=press))


def with_moment(state: GameState, moment: PressMoment) -> GameState:
    press = press_of(state)
    others = [m for m in press.moments if m.id != moment.id]
    return with_press(
        state, replace(press, moments=tuple(sorted((*others, moment), key=lambda m: m.id)))
    )


def take_id(state: GameState) -> tuple[GameState, int]:
    press = press_of(state)
    return with_press(state, replace(press, next_id=press.next_id + 1)), press.next_id


# --- Audience and credibility (TST 29.1, 29.3) ---------------------------------------------------


def audience(state: GameState, balance: Balance) -> float:
    ab = balance.press.audience
    stage = state.player.stage
    return ab.large if stage >= ab.large_stage else ab.mid if stage >= ab.mid_stage else ab.small


def credibility(state: GameState, balance: Balance) -> float:
    value = press_of(state).credibility
    return balance.press.cred_start if value is None else value


def cred_factor(state: GameState, balance: Balance) -> float:
    """Reputation gains from the press x (0.5 + credibility / 100) (TST 29.3)."""
    return 1 / 2 + credibility(state, balance) / PCT


def hiring_appeal(state: GameState, firm_id: int, balance: Balance) -> float:
    """+cred_hiring x (credibility - 50) / 50, at most cred_hiring_cap either way (TST 29.3)."""
    pb = balance.press
    value = press_of(state).credibility
    if value is None or firm_id != state.player.id:
        return 0.0
    raw = pb.cred_hiring * (value - pb.cred_start) / (PCT - pb.cred_start)
    return max(-pb.cred_hiring_cap, min(pb.cred_hiring_cap, raw))


def adjust_credibility(state: GameState, delta: float, cause: str, balance: Balance) -> GameState:
    """Credibility moves by `delta`, clamped to 0-100, remembering the cause (TST 29.3)."""
    if not delta:
        return state
    pb = balance.press
    press = press_of(state)
    old = credibility(state, balance)
    value = max(0.0, min(PCT, old + delta))
    history = (*press.cred_history, (state.turn, round(value - old, 2), cause))[-pb.cred_history :]
    return with_press(state, replace(press, credibility=value, cred_history=history))


def drift_credibility(state: GameState, balance: Balance) -> GameState:
    """press.cred_drift a month toward cred_start (TST 29.3); not a cause the panel lists."""
    pb = balance.press
    press = press_of(state)
    if press.credibility is None:
        return state
    gap = pb.cred_start - press.credibility
    if not gap:
        return state
    step = max(-pb.cred_drift, min(pb.cred_drift, gap))
    return with_press(state, replace(press, credibility=press.credibility + step))


def press_reputation(
    state: GameState, points: float, cause: str, balance: Balance, practice: str | None = None
) -> GameState:
    """A press effect on the player's reputation (TST's brand target, in reputation points)."""
    return apply_pulse(state, state.player.id, points, cause, balance, practice)


# --- Raising and keeping moments (TST 29.1) ------------------------------------------------------


def queue_moment(
    state: GameState,
    trigger: str,
    facts: Mapping[str, int | str] | None = None,
    *,
    practice: str | None = None,
    rival_id: int | None = None,
    person_id: int | None = None,
) -> GameState:
    """Raise a press moment for the player's firm. `facts` are displayed words. ADR PT-0013:
    a restricted moment never names a person, and a real person is named only in professional
    moments (moves, matters, rankings)."""
    if trigger not in (*MOMENT_TRIGGERS, REMINDER):
        raise ValueError(f"unknown press trigger {trigger!r}")
    if trigger in RESTRICTED:
        person_id = None
    state, mid = take_id(state)
    moment = PressMoment(
        id=mid,
        trigger=trigger,
        turn=state.turn,
        practice=practice,
        rival_id=rival_id,
        person_id=person_id,
        facts=tuple(sorted((k, v) for k, v in (facts or {}).items())),
    )
    return with_moment(state, moment)


def _quarter(turn: int) -> int:
    return turn // QUARTER


def _stakes(trigger: str) -> int:
    order = (*MOMENT_TRIGGERS, REMINDER)
    return order.index(trigger) if trigger in order else len(order)


def _reminder_due(state: GameState, m: PressMoment) -> bool:
    due = dict(m.facts).get("due_turn")
    return due is None or int(due) <= state.turn + 1


def schedule(state: GameState, balance: Balance) -> tuple[GameState, list[LogItem]]:
    """The month's pending moments are kept or skipped. A kept moment opens next month (an
    inbox item linked to the Press screen); a quarter keeps at most press.max_per_quarter
    (reminders apart), a month at most one."""
    next_month = state.turn + 1
    press = press_of(state)
    taken = {m.due_turn for m in press.moments if m.due_turn is not None}
    used = sum(
        1
        for m in press.moments
        if m.due_turn is not None
        and _quarter(m.due_turn) == _quarter(next_month)
        and m.trigger != REMINDER
    )
    pending = [m for m in press.moments if m.status == "pending"]
    due = [m for m in pending if m.trigger != REMINDER or _reminder_due(state, m)]
    due.sort(key=lambda m: (_stakes(m.trigger), m.id))
    logs: list[LogItem] = []
    for m in due:
        free = next_month not in taken
        fits = m.trigger == REMINDER or used < balance.press.max_per_quarter
        if free and fits:
            state = with_moment(state, replace(m, status="open", due_turn=next_month))
            taken.add(next_month)
            used += m.trigger != REMINDER
            facts = dict(m.facts)
            logs.append(
                inbox_item(
                    state.turn,
                    state.player.id,
                    "press_moment",
                    link_kind="press",
                    link_id=m.id,
                    about=TRIGGER_WORDS.get(m.trigger, m.trigger),
                    detail=str(facts.get("result", facts.get("promise", ""))),
                )
            )
        elif m.trigger != REMINDER:
            state = with_moment(state, replace(m, status="skipped"))
    keep = state.turn - balance.press.memory_months
    press = press_of(state)
    state = with_press(
        state,
        replace(
            press,
            moments=tuple(
                m for m in press.moments if m.status in ("pending", "open") or m.turn > keep
            ),
            statements=tuple(s for s in press.statements if s.turn > keep),
        ),
    )
    return state, logs


# --- Tones (TST 29.1) ----------------------------------------------------------------------


def apply_tone(
    state: GameState,
    moment: PressMoment,
    tone: str,
    balance: Balance,
    data: GameData,
    *,
    by_office: bool = False,
) -> tuple[GameState, list[LogItem]]:
    """The answer's tone; effects x a, reputation gains x the credibility factor."""
    from ptk.sim.press import characters

    pb = balance.press
    a = audience(state, balance)
    cf = cred_factor(state, balance)
    logs: list[LogItem] = []
    baseline = None
    about = TRIGGER_WORDS.get(moment.trigger, moment.trigger)
    if tone == "bold":
        state = press_reputation(
            state, pb.bold_rep * a * cf, f"a bold answer on {about}", balance, moment.practice
        )
        baseline = _rep_now(state, moment.practice, balance)
        if moment.rival_id is not None:
            state, logged = characters.bold_mention(state, moment.rival_id, balance, data)
            logs += logged
    elif tone == "measured":
        state = press_reputation(
            state,
            pb.measured_rep * a * cf,
            f"a measured answer on {about}",
            balance,
            moment.practice,
        )
    elif tone == "deflect":
        state = adjust_credibility(state, pb.deflect_cred * a, "no comment to the press", balance)
    else:
        raise ValueError(f"unknown tone {tone!r}")
    current = press_of(state).moment(moment.id) or moment
    state = with_moment(
        state,
        replace(
            current,
            status="answered",
            tone=tone,
            answered_turn=state.turn,
            by_office=by_office,
            baseline=baseline,
        ),
    )
    return state, logs


def _rep_now(state: GameState, practice: str | None, balance: Balance) -> float:
    """The player's reputation in the practice, or its mean over every practice it has."""
    pid = state.player.id
    if practice is not None:
        return reputation(state, pid, practice, balance)
    mine = state.standing.reputation.of(pid)
    return sum(e.value for e in mine) / len(mine) if mine else 0.0


def backfires(state: GameState, balance: Balance) -> GameState:
    """A bold answer in the last press.backfire_months backfires once when the firm's
    reputation where it spoke has fallen press.backfire_drop below the claim's."""
    pb = balance.press
    for m in press_of(state).moments:
        if m.tone != "bold" or m.backfired or m.answered_turn is None or m.baseline is None:
            continue
        if state.turn - m.answered_turn > pb.backfire_months:
            continue
        if _rep_now(state, m.practice, balance) < m.baseline - pb.backfire_drop:
            a = audience(state, balance)
            cause = "results contradicted a bold claim"
            state = adjust_credibility(state, -pb.bold_backfire * a, cause, balance)
            state = with_moment(state, replace(m, backfired=True))
    return state


def office_answers(
    state: GameState, balance: Balance, data: GameData
) -> tuple[GameState, list[LogItem]]:
    """Open moments due this month that the player left: the press office answers measured."""
    logs: list[LogItem] = []
    for m in press_of(state).moments:
        if m.status == "open" and m.due_turn is not None and m.due_turn <= state.turn:
            state, logged = apply_tone(state, m, "measured", balance, data, by_office=True)
            logs += logged
    return state, logs
