"""Reputation by (firm, practice, region), 0-100, and prestige (spec 12.1; PT-M16).

Each month a firm's reputation in a practice moves part of the way (`reputation.speed`) toward
its **long-run mean**, plus the month's pulses:

    mean = floor + size x s + record x r + pep x q
    value' = clamp(value + speed x (mean - value) + pulses, 0, 100)

- s: the firm's lawyers in the practice, ln(1 + L) / ln(1 + size_full_lawyers), at most 1.
- r: the record. The player's is its public outcomes (named matters won, closed, lost or
  collapsed, by size) over the last `record_months`, over `record_full`; a rival's is its
  franchise, `rival_record.strong` in its strong practices (firms.yaml, the dossier) plus
  `rival_record.share` x its share of the practice's market (its practice revenue over the
  market's `share_ref_place`-th largest, at most 1).
- q: the firm's profit-per-partner percentile among firms with a PEP (0 lowest, 1 highest).

Pulses are public events: the player's outcomes (`pulse` x the outcome's points), star partners
joining and leaving, a rival's key partners leaving, a quarter's league-table places, October's
directory bands, the press and event choices (`apply_pulse`). A pulse moves the value now; the
mean pulls it back unless the firm's fundamentals follow, so a reputation is earned over years.

Real rivals start at their mean in 2005 (their standing from firms.yaml and their figures); a
new firm starts at `start_founders` in its founding partners' practices and `start_other`
elsewhere.

**Prestige** (firm-wide, 0-100): the revenue-weighted average reputation (weights the firm's
practice revenue; lawyers where it has none yet) plus `prestige.pep_points` x q, at most 100.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from typing import Final

from ptk.sim.data_models import Balance, GameData
from ptk.sim.reputation.models import (
    REGION_NEW_YORK,
    Rep,
    RepCause,
    ReputationState,
    StandingState,
)
from ptk.sim.state import GameState

MAX_REP: Final = 100.0  # tunable-exempt: the 0-100 scale
MONTHS: Final = 12  # tunable-exempt: calendar


def clamp_rep(value: float) -> float:
    return max(0.0, min(MAX_REP, value))


# --- Lookups -----------------------------------------------------------------------------------

_INDEX: dict[int, tuple[tuple[Rep, ...], dict[tuple[int, str, int], Rep]]] = {}


def index(entries: tuple[Rep, ...]) -> dict[tuple[int, str, int], Rep]:
    """(firm, practice, region) -> entry, memoised by the tuple's identity (a month's intake
    reads it once per client and practice)."""
    hit = _INDEX.get(id(entries))
    if hit is not None and hit[0] is entries:
        return hit[1]
    table = {(e.firm_id, e.practice, e.region): e for e in entries}
    if len(_INDEX) > 8:  # tunable-exempt: memo size
        _INDEX.clear()
    _INDEX[id(entries)] = (entries, table)
    return table


def founders_practices(state: GameState, firm_id: int) -> frozenset[str]:
    """The practices of the firm's founding partners (their home practice, `role`)."""
    staff = set(state.staff_ids(firm_id))
    return frozenset(p.role for p in state.people if p.founding_partner and p.id in staff)


def start_value(state: GameState, firm_id: int, practice: str, balance: Balance) -> float:
    rb = balance.reputation
    founders = founders_practices(state, firm_id)
    return rb.start_founders if practice in founders else rb.start_other


def reputation(
    state: GameState, firm_id: int, practice: str, balance: Balance, region: int = REGION_NEW_YORK
) -> float:
    """A firm's public reputation 0-100 in a practice; a firm not yet seeded (a save from
    before PT-M16, before its first month) reads its start value."""
    entry = index(state.standing.reputation.entries).get((firm_id, practice, region))
    if entry is not None:
        return entry.value
    if firm_id == state.player.id:
        return start_value(state, firm_id, practice, balance)
    return 0.0


def market_quantile(
    state: GameState, practice: str, q: float, region: int = REGION_NEW_YORK
) -> float:
    """The q-quantile of every seeded firm's reputation in a practice (nearest rank)."""
    values = sorted(
        e.value
        for e in state.standing.reputation.entries
        if e.practice == practice and e.region == region
    )
    if not values:
        return MAX_REP
    i = min(len(values) - 1, max(0, math.ceil(q * len(values)) - 1))
    return values[i]


