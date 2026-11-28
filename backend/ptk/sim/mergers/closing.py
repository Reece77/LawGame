"""Closing (spec 8.8; ADR PT-0016 1-2): the other firm becomes part of the player's firm, or
joins its verein, or absorbs it (the exit).

An integrated merger, in order: clearance runs once more (conflicts that arose since the
votes); the other firm's closing sheet is built; its lawyers join (its key people as they are,
the rest of its pools generated on stream `merger_people`); its equity partners become partners
with their capital paid in (the sheet's capital split exactly), points by the points ratio and
budgets from the expected pool; its kept book clients join with one relationship each, its key
leaves every panel; its WIP becomes flow WIP and its receivables open bills on those clients
(both split exactly by share); its annuities become an annuity record; its lease is carried as
an office in another city, or surrendered in the home city (or a city the firm already has an
office in); its revolver is carried and the facility grows; the terms apply (name, managing
partner, comp system, card); an `Integration` record starts.
"""

from __future__ import annotations

from dataclasses import replace

from simcore.kernel.calendar import turn_to_ym
from simcore.kernel.money import BP_DENOMINATOR

from ptk.sim.data_models import Balance, GameData
from ptk.sim.ledger import (
    ANNUITIES,
    CASH,
    LEASES,
    PARTNERS_CAPITAL,
    RECEIVABLES,
    RENT,
    REVOLVER,
    RIGHT_OF_USE,
    WIP,
    LedgerEntry,
    LedgerLine,
)
from ptk.sim.log import LogItem, inbox_item
from ptk.sim.mergers import streams
from ptk.sim.mergers.books import hidden, lease_months, monthly_rent, sheet, split_exact
from ptk.sim.mergers.clearance import clear, kept_book
from ptk.sim.mergers.models import Deal, Integration, Sheet, with_deal, with_integration
from ptk.sim.mergers.profile import Side, clash, player_side, rival_side, round_pools
from ptk.sim.mergers.talks import put_mergers
from ptk.sim.mergers.terms import merged_card, our_change, pool_cents, their_change
from ptk.sim.people.models import Employment, Person
from ptk.sim.rivals.models import PLAYER_PANEL_KEY, RivalFirm
from ptk.sim.state import GameState, with_firm
from ptk.sim.streams import RngFactory

ASSOCIATE_LEVELS = tuple(f"associate_{n}" for n in range(1, 9))  # tunable-exempt: the ladder
EQUITY, INCOME, COUNSEL = "equity_partner", "income_partner", "counsel"


def merger_office_lines(sheet_: Sheet, office_id: int | None) -> tuple[LedgerLine, ...]:
    """The closing entry's lines (ADR PT-0016 2): the sheet less the eliminated lease."""
    lines = [
        LedgerLine(CASH, sheet_.cash),
        LedgerLine(WIP, sheet_.wip),
        LedgerLine(RECEIVABLES, sheet_.receivables),
        LedgerLine(ANNUITIES, -sheet_.annuities),
        LedgerLine(REVOLVER, -sheet_.revolver),
        LedgerLine(PARTNERS_CAPITAL, -sheet_.capital),
    ]
    if office_id is not None:
        lines += [
            LedgerLine(RIGHT_OF_USE, sheet_.right_of_use, office_id=office_id),
            LedgerLine(LEASES, -sheet_.leases, office_id=office_id),
        ]
    return tuple(ln for ln in lines if ln.amount != 0)


