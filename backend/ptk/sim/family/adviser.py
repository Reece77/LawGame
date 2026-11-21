"""The senior partner as adviser (spec 2.5; TST formulas.md 45.5): the old founder gives an
opinion on each vote the firm opens, in their voice, from their persona (templates; an LLM
wording within spec 15's budget is a follow-up). When a vote they opposed passes, every
partner's confidence in the MP falls by `succession.adviser_oppose` (the firm noticed the
founder's objection was overruled). They advise until they retire.

Ported from backend/tst/sim/family/adviser.py @ 121d318a (Tech Startup Tycoon); changed:
votes instead of proposals and pitches; risky votes are `succession.risky_votes`; the effect
is partner confidence (through `interfaces.confidence_change`), not board seats.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Final

from ptk.sim.data_models import Balance
from ptk.sim.founder.models import FounderLife, Opinion
from ptk.sim.founder.persona import top_trait
from ptk.sim.interfaces import confidence_change, partnership_votes
from ptk.sim.log import LogItem, inbox_item
from ptk.sim.state import GameState

SUPPORT, OPPOSE = "support", "oppose"
TITLE_MAX: Final = 80  # tunable-exempt: an opinion title's width

WORDS: Final = {
    ("visionary", SUPPORT): "Go further. This is the kind of bet that built the firm.",
    ("visionary", OPPOSE): "Too timid. It costs us without changing what we are.",
    ("ruthless", SUPPORT): "Sensible. It earns its keep; do it and do not look back.",
    ("ruthless", OPPOSE): "Wasteful. I would not have signed it, and neither should you.",
    ("beloved", SUPPORT): "Good for our people and for our name. I would do it.",
    ("beloved", OPPOSE): "Think of the partners this lands on. I would not do it.",
    ("reckless", SUPPORT): "Do it now, before another firm does.",
    ("reckless", OPPOSE): "There is a bolder move than this. Wait for it.",
}


def stance(life: FounderLife | None, risky: bool) -> tuple[str, str]:
    """(stance, voice): a bold adviser (Visionary + Reckless at least Ruthless + Beloved)
    backs risky votes and doubts small ones; a cautious one the reverse."""
    if life is None:
        return SUPPORT, "beloved"
    bold = life.visionary + life.reckless >= life.ruthless + life.beloved
    return (SUPPORT if bold == risky else OPPOSE), top_trait(life)


def adviser_id(state: GameState) -> int | None:
    """The senior partner who advises: the latest former player still at the firm."""
    you = state.founder_of(state.player.id)
    best: tuple[int, int] | None = None
    for life in state.founder_life.lives:
        if life.status != "senior_partner" or life.person_id == you:
            continue
        e = state.employment_of(life.person_id)
        if e is None or e.status != "active" or e.firm_id != state.player.id:
            continue
        key = (life.until_turn or 0, life.person_id)
        if best is None or key > best:
            best = key
    return best[1] if best else None


def adviser_month(state: GameState, balance: Balance) -> tuple[GameState, tuple[LogItem, ...]]:
    aid = adviser_id(state)
    if aid is None:
        return state, ()
    sb = balance.succession
    fl = state.founder_life
    life = fl.life(aid)
    seen = {o.vote_id for o in fl.opinions}
    new: list[Opinion] = []
    logs: list[LogItem] = []
    overruled = 0
    for v in partnership_votes(state, state.player.id):
        if v.opened_turn != state.turn or v.vote_id in seen or v.succession:
            continue
        s, voice = stance(life, v.kind in sb.risky_votes)
        title = v.title[:TITLE_MAX]
        lost = s == OPPOSE and v.status == "passed"
        overruled += int(lost)
        new.append(Opinion(state.turn, aid, v.vote_id, title, s, WORDS[(voice, s)], lost))
        p = state.person(aid)
        logs.append(
            inbox_item(
                state.turn,
                state.player.id,
                "adviser_opinion",
                link_kind="person",
                link_id=aid,
                name=f"{p.first_name} {p.last_name}",
                stance=s,
                subject=title,
                text=WORDS[(voice, s)],
            )
        )
    if not new:
        return state, ()
    if overruled:
        state = confidence_change(state, state.player.id, -sb.adviser_oppose * overruled)
    fl = state.founder_life
    opinions = (*fl.opinions, *new)[-sb.adviser_memory :]
    return replace(state, founder_life=replace(fl, opinions=opinions)), tuple(logs)
