"""A month of work on named matters (spec 7.5-7.6a), relationships (7.2) and origination.

Each open matter, by id, takes one generator from stream `matter` keyed by its id and draws
`DRAWS` uniforms in a fixed order: judge, error, catch, deadline, settlement, the other
side's view, summary judgment, outcome. Then:

- **Judge** (case kinds with a court and no judge): drawn uniformly from the court's
  judges; the planned duration takes the judge's docket speed and the discovery phase's
  hours the judge's discovery strictness. A judge moves path, timing and cost only:
  `formulas.p_win` takes no judge term (spec 7.6a, ADR PT-0013).
- **Progress**: team output o = Σ hours x effective skill on the phase's tasks / 10 x strain
  factor x the lead's supervision factor (x the judge's procedure term in discovery and
  motions); a phase needs its share of the matter's hours; output carries into later phases.
- **Pace**: a month under `progress.under_pace` of the planned pace is under-staffed; cases
  and filings then risk a missed deadline.
- **Errors** (spec 7.6): p_error by the team's skill, strain, cowboys and supervision;
  caught errors add rework hours, escaped ones are recorded (claims arrive in v2).
- **Settlement offers** (cases in discovery or motions) as pending items.
- **Outcome** when the last phase completes, at summary judgment, or when a case reaches its
  trial date regardless (the due month plus `matters.max_slip_months`).

Hidden conflicts (checks skipped) may surface from stream `conflict`, keyed by matter.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

from simcore.kernel.calendar import turn_to_ym

from ptk.sim.data_models import Balance, GameData, KindDef
from ptk.sim.fastcopy import replace
from ptk.sim.interfaces import seat_effect, tech_hours
from ptk.sim.log import LogItem, inbox_item
from ptk.sim.macro import docket_slowed, driver_shortfall
from ptk.sim.matters import formulas as fx
from ptk.sim.matters.intake import bump, with_matter
from ptk.sim.matters.models import (
    Appearance,
    HoursRecord,
    Judge,
    MarketState,
    Matter,
    Origination,
    Outcome,
    Relationship,
    SettlementOffer,
)
from ptk.sim.org.formulas import span_limit
from ptk.sim.people.models import Person
from ptk.sim.people.strain import burnout_effects_active
from ptk.sim.state import GameState
from ptk.sim.streams import RngFactory

DRAWS: Final = 8  # tunable-exempt: uniforms per matter-month, drawn whether used or not
U_JUDGE, U_ERROR, U_CATCH, U_DEADLINE, U_SETTLE, U_VIEW, U_SJ, U_OUTCOME = range(DRAWS)
PROCEDURE_PHASES: Final = frozenset({"discovery", "motions"})
SETTLEMENT_PHASES: Final = frozenset({"discovery", "motions"})
APPEARANCE_PHASES: Final = frozenset({"motions", "trial"})
CASE_KINDS: Final = frozenset({"case", "investigation"})
FEE_WINDOW: Final = 12  # tunable-exempt: months of fees a relationship remembers
QUALITY_GOOD: Final = 14.0  # tunable-exempt: craft at which advice counts as a win (balance win)
QUALITY_POOR: Final = 8.0  # tunable-exempt: craft at which advice counts as a loss


@dataclass(frozen=True, slots=True)
class TeamMonth:
    hours: float
    output: float
    skill: float  # hours-weighted effective skill on the phase's tasks
    craft: float  # hours-weighted outcome craft (case or deal)
    strain_mult: float  # hours-weighted error strain multiplier
    strain: float  # hours-weighted strain
    cowboy: bool
    supervision: float  # the lead's span factor on matters, 0-1
    shortfall: float


def _lead_factors(
    matter: Matter, leads: Mapping[int, int], people: Mapping[int, Person], balance: Balance
) -> tuple[float, float]:
    """(supervision factor, shortfall) from the lead's open matters against span(leadership)."""
    if matter.lead_id is None or matter.lead_id not in people:
        return 0.5, 1.0  # tunable-exempt: an unled matter is half-supervised
    limit = max(1, span_limit(people[matter.lead_id].skills["leadership"], balance.org))
    n = leads.get(matter.lead_id, 1)
    if n <= limit:
        return 1.0, 0.0
    return limit / n, n / limit - 1.0