def _people(
    state: GameState,
    deal: Deal,
    firm: RivalFirm,
    city: str,
    rng: RngFactory,
    data: GameData,
    balance: Balance,
) -> tuple[list[Person], list[str]]:
    """The other firm's lawyers as people: its key people first, then its pools' rest."""
    from ptk.sim.geo.cities import city_def
    from ptk.sim.people.generator import generate_person
    from ptk.sim.rivals.people import person_of

    fp = state.partnership.of(state.player.id)
    two_tier = fp is not None and fp.agreement.two_tier
    other = INCOME if two_tier else COUNSEL
    cdef = city_def(data, city)
    jurisdiction = cdef.jurisdiction if cdef is not None else "us_ny"
    need: dict[tuple[str, str], int] = {}
    for practice, e, q, a in round_pools(firm):
        need[(practice, "equity")] = e
        need[(practice, "other")] = q
        need[(practice, "associate")] = a
    out: list[Person] = []
    kinds: list[str] = []
    for m in state.rivals.members_of(firm.id):
        person = person_of(state, m, data, balance)
        if m.kind == "partner":
            slot = "equity" if person.level == EQUITY else "other"
            level = EQUITY if slot == "equity" else other
        else:
            slot, level = "associate", person.level
        key = (m.practice, slot)
        need[key] = max(0, need.get(key, 0) - 1)
        out.append(replace(person, level=level, city=city))
        kinds.append(slot)
    next_id = state.next_id("person")
    n = 0
    for (practice, slot), count in sorted(
        need.items(), key=lambda kv: (data.practice_keys.index(kv[0][0]), kv[0][1])
    ):
        role = data.practice_role(practice)
        for _ in range(count):
            n += 1
            gen = streams.people(rng, state.turn, deal.id, n)
            if slot == "equity":
                level = EQUITY
            elif slot == "other":
                level = other
            else:
                level = ASSOCIATE_LEVELS[int(gen.integers(len(ASSOCIATE_LEVELS)))]
            out.append(
                generate_person(
                    gen,
                    data,
                    balance,
                    state.turn,
                    role,
                    level,
                    person_id=next_id,
                    city=city,
                    jurisdiction=jurisdiction,
                )
            )
            kinds.append(slot)
            next_id += 1
    return out, kinds


def _hire_all(
    state: GameState,
    people: list[Person],
    rng: RngFactory,
    data: GameData,
    balance: Balance,
) -> GameState:
    from ptk.sim.hiring.pay import firm_pay_cents
    from ptk.sim.partnership.laterals import income_partner_salary
    from ptk.sim.people.reveal import new_reveal_state
    from ptk.sim.state import with_people, with_person_states, with_reveals

    firm = state.player
    ym = turn_to_ym(state.turn, state.save_meta.start_ym)
    state = with_people(state, people)
    emp_id = state.next_id("employment")
    employments = []
    for i, p in enumerate(people):
        if p.level == EQUITY:
            salary = 0
        elif p.level == INCOME:
            salary = income_partner_salary(data, balance, p.city)
        else:
            salary = firm_pay_cents(data, balance, p.level, ym, p.city, firm.pay_policy)
        employments.append(
            Employment(
                id=emp_id + i,
                person_id=p.id,
                firm_id=firm.id,
                start_turn=state.turn,
                salary_cents=salary,
            )
        )
    state = replace(
        state, employments=tuple(sorted((*state.employments, *employments), key=lambda e: e.id))
    )
    state = with_person_states(
        state,
        [replace(state.person_state(p.id), morale=balance.morale.new_hire) for p in people],
    )
    reveals = [
        new_reveal_state(
            observer_firm_id=firm.id, person=p, turn=state.turn, rng=rng, data=data, balance=balance
        )
        for p in people
    ]
    return with_reveals(state, reveals)


