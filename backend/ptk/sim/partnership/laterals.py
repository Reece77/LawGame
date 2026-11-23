"""Lateral partners (spec 5.7; ADR PT-0009 4).

A lateral partner search (a recruiter retainer) finds 1-3 partners in a practice: generated
people (stream `people_gen`, keyed by the search like any lateral search) with a book of
business shown as a range, a comp demand (a multiple of their book) and a guarantee they ask
for. Due diligence narrows the range and names the book's clients and its conflicts (clients
adverse to the firm's open matters: they are dropped at arrival). An offer resolves in phase 1
(stream `lateral`, keyed (person_id,): the acceptance, then the realised portability and the
book's arrival over 12-24 months). A guarantee fixes the partner's comp (draws and the
allocation's floor, through account 2700) for its years.
"""

from __future__ import annotations

import math
from dataclasses import replace

import numpy as np

from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import PartnershipError
from ptk.sim.hiring.models import Search
from ptk.sim.hiring.pay import band_cents
from ptk.sim.interfaces import HookResult, LateralArrival
from ptk.sim.ledger import CASH, PROFESSIONAL_FEES, RECRUITING, LedgerEntry
from ptk.sim.log import LogItem, inbox_item
from ptk.sim.matters.intake import with_relationship
from ptk.sim.matters.market import client_weight
from ptk.sim.matters.models import Relationship
from ptk.sim.money import BP_DENOMINATOR, pct_of
from ptk.sim.partnership import formulas as fx
from ptk.sim.partnership.books import capital_required_cents
from ptk.sim.partnership.common import firm_partnership, name, put
from ptk.sim.partnership.models import (
    Arrival,
    LateralCandidate,
    Partner,
    with_lateral,
    with_partner,
)
from ptk.sim.people.generator import generate_person, people_gen_stream
from ptk.sim.people.models import Employment
from ptk.sim.people.reveal import new_reveal_state
from ptk.sim.rng import RngFactory
from ptk.sim.state import (
    GameState,
    with_employment,
    with_people,
    with_person_states,
    with_reveals,
    with_search,
)

EQUITY = "equity_partner"
INCOME = "income_partner"
BOOK_STEP = 5_000_000  # tunable-exempt: books are shown in $50,000 steps
CLIENT_BOOK_CENTS = 75_000_000  # tunable-exempt: about one client per $750k of book


def lateral_stream(rng: RngFactory, turn: int, person_id: int) -> np.random.Generator:
    """The one call site of stream `lateral` (ADR PT-0012)."""
    return rng.stream(turn, "lateral", person_id)


def _round(cents: float) -> int:
    return max(BOOK_STEP, round(cents / BOOK_STEP) * BOOK_STEP)


def book_range(book: int, half_bp: int, offset: float) -> tuple[int, int]:
    """The book as the firm sees it: +-half_bp around a centre shifted by `offset` (-1..1 of
    half the width), in $50,000 steps; the true book always lies inside."""
    half = book * half_bp / BP_DENOMINATOR
    centre = book + offset * half / 2
    return _round(min(book, centre - half)), _round(max(book, centre + half))


