"""Partner flight (spec 8.7, 5.7): the `PartnerFlightHook` of `ptk.sim.interfaces`.

Monthly (phase 8), for each equity partner but the one the player plays: the chance of an
approach is spec 8.7's p_leave; an approach from a static panel firm (PT-M5's rivals use the
same hook) offers about the partner's market value and gives the firm `answer_months` to
counter. When it comes due the partner stays (honouring any counter) or leaves. A departure
serves the agreement's notice, has its capital and current account returned over three
years, and takes the portable share of the partner's clients over 3-12 months; the rest are
handed to the best remaining partner in the practice. Stream `poach`, keyed (person_id,):
one generator per partner a month, first the approach roll, then the decision on an approach
due that month, then the clients' following draws if they leave.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import replace

import numpy as np

from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import PartnershipError, UnknownApproachError
from ptk.sim.interfaces import (
    ApproachRequest,
    ApproachView,
    CounterOffer,
    DepartureReason,
    DepartureView,
    HookResult,
    LateralArrival,
    Suitor,
)
from ptk.sim.ledger import (
    DRAWINGS,
    PARTNER_CURRENT,
    PARTNERS_CAPITAL,
    UNDISTRIBUTED_PROFIT,
    AccountCode,
    LedgerEntry,
)
from ptk.sim.log import LinkKind, LogItem, inbox_item
from ptk.sim.matters.intake import with_relationship
from ptk.sim.money import Cents
from ptk.sim.partnership import formulas as fx
from ptk.sim.partnership.common import (
    book_cents,
    firm_partnership,
    home_practice,
    name,
    put,
    queue_event,
)
from ptk.sim.partnership.governance import median_book
from ptk.sim.partnership.models import (
    Approach,
    CapitalReturn,
    Departure,
    FirmPartnership,
    Partner,
    with_approach,
    with_capital_return,
    with_departure,
    with_partner,
    with_sponsor,
    without_partner,
)
from ptk.sim.people.models import EndReason
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState, with_employment

type Draws = Callable[[], np.random.Generator]

PERSON: LinkKind = "person"
GROUP_EXIT_MONTHS = 6  # tunable-exempt: spec 15's partner group exit, within six months
END_REASONS: dict[str, EndReason] = {
    "approach": "poached",
    "flight": "poached",
    "up_or_out": "resigned",
    "de_equitised": "fired",
    "expelled": "fired",
    "retired": "retired",
    "dissolved": "firm_dissolved",
}


def poach_stream(rng: RngFactory, turn: int, person_id: int) -> np.random.Generator:
    """The one call site of stream `poach` (ADR PT-0012)."""
    return rng.stream(turn, "poach", person_id)


def firm_comp_cents(p: Partner) -> int:
    """What the firm pays the partner a year, as they see it."""
    return max(p.comp_last_cents, p.budget_cents, p.guarantee_cents, 1)


def _group_size(state: GameState, fp: FirmPartnership, practice: str, data: GameData) -> int:
    return sum(
        1 for p in fp.equity_partners if home_practice(state.person(p.person_id), data) == practice
    )


def _departed_12m(fp: FirmPartnership, practice: str, turn: int) -> int:
    return sum(
        1
        for d in fp.departures
        if d.equity and d.practice == practice and turn - d.turn < fx.MONTHS_PER_YEAR
    )


class FlightHook:
    """PT-M4's implementation of `interfaces.PartnerFlightHook`."""

    def market_value_cents(
        self, state: GameState, person_id: int, balance: Balance, data: GameData
    ) -> int:
        return fx.market_value_cents(
            book_cents(state, state.person(person_id)), balance.partnership.flight
        )

    def leave_chance_bp(
        self, state: GameState, person_id: int, balance: Balance, data: GameData
    ) -> int:
        firm = state.employer_of(person_id)
        fp = state.partnership.of(firm) if firm is not None else None
        p = fp.partner(person_id) if fp is not None else None
        if fp is None or p is None:
            return 0
        cfg = balance.partnership.flight
        person = state.person(person_id)
        practice = home_practice(person, data)
        star = 1.0
        if fp.agreement.comp_system == "lockstep" and book_cents(
            state, person
        ) > cfg.star_book_mult * max(median_book(state, fp), 1):
            star = cfg.lockstep_star_mult
        loyalty = person.personality["loyalty"]
        if "lifer" in person.tags:
            loyalty = max(loyalty, balance.resign.lifer_loyalty_floor)
        return fx.leave_chance_bp(
            self.market_value_cents(state, person_id, balance, data),
            firm_comp_cents(p),
            loyalty,
            _departed_12m(fp, practice, state.turn),
            _group_size(state, fp, practice, data),
            p.confidence,
            star,
            cfg,
        )

    def approach(
        self, state: GameState, request: ApproachRequest, *, balance: Balance, data: GameData
    ) -> HookResult:
        firm = state.employer_of(request.person_id)
        fp = state.partnership.of(firm) if firm is not None else None
        if fp is None or fp.partner(request.person_id) is None:
            raise PartnershipError(f"person {request.person_id} is not a partner of a firm")
        if any(
            a.person_id == request.person_id and a.status in ("open", "countered")
            for a in fp.approaches
        ):
            raise PartnershipError("that partner already has an open approach")
        aid = state.partnership.next_approach_id
        respond = request.respond_by_turn or state.turn + balance.partnership.flight.answer_months
        a = Approach(
            id=aid,
            firm_id=fp.firm_id,
            person_id=request.person_id,
            suitor_key=request.suitor.key,
            suitor_name=request.suitor.name,
            suitor_firm_id=request.suitor.firm_id,
            offer_comp_cents=request.offer_comp_cents,
            guarantee_years=request.guarantee_years,
            made_turn=state.turn,
            respond_by_turn=respond,
        )
        state = put(state, with_approach(fp, a))
        a = with_hint(state, a, balance)
        state = put(state, with_approach(firm_partnership(state, fp.firm_id), a))
        state = replace(state, partnership=replace(state.partnership, next_approach_id=aid + 1))
        log = inbox_item(
            state.turn,
            fp.firm_id,
            "partner_approached",
            link_kind=PERSON,
            link_id=request.person_id,
            name=name(state.person(request.person_id)),
            suitor=request.suitor.name,
            offer_cents=request.offer_comp_cents,
            years=request.guarantee_years,
        )
        return HookResult(state, (), (log,))

    def counter(
        self, state: GameState, offer: CounterOffer, *, balance: Balance, data: GameData
    ) -> HookResult:
        fp, a = _open_approach(state, offer.approach_id)
        a = replace(
            a,
            status="countered",
            countered=True,
            counter_comp_cents=max(0, offer.comp_cents),
            counter_points=max(0.0, offer.points),
            counter_guarantee_years=max(
                0, min(3, offer.guarantee_years)
            ),  # tunable-exempt: spec 5.7's 1-3 years
            counter_seat=offer.seat,
        )
        a = with_hint(state, a, balance)
        return HookResult(put(state, with_approach(fp, a)))

    def stay_probability(self, state: GameState, a: Approach, balance: Balance) -> float:
        fp = firm_partnership(state, a.firm_id)
        p = fp.partner(a.person_id)
        if p is None:
            return 0.0
        person = state.person(a.person_id)
        cfg = balance.partnership.flight
        points_value = 0
        if a.counter_points and fp.equity_partners:
            total = sum(q.points for q in fp.equity_partners) or 1.0
            points_value = round(max(fp.last_profit_cents or 0, 0) * a.counter_points / total)
        return fx.stay_probability(
            firm_comp_cents(p) + a.counter_comp_cents + points_value,
            a.offer_comp_cents,
            person.personality["loyalty"],
            p.confidence,
            a.counter_guarantee_years,
            a.guarantee_years,
            a.counter_seat,
            cfg,
        )

    def resolve(
        self,
        state: GameState,
        approach_id: int,
        *,
        draws: Draws,
        balance: Balance,
        data: GameData,
        balances: Mapping[tuple[int, AccountCode], Cents],
    ) -> HookResult:
        fp, a = _open_approach(state, approach_id)
        p = fp.partner(a.person_id)
        assert p is not None
        gen = draws()
        stays = float(gen.random()) < self.stay_probability(state, a, balance)
        if stays:
            years = a.counter_guarantee_years
            comp = firm_comp_cents(p) + a.counter_comp_cents
            p2 = replace(
                p,
                promised_cents=p.promised_cents + a.counter_comp_cents,
                promised_points=p.promised_points + a.counter_points,
                seat=p.seat or a.counter_seat,
            )
            if years:
                p2 = replace(
                    p2,
                    guarantee_cents=comp,
                    guarantee_until_turn=state.turn + years * fx.MONTHS_PER_YEAR,
                )
            fp = with_partner(fp, p2)
            fp = with_approach(fp, replace(a, status="stayed", resolved_turn=state.turn))
            log = inbox_item(
                state.turn,
                fp.firm_id,
                "partner_stayed",
                link_kind=PERSON,
                link_id=a.person_id,
                name=name(state.person(a.person_id)),
                suitor=a.suitor_name,
            )
            return HookResult(put(state, fp), (), (log,))
        fp = with_approach(fp, replace(a, status="left", resolved_turn=state.turn))
        state = put(state, fp)
        suitor = Suitor(a.suitor_key, a.suitor_name, a.suitor_firm_id)
        return self.depart(
            state,
            a.person_id,
            suitor,
            "approach",
            draws=lambda: gen,
            balance=balance,
            data=data,
            balances=balances,
        )

    def depart(
        self,
        state: GameState,
        person_id: int,
        suitor: Suitor | None,
        reason: DepartureReason,
        *,
        draws: Draws,
        balance: Balance,
        data: GameData,
        balances: Mapping[tuple[int, AccountCode], Cents],
    ) -> HookResult:
        return depart_partner(state, person_id, suitor, reason, draws(), balance, data)

    def arrive(
        self,
        state: GameState,
        arrival: LateralArrival,
        *,
        draws: Draws,
        balance: Balance,
        data: GameData,
        balances: Mapping[tuple[int, AccountCode], Cents],
    ) -> HookResult:
        from ptk.sim.partnership.laterals import arrive_partner

        return arrive_partner(state, arrival, draws(), balance, data)

    def approaches(self, state: GameState, firm_id: int) -> tuple[ApproachView, ...]:
        fp = state.partnership.of(firm_id)
        if fp is None:
            return ()
        return tuple(approach_view(a) for a in fp.approaches if a.status in ("open", "countered"))

    def departures(
        self, state: GameState, firm_id: int, since_turn: int
    ) -> tuple[DepartureView, ...]:
        fp = state.partnership.of(firm_id)
        if fp is None:
            return ()
        return tuple(departure_view(d) for d in fp.departures if d.turn >= since_turn)