def _partners(
    state: GameState,
    people: list[Person],
    s: Sheet,
    our_share_bp: int,
    ours: Side,
    theirs: Side,
    balance: Balance,
) -> GameState:
    from ptk.sim.partnership.models import Partner, with_partner

    cfg = balance.partnership
    fp = state.partnership.of(state.player.id)
    assert fp is not None
    equity = [p for p in people if p.level == EQUITY]
    incomes = [p for p in people if p.level == INCOME]
    capital = split_exact(s.capital, [1.0] * len(equity))
    our_points = sum(p.points for p in fp.equity_partners) or cfg.lockstep.start_points
    share = our_share_bp / BP_DENOMINATOR
    their_points = our_points * (1.0 - share) / max(share, 1e-6)
    per = their_points / max(1, len(equity))
    pool = pool_cents(ours, theirs)
    budget = round(pool * (1.0 - share) / max(1, len(equity)))
    nudge = balance.mergers.integration.confidence_nudge * their_change(ours, theirs, our_share_bp)
    protection = balance.mergers.integration.protection_months
    for p, cap in zip(equity, capital, strict=True):
        fp = with_partner(
            fp,
            Partner(
                person_id=p.id,
                firm_id=fp.firm_id,
                klass="equity",
                admitted_turn=state.turn,
                points=per,
                capital_required_cents=cap,
                capital_cents=cap,
                budget_cents=budget,
                budget_base_cents=budget,
                # the terms protect their comp while it is harmonised (a PT-M4 guarantee:
                # a floor the rest of the partnership funds)
                guarantee_cents=budget if protection > 0 else 0,
                guarantee_until_turn=state.turn + protection - 1 if protection > 0 else None,
                confidence=cfg.confidence.start,
                nudge=nudge,
            ),
        )
    for p in incomes:
        fp = with_partner(
            fp,
            Partner(
                person_id=p.id,
                firm_id=fp.firm_id,
                klass="income",
                admitted_turn=state.turn,
                confidence=cfg.confidence.start,
            ),
        )
    ours_nudge = balance.mergers.integration.confidence_nudge * our_change(
        ours, theirs, our_share_bp
    )
    joined = {x.id for x in equity}
    for q in fp.equity_partners:
        if q.person_id not in joined:
            fp = with_partner(fp, replace(q, nudge=q.nudge + ours_nudge))
    from ptk.sim.partnership.common import put

    return put(state, fp)


def _clients(
    state: GameState, deal: Deal, firm: RivalFirm, people: list[Person], data: GameData
) -> GameState:
    """Every kept book client joins: one relationship each (a shared client keeps the higher
    score and both firms' practices); relationship partners among its equity partners in the
    client's first practice, in turn; the other firm's key leaves every panel."""
    from ptk.sim.matters.intake import with_relationship
    from ptk.sim.matters.models import Relationship
    from ptk.sim.partnership.common import home_practice
    from ptk.sim.rivals.history import replace_panel_key

    pid = state.player.id
    partners = [p for p in people if p.level == EQUITY]
    by_practice: dict[str, list[int]] = {}
    for p in partners:
        by_practice.setdefault(home_practice(p, data), []).append(p.id)
    turns: dict[str, int] = {}
    market = state.market
    order = data.practice_keys
    books: dict[int, int] = {}
    for b in kept_book(deal):
        practice = b.practices[0]
        group = by_practice.get(practice) or [p.id for p in partners]
        lead = None
        if group:
            k = turns.get(practice, 0)
            lead = group[k % len(group)]
            turns[practice] = k + 1
        old = market.relationship(b.client_id, pid)
        if old is not None:
            practices = tuple(p for p in order if p in set(old.practices) | set(b.practices))
            rel = replace(
                old,
                score=max(old.score, b.score),
                practices=practices,
                last_instructed_turn=state.turn,
            )
        else:
            rel = Relationship(
                client_id=b.client_id,
                firm_id=pid,
                score=b.score,
                partner_id=lead,
                practices=b.practices,
                since_turn=state.turn,
                last_instructed_turn=state.turn,
            )
        market = with_relationship(market, rel)
        if lead is not None:
            books[lead] = books.get(lead, 0) + 1
    market = replace_panel_key(market, firm.key, None)
    return replace(state, market=market)