def search(
    state: GameState,
    firm_id: int,
    actor_id: int,
    practice: str,
    rng: RngFactory,
    balance: Balance,
    data: GameData,
) -> tuple[GameState, tuple[LedgerEntry, ...], tuple[LogItem, ...]]:
    cfg = balance.partnership.lateral
    fp = firm_partnership(state, firm_id)
    role = data.practice_role(practice)
    search_id = state.next_id("search")
    turn = state.turn
    state = with_search(
        state,
        Search(
            id=search_id,
            firm_id=firm_id,
            role=role.key,
            channel="recruiter",
            actor_id=actor_id,
            opened_turn=turn,
            status="closed",
            closed_turn=turn,
            level=EQUITY,
        ),
    )
    lo, hi = cfg.batch
    n = int(people_gen_stream(rng, turn, search_id, 0).integers(lo, hi + 1))
    have = {r.client_id for r in state.market.relationships if r.firm_id == firm_id}
    pool = [c for c in state.market.clients if c.id not in have]
    adverse = {
        m.adverse_client_id for m in state.market.open_matters(firm_id) if m.adverse_client_id
    }
    city = state.firm(firm_id).home_city
    jurisdiction = state.save_meta.scenario_id and data.scenario(state.save_meta.scenario_id)
    bar = jurisdiction.home_jurisdiction if jurisdiction else "us_ny"
    taken: set[int] = set()
    for i in range(1, n + 1):
        gen = people_gen_stream(rng, turn, search_id, i)
        pid = state.next_id("person")
        person = generate_person(
            gen, data, balance, turn, role, EQUITY, person_id=pid, city=city, jurisdiction=bar
        )
        blo, bhi = cfg.book_cents
        book = _round(math.exp(gen.uniform(math.log(blo), math.log(bhi))))
        person = replace(person, book_cents=book)
        k = max(1, min(8, round(book / CLIENT_BOOK_CENTS)))  # tunable-exempt: 1-8 clients
        weights = np.array(
            [0.0 if c.id in taken else client_weight(c, practice, data, balance) for c in pool]
        )
        clients: tuple[int, ...] = ()
        if weights.sum() > 0:
            k = min(k, int((weights > 0).sum()))
            idx = gen.choice(len(pool), size=k, replace=False, p=weights / weights.sum())
            clients = tuple(sorted(pool[int(j)].id for j in idx))
            taken.update(clients)
        offset = float(gen.uniform(-1.0, 1.0))
        book_lo, book_hi = book_range(book, cfg.book_range_bp, offset)
        notice = fp.agreement.notice_months
        ask = pct_of(
            pct_of(book, cfg.comp_of_book_bp), BP_DENOMINATOR + cfg.notice_premium_bp * notice
        )
        years = int(gen.integers(cfg.guarantee_years[0], cfg.guarantee_years[1] + 1))
        state = with_people(state, [person])
        state = with_reveals(
            state,
            [
                new_reveal_state(
                    observer_firm_id=firm_id,
                    person=person,
                    turn=turn,
                    rng=rng,
                    data=data,
                    balance=balance,
                )
            ],
        )
        fp = with_lateral(
            firm_partnership(state, firm_id),
            LateralCandidate(
                person_id=pid,
                firm_id=firm_id,
                search_id=search_id,
                practice=practice,
                ask_cents=_round(ask),
                guarantee_ask_years=years,
                book_lo_cents=book_lo,
                book_hi_cents=book_hi,
                client_ids=clients,
                conflict_ids=tuple(c for c in clients if c in adverse),
                created_turn=turn,
                expires_turn=turn + cfg.shelf_turns,
            ),
        )
        state = put(state, fp)
    entry = LedgerEntry.transfer(
        turn=turn,
        firm_id=firm_id,
        memo="Lateral partner search retainer",
        debit=RECRUITING,
        credit=CASH,
        amount=cfg.search_cost_cents,
    )
    log = inbox_item(
        turn, firm_id, "lateral_candidates", link_kind=None, count=n, practice=practice
    )
    return state, ((entry,) if cfg.search_cost_cents else ()), (log,)


def open_candidate(state: GameState, firm_id: int, person_id: int) -> LateralCandidate:
    cand = firm_partnership(state, firm_id).lateral(person_id)
    if cand is None or cand.status != "open":
        raise PartnershipError(f"no open lateral candidate {person_id}")
    return cand


def diligence(
    state: GameState, firm_id: int, person_id: int, gen: np.random.Generator, balance: Balance
) -> tuple[GameState, tuple[LedgerEntry, ...]]:
    cfg = balance.partnership.lateral
    cand = open_candidate(state, firm_id, person_id)
    if cand.diligence:
        raise PartnershipError("diligence is already done")
    book = state.person(person_id).book_cents
    lo, hi = book_range(book, cfg.diligence_range_bp, float(gen.uniform(-1.0, 1.0)))
    cand = replace(cand, diligence=True, book_lo_cents=lo, book_hi_cents=hi)
    state = put(state, with_lateral(firm_partnership(state, firm_id), cand))
    entry = LedgerEntry.transfer(
        turn=state.turn,
        firm_id=firm_id,
        memo="Lateral partner diligence",
        debit=PROFESSIONAL_FEES,
        credit=CASH,
        amount=cfg.diligence_cost_cents,
    )
    return state, ((entry,) if cfg.diligence_cost_cents else ())