def partners_standing(state: GameState, firm_id: int, practice: str) -> float:
    """The partners' own standing in a practice, 0-1: the best partner's familiarity,
    (f - 1) / 19 (PT-M3a's measure). Clients follow a partner they know before they follow a
    firm's name, so a new firm's first panels rest on it."""
    from ptk.sim.data_models import PARTNER_LEVELS

    staff = set(state.staff_ids(firm_id))
    best = 0.0
    for person in state.people:
        if person.id in staff and person.level in PARTNER_LEVELS:
            best = max(best, (person.familiarity[practice] - 1.0) / 19.0)
    return best


def appeal_rep(state: GameState, firm_id: int, practice: str, balance: Balance) -> float:
    """The appeal's Rep (spec 7.1): the partners' standing in the practice plus appeal_span x
    the firm's public reputation / 100, plus its directory band's appeal_bonus for the year.
    Reputation adds to the partners' standing rather than replacing it, so a new firm's first
    year is PT-M3a's (the earlier milestones' guards) and a firm that earns a name is above it
    (PT-M16 decision 3)."""
    from ptk.sim.rankings.effects import appeal_bonus

    rep = reputation(state, firm_id, practice, balance)
    return (
        partners_standing(state, firm_id, practice)
        + balance.reputation.appeal_span * rep / MAX_REP
        + appeal_bonus(state, firm_id, practice, balance)
    )


def percentile(
    state: GameState, firm_id: int, practice: str, balance: Balance, region: int = REGION_NEW_YORK
) -> float:
    """PT-M7c: the firm's percentile 0-1 among every seeded firm in a practice and region: the
    share of the other firms whose reputation is below its own (ties count half)."""
    mine = reputation(state, firm_id, practice, balance, region)
    others = [
        e.value
        for e in state.standing.reputation.entries
        if e.practice == practice and e.region == region and e.firm_id != firm_id
    ]
    if not others:
        return 1.0
    below = sum(1.0 if v < mine else 0.5 if v == mine else 0.0 for v in others)
    return below / len(others)


def card_progress(state: GameState, firm_id: int, practice: str, balance: Balance) -> float:
    """PT-M7b's card progress 0-1 (spec 7.1); PT-M7c (Reece, 2026-11-23): relative, the firm's
    percentile in the practice over `top_quantile`, at most 1, so only a top-decile firm earns
    the full card (an elite boutique among them)."""
    cfg = balance.reputation.card
    return min(1.0, percentile(state, firm_id, practice, balance) / cfg.top_quantile)


def prestige_term(state: GameState, firm_id: int, balance: Balance) -> float:
    """Offer-score points from prestige (spec 12.1: it drives campus and lateral appeal)."""
    value = state.standing.reputation.prestige_of(firm_id)
    if value is None:
        return 0.0
    return balance.reputation.prestige.offer_weight * value / MAX_REP


# --- Fundamentals ------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Fundamentals:
    """One firm's public figures that set its long-run means."""

    firm_id: int
    lawyers: Mapping[str, float]  # by practice
    practice_revenue: Mapping[str, float]  # trailing 12 months, by practice
    pep_cents: float | None
    strong: frozenset[str]
    is_player: bool


def player_lawyers(state: GameState, firm_id: int, data: GameData) -> dict[str, float]:
    keys = set(data.practice_keys)
    staff = set(state.staff_ids(firm_id))
    out: dict[str, float] = {}
    for p in state.people:
        if p.id in staff and p.role in keys:
            out[p.role] = out.get(p.role, 0.0) + 1.0
    return out


def player_pep(state: GameState, firm_id: int) -> float | None:
    fp = state.partnership.of(firm_id)
    return float(fp.last_pep_cents) if fp is not None and fp.last_pep_cents else None