def _working_capital(
    state: GameState, deal: Deal, s: Sheet, balance: Balance
) -> tuple[GameState, int]:
    """WIP to flow accounts and receivables to open bills on the kept book, split exactly."""
    from ptk.sim.billing.models import Bill, FlowAccount

    cfg = balance.mergers.books
    pid = state.player.id
    kept = kept_book(deal)
    if not kept:
        # no client left to carry them: the WIP and receivables land on the firm's own
        # largest client's flow (a firm that kept no book client still collects its work)
        rels = sorted(
            (r for r in state.market.relationships if r.firm_id == pid),
            key=lambda r: (-r.fees_12m, r.client_id),
        )
        if not rels or not rels[0].practices:
            return state, 0
        targets = [(rels[0].client_id, rels[0].practices[0], 1.0)]
    else:
        targets = [(b.client_id, b.practices[0], b.share) for b in kept]
    shares = [t[2] for t in targets]
    wips = split_exact(s.wip, shares)
    ars = split_exact(s.receivables, shares)
    billing = state.billing
    flows = {(f.client_id, f.practice, f.firm_id): f for f in billing.flows}
    for (cid, practice, _), w in zip(targets, wips, strict=True):
        if w <= 0:
            continue
        key = (cid, practice, pid)
        f = flows.get(key) or FlowAccount(client_id=cid, practice=practice, firm_id=pid)
        flows[key] = replace(
            f, wip_cents=f.wip_cents + w, wip_tenths=f.wip_tenths + w * 10 // cfg.wip_rate_cents
        )
    bills = list(billing.bills)
    bill_id = billing.next_bill_id
    for i, ((cid, practice, _), amount) in enumerate(zip(targets, ars, strict=True)):
        if amount <= 0:
            continue
        bills.append(
            Bill(
                id=bill_id,
                firm_id=pid,
                client_id=cid,
                matter_id=None,
                practice=practice,
                model="hourly",
                kind="fees",
                issued_turn=state.turn,
                due_turn=state.turn + 1 + i % cfg.ar_due_months,
                standard_cents=amount,
                billed_cents=amount,
            )
        )
        bill_id += 1
    billing = replace(
        billing,
        flows=tuple(sorted(flows.values(), key=lambda f: (f.client_id, f.practice, f.firm_id))),
        bills=tuple(bills),
        next_bill_id=bill_id,
    )
    return replace(state, billing=billing), len(targets)