def judge_factor(judge: Judge | None, trait: str) -> float:
    """(trait - 10) / 10 for the matter's judge, 0 without one."""
    return 0.0 if judge is None else (judge.traits[trait] - 10.0) / 10.0


def craft_weights(kind: KindDef, balance: Balance) -> dict[str, float] | None:
    if kind.outcome == "case":
        return balance.outcomes.craft_skills
    if kind.outcome == "deal":
        return balance.outcomes.deal_skills
    return None


def team_month(
    matter: Matter,
    records: list[HoursRecord],
    people: Mapping[int, Person],
    judge: Judge | None,
    appearances: Mapping[tuple[int, int], int],
    turn: int,
    leads: Mapping[int, int],
    data: GameData,
    balance: Balance,
    hours_factor: float = 1.0,
) -> TeamMonth:
    kind = data.market.kinds[matter.kind]
    phase = kind.phases[min(matter.phase_index, len(kind.phases) - 1)]
    weights = craft_weights(kind, balance)
    sup, shortfall = _lead_factors(matter, leads, people, balance)
    hours = output = skill = craft = smult = strain = 0.0
    cowboy = False
    for r in records:
        person = people[r.person_id]
        h = r.tenths / fx.TENTHS
        eff = fx.effective_skill(person, phase.tasks, matter.practice, data, balance)
        # PT-M14: AI's tasks take hours_factor of their base hours, so an hour does more
        out = h * eff / 10.0 * fx.strain_output(person.strain, balance) * sup / hours_factor
        if judge is not None and phase.key in PROCEDURE_PHASES:
            cfg = balance.judges
            seen = appearances.get((person.id, judge.id), 0) / fx.TENTHS
            familiar = 1.0 + cfg.appearance_bonus * min(1.0, seen / cfg.appearance_full_hours)
            proc = (person.skills["procedure"] - 10.0) / 10.0
            out *= (
                1.0 + cfg.procedure * judge_factor(judge, "discovery_strictness") * proc * familiar
            )
        hours += h
        output += max(0.0, out)
        skill += h * eff
        craft += h * (fx.craft(person, weights, matter.practice, balance) if weights else eff)
        smult += h * fx.person_error_strain(
            person.strain, burnout_effects_active(person, turn, balance), balance
        )
        strain += h * person.strain
        cowboy = cowboy or "cowboy" in person.tags
    if hours <= 0:
        return TeamMonth(0.0, 0.0, 10.0, 10.0, 1.0, 0.0, False, sup, shortfall)
    return TeamMonth(
        hours=hours,
        output=output,
        skill=skill / hours,
        craft=craft / hours,
        strain_mult=smult / hours,
        strain=strain / hours,
        cowboy=cowboy,
        supervision=sup,
        shortfall=shortfall,
    )


def assign_judge(
    matter: Matter, market: MarketState, u: float, data: GameData, balance: Balance
) -> Matter:
    judges = [j for j in market.judges if j.court == matter.court and j.sits(matter.opened_turn)]
    if not judges:
        return matter
    judge = judges[min(int(u * len(judges)), len(judges) - 1)]
    speed = 1.0 - balance.judges.speed * judge_factor(judge, "docket_speed")
    kind = data.market.kinds[matter.kind]
    discovery = sum(p.share for p in kind.phases if p.key == "discovery")
    extra = balance.judges.discovery * -judge_factor(judge, "discovery_strictness") * discovery
    return replace(
        matter,
        judge_id=judge.id,
        planned_months=max(1, round(matter.planned_months * speed)),
        hours_needed_tenths=max(fx.TENTHS, round(matter.hours_needed_tenths * (1.0 + extra))),
    )