def fundamentals(state: GameState, data: GameData) -> tuple[Fundamentals, ...]:
    """The player's and every active rival's, by firm id."""
    from ptk.sim.interfaces import rival_standing

    player = state.player.id
    rep = state.standing.reputation
    out = [
        Fundamentals(
            firm_id=player,
            lawyers=player_lawyers(state, player, data),
            practice_revenue={p: float(sum(v)) for p, v in rep.practice_value},
            pep_cents=player_pep(state, player),
            strong=frozenset(),
            is_player=True,
        )
    ]
    for r in rival_standing(state, data):
        total = r.total_lawyers
        lawyers = dict(r.lawyers)
        revenue = {
            p: r.revenue_12m_cents * n / total if total > 0 else 0.0 for p, n in lawyers.items()
        }
        pep = (
            r.profit_12m_cents / r.equity_partners
            if r.equity_partners >= 1 and r.profit_12m_cents > 0
            else None
        )
        # strong practices are the dossier's (firms.yaml): a generated firm's largest pools are
        # not a franchise, so its record is its share of the market alone
        strong = r.strong if r.kind == "real" else frozenset()
        out.append(Fundamentals(r.firm_id, lawyers, revenue, pep, strong, False))
    return tuple(sorted(out, key=lambda f: f.firm_id))


def pep_percentiles(funds: Iterable[Fundamentals]) -> dict[int, float]:
    """Each firm's PEP percentile, 0-1 (ties share the lower rank); 0 without a PEP."""
    from bisect import bisect_left

    ranked = sorted((f.pep_cents, f.firm_id) for f in funds if f.pep_cents is not None)
    n = len(ranked)
    values = [p for p, _ in ranked]
    return {fid: (bisect_left(values, pep) / (n - 1) if n > 1 else 1.0) for pep, fid in ranked}


def share_refs(
    funds: Iterable[Fundamentals], balance: Balance, keys: Iterable[str]
) -> dict[str, float]:
    """Each practice's reference revenue: the market's share_ref_place-th largest."""
    place = balance.reputation.share_ref_place
    funds = tuple(funds)
    out = {}
    for p in keys:
        revenues = sorted((f.practice_revenue.get(p, 0.0) for f in funds), reverse=True)
        out[p] = revenues[min(place, len(revenues)) - 1] if revenues else 0.0
    return out


def record_points(rep: ReputationState) -> dict[str, float]:
    """The player's public outcome points by practice over the record window."""
    out: dict[str, float] = {}
    for o in rep.outcomes:
        out[o.practice] = out.get(o.practice, 0.0) + o.points
    return out


def size_term(lawyers: float, balance: Balance) -> float:
    full = balance.reputation.mean.size_full_lawyers
    return min(1.0, math.log1p(max(0.0, lawyers)) / math.log1p(full))


def long_run_mean(
    f: Fundamentals,
    practice: str,
    pep_q: float,
    share_ref: float,
    record: Mapping[str, float],
    balance: Balance,
) -> float:
    rb = balance.reputation
    w = rb.mean
    s = size_term(f.lawyers.get(practice, 0.0), balance)
    if f.is_player:
        r = max(0.0, min(1.0, record.get(practice, 0.0) / rb.record_full))
    else:
        share = min(1.0, f.practice_revenue.get(practice, 0.0) / share_ref) if share_ref > 0 else 0
        r = rb.rival_record.strong * (practice in f.strong) + rb.rival_record.share * share
    return clamp_rep(w.floor + w.size * s + w.record * r + w.pep * pep_q)


def means(
    state: GameState,
    data: GameData,
    balance: Balance,
    funds: tuple[Fundamentals, ...] | None = None,
) -> dict[tuple[int, str], float]:
    """Every firm's long-run mean by practice (region New York)."""
    funds = fundamentals(state, data) if funds is None else funds
    peps = pep_percentiles(funds)
    refs = share_refs(funds, balance, data.practice_keys)
    record = record_points(state.standing.reputation)
    # PT-M18 (T12): long_run_mean inlined over every firm and practice (thousands a month), the
    # same operations in the same order (test_pt_m18_speed checks it against long_run_mean)
    rb = balance.reputation
    w = rb.mean
    floor, ws, wr, wp = w.floor, w.size, w.record, w.pep
    full = math.log1p(w.size_full_lawyers)
    strong_w, share_w, record_full = rb.rival_record.strong, rb.rival_record.share, rb.record_full
    out: dict[tuple[int, str], float] = {}
    for f in funds:
        pep_q = peps.get(f.firm_id, 0.0)
        lawyers, revenue = f.lawyers, f.practice_revenue
        for p in data.practice_keys:
            sz = min(1.0, math.log1p(max(0.0, lawyers.get(p, 0.0))) / full)
            if f.is_player:
                r = max(0.0, min(1.0, record.get(p, 0.0) / record_full))
            else:
                ref = refs[p]
                share = min(1.0, revenue.get(p, 0.0) / ref) if ref > 0 else 0
                r = strong_w * (p in f.strong) + share_w * share
            v = floor + ws * sz + wr * r + wp * pep_q
            out[(f.firm_id, p)] = max(0.0, min(MAX_REP, v))
    return out


