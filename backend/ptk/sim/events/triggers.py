"""Triggers (TST formulas.md 16.2, 23.3): what is happening in the player's firm this month,
computed from true state in phase 12. True values are allowed here and never leave the engine:
a hit names only who and what an event is about, not why.

Ported from backend/tst/sim/events/triggers.py @ 02fba2aa (Tech Startup Tycoon); changed:
Partner Track's triggers (people, clients, matters, partnership, market, regulatory,
technology) and crises (a key person's exit, a key client walking, a key matter's trial)
replace TST's product, funding, executive and research ones.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from ptk.sim.calendar import turn_to_ym
from ptk.sim.data_models import PARTNER_LEVELS, Balance, GameData
from ptk.sim.events.data import EventsBalance
from ptk.sim.events.formulas import above_strength, below_strength, clamp01
from ptk.sim.matters.models import Matter
from ptk.sim.org.rules import org_view
from ptk.sim.people.models import current_ability
from ptk.sim.state import GameState

MONTHS_PER_YEAR = 12  # tunable-exempt: calendar
CASE = "case"
DEAL = "deal"
WON = ("won", "closed")
LOST = ("lost", "collapsed")
EXIT_REASONS = ("resigned",)
JUNIOR_FIRST = ("junior", "paralegal", "senior", "lead")  # who an error is pinned on, in order


@dataclass(frozen=True, slots=True)
class TriggerHit:
    trigger: str
    strength: float
    person_ids: tuple[int, ...] = ()
    unit_id: int | None = None
    client_id: int | None = None
    matter_id: int | None = None
    practice: str | None = None
    months: int | None = None
    amount_cents: int | None = None
    critical_ok: bool = False


def is_associate(level: str) -> bool:
    return level.startswith("associate_") or level == "senior_associate"


def triggers(
    state: GameState, start: GameState, balance: Balance, data: GameData
) -> list[TriggerHit]:
    """Every trigger that holds for the player this month, in TRIGGERS order, each trigger's
    hits by person, pair, client or matter id. `start` is the state at the start of the turn
    (for changes this month)."""
    ev = balance.events
    t = ev.trigger
    firm = state.player
    fid = firm.id
    view = org_view(state, fid)
    founder_id = state.founder_of(fid)
    staff_all = set(state.staff_ids(fid))
    staff = [e for e in state.staff(fid) if e.person_id != founder_id and e.status == "active"]
    people = {p.id: p for p in state.people}
    unit = view.unit_of
    hits: list[TriggerHit] = []

    def person_hit(trigger: str, strength: float, pid: int) -> TriggerHit:
        return TriggerHit(trigger, strength, (pid,), unit.get(pid))

    # --- people ---------------------------------------------------------------------------
    for e in staff:
        morale = state.person_state(e.person_id).morale
        s = None if morale is None else below_strength(morale, t["low_morale"])
        if s is not None:
            hits.append(person_hit("low_morale", s, e.person_id))
    for e in staff:
        person = people[e.person_id]
        if person.burnt_out:
            continue
        s = above_strength(person.strain, t["high_strain"])
        if s is not None:
            hits.append(person_hit("high_strain", s, e.person_id))
    for e in staff:
        if people[e.person_id].burnout_since == state.turn:
            hits.append(person_hit("burnout", ev.fixed("burnout"), e.person_id))
    star = t["star_associate"]
    associates = [e for e in staff if is_associate(people[e.person_id].level)]
    ranked = sorted(
        associates, key=lambda e: (-current_ability(people[e.person_id], data), e.person_id)
    )
    top = ranked[: max(1, math.ceil(len(ranked) * float(star.top_fraction or 0)))] if ranked else []
    for e in sorted(top, key=lambda e: e.person_id):
        if state.turn - e.start_turn >= (star.tenure_months or 0):
            hits.append(person_hit("star_associate", ev.fixed("star_associate"), e.person_id))
    for e in staff:
        reveal = state.reveal(fid, e.person_id)
        if reveal is not None and any(turn == state.turn for _, turn in reveal.revealed_tags):
            hits.append(person_hit("tag_noticed", ev.fixed("tag_noticed"), e.person_id))
    for e in staff:
        tenure = state.turn - e.start_turn
        if tenure > 0 and tenure % MONTHS_PER_YEAR == 0:
            hits.append(person_hit("anniversary", ev.fixed("anniversary"), e.person_id))
    pairs = _pair_matters(state, fid)
    clash, bond = t["team_clash"], t["team_bond"]
    active = {e.person_id for e in staff}
    for p in state.events.colleagues:
        if p.a not in active or p.b not in active:
            continue
        matter = pairs.get(p.key)
        client = _client_of(state, matter)
        if clash.at_most is not None and p.value <= clash.at_most:
            s = clamp01((clash.at_most - p.value) / float(clash.span or 1))
            hits.append(TriggerHit("team_clash", s, p.key, unit.get(p.a), client, matter))
    for p in state.events.colleagues:
        if p.a not in active or p.b not in active:
            continue
        matter = pairs.get(p.key)
        client = _client_of(state, matter)
        if bond.at_least is not None and p.value >= bond.at_least:
            hits.append(
                TriggerHit("team_bond", ev.fixed("team_bond"), p.key, unit.get(p.a), client, matter)
            )
    before = {m.id: m for m in start.market.matters}
    open_now = state.market.open_matters(fid)
    for m in open_now:
        was = before.get(m.id)
        # Caught errors only: escaped ones are hidden until they surface (the API's rule).
        if was is None or m.errors_caught <= was.errors_caught:
            continue
        culprit = _junior(m, staff_all, founder_id)
        if culprit is not None:
            hits.append(
                TriggerHit(
                    "associate_error",
                    ev.fixed("associate_error"),
                    (culprit,),
                    unit.get(culprit),
                    m.client_id,
                    m.id,
                    m.practice,
                )
            )

    # --- clients --------------------------------------------------------------------------
    rels = [r for r in state.market.relationships if r.firm_id == fid and r.fees_12m > 0]
    for r in rels:
        s = below_strength(r.score, t["client_cooling"])
        if s is not None:
            hits.append(
                TriggerHit(
                    "client_cooling", s, _who(r.partner_id, staff_all), client_id=r.client_id
                )
            )
    big = t["big_instruction"]
    for m in open_now:
        if m.opened_turn == state.turn and (
            m.critical or m.expected_fees_cents >= (big.min_cents or 0)
        ):
            hits.append(
                TriggerHit(
                    "big_instruction",
                    ev.fixed("big_instruction"),
                    _matter_people_ids(m, staff_all),
                    client_id=m.client_id,
                    matter_id=m.id,
                    practice=m.practice,
                )
            )
    if rels:
        top_rel = max(rels, key=lambda r: (r.fees_12m, -r.client_id))
        who = _who(top_rel.partner_id, staff_all)
        hits.append(
            TriggerHit("gc_demand", ev.fixed("gc_demand"), who, client_id=top_rel.client_id)
        )
    review = t["panel_review"]
    every = review.months or MONTHS_PER_YEAR
    for r in rels:
        years = state.turn - r.since_turn
        if years > 0 and years % every == 0:
            hits.append(
                TriggerHit(
                    "panel_review",
                    ev.fixed("panel_review"),
                    _who(r.partner_id, staff_all),
                    client_id=r.client_id,
                    months=every,
                )
            )
    fee = t["fee_dispute"]
    for m in open_now:
        if m.expected_fees_cents <= 0:
            continue
        ratio = m.wip_cents / m.expected_fees_cents  # money-exact: ratio
        if fee.ratio is not None and ratio > fee.ratio:
            s = clamp01((ratio - fee.ratio) / float(fee.span or 1))
            hits.append(_matter_hit("fee_dispute", s, m, staff_all))

    # --- matters --------------------------------------------------------------------------
    for m in open_now:
        was = before.get(m.id)
        if was is not None and m.missed_deadlines > was.missed_deadlines:
            hits.append(_matter_hit("deadline_slip", ev.fixed("deadline_slip"), m, staff_all))
    brink = t["deal_on_brink"]
    for m in open_now:
        if data.market.kinds[m.kind].outcome == DEAL and m.under_months >= (brink.months or 1):
            hits.append(_matter_hit("deal_on_brink", ev.fixed("deal_on_brink"), m, staff_all))
    for m in open_now:
        if m.settlement is not None and m.settlement.made_turn == state.turn:
            hits.append(_matter_hit("settlement_offer", ev.fixed("settlement_offer"), m, staff_all))
    closed = [
        m
        for m in state.market.matters
        if m.firm_id == fid and m.closed_turn == state.turn and m.outcome is not None
    ]
    won = t["matter_won"]
    for m in closed:
        notable = m.critical or m.expected_fees_cents >= (won.min_cents or 0)
        if notable and m.outcome in WON:
            hits.append(_matter_hit("matter_won", ev.fixed("matter_won"), m, staff_all))
    for m in closed:
        notable = m.critical or m.expected_fees_cents >= (won.min_cents or 0)
        if notable and m.outcome in LOST:
            hits.append(_matter_hit("matter_lost", ev.fixed("matter_lost"), m, staff_all))

    # --- partnership ----------------------------------------------------------------------
    for m in open_now:
        a, b = m.originator_id, m.lead_id
        if a is None or b is None or a == b or a not in staff_all or b not in staff_all:
            continue
        if people[a].level in PARTNER_LEVELS and people[b].level in PARTNER_LEVELS:
            hits.append(
                TriggerHit(
                    "credit_dispute",
                    ev.fixed("credit_dispute"),
                    (a, b),
                    unit.get(a),
                    m.client_id,
                    m.id,
                    m.practice,
                )
            )
    retire = t["partner_retiring"]
    for e in staff:
        person = people[e.person_id]
        if person.level in PARTNER_LEVELS and person.age(state.turn) >= (retire.age or 0):
            hits.append(person_hit("partner_retiring", ev.fixed("partner_retiring"), e.person_id))

    # --- market ---------------------------------------------------------------------------
    ym = turn_to_ym(state.turn, state.save_meta.start_ym)
    row = next((r for r in data.salary_scale.scale if r.from_ym == ym), None)
    if row is not None and state.turn > 0:
        hits.append(TriggerHit("scale_move", ev.fixed("scale_move"), amount_cents=row.salaries[0]))
    shift = t["demand_shift"]
    now_d, then_d = state.market.demand_cents, start.market.demand_cents
    if now_d and len(now_d) == len(then_d) and shift.ratio is not None:
        moves = [
            (abs(n / o - 1.0), i)  # money-exact: ratio
            for i, (n, o) in enumerate(zip(now_d, then_d, strict=True))
            if o > 0
        ]
        if moves:
            size, index = max(moves, key=lambda x: (x[0], -x[1]))
            if size >= shift.ratio:
                s = clamp01((size - shift.ratio) / float(shift.span or 1))
                practice = data.practices[index].key
                hits.append(TriggerHit("demand_shift", s, practice=practice))

    # --- regulatory -----------------------------------------------------------------------
    for m in closed:
        if m.outcome == "disqualified":
            hits.append(
                _matter_hit("conflict_surfaced", ev.fixed("conflict_surfaced"), m, staff_all)
            )
    audit = t["annual_audit"]
    if ym[1] == (audit.months or 1):
        hits.append(TriggerHit("annual_audit", ev.fixed("annual_audit")))
    bar = t["bar_complaint"]
    for m in open_now:
        was = before.get(m.id)
        increased = was is not None and m.missed_deadlines > was.missed_deadlines
        if increased and m.missed_deadlines >= (bar.at_least or 0):
            hits.append(_matter_hit("bar_complaint", ev.fixed("bar_complaint"), m, staff_all))

    # --- technology -----------------------------------------------------------------------
    if staff:
        hits.append(TriggerHit("tech_pitch", ev.fixed("tech_pitch")))
    if not hits:
        hits.append(TriggerHit("quiet_month", ev.fixed("quiet_month")))
    return hits


def _who(person_id: int | None, staff: set[int]) -> tuple[int, ...]:
    return (person_id,) if person_id is not None and person_id in staff else ()


def _matter_hit(trigger: str, strength: float, m: Matter, staff: set[int]) -> TriggerHit:
    return TriggerHit(
        trigger,
        strength,
        _matter_people_ids(m, staff),
        client_id=m.client_id,
        matter_id=m.id,
        practice=m.practice,
    )


def _matter_people_ids(m: Matter, staff: set[int]) -> tuple[int, ...]:
    for pid in (m.lead_id, m.originator_id):
        if pid is not None and pid in staff:
            return (pid,)
    return ()


def _junior(m: Matter, staff: set[int], founder_id: int | None) -> int | None:
    """The team member a matter's error is pinned on: the most junior role, lowest id."""
    for role in JUNIOR_FIRST:
        ids = sorted(
            t.person_id
            for t in m.team
            if t.role == role and t.person_id in staff and t.person_id != founder_id
        )
        if ids:
            return ids[0]
    return None


