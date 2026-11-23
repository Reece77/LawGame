"""Public claims (spec 12.2; TST formulas.md 29.2's promises; PT-M16): made with a bold or
measured answer to a press moment, judged on public values only, at the deadline or when
broken earlier.

Kinds: **headcount** ("we will have N lawyers by ...", 3-36 months out); **no_layoffs** (12
months: broken by any firing); **match_scale** (12 months: broken if the pay policy goes below
the market's scale); **band** ("band B in practice P by ...": kept once an October's bands put
the firm at B or better before the deadline).

Kept: reputation `kept_rep` x a x (1 + ambition) x the credibility factor in every practice,
credibility + `kept_cred` x a; morale + `kept_morale` for no layoffs. Broken: reputation
-`broken_rep` x a, credibility -`broken_cred` x a; for no layoffs, everyone's morale
-`broken_morale` and the partners' confidence in the managing partner -`broken_trust`; the
founder's Reckless persona (PT-M17's `broken_claim`); then a "you said ..." reminder within
`reminder_months` (stream `press`).

Ambition (0-1): half how far the target is (headcount: growth over `headcount_span`; band:
bands of climb over `band_span`), half how soon (a shorter deadline is bolder); the fixed kinds
`fixed_ambition`.

Ported from backend/tst/sim/press/promises.py @ 80a3807 (Tech Startup Tycoon); changed: Partner
Track's kinds and public values, reputation instead of the brand target, partner confidence
instead of relationships, no sentiment (no listing).
"""

from __future__ import annotations

from dataclasses import replace
from typing import Final

from ptk.sim.calendar import format_turn
from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import InvalidActionError
from ptk.sim.hiring.pay import EQUITY_PARTNER
from ptk.sim.interfaces import confidence_change, founder_persona_source
from ptk.sim.log import LogItem, inbox_item
from ptk.sim.money import BP_DENOMINATOR
from ptk.sim.press import moments
from ptk.sim.press.config import CLAIM_KINDS, REMINDER, TIMED
from ptk.sim.press.models import Claim, PressState
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState, with_person_states

MORALE_MAX: Final = 100.0  # tunable-exempt: the morale scale
HALF: Final = 0.5  # tunable-exempt: ambition is half the target's distance, half the deadline's
NO_BAND: Final = 7  # tunable-exempt: a practice without a band (one below band 6)


def public_lawyers(state: GameState, data: GameData) -> int:
    keys = set(data.practice_keys)
    staff = set(state.staff_ids(state.player.id))
    return sum(1 for p in state.people if p.id in staff and p.role in keys)


def current_band(state: GameState, practice: str) -> int:
    band = state.standing.rankings.band(state.player.id, practice)
    return NO_BAND if band is None else band


def claim_words(c: Claim, data: GameData, start_ym: tuple[int, int]) -> str:
    by = format_turn(c.deadline_turn, start_ym)
    match c.kind:
        case "headcount":
            return f"have {c.target} lawyers by {by}"
        case "band":
            label = data.practice(c.practice).label if c.practice else "a practice"
            return f"reach band {c.target} in {label} by {by}"
        case "no_layoffs":
            return f"make no layoffs until {by}"
    return f"pay at least the market's scale until {by}"


def _time_ambition(months: int, balance: Balance) -> float:
    lo, hi = balance.press.claims.months
    return max(0.0, min(1.0, (hi - months) / (hi - lo)))


def open_claims(state: GameState) -> tuple[Claim, ...]:
    return moments.press_of(state).open_claims


def make(
    state: GameState,
    moment_id: int,
    kind: str,
    balance: Balance,
    data: GameData,
    *,
    practice: str | None = None,
    target: int | None = None,
    months: int | None = None,
) -> tuple[GameState, Claim]:
    """The rules of making a claim (TST 29.2): with a bold or measured answer, one a moment,
    at most claims.max_open open."""
    cb = balance.press.claims
    if kind not in CLAIM_KINDS:
        raise InvalidActionError(f"unknown claim {kind!r}")
    if len(open_claims(state)) >= cb.max_open:
        raise InvalidActionError(f"at most {cb.max_open} public claims open at once")
    if any(c.moment_id == moment_id for c in moments.press_of(state).claims):
        raise InvalidActionError("one claim a press moment")
    lo, hi = cb.months
    if kind in TIMED:
        if months is None or not lo <= months <= hi:
            raise InvalidActionError(f"a {kind} claim is due {lo} to {hi} months out")
    else:
        months = cb.fixed_months
    baseline = 0
    ambition = cb.fixed_ambition
    if kind == "headcount":
        now = public_lawyers(state, data)
        if target is None or target <= now:
            raise InvalidActionError(f"the target must be above today's {now} lawyers")
        baseline = now
        growth = (target - now) / max(1, now)
        ambition = HALF * min(1.0, growth / cb.headcount_span) + HALF * _time_ambition(
            months, balance
        )
    elif kind == "band":
        if practice not in data.practice_keys:
            raise InvalidActionError("a band claim names a practice")
        if target is None or not 1 <= target <= NO_BAND - 1:
            raise InvalidActionError("a band claim names a band 1-6")
        baseline = current_band(state, practice)
        if target >= baseline:
            raise InvalidActionError("the band must be better than today's")
        ambition = HALF * min(1.0, (baseline - target) / cb.band_span) + HALF * _time_ambition(
            months, balance
        )
    elif kind == "match_scale" and state.player.pay_policy.pct_bp < BP_DENOMINATOR:
        raise InvalidActionError("the firm pays below the scale today")
    state, cid = moments.take_id(state)
    claim = Claim(
        id=cid,
        kind=kind,
        made_turn=state.turn,
        deadline_turn=state.turn + months,
        moment_id=moment_id,
        practice=practice if kind == "band" else None,
        target=target or 0,
        baseline=baseline,
        ambition=round(ambition, 4),
        audience=moments.audience(state, balance),
    )
    press = moments.press_of(state)
    return moments.with_press(state, replace(press, claims=(*press.claims, claim))), claim