def offer(
    state: GameState, firm_id: int, person_id: int, comp: int, years: int, equity: bool
) -> GameState:
    fp = firm_partnership(state, firm_id)
    cand = open_candidate(state, firm_id, person_id)
    if not equity and not fp.agreement.two_tier:
        raise PartnershipError("the agreement has no income partners (two-tier is off)")
    if comp <= 0 or not 0 <= years <= 3:  # tunable-exempt: spec 5.7's guarantees of 1-3 years
        raise PartnershipError("an offer needs comp above zero and a guarantee of 0-3 years")
    cand = replace(
        cand,
        status="offered",
        offer_comp_cents=comp,
        offer_guarantee_years=years,
        offer_equity=equity,
        offer_turn=state.turn,
    )
    return put(state, with_lateral(fp, cand))


def accept_probability(cand: LateralCandidate, balance: Balance) -> float:
    cfg = balance.partnership.lateral
    x = (
        cfg.accept_base
        + cfg.accept_k * (cand.offer_comp_cents / max(cand.ask_cents, 1) - 1)
        + cfg.guarantee_weight * (cand.offer_guarantee_years - cand.guarantee_ask_years)
    )
    return 1 / (1 + math.exp(-x))


def resolve_offers(
    state: GameState, rng: RngFactory, balance: Balance, data: GameData
) -> tuple[GameState, tuple[LedgerEntry, ...], tuple[LogItem, ...]]:
    """Phase 1: offered candidates accept or decline; open ones past their shelf expire."""
    entries: list[LedgerEntry] = []
    logs: list[LogItem] = []
    for fp0 in state.partnership.firms:
        for cand in fp0.laterals:
            fp = firm_partnership(state, fp0.firm_id)
            if cand.status == "open" and cand.expires_turn <= state.turn:
                state = put(
                    state,
                    with_lateral(fp, replace(cand, status="expired", resolved_turn=state.turn)),
                )
                continue
            if cand.status != "offered":
                continue
            gen = lateral_stream(rng, state.turn, cand.person_id)
            accepted = float(gen.random()) < accept_probability(cand, balance)
            person = state.person(cand.person_id)
            if not accepted:
                state = put(
                    state,
                    with_lateral(fp, replace(cand, status="declined", resolved_turn=state.turn)),
                )
                logs.append(
                    inbox_item(
                        state.turn,
                        fp.firm_id,
                        "lateral_declined",
                        link_kind="person",
                        link_id=cand.person_id,
                        name=name(person),
                    )
                )
                continue
            state = put(
                state, with_lateral(fp, replace(cand, status="hired", resolved_turn=state.turn))
            )
            res = arrive_partner(
                state,
                LateralArrival(
                    person_id=cand.person_id,
                    firm_id=fp.firm_id,
                    from_suitor=None,
                    comp_cents=cand.offer_comp_cents,
                    guarantee_years=cand.offer_guarantee_years,
                    equity=cand.offer_equity,
                    client_ids=tuple(c for c in cand.client_ids if c not in cand.conflict_ids),
                ),
                gen,
                balance,
                data,
                recruiter_fee=True,
            )
            state = res.state
            entries += res.entries
            logs += res.log
    return state, tuple(entries), tuple(logs)


