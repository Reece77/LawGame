"""Disciplinary cases against lawyers (spec 11.4; ADR PT-0017 4; TST 48.3's visible stages).

- **Causes.** Triggered: a padder whose padding came to light (`billing.padding_found`), the
  lead of a matter a surfaced conflict closed, the lead of a matter a claim was noticed on (a
  failure of supervision), a lawyer who misused client money (`trust`). Drawn each month per
  lawyer: a client's complaint (neglect), and misleading the court for a litigator who worked a
  case matter. Each chance is its bp at integrity 10 x exp(slope x (10 - integrity) / 10) x the
  rule-bender and cowboy tags x lax supervision x (1 - weight x the GC's effect) (stream
  `discipline`, one generator a firm a month, triggers first, then lawyers by id).
- **Real people are never subjects** (ADR PT-0013): every draw skips a person flagged real, and
  a trigger naming one opens nothing. A person with an open case gets no second one.
- **Stages** (stream `discipline_case`): complaint, investigation, hearing. The firm answers a
  case once (`RespondCase`): cooperate (culpability x (1 - cooperate_bp)) or contest (the
  firm's lawyers' costs to 6600; culpability falls or rises by contest_bp on a draw).
  Unanswered, the default is to cooperate.
- **Outcome** at the hearing's end: found against the lawyer with chance = culpability (hidden:
  (20 - integrity) / 20 + N(0, sd)), with the sanction of the highest band it reaches;
  otherwise dismissed. A sanction costs the subject morale; reprimand and above are public
  (reputation in their practice); a suspension takes them off billable work until it ends; a
  disbarment ends their time at the firm (a partner leaves through PT-M4's departure,
  "expelled").
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace

import numpy as np

from ptk.sim.data_models import Balance, GameData
from ptk.sim.ledger import AccountCode
from ptk.sim.money import Cents
from ptk.sim.people.models import Person
from ptk.sim.risk import draws as dr
from ptk.sim.risk import formulas as fx
from ptk.sim.risk.common import (
    PROFESSIONAL_FEES,
    Books,
    gc_effect,
    is_partner,
    lawyers,
    lax,
    name,
    practice_of,
    with_risk,
)
from ptk.sim.risk.models import (
    CaseCause,
    CaseChoice,
    CaseOutcome,
    DisciplinaryCase,
    take_id,
    with_case,
)
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState

CASE_MATTERS = frozenset({"case", "investigation"})
PUBLIC = frozenset({"reprimand", "fine", "suspension", "disbarment"})


def jurisdiction(state: GameState, person: Person, data: GameData) -> str:
    from ptk.sim.geo.cities import office_jurisdiction, person_office_id

    firm = state.player.id
    return office_jurisdiction(state, firm, person_office_id(state, firm, person), data)


def chance_mult(state: GameState, person: Person, balance: Balance, data: GameData) -> float:
    """The person's multiplier on every cause's chance (engine-only)."""
    d = balance.risk.discipline
    m = fx.integrity_mult(person.personality["integrity"], d.integrity_slope)
    if "rule_bender" in person.tags:
        m *= d.rule_bender_mult
    if "cowboy" in person.tags:
        m *= d.cowboy_mult
    if lax(state, state.player.id):
        m *= d.lax_mult
    return m * fx.gc_mult(gc_effect(state, state.player.id, balance, data), d.gc_bp)


def open_case(
    state: GameState,
    person_id: int,
    cause: CaseCause,
    gen: np.random.Generator,
    books: Books,
    balance: Balance,
    data: GameData,
    matter_id: int | None = None,
) -> GameState:
    """Open a case unless the person is flagged real or already has an open one."""
    person = state.person(person_id)
    if person.real or any(c.is_open and c.person_id == person_id for c in state.risk.cases):
        return state
    d = balance.risk.discipline
    noise = float(gen.normal(0.0, d.culpability_sd)) if d.culpability_sd > 0 else 0.0
    culpability = min(1.0, max(0.0, (20.0 - person.personality["integrity"]) / 20.0 + noise))
    risk, cid = take_id(state.risk)
    case = DisciplinaryCase(
        id=cid,
        firm_id=books.firm_id,
        person_id=person_id,
        cause=cause,
        jurisdiction=jurisdiction(state, person, data),
        opened_turn=books.turn,
        culpability=culpability,
        stage_until=books.turn + d.stages.complaint.lo,
        matter_id=matter_id,
    )
    books.inbox("case_opened", cid, name=name(person), cause=cause.replace("_", " "))
    return with_risk(state, with_case(risk, case))


def _triggers(
    start: GameState, state: GameState, claims_noticed: list[int]
) -> list[tuple[int, CaseCause, int | None, str]]:
    """(person, cause, matter, key) for the month's triggered chances, in a fixed order."""
    out: list[tuple[int, CaseCause, int | None, str]] = []
    firm = state.player.id
    for pid in sorted(set(state.billing.padding_found) - set(start.billing.padding_found)):
        out.append((pid, "padding", None, "padding_bp"))
    before = {m.id: m.outcome for m in start.market.matters}
    for m in state.market.matters:
        surfaced = m.outcome == "disqualified" and before.get(m.id) != "disqualified"
        if m.firm_id == firm and surfaced and m.lead_id is not None:
            out.append((m.lead_id, "conflicts", m.id, "conflicts_bp"))
    for cid in claims_noticed:
        claim = state.risk.claim(cid)
        if claim is None:
            continue
        cm = state.market.matter(claim.matter_id)
        if cm is not None and cm.lead_id is not None:
            out.append((cm.lead_id, "supervision", cm.id, "supervision_bp"))
    return out