def _client_of(state: GameState, matter_id: int | None) -> int | None:
    m = state.market.matter(matter_id) if matter_id is not None else None
    return m.client_id if m is not None else None


def _pair_matters(state: GameState, firm_id: int) -> dict[tuple[int, int], int]:
    from ptk.sim.events.colleagues import team_pairs

    return team_pairs(state, firm_id)


# --- Matter draws and crises -----------------------------------------------------------------


def matter_draws(
    state: GameState, gen: np.random.Generator, balance: Balance, data: GameData
) -> list[TriggerHit]:
    """For each of the player's open case matters by id: a smoking-gun draw, then (with a judge
    assigned) a ruling draw, on the director's events stream after the count and crises."""
    ev = balance.events
    fid = state.player.id
    staff = set(state.staff_ids(fid))
    hits: list[TriggerHit] = []
    for m in state.market.open_matters(fid):
        if data.market.kinds[m.kind].outcome != CASE:
            continue
        if float(gen.random()) < float(ev.trigger["smoking_gun"].chance or 0):
            hits.append(_matter_hit("smoking_gun", ev.fixed("smoking_gun"), m, staff))
        if m.judge_id is not None and float(gen.random()) < float(
            ev.trigger["judge_ruling"].chance or 0
        ):
            hits.append(_matter_hit("judge_ruling", ev.fixed("judge_ruling"), m, staff))
    return hits