def with_hint(state: GameState, a: Approach, balance: Balance) -> Approach:
    """The approach with its stay band refreshed (shown; the probability never is)."""
    p = FLIGHT_HOOK.stay_probability(state, a, balance)
    return replace(a, stay_hint=fx.stay_label(p, balance.partnership.flight))


def approach_view(a: Approach) -> ApproachView:
    counter = (
        CounterOffer(
            a.id, a.counter_comp_cents, a.counter_points, a.counter_guarantee_years, a.counter_seat
        )
        if a.countered
        else None
    )
    return ApproachView(
        approach_id=a.id,
        firm_id=a.firm_id,
        person_id=a.person_id,
        suitor=Suitor(a.suitor_key, a.suitor_name, a.suitor_firm_id),
        offer_comp_cents=a.offer_comp_cents,
        guarantee_years=a.guarantee_years,
        made_turn=a.made_turn,
        respond_by_turn=a.respond_by_turn,
        status=a.status,
        counter=counter,
        stay_label=a.stay_hint,
    )


def departure_view(d: Departure) -> DepartureView:
    return DepartureView(
        person_id=d.person_id,
        firm_id=d.firm_id,
        suitor=Suitor(d.suitor_key, d.suitor_name or "", d.suitor_firm_id)
        if d.suitor_key
        else None,
        turn=d.turn,
        practice=d.practice,
        reason=d.reason,  # type: ignore[arg-type]
        client_ids=tuple(c for c, _ in d.follows),
    )


