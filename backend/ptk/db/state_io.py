"""Load the game state from a save and write a turn's results (ADR-0004)."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import replace

from sqlalchemy import func, insert, select
from sqlalchemy.orm import Session

from ptk.db.billing_io import load_billing, write_billing, write_client_book
from ptk.db.events_io import load_events, write_events
from ptk.db.inbox import inbox_rows
from ptk.db.market_io import insert_market, load_market, write_market
from ptk.db.models import (
    CandidateRow,
    EmploymentRow,
    FirmRow,
    LedgerEntryRow,
    LedgerLineRow,
    OfferRow,
    PersonRow,
    PersonStateRow,
    RevealRow,
    SaveMetaRow,
    SearchRow,
    TurnLogRow,
    TurnSnapshotRow,
)
from ptk.db.org_io import load_org, write_org
from ptk.db.partnership_io import load_partnership, write_partnership
from ptk.db.rivals_io import insert_rivals, load_rivals, write_panels, write_rivals
from ptk.sim.billing.models import ClientBookEntry
from ptk.sim.data_models import InboxTemplate
from ptk.sim.hiring.models import Candidate, Offer, PayPolicy, PersonState, Search
from ptk.sim.ledger import LedgerEntry
from ptk.sim.log import LogItem
from ptk.sim.money import Cents
from ptk.sim.people.models import (
    AttrSet,
    Employment,
    Familiarity,
    HiddenTraits,
    Person,
    Personality,
    RevealRecord,
    RevealState,
    Skills,
)
from ptk.sim.snapshot import TurnSnapshot
from ptk.sim.state import FirmState, GameState, SaveMeta

META_ID = 1
_SIGN = 2**63  # SQLite integers are signed 64-bit; seeds are 0..2**64-1


def seed_to_db(seed: int) -> int:
    return seed - _SIGN


def seed_from_db(value: int) -> int:
    return value + _SIGN


def insert_new(session: Session, state: GameState, entries: tuple[LedgerEntry, ...]) -> None:
    meta = state.save_meta
    session.add(
        SaveMetaRow(
            id=META_ID,
            name=meta.name,
            master_seed=seed_to_db(meta.master_seed),
            scenario_id=meta.scenario_id,
            difficulty=meta.difficulty,
            start_year=meta.start_ym[0],
            start_month=meta.start_ym[1],
            current_turn=state.turn,
            game_state=meta.game_state,
            ended_turn=meta.ended_turn,
        )
    )
    for firm in state.firms:
        session.add(
            FirmRow(
                id=firm.id,
                name=firm.name,
                is_player=firm.is_player,
                stage=firm.stage,
                founded_turn=firm.founded_turn,
                home_city=firm.home_city,
                pay_policy_mode=firm.pay_policy.mode,
                pay_policy_bp=firm.pay_policy.pct_bp,
                conflict_checks=firm.conflict_checks,
                pro_bono_credit_hours=firm.pro_bono_credit_hours,
                pro_bono_avg_tenths=firm.pro_bono_avg_tenths,
                rate_rise_bp=firm.rate_rise_bp,
                rate_index=firm.rate_index,
                rate_card=_card_json(firm.rate_card),  # PT-M7b
                billable_target_hours=firm.billable_target_hours,
            )
        )
    session.flush()
    write_people(session, state)
    write_org(session, state)
    insert_market(session, state.market)
    insert_rivals(session, state.rivals)  # PT-M5
    write_partnership(session, state.partnership)
    write_events(session, state.events)
    write_entries(session, entries)


def load_state(session: Session) -> GameState:
    row = session.get(SaveMetaRow, META_ID)
    if row is None:
        raise LookupError("save has no save_meta row")
    meta = SaveMeta(
        name=row.name,
        master_seed=seed_from_db(row.master_seed),
        scenario_id=row.scenario_id,
        difficulty=row.difficulty,
        start_ym=(row.start_year, row.start_month),
        game_state=row.game_state,  # type: ignore[arg-type]
        ended_turn=row.ended_turn,
    )
    rivals = load_rivals(session)  # PT-M5: rival firms' rows are not the player's firms
    rival_ids = {f.id for f in rivals.firms}
    firms = tuple(
        FirmState(
            id=f.id,
            name=f.name,
            is_player=f.is_player,
            stage=f.stage,
            founded_turn=f.founded_turn,
            home_city=f.home_city,
            pay_policy=PayPolicy(mode=f.pay_policy_mode, pct_bp=f.pay_policy_bp),  # type: ignore[arg-type]
            conflict_checks=f.conflict_checks,
            pro_bono_credit_hours=f.pro_bono_credit_hours,
            pro_bono_avg_tenths=f.pro_bono_avg_tenths,
            rate_rise_bp=f.rate_rise_bp,
            rate_index=f.rate_index,
            rate_card=_card_tuple(f.rate_card),  # PT-M7b
            billable_target_hours=f.billable_target_hours,
        )
        for f in session.scalars(select(FirmRow).order_by(FirmRow.id))
        if f.id not in rival_ids
    )
    return GameState(
        save_meta=meta,
        turn=row.current_turn,
        firms=firms,
        people=tuple(_person(r) for r in session.scalars(select(PersonRow).order_by(PersonRow.id))),
        employments=tuple(
            Employment(
                id=e.id,
                person_id=e.person_id,
                firm_id=e.firm_id,
                start_turn=e.start_turn,
                end_turn=e.end_turn,
                status=e.status,  # type: ignore[arg-type]
                end_reason=e.end_reason,  # type: ignore[arg-type]
                salary_cents=e.salary_cents,
            )
            for e in session.scalars(select(EmploymentRow).order_by(EmploymentRow.id))
        ),
        reveals=tuple(
            _reveal(r)
            for r in session.scalars(
                select(RevealRow).order_by(RevealRow.observer_firm_id, RevealRow.person_id)
            )
        ),
        org=load_org(session),
        billing=load_billing(
            session, row.current_turn, next((f.id for f in firms if f.is_player), None)
        ),
        market=load_market(session, row.current_turn),
        partnership=load_partnership(session),
        events=load_events(session),
        searches=tuple(
            _search(r) for r in session.scalars(select(SearchRow).order_by(SearchRow.id))
        ),
        candidates=tuple(
            _candidate(r)
            for r in session.scalars(select(CandidateRow).order_by(CandidateRow.person_id))
        ),
        offers=tuple(_offer(r) for r in session.scalars(select(OfferRow).order_by(OfferRow.id))),
        person_states=tuple(
            PersonState(
                person_id=r.person_id,
                energy=r.energy,
                morale=r.morale,
                pro_bono_ytd_tenths=r.pro_bono_ytd_tenths,
            )
            for r in session.scalars(select(PersonStateRow).order_by(PersonStateRow.person_id))
        ),
        rivals=rivals,
    )


# --- Hiring (PT-M1b) ------------------------------------------------------------------------


def _search(r: SearchRow) -> Search:
    return Search(
        id=r.id,
        firm_id=r.firm_id,
        role=r.role,
        channel=r.channel,  # type: ignore[arg-type]
        actor_id=r.actor_id,
        opened_turn=r.opened_turn,
        status=r.status,  # type: ignore[arg-type]
        closed_turn=r.closed_turn,
        level=r.level,
        school_tiers=tuple(json.loads(r.school_tiers_json)),
        plan_id=r.plan_id,
    )


def _candidate(r: CandidateRow) -> Candidate:
    return Candidate(
        person_id=r.person_id,
        firm_id=r.firm_id,
        search_id=r.search_id,
        channel=r.channel,  # type: ignore[arg-type]
        ask_cents=r.ask_cents,
        created_turn=r.created_turn,
        expires_turn=r.expires_turn,
        status=r.status,  # type: ignore[arg-type]
        resolved_turn=r.resolved_turn,
        interviewed_turn=r.interviewed_turn,
    )


def _offer(r: OfferRow) -> Offer:
    return Offer(
        id=r.id,
        firm_id=r.firm_id,
        candidate_id=r.candidate_id,
        actor_id=r.actor_id,
        salary_cents=r.salary_cents,
        made_turn=r.made_turn,
        start_turn=r.start_turn,
        status=r.status,  # type: ignore[arg-type]
        resolved_turn=r.resolved_turn,
        plan_id=r.plan_id,
        unit_id=r.unit_id,
    )


def write_hiring(session: Session, state: GameState) -> None:
    """Upsert searches, candidates, offers and person state (current-state tables)."""
    for s in state.searches:
        session.merge(
            SearchRow(
                id=s.id,
                firm_id=s.firm_id,
                role=s.role,
                channel=s.channel,
                actor_id=s.actor_id,
                opened_turn=s.opened_turn,
                status=s.status,
                closed_turn=s.closed_turn,
                level=s.level,
                school_tiers_json=json.dumps(list(s.school_tiers)),
                plan_id=s.plan_id,
            )
        )
    session.flush()
    for c in state.candidates:
        session.merge(
            CandidateRow(
                person_id=c.person_id,
                firm_id=c.firm_id,
                search_id=c.search_id,
                channel=c.channel,
                ask_cents=c.ask_cents,
                created_turn=c.created_turn,
                expires_turn=c.expires_turn,
                status=c.status,
                resolved_turn=c.resolved_turn,
                interviewed_turn=c.interviewed_turn,
            )
        )
    for o in state.offers:
        session.merge(
            OfferRow(
                id=o.id,
                firm_id=o.firm_id,
                candidate_id=o.candidate_id,
                actor_id=o.actor_id,
                salary_cents=o.salary_cents,
                made_turn=o.made_turn,
                start_turn=o.start_turn,
                status=o.status,
                resolved_turn=o.resolved_turn,
                plan_id=o.plan_id,
                unit_id=o.unit_id,
            )
        )
    for ps in state.person_states:
        session.merge(
            PersonStateRow(
                person_id=ps.person_id,
                energy=ps.energy,
                morale=ps.morale,
                pro_bono_ytd_tenths=ps.pro_bono_ytd_tenths,
            )
        )


# --- People -----------------------------------------------------------------------------------


def _attrs(values: AttrSet) -> str:
    return json.dumps([[k, v] for k, v in values.items])


def _items(text: str) -> tuple[tuple[str, float], ...]:
    return tuple((str(k), float(v)) for k, v in json.loads(text))


def _person(r: PersonRow) -> Person:
    return Person(
        id=r.id,
        first_name=r.first_name,
        last_name=r.last_name,
        birth_turn=r.birth_turn,
        role=r.role,
        level=r.level,
        skills=Skills(_items(r.skills_json)),
        personality=Personality(_items(r.personality_json)),
        hidden=HiddenTraits(_items(r.hidden_json)),
        potential_ability=r.potential_ability,
        familiarity=Familiarity(_items(r.familiarity_json)),
        familiarity_peak=Familiarity(_items(r.familiarity_peak_json)),
        interests=tuple(json.loads(r.interests_json)),
        work_style=r.work_style,
        tags=tuple(json.loads(r.tags_json)),
        school_tier=r.school_tier,
        bar_admissions=tuple(json.loads(r.bar_admissions_json)),
        city=r.city,
        strain=r.strain,
        burnout_since=r.burnout_since,
        last_burnout_turn=r.last_burnout_turn,
        book_cents=r.book_cents,
        portability_bp=r.portability_bp,
        is_founder=r.is_founder,
        founding_partner=r.founding_partner,
        background=r.background,
        real=r.real,
    )


def _person_row(p: Person) -> PersonRow:
    return PersonRow(
        id=p.id,
        first_name=p.first_name,
        last_name=p.last_name,
        birth_turn=p.birth_turn,
        role=p.role,
        level=p.level,
        skills_json=_attrs(p.skills),
        personality_json=_attrs(p.personality),
        hidden_json=_attrs(p.hidden),
        potential_ability=p.potential_ability,
        familiarity_json=_attrs(p.familiarity),
        familiarity_peak_json=_attrs(p.familiarity_peak),
        interests_json=json.dumps(list(p.interests)),
        work_style=p.work_style,
        tags_json=json.dumps(list(p.tags)),
        school_tier=p.school_tier,
        bar_admissions_json=json.dumps(list(p.bar_admissions)),
        city=p.city,
        strain=p.strain,
        burnout_since=p.burnout_since,
        last_burnout_turn=p.last_burnout_turn,
        book_cents=p.book_cents,
        portability_bp=p.portability_bp,
        is_founder=p.is_founder,
        founding_partner=p.founding_partner,
        background=p.background,
        real=p.real,
    )


def _reveal(r: RevealRow) -> RevealState:
    return RevealState(
        observer_firm_id=r.observer_firm_id,
        person_id=r.person_id,
        attributes=tuple(
            (str(k), RevealRecord(hw=float(hw), offset=float(o), last_updated_turn=int(t)))
            for k, hw, o, t in json.loads(r.attributes_json)
        ),
        profile_revealed_turn=r.profile_revealed_turn,
        revealed_tags=tuple((str(k), int(t)) for k, t in json.loads(r.revealed_tags_json)),
    )


def write_people(session: Session, state: GameState) -> None:
    """Upsert every person, employment and reveal record (current-state tables)."""
    for person in state.people:
        session.merge(_person_row(person))
    session.flush()
    for e in state.employments:
        session.merge(
            EmploymentRow(
                id=e.id,
                person_id=e.person_id,
                firm_id=e.firm_id,
                start_turn=e.start_turn,
                end_turn=e.end_turn,
                status=e.status,
                end_reason=e.end_reason,
                salary_cents=e.salary_cents,
            )
        )
    for rv in state.reveals:
        session.merge(
            RevealRow(
                observer_firm_id=rv.observer_firm_id,
                person_id=rv.person_id,
                attributes_json=json.dumps(
                    [[k, r.hw, r.offset, r.last_updated_turn] for k, r in rv.attributes]
                ),
                profile_revealed_turn=rv.profile_revealed_turn,
                revealed_tags_json=json.dumps([[k, t] for k, t in rv.revealed_tags]),
            )
        )
    write_hiring(session, state)


def ledger_balances(session: Session) -> dict[tuple[int, str], Cents]:
    stmt = (
        select(LedgerEntryRow.firm_id, LedgerLineRow.account, func.sum(LedgerLineRow.amount_cents))
        .join(LedgerEntryRow, LedgerLineRow.entry_id == LedgerEntryRow.id)
        .group_by(LedgerEntryRow.firm_id, LedgerLineRow.account)
    )
    return {(int(f), str(a)): int(total) for f, a, total in session.execute(stmt)}


def write_entries(session: Session, entries: tuple[LedgerEntry, ...]) -> None:
    if len(entries) > BULK_ENTRIES:  # PT-M5: rivals post an entry each a month
        _bulk_entries(session, entries)
        return
    for entry in entries:
        row = LedgerEntryRow(turn=entry.turn, firm_id=entry.firm_id, memo=entry.memo)
        session.add(row)
        session.flush()
        session.add_all(
            LedgerLineRow(
                entry_id=row.id,
                account=line.account,
                amount_cents=line.amount,
                practice=line.practice,
                office_id=line.office_id,
            )
            for line in entry.lines
        )


BULK_ENTRIES = 20  # tunable-exempt: entries above which one bulk insert is faster


def _bulk_entries(session: Session, entries: tuple[LedgerEntry, ...]) -> None:
    """The same rows as one entry at a time, in order, with ids assigned here."""
    session.flush()
    first = (session.scalar(select(func.max(LedgerEntryRow.id))) or 0) + 1
    session.execute(
        insert(LedgerEntryRow),
        [
            {"id": first + i, "turn": e.turn, "firm_id": e.firm_id, "memo": e.memo}
            for i, e in enumerate(entries)
        ],
    )
    session.execute(
        insert(LedgerLineRow),
        [
            {
                "entry_id": first + i,
                "account": line.account,
                "amount_cents": line.amount,
                "practice": line.practice,
                "office_id": line.office_id,
            }
            for i, e in enumerate(entries)
            for line in e.lines
        ],
    )


def write_log(
    session: Session,
    state: GameState,
    log_items: tuple[LogItem, ...],
    templates: Mapping[str, InboxTemplate] | None,
) -> None:
    """The turn log, and the player firm's templated items as inbox rows."""
    session.add_all(
        TurnLogRow(turn=i.turn, firm_id=i.firm_id, kind=i.kind, message=i.message)
        for i in log_items
    )
    if templates is not None:
        session.add_all(inbox_rows(log_items, state.player.id, templates))