# --- Judging (TST 29.2): public values only ----------------------------------------------


def verdict(state: GameState, c: Claim, data: GameData, fired: int = 0) -> str | None:
    """'kept', 'broken' or None (still open). `fired`: people fired this month."""
    due = state.turn >= c.deadline_turn
    match c.kind:
        case "headcount":
            if public_lawyers(state, data) >= c.target:
                return "kept"
            if due:
                return "broken"
        case "band":
            assert c.practice is not None
            published = state.standing.rankings.published_turn("bands")
            if (
                published is not None
                and c.made_turn < published <= state.turn
                and current_band(state, c.practice) <= c.target
            ):
                return "kept"
            if due:
                return "broken"
        case "no_layoffs":
            if fired:
                return "broken"
            if due:
                return "kept"
        case "match_scale":
            if state.player.pay_policy.pct_bp < BP_DENOMINATOR:
                return "broken"
            if due:
                return "kept"
    return None


def check(
    state: GameState, rng: RngFactory, balance: Balance, data: GameData, fired: int
) -> tuple[GameState, list[LogItem]]:
    """Every open claim is judged; a broken one schedules its reminder (stream `press`)."""
    logs: list[LogItem] = []
    gen = None
    for c in sorted(open_claims(state), key=lambda x: x.id):
        result = verdict(state, c, data, fired)
        if result is None:
            continue
        if gen is None:
            gen = rng.stream(state.turn, "press", state.player.id)
        lo, hi = balance.press.reminder_months
        wait = int(gen.integers(lo, hi + 1))
        state, logged = resolve(state, c, result, balance, data, wait)
        logs += logged
    return state, logs


def resolve(
    state: GameState,
    c: Claim,
    result: str,
    balance: Balance,
    data: GameData,
    reminder_in: int,
) -> tuple[GameState, list[LogItem]]:
    cb = balance.press.claims
    a = c.audience
    pid = state.player.id
    words = claim_words(c, data, state.save_meta.start_ym)
    if result == "kept":
        cf = moments.cred_factor(state, balance)
        state = moments.press_reputation(
            state, cb.kept_rep * a * (1 + c.ambition) * cf, f"kept: {words}", balance
        )
        state = moments.adjust_credibility(state, cb.kept_cred * a, f"kept: {words}", balance)
        if c.kind == "no_layoffs":
            state = morale_all(state, cb.kept_morale)
        state = _with_claim(state, replace(c, status="kept", resolved_turn=state.turn))
        return state, [
            inbox_item(state.turn, pid, "claim_kept", link_kind="press", link_id=c.id, claim=words)
        ]
    state = moments.press_reputation(state, -cb.broken_rep * a, f"broken: {words}", balance)
    state = moments.adjust_credibility(state, -cb.broken_cred * a, f"broken: {words}", balance)
    if c.kind == "no_layoffs":
        state = morale_all(state, -cb.broken_morale)
        state = confidence_change(state, pid, -cb.broken_trust)
    state = founder_persona_source(state, pid, "broken_claim", balance)
    state = moments.queue_moment(
        state, REMINDER, {"promise": words, "due_turn": state.turn + reminder_in}
    )
    state = _with_claim(
        state,
        replace(
            c, status="broken", resolved_turn=state.turn, reminder_turn=state.turn + reminder_in
        ),
    )
    return state, [
        inbox_item(state.turn, pid, "claim_broken", link_kind="press", link_id=c.id, claim=words)
    ]


def _with_claim(state: GameState, c: Claim) -> GameState:
    press: PressState = moments.press_of(state)
    claims = tuple(c if x.id == c.id else x for x in press.claims)
    return moments.with_press(state, replace(press, claims=claims))


def morale_all(state: GameState, delta: float) -> GameState:
    """Everyone on the firm's books with a morale moves by `delta` (equity partners and the
    founding partners keep theirs: TST's founder exception, PT-M1b's morale scope)."""
    staff = set(state.staff_ids(state.player.id))
    changed = []
    for ps in state.person_states:
        if ps.person_id in staff and ps.morale is not None:
            if state.person(ps.person_id).level == EQUITY_PARTNER:
                continue
            changed.append(replace(ps, morale=max(0.0, min(MORALE_MAX, ps.morale + delta))))
    return with_person_states(state, changed) if changed else state