def _open_approach(state: GameState, approach_id: int) -> tuple[FirmPartnership, Approach]:
    for fp in state.partnership.firms:
        a = fp.approach(approach_id)
        if a is not None:
            if a.status not in ("open", "countered"):
                raise PartnershipError(f"approach {approach_id} is closed")
            return fp, a
    raise UnknownApproachError(f"no approach {approach_id}")


# --- Departures ------------------------------------------------------------------------------


def depart_partner(
    state: GameState,
    person_id: int,
    suitor: Suitor | None,
    reason: str,
    gen: np.random.Generator,
    balance: Balance,
    data: GameData,
) -> HookResult:
    firm = state.employer_of(person_id)
    if firm is None:
        raise PartnershipError(f"person {person_id} is not on a firm's books")
    fp = firm_partnership(state, firm)
    p = fp.partner(person_id)
    if p is None:
        raise PartnershipError(f"person {person_id} is not a partner")
    cfg = balance.partnership
    person = state.person(person_id)
    turn = state.turn
    leave = turn + max(1, fp.agreement.notice_months)
    entries: list[LedgerEntry] = []
    # the year's draws are their share (no true-up for a leaver; ADR PT-0003 6)
    if p.drawn_ytd_cents:
        for memo, debit, credit in (
            ("Leaver's draws allocated", UNDISTRIBUTED_PROFIT, PARTNER_CURRENT),
            ("Leaver's drawings closed", PARTNER_CURRENT, DRAWINGS),
        ):
            entries.append(
                LedgerEntry.transfer(
                    turn=turn,
                    firm_id=firm,
                    memo=memo,
                    debit=debit,
                    credit=credit,
                    amount=p.drawn_ytd_cents,
                )
            )
        fp = replace(fp, allocated_ytd_cents=fp.allocated_ytd_cents + p.drawn_ytd_cents)
    current = p.current_cents
    capital = p.capital_cents
    owed = capital + current
    ret = CapitalReturn(
        person_id=person_id,
        monthly_cents=-(-max(owed, 0) // cfg.capital.return_months),
        remaining_capital_cents=capital if current >= 0 else max(0, capital + current),
        remaining_current_cents=max(0, current),
        start_turn=leave,
    )
    if current < 0:
        # an overdrawn leaver repays from their capital: 3000 down, 2700 back to zero
        settle = min(capital, -current)
        if settle:
            entries.append(
                LedgerEntry.transfer(
                    turn=turn,
                    firm_id=firm,
                    memo="Leaver's overdrawn account set off",
                    debit=PARTNERS_CAPITAL,
                    credit=PARTNER_CURRENT,
                    amount=settle,
                )
            )
        # PT-M5 (integration fix): an overdraft beyond their capital is not recovered; the
        # remaining partners bear it (3100 down, 2700 back to zero), so the partners' tally
        # and the ledger agree once the leaver is gone
        short = -current - settle
        if short:
            entries.append(
                LedgerEntry.transfer(
                    turn=turn,
                    firm_id=firm,
                    memo="Leaver's unrecovered overdraft borne by the partners",
                    debit=UNDISTRIBUTED_PROFIT,
                    credit=PARTNER_CURRENT,
                    amount=short,
                )
            )
    fp = with_capital_return(without_partner(fp, person_id), ret)
    # clients: the portable share follows; the rest pass to a colleague
    practice = home_practice(person, data)
    follows: list[tuple[int, int]] = []
    portability = (person.portability_bp or 0) / 10_000  # tunable-exempt: bp to a share
    successor = _successor(state, fp, person_id, practice, data)
    market = state.market
    lo, hi = cfg.flight.follow_months
    for rel in state.market.relationships:
        if rel.firm_id != firm or rel.partner_id != person_id:
            continue
        if suitor is not None and float(gen.random()) < portability:
            follows.append((rel.client_id, leave + int(gen.integers(lo, hi + 1))))
        else:
            market = with_relationship(
                market,
                replace(
                    rel,
                    partner_id=successor,
                    score=max(0.0, rel.score - cfg.flight.orphan_drop),
                ),
            )
    state = replace(state, market=market)
    dep = Departure(
        person_id=person_id,
        firm_id=firm,
        turn=turn,
        leave_turn=leave,
        practice=practice,
        reason=reason,
        equity=p.equity,
        suitor_key=suitor.key if suitor else None,
        suitor_name=suitor.name if suitor else None,
        suitor_firm_id=suitor.firm_id if suitor else None,
        book_cents=book_cents(state, person),
        follows=tuple(sorted(follows)),
    )
    fp = with_departure(fp, dep)
    for a in fp.approaches:
        if a.person_id == person_id and a.status in ("open", "countered"):
            fp = with_approach(fp, replace(a, status="withdrawn", resolved_turn=turn))
    for assoc, sponsor in fp.sponsors:
        if sponsor == person_id:
            fp = with_sponsor(fp, assoc, None)
    if fp.mp_id == person_id:
        fp = replace(fp, mp_id=state.founder_of(firm))
    state = put(state, fp)
    group = [
        d.person_id
        for d in fp.departures
        if d.equity and d.practice == practice and turn - d.turn < GROUP_EXIT_MONTHS
    ]
    if p.equity and len(group) >= 2:  # tunable-exempt: a group is two or more
        state = queue_event(
            state,
            firm,
            "partner_group_exit",
            balance,
            person_ids=tuple(group),
            practice=practice,
        )
    e = state.employment_of(person_id)
    if e is not None:
        state = with_employment(
            state,
            replace(
                e, status="notice", end_turn=leave, end_reason=END_REASONS.get(reason, "resigned")
            ),
        )
    log = inbox_item(
        turn,
        firm,
        "partner_leaving",
        link_kind=PERSON,
        link_id=person_id,
        name=name(person),
        destination=suitor.name if suitor else "outside the market",
        clients=len(follows),
    )
    return HookResult(state, tuple(entries), (log,))


def _successor(
    state: GameState, fp: FirmPartnership, leaving: int, practice: str, data: GameData
) -> int | None:
    best: tuple[float, int] | None = None
    for p in fp.partners:
        if p.person_id == leaving:
            continue
        person = state.person(p.person_id)
        score = person.familiarity[practice] if practice in person.familiarity else 0.0  # noqa: SIM401
        key = (-score, p.person_id)
        if best is None or key < best:
            best = key
    return best[1] if best else fp.mp_id


def clients_follow(state: GameState) -> tuple[GameState, tuple[LogItem, ...]]:
    """Phase 8: clients whose partner left go with them this month."""
    logs: list[LogItem] = []
    market = state.market
    for fp in state.partnership.firms:
        for d in fp.departures:
            for client_id, when in d.follows:
                if when != state.turn:
                    continue
                rel = market.relationship(client_id, fp.firm_id)
                if rel is None:
                    continue
                market = replace(
                    market,
                    relationships=tuple(
                        r
                        for r in market.relationships
                        if (r.client_id, r.firm_id) != (client_id, fp.firm_id)
                    ),
                )
                logs.append(
                    inbox_item(
                        state.turn,
                        fp.firm_id,
                        "client_followed",
                        link_kind="client",
                        link_id=client_id,
                        client=market.client(client_id).name,
                        name=name(state.person(d.person_id)),
                    )
                )
    return replace(state, market=market), tuple(logs)


# --- Phase 8 --------------------------------------------------------------------------------


def _suitor_for(
    gen: np.random.Generator, practice: str, data: GameData, state: GameState
) -> Suitor:
    """PT-M5: a live rival firm with a New York office and lawyers in the practice, by its
    lawyers there (one draw, as before); the static panel firms without rivals."""
    rivals = [
        f
        for f in state.rivals.active
        if f.ny_office and f.kind != "boutique" and f.pool(practice).lawyers >= 1.0
    ]
    if rivals:
        w = np.array([f.pool(practice).lawyers for f in rivals])
        j = int(gen.choice(len(rivals), p=w / w.sum()))
        return Suitor(rivals[j].key, rivals[j].name, rivals[j].id)
    firms = data.clients.panel_firms
    weights = np.array([2.0 if practice in f.strong else 1.0 for f in firms])
    i = int(gen.choice(len(firms), p=weights / weights.sum()))
    return Suitor(firms[i].key, firms[i].name)


def flight_month(
    state: GameState,
    rng: RngFactory,
    balance: Balance,
    data: GameData,
    balances: Mapping[tuple[int, AccountCode], Cents],
) -> tuple[GameState, tuple[LedgerEntry, ...], tuple[LogItem, ...]]:
    cfg = balance.partnership.flight
    entries: list[LedgerEntry] = []
    logs: list[LogItem] = []
    state, followed = clients_follow(state)
    logs += followed
    for fp0 in state.partnership.firms:
        player = state.founder_of(fp0.firm_id)
        for p in fp0.equity_partners:
            if p.person_id == player:
                continue
            fp = firm_partnership(state, fp0.firm_id)
            if fp.partner(p.person_id) is None:
                continue
            gen = poach_stream(rng, state.turn, p.person_id)
            chance = FLIGHT_HOOK.leave_chance_bp(state, p.person_id, balance, data)
            roll = int(gen.integers(0, 10_000))  # tunable-exempt: a bp roll
            due = next(
                (
                    a
                    for a in fp.approaches
                    if a.person_id == p.person_id
                    and a.status in ("open", "countered")
                    and a.respond_by_turn <= state.turn
                ),
                None,
            )
            if due is not None:
                res = FLIGHT_HOOK.resolve(
                    state,
                    due.id,
                    draws=_const(gen),
                    balance=balance,
                    data=data,
                    balances=balances,
                )
                state = res.state
                entries += res.entries
                logs += res.log
                continue
            busy = any(
                a.person_id == p.person_id and a.status in ("open", "countered")
                for a in fp.approaches
            )
            if busy or roll >= chance:
                continue
            person = state.person(p.person_id)
            suitor = _suitor_for(gen, home_practice(person, data), data, state)
            lo, hi = cfg.offer_mult
            market = FLIGHT_HOOK.market_value_cents(state, p.person_id, balance, data)
            offer = round(market * float(gen.uniform(lo, hi)))
            years = int(gen.integers(cfg.guarantee_years[0], cfg.guarantee_years[1] + 1))
            res = FLIGHT_HOOK.approach(
                state,
                ApproachRequest(p.person_id, suitor, offer, years),
                balance=balance,
                data=data,
            )
            state = res.state
            logs += res.log
    return state, tuple(entries), tuple(logs)


def _const(gen: np.random.Generator) -> Draws:
    return lambda: gen


FLIGHT_HOOK = FlightHook()