def advance_phases(
    matter: Matter, output_hours: float, kind: KindDef
) -> tuple[Matter, bool, list[str]]:
    """Add output to the current phase, carrying over; returns (matter, finished, phases done)."""
    index, progress = matter.phase_index, matter.phase_progress
    done: list[str] = []
    left = output_hours
    total_hours = matter.hours_needed_tenths / fx.TENTHS
    while index < len(kind.phases) and left > 0:
        need = kind.phases[index].share * total_hours * (1.0 - progress)
        if left >= need:
            left -= need
            done.append(kind.phases[index].key)
            index, progress = index + 1, 0.0
        else:
            progress += left / (kind.phases[index].share * total_hours)
            left = 0.0
    finished = index >= len(kind.phases)
    return replace(matter, phase_index=index, phase_progress=progress), finished, done


def resolve(
    matter: Matter,
    prep: float,
    u: float,
    people: Mapping[int, Person],
    data: GameData,
    balance: Balance,
    shortfall: float = 0.0,
) -> tuple[Outcome, float]:
    """The outcome and its quality (1-20) for a matter at its end (spec 7.6). `shortfall`
    (PT-M7b): the deal's driver index below 1, which lowers its chance to close."""
    kind = data.market.kinds[matter.kind]
    out = balance.outcomes
    crisis_k = balance.macro.crisis.close_k
    craft_mean = matter.craft_hours / matter.craft_weight if matter.craft_weight > 0 else 10.0
    if kind.outcome == "case":
        lead = people.get(matter.lead_id) if matter.lead_id is not None else None
        bm = lead.hidden["big_moments"] if lead is not None else 10.0
        q = fx.case_quality(craft_mean, prep, bm, out)
        return (
            "won" if u < fx.p_win(q, matter.opposing_quality, matter.merits, out) else "lost"
        ), q
    if kind.outcome == "deal":
        q = craft_mean - out.prep * max(0.0, 1.0 - prep)
        p = fx.p_close(q, matter.critical, out, crisis_k * shortfall)  # PT-M7b
        return ("closed" if u < p else "collapsed"), q
    return "done", craft_mean


def outcome_points(matter: Matter, outcome: Outcome, quality: float, balance: Balance) -> float:
    cfg = balance.relationships
    if outcome in ("won", "closed"):
        pts = cfg.win
    elif outcome == "lost":
        pts = cfg.loss
    elif outcome == "collapsed":
        pts = cfg.loss / 2
    elif outcome == "done":
        pts = cfg.win if quality >= QUALITY_GOOD else cfg.loss if quality <= QUALITY_POOR else 0.0
    else:
        pts = 0.0
    return pts * (cfg.critical_mult if matter.critical else 1.0)


def close_matter(
    market: MarketState,
    matter: Matter,
    outcome: Outcome,
    quality: float,
    turn: int,
    balance: Balance,
    points: float | None = None,
) -> tuple[MarketState, LogItem]:
    """`points` (PT-M7b): the relationship's move, when not the outcome's (a pulled deal)."""
    closed = replace(
        matter,
        status="closed",
        outcome=outcome,
        quality=quality,
        closed_turn=turn,
        settlement=None,
        team=matter.team,
    )
    market = with_matter(market, closed)
    if points is None:
        points = outcome_points(matter, outcome, quality, balance)
    market = bump(market, matter.client_id, matter.firm_id, points)
    item = inbox_item(
        turn,
        matter.firm_id,
        "matter_closed",
        link_kind="matter",
        link_id=matter.id,
        matter=matter.name,
        result=outcome,
    )
    return market, item