def _litigators(state: GameState) -> set[int]:
    firm = state.player.id
    cases = {m.id for m in state.market.matters if m.firm_id == firm and m.kind in CASE_MATTERS}
    return {h.person_id for h in state.market.hours if h.matter_id in cases and h.tenths > 0}


def home_jurisdiction(state: GameState, data: GameData) -> str:
    scenario = data.scenario(state.save_meta.scenario_id)
    return scenario.home_jurisdiction if scenario is not None else data.jurisdictions[0].key


def conflicts_surfaced(start: GameState, state: GameState) -> bool:
    before = {m.id: m.outcome for m in start.market.matters}
    return any(
        m.firm_id == state.player.id
        and m.outcome == "disqualified"
        and before.get(m.id) != "disqualified"
        for m in state.market.matters
    )


def new_cases(
    start: GameState,
    state: GameState,
    gen: np.random.Generator,
    books: Books,
    balance: Balance,
    data: GameData,
    claims_noticed: list[int],
) -> GameState:
    d = balance.risk.discipline
    staff = set(state.staff_ids(books.firm_id))
    for pid, cause, matter_id, key in _triggers(start, state, claims_noticed):
        u = float(gen.random())
        if pid not in staff or state.person(pid).real:
            continue
        p = getattr(d.causes, key) / fx.BP * chance_mult(state, state.person(pid), balance, data)
        if u < min(1.0, p):
            state = open_case(state, pid, cause, gen, books, balance, data, matter_id)
    court = _litigators(state)
    for person in lawyers(state, books.firm_id, data):
        u = float(gen.random())
        if person.real:
            continue
        base = d.causes.neglect + (d.causes.court if person.id in court else 0)
        p = base / fx.BP * chance_mult(state, person, balance, data)
        if u < p:
            drawn: CaseCause = (
                "court"
                if person.id in court and u < p * d.causes.court / max(1, base)
                else "neglect"
            )
            state = open_case(state, person.id, drawn, gen, books, balance, data)
    return state


# --- A case's month ---------------------------------------------------------------------------


def respond(
    state: GameState, case: DisciplinaryCase, choice: CaseChoice, books: Books, balance: Balance
) -> GameState:
    if choice == "contest":
        books.pay(
            PROFESSIONAL_FEES, balance.risk.discipline.contest_cents, f"Defence of case {case.id}"
        )
    return with_risk(state, with_case(state.risk, replace(case, choice=choice)))


def _sanction(culpability: float, balance: Balance) -> CaseOutcome:
    band = balance.risk.discipline.outcomes[0].key
    for o in balance.risk.discipline.outcomes:
        if culpability >= o.min:
            band = o.key
    return band


