"""Turn-phase steps for hiring, pay, payroll, morale and departures (spec 4.1, 5.3-5.7).

Ported from backend/tst/sim/hiring/phases.py @ 02fba2aa (Tech Startup Tycoon); changed:
firms; campus offers sign a year ahead and the class starts the September after (spec 5.7);
payroll posts to Partner Track's accounts (5000 associates and counsel, 5020 income partners,
5100 staff, 5200 benefits, 6000 rent per head, 6200 recruiting) with December bonuses to 5010;
associates are paid on the firm's scale (phase 9 raises them, never cuts); morale reads
Partner Track's terms (spec 5.3) and resignation its bonus timing; candidate pools by lateral
channel and, in April, the campus pools (stream `campus`); summer months scout the summer
associates; no rivals, options, offices, divisions, free agents, relocation or retirement.
PT-M6: event modifiers multiply a person's morale target (ptk.sim.events.modifiers).
PT-M17: the player's recruiting term on offers and their resignation factor (persona,
foundation, bar politics; `ptk.sim.interfaces`).

Each step is pure: state (plus the turn's generators) in; new state, ledger entries and log
items out. People are processed in ascending id order; every random draw comes from its
own stream keyed by the entity it belongs to (ADR-0013).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Final

import numpy as np

from ptk.sim.calendar import MONTHS_PER_YEAR, YearMonth, format_turn, turn_to_ym
from ptk.sim.data_models import Balance, GameData
from ptk.sim.events.modifiers import person_factor
from ptk.sim.hiring.formulas import (
    ROLL_RANGE,
    acceptance_probability,
    benefits_cents,
    bonus_fairness_shock,
    hours_term,
    interest_term,
    is_lowball,
    monthly_salary_cents,
    morale_noise_sd,
    morale_step,
    morale_target,
    offer_score,
    pay_term,
    prospects_term,
    recruiter_fee_cents,
    rent_cents,
    resignation_bp,
    roll_succeeds,
)
from ptk.sim.hiring.models import (
    ONE_BATCH,
    Candidate,
    CandidateStatus,
    OfferStatus,
    PersonState,
    Search,
)
from ptk.sim.hiring.pay import (
    firm_pay_cents,
    firm_scale_cents,
    market_bonus_cents,
    market_pay_cents,
    on_scale,
    policy_pay_cents,
    prorated,
)
from ptk.sim.hiring.rules import (
    campus_start_turn,
    favoured_interests,
    offer_pitch,
    prestige,
)
from ptk.sim.interfaces import (
    founder_recruiting_term,
    founder_resign_mult,
    has_sponsor,
    manager_morale_term,
    seat_effect,
)
from ptk.sim.ledger import (
    BENEFITS,
    BONUSES,
    CASH,
    INCOME_PARTNER_SALARIES,
    RECRUITING,
    RENT,
    SALARIES,
    STAFF_SALARIES,
    AccountCode,
    LedgerEntry,
    LedgerLine,
)
from ptk.sim.log import LogItem, inbox_item
from ptk.sim.macro import lateral_heat
from ptk.sim.matters.pro_bono import morale_term as pro_bono_morale
from ptk.sim.money import Cents, pct_of
from ptk.sim.people.generator import generate_person, people_gen_stream, weighted_pick
from ptk.sim.people.models import Employment, Person, RevealState, WorkMonth
from ptk.sim.people.reveal import apply_knowledge_action, new_reveal_state
from ptk.sim.people.strain import burnout_effects_active
from ptk.sim.rng import RngFactory
from ptk.sim.state import (
    GameState,
    with_candidates,
    with_employment,
    with_offer,
    with_people,
    with_person_states,
    with_reveals,
    with_search,
)

JOB_HOPPER: Final = "job_hopper"
LIFER: Final = "lifer"
MORALE_TARGET: Final = "morale_target"  # PT-M6: an event modifier's stat
INCOME_PARTNER: Final = "income_partner"
EQUITY_PARTNER: Final = "equity_partner"
STAFF_KINDS: Final = frozenset({"paralegal", "business_services"})
SCOUTING: Final = "scouting_month"
TENTHS_PER_HOUR: Final = 10  # tunable-exempt: hours are integer tenths (ADR PT-0005)


def _name(person: Person) -> str:
    return f"{person.first_name} {person.last_name}"


def _ym(state: GameState) -> YearMonth:
    return turn_to_ym(state.turn, state.save_meta.start_ym)


def _role_label(person: Person, data: GameData) -> str:
    return data.role(person.role).label


def _level_label(level: str) -> str:
    return level.replace("_", " ").replace("associate ", "class-year-")


def _employees(state: GameState) -> list[tuple[Employment, Person]]:
    """Staff (active or notice) who are not founding partners, by person id."""
    pairs = []
    for e in state.employments:
        if e.counts_as_staff:
            person = state.person(e.person_id)
            if not person.founding_partner:
                pairs.append((e, person))
    return sorted(pairs, key=lambda pair: pair[1].id)


# --- Phase 1: notices end, offers resolve, signed classes start ------------------------------


def end_notices(state: GameState) -> tuple[GameState, tuple[LogItem, ...]]:
    """Notice employments become ended in phase 1 of their end_turn (TST 10)."""
    logs = []
    for e in state.employments:
        if e.status == "notice" and e.end_turn is not None and e.end_turn <= state.turn:
            state = with_employment(state, replace(e, status="ended"))
            logs.append(
                inbox_item(
                    state.turn,
                    e.firm_id,
                    "employee_left",
                    name=_name(state.person(e.person_id)),
                    reason=e.end_reason or "left",
                )
            )
    return state, tuple(logs)


def _hire(
    state: GameState, person: Person, firm_id: int, salary: Cents, balance: Balance
) -> GameState:
    """Employ a person from this turn, at new-hire morale, with their profile known."""
    hire = Employment(
        id=state.next_id("employment"),
        person_id=person.id,
        firm_id=firm_id,
        start_turn=state.turn,
        salary_cents=salary,
    )
    state = with_employment(state, hire)
    ps = state.person_state(person.id)
    state = with_person_states(state, [replace(ps, morale=balance.morale.new_hire)])
    # Working together shows interests and work style (TST M1c review): reveal them at hire.
    reveal = state.reveal(firm_id, person.id)
    if reveal is not None and reveal.profile_revealed_turn is None:
        state = with_reveals(state, [replace(reveal, profile_revealed_turn=state.turn)])
    return state


def resolve_offers(
    state: GameState, rng: RngFactory, balance: Balance, data: GameData
) -> tuple[GameState, tuple[LedgerEntry, ...], tuple[LogItem, ...]]:
    """Pending offers resolve in offer-id order (stream hiring, key offer id; TST 7). A lateral
    joins at once; a campus hire signs for next September (spec 5.7)."""
    entries: list[LedgerEntry] = []
    logs: list[LogItem] = []
    hiring = balance.hiring
    for offer in [o for o in state.offers if o.status == "pending"]:
        candidate = state.candidate(offer.candidate_id)
        person = state.person(offer.candidate_id)
        ask = candidate.ask_cents if candidate is not None else offer.salary_cents
        # money-exact: ratio
        ratio = offer.salary_cents / ask
        draw = float(rng.stream(state.turn, "hiring", offer.id).random())
        accepted = False
        if candidate is not None and candidate.status == "open" and not is_lowball(ratio, hiring):
            score = offer_score(
                ratio=ratio,
                matching_interests=favoured_interests(person, data, balance),
                risk_appetite=person.personality["risk_appetite"],
                offer=hiring.offer,
                prestige=prestige(state, offer.firm_id, balance),
                pitch=offer_pitch(state, offer.actor_id, balance)
                + founder_recruiting_term(state, offer.firm_id, balance),  # PT-M17
            )
            accepted = draw < acceptance_probability(score, hiring.offer)
        status: OfferStatus = "accepted" if accepted else "declined"
        campus = candidate is not None and candidate.channel == "campus"
        start = (
            campus_start_turn(state.turn, state.save_meta.start_ym, balance)
            if campus and accepted
            else state.turn
        )
        state = with_offer(
            state, replace(offer, status=status, resolved_turn=state.turn, start_turn=start)
        )
        if candidate is not None:
            cand_status: CandidateStatus = (
                ("signed" if campus else "hired") if accepted else "declined"
            )
            state = with_candidates(
                state, [replace(candidate, status=cand_status, resolved_turn=state.turn)]
            )
        if not accepted:
            logs.append(
                inbox_item(
                    state.turn,
                    offer.firm_id,
                    "offer_declined",
                    link_kind="candidate",
                    link_id=person.id,
                    name=_name(person),
                    role=_role_label(person, data),
                )
            )
            continue
        if campus:
            logs.append(
                inbox_item(
                    state.turn,
                    offer.firm_id,
                    "campus_offer_accepted",
                    link_kind="candidate",
                    link_id=person.id,
                    name=_name(person),
                    role=_role_label(person, data),
                    class_year=turn_to_ym(start, state.save_meta.start_ym)[0],
                    start_label=format_turn(start, state.save_meta.start_ym),
                )
            )
            continue
        state = _hire(state, person, offer.firm_id, offer.salary_cents, balance)
        if candidate is not None and candidate.channel == "recruiter":
            fee = recruiter_fee_cents(offer.salary_cents, person.level, hiring)
            if fee:
                entries.append(
                    LedgerEntry.transfer(
                        turn=state.turn,
                        firm_id=offer.firm_id,
                        memo=f"Recruiter fee: {_name(person)}",
                        debit=RECRUITING,
                        credit=CASH,
                        amount=fee,
                    )
                )
        logs.append(
            inbox_item(
                state.turn,
                offer.firm_id,
                "offer_accepted",
                link_kind="person",
                link_id=person.id,
                name=_name(person),
                level=_level_label(person.level),
                role=_role_label(person, data),
                salary_cents=offer.salary_cents,
            )
        )
    return state, tuple(entries), tuple(logs)


def start_signed(
    state: GameState, balance: Balance, data: GameData
) -> tuple[GameState, tuple[LogItem, ...]]:
    """A signed campus class starts in phase 1 of its start turn, on the firm's scale salary
    for that year (or the offer's, if higher)."""
    logs = []
    ym = _ym(state)
    for offer in state.offers:
        if offer.status != "accepted" or offer.start_turn != state.turn:
            continue
        candidate = state.candidate(offer.candidate_id)
        if candidate is None or candidate.status != "signed":
            continue
        person = state.person(offer.candidate_id)
        policy = state.firm(offer.firm_id).pay_policy
        salary = max(offer.salary_cents, firm_scale_cents(data, ym, person.level, policy))
        state = with_candidates(state, [replace(candidate, status="hired")])
        state = _hire(state, person, offer.firm_id, salary, balance)
        logs.append(
            inbox_item(
                state.turn,
                offer.firm_id,
                "class_started",
                link_kind="person",
                link_id=person.id,
                name=_name(person),
                role=_role_label(person, data),
                salary_cents=salary,
            )
        )
    return state, tuple(logs)


# --- Phase 6: payroll and operating costs ----------------------------------------------------


def salary_account(level: str, balance: Balance) -> AccountCode | None:
    """5000 associates, counsel and trainees; 5020 income partners; 5100 paralegals and
    business services; equity partners take no salary (ADR PT-0003)."""
    if level == EQUITY_PARTNER:
        return None
    if level == INCOME_PARTNER:
        return INCOME_PARTNER_SALARIES
    if balance.people.levels[level].kind in STAFF_KINDS:
        return STAFF_SALARIES
    return SALARIES


@dataclass(frozen=True, slots=True)
class CostLine:
    label: str
    account: AccountCode
    amount: Cents


def monthly_cost_lines(
    state: GameState, firm_id: int, balance: Balance, data: GameData
) -> tuple[CostLine, ...]:
    """One firm's phase-6 costs this month (before December bonuses). The Overview shows the
    same lines as this month's payroll projection (TST 8 pattern)."""
    by_account: dict[AccountCode, Cents] = {}
    benefits = 0
    heads = 0
    lawyers = 0
    for e in state.staff(firm_id):
        heads += 1
        person = state.person(e.person_id)
        lawyers += data.role(person.role).kind == "lawyer"
        account = salary_account(person.level, balance)
        if account is None or e.salary_cents <= 0:
            continue
        monthly = monthly_salary_cents(e.salary_cents)
        by_account[account] = by_account.get(account, 0) + monthly
        benefits += benefits_cents(monthly, balance.pay)
    firm = state.firm(firm_id)
    job_posts = sum(
        1
        for s in state.searches
        if s.firm_id == firm_id and s.status == "open" and s.channel == "job_post"
    )
    summer = _summer_pay_cents(state, firm_id, balance, data)
    lines = [
        CostLine("Associate and counsel salaries", SALARIES, by_account.get(SALARIES, 0)),
        CostLine(
            "Income-partner salaries",
            INCOME_PARTNER_SALARIES,
            by_account.get(INCOME_PARTNER_SALARIES, 0),
        ),
        CostLine("Staff salaries", STAFF_SALARIES, by_account.get(STAFF_SALARIES, 0)),
        CostLine("Benefits", BENEFITS, benefits),
        CostLine("Rent", RENT, _office_rent(state, firm_id, heads, balance, data)),
        *overhead_lines(lawyers, firm.home_city, balance),
        CostLine("Job posts", RECRUITING, balance.hiring.job_post_cost_cents * job_posts),
        CostLine("Summer programme", RECRUITING, summer),
    ]
    return tuple(lines)


OVERHEAD_LINES: Final = (
    ("Support staff", STAFF_SALARIES, "support_staff"),
    ("Technology", "6100_technology", "technology"),
    ("Insurance", "6300_insurance", "insurance"),
    ("General and administrative", "6900_general_admin", "general_admin"),
)


def overhead_lines(lawyers: int, city: str, balance: Balance) -> tuple[CostLine, ...]:
    """PT-M7: each lawyer on the books carries a month's overhead (pay.overhead_per_lawyer_cents,
    by the city's pay band)."""
    pay = balance.pay
    return tuple(
        CostLine(
            label, account, lawyers * pct_of(pay.overhead_per_lawyer_cents[key], pay.city(city))
        )
        for label, account, key in OVERHEAD_LINES
    )


def _summer_pay_cents(state: GameState, firm_id: int, balance: Balance, data: GameData) -> Cents:
    """Summer associates are paid summer_pay_bp of a first-year's monthly scale salary in each
    summer month (6200)."""
    campus = balance.campus
    ym = _ym(state)
    if not campus.summer_months.lo <= ym[1] <= campus.summer_months.hi:
        return 0
    summers = sum(
        1
        for c in state.candidates
        if c.firm_id == firm_id and c.channel == "campus" and c.status == "open"
    )
    if not summers:
        return 0
    policy = state.firm(firm_id).pay_policy
    monthly = monthly_salary_cents(firm_scale_cents(data, ym, campus.level, policy))
    return summers * pct_of(monthly, campus.summer_pay_bp)


def bonus_cents(
    state: GameState, e: Employment, person: Person, balance: Balance, data: GameData
) -> tuple[Cents, Cents]:
    """(paid, market) year-end bonus for one person: the market's by class year (or the
    level's discretionary share), associates' times the firm's policy, prorated by months
    employed in the year. Notice employments and equity partners get none (spec 5.4)."""
    if e.status != "active" or person.level == EQUITY_PARTNER or e.salary_cents <= 0:
        return 0, 0
    year, month = _ym(state)
    first = state.turn - (month - 1)  # January's turn
    months = state.turn - max(e.start_turn, first) + 1
    market = prorated(
        market_bonus_cents(data, balance, person.level, year, e.salary_cents),
        months,
        MONTHS_PER_YEAR,
    )
    if on_scale(person.level):
        return policy_pay_cents(market, state.firm(e.firm_id).pay_policy), market
    return market, market


def payroll(
    state: GameState, balance: Balance, data: GameData
) -> tuple[tuple[LedgerEntry, ...], tuple[LogItem, ...]]:
    """Phase 6: each firm's costs in one entry, and December's bonuses in another."""
    entries: list[LedgerEntry] = []
    logs: list[LogItem] = []
    december = _ym(state)[1] == balance.pay.bonus_month
    for firm in state.firms:
        costs = [c for c in monthly_cost_lines(state, firm.id, balance, data) if c.amount]
        total = sum(c.amount for c in costs)
        if total:
            entries.append(
                LedgerEntry(
                    turn=state.turn,
                    firm_id=firm.id,
                    memo="Monthly costs: " + ", ".join(c.label for c in costs),
                    lines=(
                        *(LedgerLine(c.account, c.amount) for c in costs),
                        LedgerLine(CASH, -total),
                    ),
                )
            )
        if not december:
            continue
        paid = 0
        count = 0
        for e in state.staff(firm.id):
            amount, _market = bonus_cents(state, e, state.person(e.person_id), balance, data)
            if amount:
                paid += amount
                count += 1
        if paid:
            entries.append(
                LedgerEntry.transfer(
                    turn=state.turn,
                    firm_id=firm.id,
                    memo=f"Year-end bonuses ({count})",
                    debit=BONUSES,
                    credit=CASH,
                    amount=paid,
                )
            )
            pct = firm.pay_policy.pct_bp
            policy = (
                "in line with" if pct == 10_000 else "below" if pct < 10_000 else "above"
            )  # tunable-exempt: 100%
            logs.append(
                inbox_item(
                    state.turn,
                    firm.id,
                    "bonuses_paid",
                    link_kind="finance",
                    total_cents=paid,
                    count=count,
                    policy=policy,
                )
            )
    return tuple(entries), tuple(logs)


# --- Phase 8: morale, resignations, tag reveals ----------------------------------------------


def hours_ratio(person: Person, work: WorkMonth | None, balance: Balance) -> float | None:
    """Billable hours this month at an annual rate, over the level's billable target. None
    without a month of work recorded, or for a level with no target."""
    target = balance.people.levels[person.level].billable_target_hours
    if work is None or target <= 0:
        return None
    # PT-M7a (spec 7.8): pro bono counts toward the target only as far as the firm credits it
    billable = sum(t for _, t in work.practice_tenths) - work.pro_bono_tenths + work.credited_tenths
    return billable * MONTHS_PER_YEAR / (target * TENTHS_PER_HOUR)


def morale_terms(
    state: GameState,
    e: Employment,
    person: Person,
    work: WorkMonth | None,
    balance: Balance,
    data: GameData,
) -> float:
    """P + interesting work + hours + prospects + the manager term (spec 5.3; TST 9) + pro
    bono (PT-M7a, spec 7.8: real responsibility early)."""
    cfg = balance.morale
    city = state.firm(e.firm_id).home_city
    market = market_pay_cents(data, balance, person.level, _ym(state), city)
    return (
        pay_term(e.salary_cents, market, cfg)
        + interest_term(favoured_interests(person, data, balance), cfg)
        + hours_term(hours_ratio(person, work, balance), cfg)
        + prospects_term(person.level, has_sponsor(state, person.id), cfg)  # PT-M4's sponsors
        + manager_morale_term(state, person.id, balance, data)
        + pro_bono_morale(person.level, work.pro_bono_tenths if work else 0, balance)  # PT-M7a
    )


def month_multiplier(level: str, month: int, balance: Balance) -> float:
    """Bonus timing (spec 5.3): associates and staff leave after January's bonus; income
    partners after the April true-up."""
    table = (
        balance.resign.partner_months
        if level == INCOME_PARTNER
        else balance.resign.associate_months
    )
    return table.get(month, 1.0)


def morale_and_departures(
    state: GameState,
    rng: RngFactory,
    balance: Balance,
    data: GameData,
    work: Mapping[int, WorkMonth],
) -> tuple[GameState, tuple[LogItem, ...]]:
    """Morale (stream morale), then a resignation roll (stream resign) for active employees,
    by person id. Founding partners are excluded; equity partners do not resign here (their
    flight is PT-M4). December adds the bonus-fairness shock (spec 5.3)."""
    logs: list[LogItem] = []
    cfg = balance.morale
    month = _ym(state)[1]
    december = month == balance.pay.bonus_month
    heat = lateral_heat(state.turn, state.save_meta.start_ym, data, balance)  # PT-M7
    moved: list[PersonState] = []
    for employment, person in _employees(state):
        target = morale_target(
            morale_terms(state, employment, person, work.get(person.id), balance, data), cfg
        ) * person_factor(state, person.id, MORALE_TARGET)  # PT-M6: event modifiers
        ps = state.person_state(person.id)
        start = cfg.start if ps.morale is None else ps.morale
        noise = float(
            rng.stream(state.turn, "morale", person.id).normal(
                0.0, morale_noise_sd(person.personality["temperament"], cfg)
            )
        )
        morale = morale_step(start, target, noise, cfg)
        if december:
            paid, market = bonus_cents(state, employment, person, balance, data)
            morale = min(max(morale + bonus_fairness_shock(paid, market, cfg), 0.0), 100.0)
        moved.append(replace(ps, morale=morale))

        if employment.status != "active" or person.level == EQUITY_PARTNER:
            continue
        chance = resignation_bp(
            morale,
            person.personality["loyalty"],
            balance.resign,
            job_hopper=JOB_HOPPER in person.tags,
            lifer=LIFER in person.tags,
            burnout=burnout_effects_active(person, state.turn, balance),
            month_mult=month_multiplier(person.level, month, balance),
            heat=heat * founder_resign_mult(state, employment.firm_id, balance),  # PT-M17
        )
        roll = int(rng.stream(state.turn, "resign", person.id).integers(0, ROLL_RANGE))
        if not roll_succeeds(roll, chance):
            continue
        state = with_employment(
            state,
            replace(employment, status="notice", end_turn=state.turn + 1, end_reason="resigned"),
        )
        logs.append(
            inbox_item(
                state.turn,
                employment.firm_id,
                "resigned",
                link_kind="person",
                link_id=person.id,
                name=_name(person),
            )
        )
    return with_person_states(state, moved), tuple(logs)


def monthly_tag_reveals(
    state: GameState, rng: RngFactory, balance: Balance, data: GameData
) -> tuple[GameState, tuple[LogItem, ...]]:
    """Each hidden tag of an employee reveals to the employer at reveal_bp_per_month
    (stream tags, key person id; one roll per still-hidden tag, in the person's tag order)."""
    logs: list[LogItem] = []
    updated: list[RevealState] = []
    for employment, person in _employees(state):
        reveal = state.reveal(employment.firm_id, person.id)
        if reveal is None or not person.tags:
            continue
        known = {t for t, _ in reveal.revealed_tags}
        hidden = [t for t in person.tags if t not in known]
        if not hidden:
            continue
        gen = rng.stream(state.turn, "tags", person.id)
        found = [
            t
            for t in hidden
            if roll_succeeds(int(gen.integers(0, ROLL_RANGE)), balance.tags.reveal_bp_per_month)
        ]
        if not found:
            continue
        updated.append(
            replace(
                reveal, revealed_tags=reveal.revealed_tags + tuple((t, state.turn) for t in found)
            )
        )
        logs += [
            inbox_item(
                state.turn,
                employment.firm_id,
                "tag_revealed",
                link_kind="person",
                link_id=person.id,
                name=_name(person),
                reveal_text=next(x.reveal_text for x in data.tags if x.key == t),
            )
            for t in found
        ]
    return with_reveals(state, updated), tuple(logs)


# --- Phase 9: the salary scale moves ----------------------------------------------------------


def apply_scale(state: GameState, data: GameData) -> GameState:
    """Associates are paid at least the firm's scale for their class year this month: a new
    year's scale or a September class-year step raises them; nothing ever cuts pay."""
    ym = _ym(state)
    for e in state.employments:
        if not e.counts_as_staff:
            continue
        person = state.person(e.person_id)
        if not on_scale(person.level):
            continue
        scale = firm_scale_cents(data, ym, person.level, state.firm(e.firm_id).pay_policy)
        if scale > e.salary_cents:
            state = with_employment(state, replace(e, salary_cents=scale))
    return state


# --- Phase 12: candidates leave, new batches, the campus season, energy ----------------------


def expire_candidates(state: GameState) -> GameState:
    """Open candidates without a pending offer leave in phase 12 of their expires_turn."""
    expired = [
        replace(c, status="expired", resolved_turn=state.turn)
        for c in state.candidates
        if c.status == "open"
        and c.expires_turn <= state.turn
        and state.pending_offer_for(c.person_id) is None
    ]
    return with_candidates(state, expired)


def ask_cents(
    gen: np.random.Generator,
    person: Person,
    state: GameState,
    firm_id: int,
    balance: Balance,
    data: GameData,
) -> Cents:
    """A candidate's ask: the market's pay for their level in the firm's city, times their
    school tier's share (lawyers), times 1 + Normal(0, noise_sd), in whole $1,000s. Drawn
    last from the person's own generator."""
    ask_cfg = balance.hiring.ask
    market = market_pay_cents(
        data, balance, person.level, _ym(state), state.firm(firm_id).home_city
    )
    if person.school_tier is not None:
        market = pct_of(
            market, ask_cfg.tier_bp.get(person.school_tier, 10_000)
        )  # tunable-exempt: 100%
    factor = max(0.5, 1 + float(gen.normal(0.0, ask_cfg.noise_sd)))  # tunable-exempt: a floor
    step = ask_cfg.round_to_cents
    return max(step, round(market * factor / step) * step)


def _actor(state: GameState, search: Search) -> Person | None:
    return next((p for p in state.people if p.id == search.actor_id), None)


def _jurisdiction(state: GameState, data: GameData) -> str:
    scenario = data.scenario(state.save_meta.scenario_id)
    return scenario.home_jurisdiction if scenario is not None else data.jurisdictions[0].key


def _new_candidates(
    state: GameState,
    search: Search,
    people: list[tuple[Person, Cents]],
    knowledge: tuple[str, ...],
    expires_turn: int,
    rng: RngFactory,
    balance: Balance,
    data: GameData,
) -> GameState:
    actor = _actor(state, search)
    scout = actor.skills["judgment_of_talent"] if actor is not None else 0.0
    skill_keys = frozenset(data.skill_keys)
    candidates: list[Candidate] = []
    reveals: list[RevealState] = []
    for person, ask in people:
        candidates.append(
            Candidate(
                person_id=person.id,
                firm_id=search.firm_id,
                search_id=search.id,
                channel=search.channel,
                ask_cents=ask,
                created_turn=state.turn,
                expires_turn=expires_turn,
            )
        )
        reveal = new_reveal_state(
            observer_firm_id=search.firm_id,
            person=person,
            turn=state.turn,
            rng=rng,
            data=data,
            balance=balance,
        )
        for action in knowledge:
            reveal = apply_knowledge_action(
                reveal, action, scout, balance, turn=state.turn, skill_keys=skill_keys
            )
        reveals.append(reveal)
    state = with_people(state, [p for p, _ in people])
    state = with_candidates(state, candidates)
    return with_reveals(state, reveals)


def lateral_batches(
    state: GameState, rng: RngFactory, balance: Balance, data: GameData
) -> tuple[GameState, tuple[LogItem, ...]]:
    """Each open lateral search produces a batch (stream people_gen, key (search id, n)).

    Draw order: batch size from key (search id, 0) [n = 0 is the batch's own draws], then
    for the n-th candidate (n from 1) in its own generator: level (from the channel's mix
    unless the search names one), school tier (when the search filters), the person, then
    the ask. Referral and recruiter searches close after their batch; a job post stays open.
    """
    logs: list[LogItem] = []
    jurisdiction = _jurisdiction(state, data)
    for search in [s for s in state.searches if s.status == "open" and s.channel != "campus"]:
        channel = balance.hiring.channels[search.channel]
        batch_gen = people_gen_stream(rng, state.turn, search.id, 0)
        count = int(batch_gen.integers(int(channel.size.lo), int(channel.size.hi), endpoint=True))
        actor = _actor(state, search)
        if (
            actor is not None
            and channel.sociability_threshold is not None
            and actor.personality["sociability"] >= channel.sociability_threshold
        ):
            count += channel.sociability_bonus
        role = data.role(search.role)
        mix = balance.hiring.level_mix[role.kind]
        city = state.firm(search.firm_id).home_city
        first = state.next_id("person")
        people: list[tuple[Person, Cents]] = []
        for n in range(1, count + 1):
            gen = people_gen_stream(rng, state.turn, search.id, n)
            level = search.level or weighted_pick(gen, mix, list(mix))
            tier = None
            if search.school_tiers and role.kind == "lawyer":
                weights = {
                    t: balance.people.school_tier_weights.get(t, 1.0) for t in search.school_tiers
                }
                tier = weighted_pick(gen, weights, list(search.school_tiers))
            person = generate_person(
                gen,
                data,
                balance,
                state.turn,
                role,
                level,
                person_id=first + n - 1,
                city=city,
                jurisdiction=jurisdiction,
                school_tier=tier,
            )
            people.append((person, ask_cents(gen, person, state, search.firm_id, balance, data)))
        state = _new_candidates(
            state,
            search,
            people,
            channel.knowledge,
            state.turn + balance.hiring.candidate_shelf_turns,
            rng,
            balance,
            data,
        )
        if search.channel in ONE_BATCH:
            state = with_search(state, replace(search, status="closed", closed_turn=state.turn))
        logs.append(
            inbox_item(
                state.turn,
                search.firm_id,
                "candidates_arrived",
                link_kind="search",
                link_id=search.id,
                count=count,
                role=role.label,
                channel=search.channel.replace("_", " "),
                shelf=balance.hiring.candidate_shelf_turns,
            )
        )
    return state, tuple(logs)


def _office_rent(
    state: GameState, firm_id: int, heads: int, balance: Balance, data: GameData
) -> Cents:
    """Rent per head; PT-M8 (spec 9.1): the COO's office costs x (1 - coo_office x e)."""
    rent = rent_cents(heads, state.firm(firm_id).home_city, balance.pay)
    e = seat_effect(state, firm_id, "coo", balance, data)
    return rent if e == 0 else round(rent * (1.0 - balance.seats.effects.coo_office * e))


def _lifted(person: Person, keys: tuple[str, ...], points: float) -> Person:
    """A campus candidate's role skills moved by `points` (the CHRO, PT-M8), clamped 1-20."""
    from ptk.sim.scale import clamp_attr

    changes = {k: clamp_attr(person.skills[k] + points) for k in keys}
    return replace(person, skills=person.skills.updated(changes))


def campus_pools(
    state: GameState, rng: RngFactory, balance: Balance, data: GameData
) -> tuple[GameState, tuple[LogItem, ...]]:
    """In phase 12 of the pool month (April), each open campus search draws its summer
    associates: per_tier[tier] from each tier it visits (all v1 US tiers if it names none),
    stream campus, key (year, tier index, search id); each person's draws in order, then
    their ask. They arrive for the summer programme and stay until the offer month."""
    campus = balance.campus
    year, month = _ym(state)
    if month != campus.pool_month:
        return state, ()
    logs: list[LogItem] = []
    jurisdiction = _jurisdiction(state, data)
    tiers = [t for t in data.school_tiers if t.available_in == "v1" and t.country == "us"]
    expires = state.turn + (campus.offer_month - campus.pool_month)
    for search in [s for s in state.searches if s.status == "open" and s.channel == "campus"]:
        role = data.role(search.role)
        city = state.firm(search.firm_id).home_city
        people: list[tuple[Person, Cents]] = []
        # PT-M8 (spec 9.1): the CHRO's campus programme draws a stronger (or weaker) class
        lift = balance.seats.effects.chro_campus_points * seat_effect(
            state, search.firm_id, "chro", balance, data
        )
        for index, tier in enumerate(data.school_tiers):
            if tier not in tiers or (search.school_tiers and tier.key not in search.school_tiers):
                continue
            gen = rng.stream(state.turn, "campus", year, index, search.id)
            for _ in range(campus.per_tier.get(tier.key, 0)):
                person = generate_person(
                    gen,
                    data,
                    balance,
                    state.turn,
                    role,
                    campus.level,
                    person_id=state.next_id("person") + len(people),
                    city=city,
                    jurisdiction=jurisdiction,
                    school_tier=tier.key,
                )
                if lift:
                    person = _lifted(person, role.primary, lift)
                people.append(
                    (person, ask_cents(gen, person, state, search.firm_id, balance, data))
                )
        state = _new_candidates(
            state, search, people, campus.knowledge, expires, rng, balance, data
        )
        state = with_search(state, replace(search, status="closed", closed_turn=state.turn))
        logs.append(
            inbox_item(
                state.turn,
                search.firm_id,
                "summer_programme",
                link_kind="search",
                link_id=search.id,
                count=len(people),
                role=role.label,
            )
        )
    return state, tuple(logs)


def summer_month(state: GameState, balance: Balance, data: GameData) -> GameState:
    """Each summer month (May-July), a firm learns its summer associates as a scouting month,
    with its best true judgment of talent among active staff as scout (TST 4)."""
    campus = balance.campus
    if not campus.summer_months.lo <= _ym(state)[1] <= campus.summer_months.hi:
        return state
    skill_keys = frozenset(data.skill_keys)
    scouts: dict[int, float] = {}
    for e in state.employments:
        if e.status == "active":
            judgment = state.person(e.person_id).skills["judgment_of_talent"]
            scouts[e.firm_id] = max(scouts.get(e.firm_id, 0.0), judgment)
    updated = []
    for c in state.candidates:
        if c.channel != "campus" or c.status != "open":
            continue
        reveal = state.reveal(c.firm_id, c.person_id)
        if reveal is not None:
            updated.append(
                apply_knowledge_action(
                    reveal,
                    SCOUTING,
                    scouts.get(c.firm_id, 0.0),
                    balance,
                    turn=state.turn,
                    skill_keys=skill_keys,
                )
            )
    return with_reveals(state, updated)


def reset_energy(state: GameState, balance: Balance) -> GameState:
    """The player's founding partner's energy resets after phase 12 for the new month
    (ADR-0014). PT-M2's delegates get theirs through the hook in phase 2."""
    founders = [p.id for p in state.people if p.is_founder]
    return with_person_states(
        state,
        [replace(state.person_state(pid), energy=balance.energy.per_month) for pid in founders],
    )


def starting_pay(state: GameState, balance: Balance, data: GameData) -> GameState:
    """At a new game: every employment's salary at the firm's pay for its level, morale at
    morale.start for everyone but founding partners, and the founder's energy."""
    ym = _ym(state)
    for e in state.employments:
        person = state.person(e.person_id)
        firm = state.firm(e.firm_id)
        salary = firm_pay_cents(data, balance, person.level, ym, firm.home_city, firm.pay_policy)
        state = with_employment(state, replace(e, salary_cents=salary))
    morale = [
        PersonState(person_id=p.id, morale=balance.morale.start)
        for p in state.people
        if not p.founding_partner
    ]
    state = with_person_states(state, morale)
    return reset_energy(state, balance)
