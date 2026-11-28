"""The press's month (spec 12.2; TST formulas.md 29; PT-M16), in phase 10 after reputation and
the rankings. Order: the month's moments are raised from what happened (rivals' collapses and
mergers, the firm's layoffs, big verdicts, lateral splashes, ranking days, the salary scale);
feuds and rivals' statements; claims are judged; bold answers' backfires; open moments left
unanswered get the press office's answer; credibility drifts; then the moments are kept or
skipped for next month.

Ported from backend/tst/sim/press/phase.py @ 80a3807 (Tech Startup Tycoon); changed: Partner
Track's triggers, read through `ptk.sim.interfaces` and the turn's start state; no departures
record (TST 29.5)."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace

from simcore.kernel.calendar import turn_to_ym

from ptk.sim.data_models import Balance, GameData
from ptk.sim.hiring.pay import market_scale_cents
from ptk.sim.interfaces import rival_moves_in, rival_name
from ptk.sim.log import LogItem
from ptk.sim.press import characters, claims, moments
from ptk.sim.state import GameState
from ptk.sim.streams import RngFactory

FIRST_YEAR = "associate_1"  # tunable-exempt: the scale's first-year step names the scale's moves


def fired_this_month(state: GameState, start: GameState) -> tuple[int, int]:
    """(people fired this month, the firm's staff at the month's start)."""
    pid = state.player.id
    before = {e.person_id for e in start.employments if e.firm_id == pid and e.status == "active"}
    fired = sum(
        1
        for e in state.employments
        if e.firm_id == pid
        and e.person_id in before
        and e.end_reason == "fired"
        and e.status != "active"
    )
    return fired, len(before)


def raise_moments(
    state: GameState,
    start: GameState,
    balance: Balance,
    data: GameData,
    ranking_days: Iterable[tuple[str, dict[str, str | int]]],
    fired: int,
    staff: int,
) -> GameState:
    pb = balance.press
    pid = state.player.id
    for move in rival_moves_in(state, state.turn):
        name = rival_name(state, move.firm_id) or "a rival"
        if move.action in ("collapsed", "failed"):
            state = moments.queue_moment(
                state, "collapse", {"result": f"{name} collapses"}, rival_id=move.firm_id
            )
        elif move.action == "merged":
            other = rival_name(state, move.other_firm_id) if move.other_firm_id else None
            words = f"{name} merges into {other}" if other else f"{name} merges"
            state = moments.queue_moment(state, "merger", {"result": words}, rival_id=move.firm_id)
        elif move.action == "lost_to_player":
            state = moments.queue_moment(
                state,
                "lateral",
                {"result": f"a partner joins the firm from {name}"},
                rival_id=move.firm_id,
                person_id=move.person_id,
            )
    if staff and fired > 1 and fired >= pb.layoff_share * staff:
        state = moments.queue_moment(state, "layoffs", {"result": f"{fired} people let go"})
    for m in state.market.matters:
        if (
            m.firm_id == pid
            and m.closed_turn == state.turn
            and m.kind == "case"
            and m.outcome in ("won", "lost")
            and m.expected_fees_cents >= pb.big_cents
        ):
            state = moments.queue_moment(
                state,
                "verdict",
                {"result": f"{m.name}: {m.outcome}"},
                practice=m.practice,
                person_id=m.lead_id,
            )
    before = set(start.standing.reputation.stars)
    after = set(state.standing.reputation.stars)
    for person_id, practice in sorted(after - before):
        state = moments.queue_moment(
            state,
            "lateral",
            {"result": "a star partner joins the firm"},
            practice=practice,
            person_id=person_id,
        )
    for _person_id, practice in sorted(before - after):
        state = moments.queue_moment(
            state, "lateral", {"result": "a star partner leaves the firm"}, practice=practice
        )
    for trigger, facts in ranking_days:
        named = facts.get("practice")
        told = {k: v for k, v in facts.items() if k != "practice"}
        state = moments.queue_moment(state, trigger, told, practice=str(named) if named else None)
    ym = turn_to_ym(state.turn, state.save_meta.start_ym)
    scale = market_scale_cents(data, ym, FIRST_YEAR)
    press = moments.press_of(state)
    if press.scale_seen and scale != press.scale_seen:
        state = moments.queue_moment(
            state,
            "salary_scale",
            {"result": f"first-year salaries move to {scale // 100:,} dollars"},
        )
    return moments.with_press(state, replace(moments.press_of(state), scale_seen=scale))


def month(
    state: GameState,
    start: GameState,
    rng: RngFactory,
    balance: Balance,
    data: GameData,
    ranking_days: Iterable[tuple[str, dict[str, str | int]]] = (),
) -> tuple[GameState, list[LogItem]]:
    if state.ended:
        return state, []
    press = moments.press_of(state)
    if press.credibility is None:  # TST 29.3: every firm starts at cred_start
        state = moments.with_press(state, replace(press, credibility=balance.press.cred_start))
    fired, staff = fired_this_month(state, start)
    state = raise_moments(state, start, balance, data, ranking_days, fired, staff)
    state = characters.month(state, rng, balance, data)
    state, claim_logs = claims.check(state, rng, balance, data, fired)
    state = moments.backfires(state, balance)
    state, office_logs = moments.office_answers(state, balance, data)
    state = moments.drift_credibility(state, balance)
    state, scheduled = moments.schedule(state, balance)
    return state, [*claim_logs, *office_logs, *scheduled]