def matter_month(
    state: GameState,
    matter: Matter,
    records: list[HoursRecord],
    leads: Mapping[int, int],
    rng: RngFactory,
    data: GameData,
    balance: Balance,
) -> tuple[MarketState, list[LogItem]]:
    turn = state.turn
    market = state.market
    gen = rng.stream(turn, "matter", matter.id)
    u = [float(x) for x in gen.random(DRAWS)]
    logs: list[LogItem] = []
    kind = data.market.kinds[matter.kind]
    if matter.court is not None and matter.judge_id is None:
        matter = assign_judge(matter, market, u[U_JUDGE], data, balance)
    judge = market.judge(matter.judge_id) if matter.judge_id is not None else None
    people = {p.id: p for p in state.people}
    appearances = {(a.person_id, a.judge_id): a.tenths for a in market.appearances}
    phase_tasks = kind.phases[min(matter.phase_index, len(kind.phases) - 1)].tasks
    hours_factor = tech_hours(state, matter.firm_id, data, balance).factor(phase_tasks)
    team = team_month(
        matter, records, people, judge, appearances, turn, leads, data, balance, hours_factor
    )
    phase_key = kind.phases[min(matter.phase_index, len(kind.phases) - 1)].key
    worked = sum(r.tenths for r in records)
    matter = replace(
        matter,
        worked_tenths=matter.worked_tenths + worked,
        wip_cents=matter.wip_cents + sum(r.value_cents for r in records),
        craft_hours=matter.craft_hours + team.craft * team.hours,
        craft_weight=matter.craft_weight + team.hours,
    )
    # PT-M10: courts slowed by a dated shock (2020): an open case's planned duration grows
    if matter.court is not None and docket_slowed(
        data.macro, turn_to_ym(turn, state.save_meta.start_ym)
    ):
        matter = replace(matter, planned_months=matter.planned_months + 1)
    # pace and deadlines
    pace = matter.hours_needed_tenths / max(1, matter.planned_months) * hours_factor  # PT-M14
    if worked < balance.progress.under_pace * pace:
        matter = replace(matter, under_months=matter.under_months + 1)
        if (
            matter.kind in ("case", "filing")
            and u[U_DEADLINE] < balance.errors.deadline_miss_bp / 10000
        ):
            matter = replace(
                matter,
                missed_deadlines=matter.missed_deadlines + 1,
                errors_escaped=matter.errors_escaped + 1,
            )
            market = bump(
                market, matter.client_id, matter.firm_id, balance.relationships.missed_deadline
            )
            logs.append(
                inbox_item(
                    turn,
                    matter.firm_id,
                    "deadline_missed",
                    link_kind="matter",
                    link_id=matter.id,
                    matter=matter.name,
                )
            )
    # errors
    if worked > 0:
        p_err = fx.error_chance(team.skill, team.strain_mult, team.cowboy, team.shortfall, balance)
        if u[U_ERROR] < p_err:
            if u[U_CATCH] < balance.errors.catch_bp / 10000 * team.supervision:
                rework = round(matter.hours_needed_tenths * balance.errors.rework_share)
                matter = replace(
                    matter,
                    errors_caught=matter.errors_caught + 1,
                    hours_needed_tenths=matter.hours_needed_tenths + rework,
                )
            else:
                matter = replace(matter, errors_escaped=matter.errors_escaped + 1)
                if judge is not None:
                    sanctions = 1.0 + balance.judges.sanctions * judge_factor(
                        judge, "sanctions_strictness"
                    )
                    market = bump(
                        market,
                        matter.client_id,
                        matter.firm_id,
                        balance.relationships.escaped_error * sanctions,
                    )
    # appearances before the judge
    if judge is not None and phase_key in APPEARANCE_PHASES:
        seen = dict(appearances)
        for r in records:
            seen[(r.person_id, judge.id)] = seen.get((r.person_id, judge.id), 0) + r.tenths
        market = replace(
            market,
            appearances=tuple(
                Appearance(person_id=p, judge_id=j, tenths=t) for (p, j), t in sorted(seen.items())
            ),
        )
    # progress
    matter, finished, done = advance_phases(matter, team.output, kind)
    outcome: Outcome | None = None
    quality = 0.0
    if kind.outcome == "case" and "motions" in done and not finished:
        sj = (
            balance.judges.summary_judgment_bp
            / 10000
            * (1.0 + balance.judges.summary_judgment * judge_factor(judge, "summary_judgment"))
        )
        if judge is not None and u[U_SJ] < sj:
            outcome, quality = resolve(matter, 1.0, u[U_OUTCOME], people, data, balance)
    due = matter.opened_turn + matter.planned_months + balance.matters.max_slip_months
    # PT-M7b: a deal's driver index below 1 (the crisis) lowers its chance to close
    shortfall = (
        driver_shortfall(
            data.practice(matter.practice), turn_to_ym(turn, state.save_meta.start_ym), data
        )
        if kind.outcome == "deal"
        else 0.0
    )
    if outcome is None and finished:
        outcome, quality = resolve(matter, 1.0, u[U_OUTCOME], people, data, balance, shortfall)
    elif outcome is None and turn >= due and kind.outcome in ("case", "deal"):
        prep = _completed(matter, kind)
        outcome, quality = resolve(matter, prep, u[U_OUTCOME], people, data, balance, shortfall)
    collapse_points: float | None = None
    if outcome is None and shortfall > 0:
        # ... and may collapse it in progress (stream `deal_collapse`): the client pulls the
        # deal, which costs the firm the rest of its fees but not the relationship
        hazard = balance.macro.crisis.collapse_month_bp / 10000 * shortfall
        if float(rng.stream(turn, "deal_collapse", matter.id).random()) < hazard:
            outcome, collapse_points = "collapsed", 0.0
            quality = matter.craft_hours / matter.craft_weight if matter.craft_weight > 0 else 10.0
    # settlement offers (cases): the other side's view of our expected recovery
    if outcome is None and matter.kind in CASE_KINDS and matter.stakes_cents > 0:
        if matter.settlement is not None and turn > matter.settlement.expires_turn:
            matter = replace(matter, settlement=None)
        if matter.settlement is None and phase_key in SETTLEMENT_PHASES:
            cfg = balance.judges
            mult = max(
                cfg.settlement_floor,
                1.0
                + cfg.settlement * judge_factor(judge, "settlement_pressure")
                - cfg.trial * judge_factor(judge, "trial_appetite"),
            )
            if u[U_SETTLE] < balance.settlement.base_bp / 10000 * mult:
                q = fx.case_quality(
                    matter.craft_hours / matter.craft_weight if matter.craft_weight > 0 else 10.0,
                    1.0,
                    10.0,
                    balance.outcomes,
                )
                noise = balance.settlement.view_sd * (2.0 * u[U_VIEW] - 1.0)
                view = fx.sigmoid(
                    balance.outcomes.case_k * (q - matter.opposing_quality) + matter.merits + noise
                )
                fraction = round(view * balance.settlement.discount * 10000)
                matter = replace(
                    matter,
                    settlement=SettlementOffer(
                        fraction_bp=fraction,
                        made_turn=turn,
                        expires_turn=turn + balance.settlement.window_turns,
                    ),
                )
                logs.append(
                    inbox_item(
                        turn,
                        matter.firm_id,
                        "settlement_offer",
                        link_kind="matter",
                        link_id=matter.id,
                        matter=matter.name,
                        offer_cents=matter.stakes_cents * fraction // 10000,
                    )
                )
    if outcome is not None:
        market, item = close_matter(
            market, matter, outcome, quality, turn, balance, collapse_points
        )
        logs.append(item)
    else:
        market = with_matter(market, matter)
    return market, logs