def write_turn(
    session: Session,
    new_state: GameState,
    entries: tuple[LedgerEntry, ...],
    log_items: tuple[LogItem, ...],
    snapshot: TurnSnapshot,
    templates: Mapping[str, InboxTemplate] | None = None,
    client_book: tuple[ClientBookEntry, ...] = (),
) -> None:
    write_entries(session, entries)
    write_client_book(session, client_book)
    write_log(session, new_state, log_items, templates)
    session.add_all(
        TurnSnapshotRow(turn=snapshot.turn, firm_id=f.firm_id, kpis_json=json.dumps(f.kpis()))
        for f in snapshot.firms
    )
    meta = session.get(SaveMetaRow, META_ID)
    assert meta is not None
    meta.current_turn = new_state.turn
    meta.game_state = new_state.save_meta.game_state
    meta.ended_turn = new_state.save_meta.ended_turn
    write_firms(session, new_state)
    write_people(session, new_state)
    write_org(session, new_state)
    write_market(session, new_state.market)
    write_events(session, new_state.events)
    write_billing(session, new_state.billing)
    write_rivals(session, new_state.rivals)  # PT-M5
    write_panels(session, new_state.market)
    write_partnership(session, new_state.partnership)


def write_firms(session: Session, state: GameState) -> None:
    for firm in state.firms:
        row = session.get(FirmRow, firm.id)
        assert row is not None
        row.name, row.stage = firm.name, firm.stage
        row.pay_policy_mode, row.pay_policy_bp = firm.pay_policy.mode, firm.pay_policy.pct_bp
        row.conflict_checks = firm.conflict_checks
        row.pro_bono_credit_hours = firm.pro_bono_credit_hours  # PT-M7a
        row.pro_bono_avg_tenths = firm.pro_bono_avg_tenths
        row.rate_rise_bp = firm.rate_rise_bp
        row.rate_index = firm.rate_index
        row.rate_card = _card_json(firm.rate_card)  # PT-M7b
        row.billable_target_hours = firm.billable_target_hours


def with_turn(state: GameState, turn: int) -> GameState:
    return replace(state, turn=turn)


def _card_json(card: tuple[tuple[str, int], ...]) -> str:
    """PT-M7b: a firm's card by practice as stored ({practice: bp}, keys sorted)."""
    return json.dumps(dict(card), sort_keys=True)


def _card_tuple(text: str) -> tuple[tuple[str, int], ...]:
    return tuple(sorted((str(k), int(v)) for k, v in json.loads(text or "{}").items()))