def arrive_partner(
    state: GameState,
    arrival: LateralArrival,
    gen: np.random.Generator,
    balance: Balance,
    data: GameData,
    *,
    recruiter_fee: bool = False,
) -> HookResult:
    """A lateral partner joins `arrival.firm_id` this turn. Their previous employment (a
    rival's, PT-M5) ends; the firm must already know them (a reveal record)."""
    cfg = balance.partnership
    turn = state.turn
    firm_id = arrival.firm_id
    fp = firm_partnership(state, firm_id)
    person = state.person(arrival.person_id)
    old = state.employment_of(person.id)
    if old is not None:
        state = with_employment(
            state, replace(old, status="ended", end_turn=turn, end_reason="poached")
        )
    level = EQUITY if arrival.equity else INCOME
    salary = 0 if arrival.equity else arrival.comp_cents
    # PT-M11: a partner joining an office in their own city stays there
    from ptk.sim.geo.cities import office_in

    city = person.city if office_in(state, firm_id, person.city) else state.firm(firm_id).home_city
    state = with_people(state, [replace(person, level=level, city=city)])
    state = with_employment(
        state,
        Employment(
            id=state.next_id("employment"),
            person_id=person.id,
            firm_id=firm_id,
            start_turn=turn,
            salary_cents=salary,
        ),
    )
    ps = state.person_state(person.id)
    state = with_person_states(state, [replace(ps, morale=balance.morale.new_hire)])
    years = arrival.guarantee_years
    required = capital_required_cents(arrival.comp_cents, fp.agreement) if arrival.equity else 0
    partner = Partner(
        person_id=person.id,
        firm_id=firm_id,
        klass="equity" if arrival.equity else "income",
        admitted_turn=turn,
        points=cfg.lockstep.start_points,
        capital_required_cents=required,
        capital_instalment_cents=-(-required // cfg.capital.pay_in_months),
        budget_cents=arrival.comp_cents if arrival.equity else 0,
        guarantee_cents=arrival.comp_cents if years and arrival.equity else 0,
        guarantee_until_turn=turn + years * fx.MONTHS_PER_YEAR - 1
        if years and arrival.equity
        else None,
        confidence=cfg.confidence.start,
    )
    fp = with_partner(fp, partner)
    # the book: realised portability, then each client's month within the arrival window
    lc = cfg.lateral
    hidden = (person.portability_bp or 0) / BP_DENOMINATOR
    realised = min(
        1.0, max(0.0, hidden + float(gen.normal(0.0, lc.realised_sd_bp / BP_DENOMINATOR)))
    )
    window = int(gen.integers(lc.arrival_months[0], lc.arrival_months[1] + 1))
    practice = data.role(person.role).practice or person.role
    arrivals = list(fp.arrivals)
    for client_id in arrival.client_ids:
        if float(gen.random()) < realised:
            arrivals.append(
                Arrival(
                    person.id, firm_id, client_id, turn + int(gen.integers(1, window + 1)), practice
                )
            )
    fp = replace(fp, arrivals=tuple(sorted(arrivals, key=lambda a: (a.turn, a.client_id))))
    state = put(state, fp)
    entries: tuple[LedgerEntry, ...] = ()
    fee = pct_of(arrival.comp_cents, lc.fee_bp) if recruiter_fee else 0
    if fee:
        entries = (
            LedgerEntry.transfer(
                turn=turn,
                firm_id=firm_id,
                memo="Lateral partner recruiter fee",
                debit=RECRUITING,
                credit=CASH,
                amount=fee,
            ),
        )
    log = inbox_item(
        turn,
        firm_id,
        "lateral_joined",
        link_kind="person",
        link_id=person.id,
        name=name(person),
        comp_cents=arrival.comp_cents,
        years=years,
    )
    return HookResult(state, entries, (log,))


def books_arrive(state: GameState, balance: Balance) -> tuple[GameState, tuple[LogItem, ...]]:
    """Phase 8: a lateral's clients that follow them this month become the firm's."""
    logs: list[LogItem] = []
    lo, hi = balance.partnership.lateral.start_relationship
    for fp in state.partnership.firms:
        due = [a for a in fp.arrivals if a.turn <= state.turn]
        if not due:
            continue
        market = state.market
        staff = set(state.staff_ids(fp.firm_id))
        for a in due:
            if a.person_id not in staff or market.relationship(a.client_id, fp.firm_id) is not None:
                continue
            market = with_relationship(
                market,
                Relationship(
                    client_id=a.client_id,
                    firm_id=fp.firm_id,
                    score=(lo + hi) / 2,
                    partner_id=a.person_id,
                    practices=(a.practice,),
                    since_turn=state.turn,
                    last_instructed_turn=state.turn,
                ),
            )
            logs.append(
                inbox_item(
                    state.turn,
                    fp.firm_id,
                    "client_arrived",
                    link_kind="client",
                    link_id=a.client_id,
                    client=market.client(a.client_id).name,
                    name=name(state.person(a.person_id)),
                )
            )
        state = replace(state, market=market)
        state = put(
            state, replace(fp, arrivals=tuple(a for a in fp.arrivals if a.turn > state.turn))
        )
    return state, tuple(logs)


def income_partner_salary(data: GameData, balance: Balance, city: str) -> int:
    return pct_of(
        band_cents(data, balance, INCOME, city), balance.partnership.income_partner_salary_bp
    )