def _completed(matter: Matter, kind: KindDef) -> float:
    done = sum(p.share for p in kind.phases[: matter.phase_index])
    if matter.phase_index < len(kind.phases):
        done += kind.phases[matter.phase_index].share * matter.phase_progress
    return min(1.0, done)


def settle(
    market: MarketState,
    matter: Matter,
    turn: int,
    balance: Balance,
    data: GameData,
    people: Mapping[int, Person],
) -> tuple[MarketState, LogItem]:
    """The client accepts the pending offer: the case ends settled; the relationship moves by
    the offer against the case's true expected recovery (hidden)."""
    assert matter.settlement is not None
    craft_mean = matter.craft_hours / matter.craft_weight if matter.craft_weight > 0 else 10.0
    lead = people.get(matter.lead_id) if matter.lead_id is not None else None
    bm = lead.hidden["big_moments"] if lead is not None else 10.0
    q = fx.case_quality(craft_mean, 1.0, bm, balance.outcomes)
    true_p = fx.p_win(q, matter.opposing_quality, matter.merits, balance.outcomes)
    gain = matter.settlement.fraction_bp / 10000 - true_p
    closed = replace(
        matter, status="closed", outcome="settled", quality=q, closed_turn=turn, settlement=None
    )
    market = with_matter(market, closed)
    mult = balance.relationships.critical_mult if matter.critical else 1.0
    market = bump(
        market, matter.client_id, matter.firm_id, balance.relationships.settle * gain * mult
    )
    item = inbox_item(
        turn,
        matter.firm_id,
        "matter_closed",
        link_kind="matter",
        link_id=matter.id,
        matter=matter.name,
        result="settled",
    )
    return market, item