def _annuities(state: GameState, deal: Deal, s: Sheet, balance: Balance) -> GameState:
    from ptk.sim.founder.models import Annuity, with_annuity

    if s.annuities <= 0:
        return state
    months = balance.mergers.books.annuity_years * 12  # tunable-exempt: months in a year
    ann = Annuity(
        person_id=-deal.id,  # the other firm's retired partners, together (ADR PT-0016 2)
        firm_id=state.player.id,
        monthly_cents=max(1, s.annuities // months),
        remaining_cents=s.annuities,
        start_turn=state.turn + 1,
        end_turn=state.turn + 1 + months,
    )
    return replace(state, founder_life=with_annuity(state.founder_life, ann))


def _office(
    state: GameState,
    firm: RivalFirm,
    city: str,
    people: list[Person],
    rng: RngFactory,
    data: GameData,
    balance: Balance,
) -> tuple[GameState, int | None, int]:
    """(state, the carried office's id or None, the surrender's cost)."""
    from ptk.sim.geo.cities import office_in
    from ptk.sim.geo.models import Office, with_office

    pid = state.player.id
    rent = monthly_rent(firm, data, balance)
    if city == state.player.home_city or office_in(state, pid, city) is not None:
        return state, None, rent * balance.mergers.integration.surrender_months
    h = hidden(rng, firm, balance)
    oid = state.geo.next_office_id
    office = Office(
        id=oid,
        firm_id=pid,
        city=city,
        seats=max(1, len(people)),
        opened_turn=state.turn,
        how="merger",
        term_months=lease_months(h),
        rent_cents=rent,
        fit_out_cents=0,
        lease_start_turn=state.turn + 1,
    )
    return replace(state, geo=with_office(state.geo, office)), oid, 0


def _end_rival(state: GameState, firm: RivalFirm, people: list[Person]) -> GameState:
    from ptk.sim.rivals.history import record
    from ptk.sim.rivals.history import with_firm as rival_with
    from ptk.sim.rivals.people import drop_member

    rivals = state.rivals
    for m in rivals.members_of(firm.id):
        rivals = drop_member(rivals, m.person_id)
    ended = replace(firm, status="merged", ended_turn=state.turn, successor=PLAYER_PANEL_KEY)
    rivals = rival_with(rivals, ended)
    rivals, _ = record(
        rivals, ended, state.turn, "merged", f"{firm.name} merges with {state.player.name}"
    )
    return replace(state, rivals=rivals)


def _apply_terms(
    state: GameState, deal: Deal, firm: RivalFirm, people: list[Person], ours: Side, theirs: Side
) -> GameState:
    from ptk.sim.partnership.common import put

    assert deal.terms is not None
    t = deal.terms
    me = state.player
    name = {"ours": me.name, "theirs": firm.name, "combined": f"{me.name.split()[0]} {firm.short}"}[
        t.name
    ]
    state = with_firm(state, replace(me, name=name, rate_index=merged_card(ours, theirs, t.rates)))
    fp = state.partnership.of(me.id)
    assert fp is not None
    fp = replace(fp, agreement=replace(fp.agreement, comp_system=t.comp_system))  # type: ignore[arg-type]
    if t.mp == "theirs":
        seniors = sorted(
            (p for p in people if p.level == EQUITY), key=lambda p: (-p.book_cents, p.id)
        )
        if seniors:
            fp = replace(fp, ousted_mp_id=fp.mp_id, mp_id=seniors[0].id)
    return put(state, fp)


def _contested(
    state: GameState, firm: RivalFirm, data: GameData, balance: Balance
) -> tuple[str, ...]:
    """PT-M12: the practices where each firm had at least `integration.contested_min_share` of
    its own lawyers before closing (the player's by home practice, the other's by pool)."""
    from ptk.sim.partnership.common import home_practice

    floor = balance.mergers.integration.contested_min_share
    mine: dict[str, int] = {}
    for p in state.staff_ids(state.player.id):
        person = state.person(p)
        if data.role(person.role).kind == "lawyer":
            key = home_practice(person, data)
            mine[key] = mine.get(key, 0) + 1
    n_mine = sum(mine.values())
    n_theirs = firm.lawyers
    if n_mine <= 0 or n_theirs <= 0:
        return ()
    theirs = {pool.practice: pool.lawyers for pool in firm.pools}
    return tuple(
        sorted(
            k for k in mine if mine[k] / n_mine >= floor and theirs.get(k, 0.0) / n_theirs >= floor
        )
    )


def close_merger(
    state: GameState, deal: Deal, rng: RngFactory, data: GameData, balance: Balance
) -> tuple[GameState, tuple[LedgerEntry, ...], tuple[LogItem, ...]]:
    firm = state.rivals.firm(deal.rival_id)
    terms = deal.terms
    assert firm is not None and terms is not None
    pid = state.player.id
    ours, theirs = player_side(state, data, balance), rival_side(firm, data)
    contested = _contested(state, firm, data, balance)  # PT-M12: before the people join
    before = state.partnership.of(pid)
    budgets_before = (
        [(p.person_id, p.budget_cents) for p in before.equity_partners] if before else []
    )
    state, deal, logs = clear(state, deal, rng, balance)
    s = sheet(firm, rng, data, balance)
    city = data.geo.city_key(firm.hq) or state.player.home_city
    people, _kinds = _people(state, deal, firm, city, rng, data, balance)
    # their equity partners' books: their share of the firm's revenue
    equity = [p for p in people if p.level == EQUITY]
    book_each = round(theirs.revenue_cents * balance.rivals.key_book_share / max(1, len(equity)))
    people = [
        replace(p, book_cents=max(p.book_cents, book_each)) if p.level == EQUITY else p
        for p in people
    ]
    state = _hire_all(state, people, rng, data, balance)
    state = _partners(state, people, s, terms.our_share_bp, ours, theirs, balance)
    state = _clients(state, deal, firm, people, data)
    state, _ = _working_capital(state, deal, s, balance)
    state = _annuities(state, deal, s, balance)
    state, office_id, surrender = _office(state, firm, city, people, rng, data, balance)
    entries = [
        LedgerEntry(
            turn=state.turn,
            firm_id=pid,
            memo=f"Merger: the books of {firm.name}",
            lines=merger_office_lines(s, office_id),
        )
    ]
    if surrender > 0:
        entries.append(
            LedgerEntry.transfer(
                turn=state.turn,
                firm_id=pid,
                memo=f"Merger: {firm.name}'s lease surrendered",
                debit=RENT,
                credit=CASH,
                amount=surrender,
            )
        )
    fp = state.partnership.of(pid)
    if fp is not None:
        from ptk.sim.partnership.common import put

        # the carried WIP and receivables are not this year's growth in working capital (the
        # cash-basis profit, ADR PT-0003 3): they came with the other firm's capital
        state = put(
            state,
            replace(
                fp,
                wc_closed_cents=fp.wc_closed_cents + s.wip + s.receivables,
                facility_cents=fp.facility_cents
                + round(s.revolver * balance.mergers.books.facility_mult),
            ),
        )
    name_before = firm.name
    state = _end_rival(state, firm, people)
    state = _apply_terms(state, deal, firm, people, ours, theirs)
    from ptk.sim.mergers.terms import card_rise

    rise = card_rise(ours, theirs, terms.rates)[0]
    fp = state.partnership.of(pid)
    assert fp is not None
    their_ids = {p.id for p in people}
    integ = Integration(
        deal_id=deal.id,
        rival_key=firm.key,
        name=name_before,
        closed_turn=state.turn,
        until_turn=state.turn + balance.mergers.integration.months,
        clash=clash(ours, theirs, balance),
        their_people=tuple(sorted(their_ids)),
        their_partners=tuple(sorted(p.id for p in equity)),
        our_partners=tuple(
            sorted(p.person_id for p in fp.equity_partners if p.person_id not in their_ids)
        ),
        pep_before=tuple(
            sorted(
                [(p, b) for p, b in budgets_before if p not in their_ids]
                + [(p.id, theirs.pep_cents) for p in equity]
            )
        ),
        card_rise=rise,
        balk_clients=tuple(b.client_id for b in kept_book(deal)) if rise > 0 else (),
        surrender_cents=surrender,
        lawyers_at_closing=ours.lawyers + len(people),
        partners_at_closing=len(fp.equity_partners),
        contested=contested,
    )
    deal = replace(deal, stage="closed", stage_turn=state.turn, ended_turn=state.turn)
    ms = with_integration(with_deal(state.mergers, deal), integ)
    state = put_mergers(state, ms)
    logs = (
        *logs,
        inbox_item(
            state.turn,
            pid,
            "merger_closed",
            link_kind="mergers",
            link_id=deal.id,
            firm=name_before,
            name=state.player.name,
            lawyers=len(people),
            clients=len(kept_book(deal)),
        ),
    )
    return state, tuple(entries), logs


def december_budgets(state: GameState, balance: Balance) -> GameState:
    """Phase 7, December, after the allocation: a partner who joined by a merger this year
    keeps next year's budget at their points' share of the year's profit (the allocation
    weights a part year, as PT-M7c found for December admissions: a part-year budget left
    them seeing almost no comp, and flight took them)."""
    from ptk.sim.partnership.common import put, ym
    from ptk.sim.partnership.models import with_partner

    if ym(state)[1] != 12 or not state.mergers.integrations:  # tunable-exempt: December
        return state
    fp = state.partnership.of(state.player.id)
    if fp is None or fp.last_profit_cents is None:
        return state
    year_start = state.turn - 11  # tunable-exempt: this year's first turn
    joined: set[int] = set()
    for i in state.mergers.integrations:
        if i.closed_turn >= year_start:
            joined.update(i.their_partners)
    if not joined:
        return state
    total = sum(p.points for p in fp.equity_partners) or 1.0
    pool = (
        max(0, fp.last_profit_cents) * (BP_DENOMINATOR - fp.agreement.retain_bp) // BP_DENOMINATOR
    )
    for p in fp.equity_partners:
        if p.person_id in joined:
            budget = max(p.budget_cents, round(pool * p.points / total))
            fp = with_partner(fp, replace(p, budget_cents=budget, budget_base_cents=budget))
    return put(state, fp)
