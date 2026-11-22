"""Rival managing partners as characters (spec 12.2; TST formulas.md 29.4; PT-M16).

Each rival's managing partner is its chair while on its staff, else its key partner with the
lowest id (`interfaces.rival_managing_partner`). At their firm's own moves (a lateral hire, a
team lift, a new office, a merger) they make a statement with chance `statement_chance`
(stream `press_rival`, keyed by the rival's stable key and the move's count that month);
with chance `jab_base` + `jab_feud` x feud / 100 it is a jab at the player, which opens a
`jab` moment. When a bold answer names a rival, its managing partner answers.

A feud between the player's managing partner and each rival's, 0-100: + `bold_mention` when a
bold answer names them, + `poach` for each key partner the player hires from them, +
`approach` when they approach one of the player's people; - `decay` a month. At `rivalry` the
rival's stance toward the player hardens (`rivalry_stance`, PT-M5's label) and a `rivalry`
moment follows. Feuds and their causes are public.

ADR PT-0013: a real managing partner's words are professional only (their firm's moves and
the market); a jab (a public dig) from a firm whose managing partner is real comes from its
spokesperson, never in the real person's name.

Ported from backend/tst/sim/rivals/characters.py's role in TST 29.4 and
backend/tst/sim/press/names.py @ 80a3807 (Tech Startup Tycoon); changed: law firms' managing
partners through `ptk.sim.interfaces`, Partner Track's causes and moves, template words only.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Final

from ptk.sim.data_models import Balance, GameData
from ptk.sim.interfaces import (
    rival_managing_partner,
    rival_moves_in,
    rival_name,
    rival_stance_nudge,
    rival_standing,
)
from ptk.sim.log import LogItem
from ptk.sim.press import moments
from ptk.sim.press.models import Feud, PressState, Statement
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState

SPOKEN_MOVES: Final = frozenset({"hire_lateral", "lift_team", "open_office", "merged"})
STATEMENT_WORDS: Final[dict[str, str]] = {
    "hire_lateral": "we keep adding the partners our clients ask for",
    "lift_team": "the team that joined us makes us stronger in every deal we do",
    "open_office": "our clients want us where they do business",
    "merged": "together we offer clients a platform no one else can",
}
JAB = "{player} talks a big game for a firm its size"
ANSWER = "our record speaks for itself; {player} can say what it likes"


def _feud(press: PressState, rival_id: int) -> Feud:
    return press.feud(rival_id) or Feud(rival_id=rival_id)


def _with_feud(press: PressState, feud: Feud) -> PressState:
    others = [f for f in press.feuds if f.rival_id != feud.rival_id]
    return replace(press, feuds=tuple(sorted((*others, feud), key=lambda f: f.rival_id)))


def add_feud(
    state: GameState, rival_id: int, points: float, cause: str, balance: Balance
) -> GameState:
    fb = balance.press.feud
    press = moments.press_of(state)
    feud = _feud(press, rival_id)
    score = max(0.0, min(100.0, feud.score + points))  # tunable-exempt: the 0-100 scale
    causes = (*feud.causes, (state.turn, round(score - feud.score, 2), cause))[-fb.causes_kept :]
    return moments.with_press(state, _with_feud(press, replace(feud, score=score, causes=causes)))


def _speaker(
    state: GameState, rival_id: int, jab: bool, data: GameData, balance: Balance
) -> tuple[int | None, str]:
    """Who speaks for the rival: its managing partner, or its spokesperson for a jab when the
    managing partner is real (ADR PT-0013)."""
    name = rival_name(state, rival_id) or "a rival"
    mp = rival_managing_partner(state, rival_id, data, balance)
    if mp is None or (jab and mp.real):
        return None, f"a spokesperson for {name}"
    return mp.person_id, f"{mp.name} of {name}"


def statement(
    state: GameState,
    rival_id: int,
    kind: str,
    words: str,
    data: GameData,
    balance: Balance,
) -> GameState:
    person_id, speaker = _speaker(state, rival_id, kind == "jab", data, balance)
    state, sid = moments.take_id(state)
    press = moments.press_of(state)
    text = f"{speaker}: “{words.format(player=state.player.name)}”"
    record = Statement(sid, rival_id, person_id, state.turn, kind, text)  # type: ignore[arg-type]
    return moments.with_press(state, replace(press, statements=(*press.statements, record)))


def bold_mention(
    state: GameState, rival_id: int, balance: Balance, data: GameData | None = None
) -> tuple[GameState, list[LogItem]]:
    """A bold answer named this rival: the feud rises and its managing partner answers."""
    state = add_feud(
        state, rival_id, balance.press.feud.bold_mention, "named in a bold answer", balance
    )
    if data is not None:
        state = statement(state, rival_id, "answer", ANSWER, data, balance)
    return state, []


def month(state: GameState, rng: RngFactory, balance: Balance, data: GameData) -> GameState:
    """Feuds decay and take the month's causes; rivals' managing partners speak at their
    firms' moves; a feud that reaches rivalry hardens the rival and raises a moment."""
    fb = balance.press.feud
    pb = balance.press
    # the press follows the real firms' managing partners (generated firms make no news)
    views = {r.firm_id: r for r in rival_standing(state, data) if r.kind == "real"}
    press = moments.press_of(state)
    for feud in press.feuds:  # decay first: this month's causes count in full
        if feud.score > 0:
            press = _with_feud(press, replace(feud, score=max(0.0, feud.score - fb.decay)))
    state = moments.with_press(state, press)
    for fid, view in sorted(views.items()):
        seen = _feud(moments.press_of(state), fid).lost_seen
        if view.lost_to_player > seen:
            state = add_feud(
                state,
                fid,
                fb.poach * (view.lost_to_player - seen),
                "a partner hired from them",
                balance,
            )
        press = moments.press_of(state)
        feud = _feud(press, fid)
        if feud.lost_seen != view.lost_to_player:
            state = moments.with_press(
                state, _with_feud(press, replace(feud, lost_seen=view.lost_to_player))
            )
    spoken: dict[int, int] = {}  # each rival's spoken moves so far this month (the stream's n)
    for move in rival_moves_in(state, state.turn):
        if move.firm_id not in views:
            continue
        if move.action == "approach_player":
            state = add_feud(state, move.firm_id, fb.approach, "approached your people", balance)
        if move.action not in SPOKEN_MOVES:
            continue
        n = spoken.get(move.firm_id, 0)
        spoken[move.firm_id] = n + 1
        gen = rng.stream(state.turn, "press_rival", *views[move.firm_id].rival_key, n)
        if float(gen.random()) >= pb.statement_chance:
            continue
        score = _feud(moments.press_of(state), move.firm_id).score
        jab = float(gen.random()) < pb.jab_base + pb.jab_feud * score / 100  # tunable-exempt: 0-100
        if jab:
            state = statement(state, move.firm_id, "jab", JAB, data, balance)
            state = moments.queue_moment(
                state,
                "jab",
                {"result": f"{views[move.firm_id].name} takes a dig at the firm"},
                rival_id=move.firm_id,
            )
        else:
            state = statement(
                state, move.firm_id, "statement", STATEMENT_WORDS[move.action], data, balance
            )
    for feud in moments.press_of(state).feuds:
        if feud.score >= fb.rivalry and feud.rivalry_turn is None and feud.rival_id in views:
            state = rival_stance_nudge(state, feud.rival_id, fb.rivalry_stance)
            press = moments.press_of(state)
            state = moments.with_press(
                state, _with_feud(press, replace(feud, rivalry_turn=state.turn))
            )
            state = moments.queue_moment(
                state,
                "rivalry",
                {"result": f"the rivalry with {views[feud.rival_id].name}"},
                rival_id=feud.rival_id,
            )
        elif feud.score < fb.rivalry / 2 and feud.rivalry_turn is not None:
            press = moments.press_of(state)
            state = moments.with_press(state, _with_feud(press, replace(feud, rivalry_turn=None)))
    return state