def key_people(state: GameState, data: GameData, cfg: EventsBalance) -> set[int]:
    """Partners and the top share of the firm's other lawyers by current ability."""
    fid = state.player.id
    founder = state.founder_of(fid)
    people = {p.id: p for p in state.people}
    staff = [e.person_id for e in state.staff(fid) if e.person_id != founder]
    partners = {p for p in staff if people[p].level in PARTNER_LEVELS}
    others = sorted(
        (p for p in staff if p not in partners),
        key=lambda p: (-current_ability(people[p], data), p),
    )
    share = cfg.crisis.key_exit_top_fraction
    top = set(others[: math.floor(len(others) * share)])  # none in a firm of a few people
    return partners | top


def crisis_hits(state: GameState, balance: Balance, data: GameData) -> list[TriggerHit]:
    """In fixed order: key exits this month (by person id), a key client walking (by client
    id), a key matter's trial (by matter id)."""
    cfg = balance.events
    fid = state.player.id
    view = org_view(state, fid)
    staff = set(state.staff_ids(fid))
    hits: list[TriggerHit] = []
    key = key_people(state, data, cfg)
    for e in state.staff(fid):
        if (
            e.status == "notice"
            and e.end_turn == state.turn + 1
            and e.end_reason in EXIT_REASONS
            and e.person_id in key
        ):
            hits.append(
                TriggerHit(
                    "key_exit", 1.0, (e.person_id,), view.unit_of.get(e.person_id), critical_ok=True
                )
            )
    rels = [r for r in state.market.relationships if r.firm_id == fid]
    total = sum(r.fees_12m for r in rels)
    for r in rels:
        if total <= 0 or r.fees_12m < cfg.crisis.walkout_share * total:
            continue
        if r.score < cfg.crisis.walkout_below:
            who = _who(r.partner_id, staff)
            hits.append(
                TriggerHit("client_walkout", 1.0, who, client_id=r.client_id, critical_ok=True)
            )
    recent = {
        e.matter_id
        for e in state.events.events
        if e.trigger == "verdict_due" and e.turn > state.turn + 1 - cfg.crisis.verdict_months
    }
    for m in state.market.open_matters(fid):
        kind = data.market.kinds[m.kind]
        if not m.critical or kind.outcome != CASE or m.id in recent:
            continue
        if m.phase_index == len(kind.phases) - 1:
            hit = _matter_hit("verdict_due", 1.0, m, staff)
            hits.append(
                TriggerHit(
                    hit.trigger,
                    hit.strength,
                    hit.person_ids,
                    client_id=hit.client_id,
                    matter_id=hit.matter_id,
                    practice=hit.practice,
                    critical_ok=True,
                )
            )
    return hits