def _leave(
    state: GameState,
    person: Person,
    gen: np.random.Generator,
    balance: Balance,
    data: GameData,
    balances: Mapping[tuple[int, AccountCode], Cents],
    books: Books,
) -> GameState:
    e = state.employment_of(person.id)
    if e is None or e.status == "ended":
        return state
    if is_partner(person) and state.partnership.of(e.firm_id) is not None:
        from ptk.sim.interfaces import partner_flight

        res = partner_flight().depart(
            state,
            person.id,
            None,
            "expelled",
            draws=lambda: gen,
            balance=balance,
            data=data,
            balances=balances,
        )
        books.entries.extend(res.entries)
        books.logs.extend(res.log)
        return res.state
    from ptk.sim.state import with_employment

    return with_employment(
        state, replace(e, status="notice", end_turn=books.turn + 1, end_reason="fired")
    )


def case_month(
    state: GameState,
    case: DisciplinaryCase,
    rng: RngFactory,
    books: Books,
    balance: Balance,
    data: GameData,
    balances: Mapping[tuple[int, AccountCode], Cents],
) -> GameState:
    from ptk.sim.reputation.formulas import apply_pulse
    from ptk.sim.state import with_person_states

    d = balance.risk.discipline
    turn = books.turn
    if case.stage_until is None or turn < case.stage_until:
        return state
    gen = dr.case_month(rng, turn, case.id)
    u = [float(x) for x in gen.random(3)]
    if case.stage == "complaint":
        case = replace(
            case, stage="investigation", stage_until=turn + fx.span(u[0], d.stages.investigation)
        )
    elif case.stage == "investigation":
        case = replace(case, stage="hearing", stage_until=turn + fx.span(u[0], d.stages.hearing))
    elif case.stage == "hearing":
        choice = case.choice or "cooperate"
        cul = case.culpability
        if choice == "cooperate":
            cul *= 1.0 - d.cooperate_bp / fx.BP
        else:
            cul *= 1.0 - d.contest_bp / fx.BP if u[2] < 0.5 else 1.0 + d.contest_bp / fx.BP
        cul = min(1.0, cul)
        person = state.person(case.person_id)
        if u[1] >= cul:
            case = replace(
                case, stage="closed", outcome="dismissed", closed_turn=turn, choice=choice
            )
        else:
            outcome = _sanction(cul, balance)
            until = turn + fx.span(u[0], d.suspension_months) if outcome == "suspension" else None
            case = replace(
                case,
                stage="closed",
                outcome=outcome,
                closed_turn=turn,
                choice=choice,
                suspended_until=until,
            )
            ps = state.person_state(person.id)
            if ps.morale is not None:
                state = with_person_states(
                    state, [replace(ps, morale=max(0.0, ps.morale + d.morale_points))]
                )
            if outcome in PUBLIC:
                state = apply_pulse(
                    state,
                    books.firm_id,
                    d.public_points,
                    "a disciplinary sanction",
                    balance,
                    practice_of(person, data) or None,
                )
            if outcome == "disbarment":
                state = _leave(state, person, gen, balance, data, balances, books)
        books.inbox(
            "case_closed",
            case.id,
            name=name(person),
            outcome=case.outcome or "dismissed",
            months=0 if case.suspended_until is None else case.suspended_until - turn,
        )
    return with_risk(state, with_case(state.risk, case))


def cases_month(
    state: GameState,
    rng: RngFactory,
    books: Books,
    balance: Balance,
    data: GameData,
    balances: Mapping[tuple[int, AccountCode], Cents],
) -> GameState:
    for case in [c for c in state.risk.cases if c.firm_id == books.firm_id and c.is_open]:
        if case.choice is None and case.stage != "hearing" and turn_due(case, books.turn, balance):
            state = respond(state, case, "cooperate", books, balance)
            case = state.risk.case(case.id) or case
        state = case_month(state, case, rng, books, balance, data, balances)
    return state


def turn_due(case: DisciplinaryCase, turn: int, balance: Balance) -> bool:
    """The firm's window to answer has passed: the default answer (cooperate) is taken."""
    return turn >= case.opened_turn + balance.risk.discipline.window