def surface_hidden_conflicts(
    state: GameState, rng: RngFactory, balance: Balance, data: GameData
) -> tuple[MarketState, list[LogItem]]:
    market = state.market
    logs: list[LogItem] = []
    for m in [x for x in market.matters if x.is_open and x.hidden_conflict]:
        u = float(rng.stream(state.turn, "conflict", m.id).random())
        # PT-M8 (spec 9.1): the firm's general counsel catches conflicts before they surface
        gc = 1.0 - balance.seats.effects.gc_conflicts * seat_effect(
            state, m.firm_id, "general_counsel", balance, data
        )
        if u >= gc * balance.conflicts.hidden_surface_bp / 10000:
            continue
        closed = replace(
            m, status="closed", outcome="disqualified", closed_turn=state.turn, settlement=None
        )
        market = with_matter(market, closed)
        for cid in (m.client_id, m.adverse_client_id):
            if cid is not None:
                market = bump(market, cid, m.firm_id, balance.relationships.disqualified)
        logs.append(
            inbox_item(
                state.turn,
                m.firm_id,
                "matter_disqualified",
                link_kind="matter",
                link_id=m.id,
                matter=m.name,
            )
        )
    return market, logs


def relationships_month(
    state: GameState,
    firm_id: int,
    records: tuple[HoursRecord, ...],
    unserved: Mapping[tuple[int, str], float],
    data: GameData,
    balance: Balance,
) -> MarketState:
    """Monthly moves (spec 7.2): fees, drift toward drift_to, service, team strain, the
    relationship partner's client care and cross-practice breadth."""
    cfg = balance.relationships
    market = state.market
    people = {p.id: p for p in state.people}
    staff = set(state.staff_ids(firm_id))
    fees: dict[int, int] = {}
    strain_h: dict[int, tuple[float, float]] = {}
    for r in records:
        fees[r.client_id] = fees.get(r.client_id, 0) + r.value_cents
        h, s = strain_h.get(r.client_id, (0.0, 0.0))
        strain_h[r.client_id] = (h + r.tenths, s + r.tenths * people[r.person_id].strain)
    moved: dict[tuple[int, int], Relationship] = {}
    for rel in [r for r in market.relationships if r.firm_id == firm_id]:
        client = market.client(rel.client_id)
        drift = cfg.drift * (1.0 - 0.5 * (client.loyalty - 10.0) / 10.0)
        lost_share = unserved.get((rel.client_id, ""), 0.0)
        pts = drift * (cfg.drift_to - rel.score) + cfg.service * lost_share
        h, s = strain_h.get(rel.client_id, (0.0, 0.0))
        if h > 0 and s / h > cfg.strain_at:
            pts += cfg.strain
        partner = people.get(rel.partner_id) if rel.partner_id is not None else None
        if partner is not None and partner.id in staff:
            pts += cfg.care * (partner.skills["client_care"] - 10.0) / 10.0
        pts += min(cfg.breadth_cap, cfg.breadth * max(0, len(rel.practices) - 1))
        window = (*rel.fees, fees.get(rel.client_id, 0))[-FEE_WINDOW:]
        moved[(rel.client_id, rel.firm_id)] = replace(
            rel,
            score=min(100.0, max(0.0, rel.score + pts)),
            lost_share=lost_share,
            fees=window,
        )
    # PT-M18 (T12): the month's moves applied at once, as `with_relationship` one at a time
    # would leave them (the others in their order, every relationship sorted by its key)
    rest = [r for r in market.relationships if (r.client_id, r.firm_id) not in moved]
    merged = sorted([*rest, *moved.values()], key=lambda r: (r.client_id, r.firm_id))
    return replace(market, relationships=tuple(merged))