def prestige_of(entries: Iterable[Rep], f: Fundamentals, pep_q: float, balance: Balance) -> float:
    """Revenue-weighted average reputation plus prestige.pep_points x q (spec 12.1).
    `entries`: the firm's own (others are ignored)."""
    reps = {e.practice: e.value for e in entries if e.firm_id == f.firm_id}
    weights = {p: f.practice_revenue.get(p, 0.0) for p in reps}
    if sum(weights.values()) <= 0:
        weights = {p: f.lawyers.get(p, 0.0) for p in reps}
    total = sum(weights.values())
    avg = (
        sum(reps[p] * w for p, w in weights.items()) / total
        if total > 0
        else (sum(reps.values()) / len(reps) if reps else 0.0)
    )
    return clamp_rep(avg + balance.reputation.prestige.pep_points * pep_q)


# --- Writing -----------------------------------------------------------------------------------


def with_reputation(state: GameState, rep: ReputationState) -> GameState:
    return replace(state, standing=replace(state.standing, reputation=rep))


def with_standing(state: GameState, standing: StandingState) -> GameState:
    return replace(state, standing=standing)


def remember(rep: ReputationState, cause: RepCause, balance: Balance) -> ReputationState:
    kept = (*rep.causes, cause)[-balance.reputation.causes_kept :]
    return replace(rep, causes=kept)


def apply_pulses(
    state: GameState,
    pulses: Iterable[tuple[int, str | None, float, str]],
    balance: Balance,
) -> GameState:
    """Many pulses in one pass: (firm, practice or None for every practice, points, cause)."""
    pulses = [p for p in pulses if p[2]]
    if not pulses:
        return state
    by_firm: dict[int, list[tuple[str | None, float, str]]] = {}
    for fid, practice, points, cause in pulses:
        by_firm.setdefault(fid, []).append((practice, points, cause))
    rep = state.standing.reputation
    player = state.player.id
    entries = []
    for e in rep.entries:
        todo = by_firm.get(e.firm_id)
        if todo is None:
            entries.append(e)
            continue
        value = e.value
        for practice, points, _ in todo:
            if practice is None or practice == e.practice:
                value = clamp_rep(value + points)
        entries.append(e if value == e.value else replace(e, value=value))
    rep = replace(rep, entries=tuple(entries))
    for practice, points, cause in by_firm.get(player, ()):
        rep = remember(rep, RepCause(state.turn, practice, round(points, 2), cause), balance)
    return with_reputation(state, rep)


def apply_pulse(
    state: GameState,
    firm_id: int,
    points: float,
    cause: str,
    balance: Balance,
    practice: str | None = None,
) -> GameState:
    """Move a firm's reputation now by `points` in one practice, or every practice (None),
    clamped to 0-100; the player's changes are remembered with their cause."""
    if not points:
        return state
    rep = state.standing.reputation
    moved = 0.0
    entries = []
    for e in rep.entries:
        if e.firm_id == firm_id and (practice is None or e.practice == practice):
            value = clamp_rep(e.value + points)
            moved = value - e.value if practice is not None else points
            entries.append(replace(e, value=value))
        else:
            entries.append(e)
    rep = replace(rep, entries=tuple(entries))
    if firm_id == state.player.id and moved:
        rep = remember(rep, RepCause(state.turn, practice, round(moved, 2), cause), balance)
    return with_reputation(state, rep)
