"""Relationships between colleagues (TST formulas.md 16.7): two people on the same open matter
team form a pair; its start value comes from their temperaments, behaviour tags push it each
month, and it drifts back toward the start. Events read pairs (team_clash, team_bond) and
change them (pair_delta). The player sees only a label.

Ported from backend/tst/sim/people/relationships.py @ 02fba2aa (Tech Startup Tycoon) and the
monthly step of tst/sim/org/relationships.py; changed: pairs form on matter teams, not units;
no W_rel morale term yet (a follow-up); a pair is dropped when either person leaves the firm.
"""

from __future__ import annotations

from dataclasses import replace

from ptk.sim.events.data import ColleaguesBalance
from ptk.sim.events.models import ColleaguePair, with_pairs
from ptk.sim.state import GameState

TEMPERAMENT = "temperament"
LABELS = ("hostile", "strained", "neutral", "good", "close")


def pair_key(x: int, y: int) -> tuple[int, int]:
    return (x, y) if x < y else (y, x)


def relationship_start(temperament_a: float, temperament_b: float, cfg: ColleaguesBalance) -> float:
    """round(base - per_temperament x |temperament_a - temperament_b|), clamped (true values)."""
    raw = round(cfg.start_base - cfg.start_per_temperament * abs(temperament_a - temperament_b))
    return float(max(cfg.start_clamp.lo, min(cfg.start_clamp.hi, raw)))


def clamp_relationship(value: float, cfg: ColleaguesBalance) -> float:
    return max(cfg.range.lo, min(cfg.range.hi, value))


def relationship_step(value: float, start: float, push: float, cfg: ColleaguesBalance) -> float:
    """One month: tag pushes first, then `drift` of the way back to the start value."""
    pushed = value + push
    return clamp_relationship(pushed + cfg.drift * (start - pushed), cfg)


def relationship_label(value: float, cfg: ColleaguesBalance) -> str:
    """hostile, strained, neutral, good or close, on the rounded value."""
    v = round(value)
    hostile, strained, good, close = cfg.label_bounds
    if v <= hostile:
        return "hostile"
    if v <= strained:
        return "strained"
    if v < good:
        return "neutral"
    if v < close:
        return "good"
    return "close"


def team_pairs(state: GameState, firm_id: int) -> dict[tuple[int, int], int]:
    """Every pair of people on the books who share an open matter team, with the lowest such
    matter id (the matter an event about them names)."""
    staff = set(state.staff_ids(firm_id))
    out: dict[tuple[int, int], int] = {}
    for matter in state.market.open_matters(firm_id):
        ids = sorted(m.person_id for m in matter.team if m.person_id in staff)
        for i, a in enumerate(ids):
            for b in ids[i + 1 :]:
                out.setdefault((a, b), matter.id)
    return out


def colleagues_month(state: GameState, cfg: ColleaguesBalance) -> GameState:
    """Phase 12, before the director: new team-mates form pairs at their start value; every
    pair whose people are both still on the player firm's books takes one monthly step; pairs
    with someone gone are dropped."""
    firm_id = state.player.id
    staff = set(state.staff_ids(firm_id))
    existing = {p.key: p for p in state.events.colleagues}
    for a, b in team_pairs(state, firm_id):
        if (a, b) not in existing:
            pa, pb = state.person(a), state.person(b)
            start = relationship_start(
                pa.personality[TEMPERAMENT], pb.personality[TEMPERAMENT], cfg
            )
            existing[(a, b)] = ColleaguePair(a, b, start, start, state.turn)
    pushes = {pid: _push(state, pid, cfg) for pid in staff}
    out: list[ColleaguePair] = []
    for key in sorted(existing):
        pair = existing[key]
        if pair.a not in staff or pair.b not in staff:
            continue
        push = pushes[pair.a] + pushes[pair.b]
        out.append(replace(pair, value=relationship_step(pair.value, pair.start, push, cfg)))
    return replace(state, events=with_pairs(state.events, tuple(out)))


def _push(state: GameState, person_id: int, cfg: ColleaguesBalance) -> float:
    """The monthly push a person's behaviour tags give each pair they are in (TST 16.7)."""
    return sum(cfg.tag_push.get(tag, 0.0) for tag in state.person(person_id).tags)


def with_pair_value(state: GameState, a: int, b: int, value: float) -> GameState:
    pair = state.events.pair(a, b)
    if pair is None:
        return state
    pairs = tuple(
        replace(p, value=value) if p.key == pair.key else p for p in state.events.colleagues
    )
    return replace(state, events=with_pairs(state.events, pairs))