def credit_origination(
    market: MarketState,
    records: tuple[HoursRecord, ...],
    turn: int,
    start: tuple[int, int],
    firm_id: int,
) -> MarketState:
    """Origination credit (spec 7.2): each hour's standard value goes to the matter's
    originator, or for flow to the client's relationship partner."""
    year = turn_to_ym(turn, start)[0]
    credit: dict[int, int] = {}
    for r in records:
        if r.matter_id is not None:
            m = market.matter(r.matter_id)
            pid = m.originator_id if m is not None else None
        else:
            rel = market.relationship(r.client_id, firm_id)
            pid = rel.partner_id if rel is not None else None
        if pid is not None:
            credit[pid] = credit.get(pid, 0) + r.value_cents
    if not credit:
        return market
    table = {(o.person_id, o.year): o.cents for o in market.originations}
    for pid, cents in credit.items():
        table[(pid, year)] = table.get((pid, year), 0) + cents
    return replace(
        market,
        originations=tuple(
            Origination(person_id=p, year=y, cents=c) for (p, y), c in sorted(table.items())
        ),
    )


def work_month(
    state: GameState,
    firm_id: int,
    rng: RngFactory,
    unserved: Mapping[tuple[int, str], float],
    data: GameData,
    balance: Balance,
) -> tuple[GameState, list[LogItem]]:
    """Phase 5's matter work for one firm, after phase 4 recorded the month's hours."""
    records = state.market.hours
    by_matter: dict[int, list[HoursRecord]] = {}
    for r in records:
        if r.matter_id is not None:
            by_matter.setdefault(r.matter_id, []).append(r)
    leads: dict[int, int] = {}
    for m in state.market.open_matters(firm_id):
        if m.lead_id is not None:
            leads[m.lead_id] = leads.get(m.lead_id, 0) + 1
    logs: list[LogItem] = []
    for m in state.market.open_matters(firm_id):
        current = state.market.matter(m.id)
        assert current is not None
        market, items = matter_month(
            state, current, by_matter.get(m.id, []), leads, rng, data, balance
        )
        state = replace(state, market=market)
        logs.extend(items)
    market, items = surface_hidden_conflicts(state, rng, balance, data)
    state = replace(state, market=market)
    logs.extend(items)
    market = credit_origination(
        state.market, records, state.turn, state.save_meta.start_ym, firm_id
    )
    state = replace(state, market=market)
    state = replace(
        state, market=relationships_month(state, firm_id, records, unserved, data, balance)
    )
    return state, logs
