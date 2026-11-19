"""Load the game state from a save and write a turn's results (ADR-0004)."""

from __future__ import annotations

import json
from dataclasses import replace

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ptk.db.models import (
    EmploymentRow,
    FirmRow,
    LedgerEntryRow,
    LedgerLineRow,
    PersonRow,
    RevealRow,
    SaveMetaRow,
    TurnLogRow,
    TurnSnapshotRow,
)
from ptk.db.org_io import load_org, write_org
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
            )
        )
    session.flush()
    write_people(session, state)
    write_org(session, state)
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
    firms = tuple(
        FirmState(
            id=f.id,
            name=f.name,
            is_player=f.is_player,
            stage=f.stage,
            founded_turn=f.founded_turn,
            home_city=f.home_city,
        )
        for f in session.scalars(select(FirmRow).order_by(FirmRow.id))
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


def ledger_balances(session: Session) -> dict[tuple[int, str], Cents]:
    stmt = (
        select(LedgerEntryRow.firm_id, LedgerLineRow.account, func.sum(LedgerLineRow.amount_cents))
        .join(LedgerEntryRow, LedgerLineRow.entry_id == LedgerEntryRow.id)
        .group_by(LedgerEntryRow.firm_id, LedgerLineRow.account)
    )
    return {(int(f), str(a)): int(total) for f, a, total in session.execute(stmt)}


def write_entries(session: Session, entries: tuple[LedgerEntry, ...]) -> None:
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


def write_turn(
    session: Session,
    new_state: GameState,
    entries: tuple[LedgerEntry, ...],
    log_items: tuple[LogItem, ...],
    snapshot: TurnSnapshot,
) -> None:
    write_entries(session, entries)
    session.add_all(
        TurnLogRow(turn=i.turn, firm_id=i.firm_id, kind=i.kind, message=i.message)
        for i in log_items
    )
    session.add_all(
        TurnSnapshotRow(turn=snapshot.turn, firm_id=f.firm_id, kpis_json=json.dumps(f.kpis()))
        for f in snapshot.firms
    )
    meta = session.get(SaveMetaRow, META_ID)
    assert meta is not None
    meta.current_turn = new_state.turn
    meta.game_state = new_state.save_meta.game_state
    meta.ended_turn = new_state.save_meta.ended_turn
    for firm in new_state.firms:
        row = session.get(FirmRow, firm.id)
        assert row is not None
        row.name, row.stage = firm.name, firm.stage
    write_people(session, new_state)
    write_org(session, new_state)


def with_turn(state: GameState, turn: int) -> GameState:
    return replace(state, turn=turn)
