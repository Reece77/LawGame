"""Load and write clients, judges, relationships and matters (schema v5, PT-M3a).

Clients and judges are written once, at game creation. Relationships, matters, appearances,
origination and the month's demand are current-state tables, rewritten in place (deleted and
bulk-inserted: they are small). The month's hours are appended to `hours_log`; the state
keeps the last month's, read back from the log.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from sqlalchemy import delete, func, insert, select
from sqlalchemy.orm import Session

from ptk.db.models import (
    AppearanceRow,
    ClientRow,
    HoursLogRow,
    JudgeRow,
    MarketDemandRow,
    MatterRow,
    OriginationRow,
    RelationshipRow,
)
from ptk.sim.matters.models import (
    Appearance,
    Client,
    GeneralCounsel,
    HoursRecord,
    Judge,
    JudgeTraits,
    MarketState,
    Matter,
    Origination,
    Relationship,
    SettlementOffer,
    TeamMember,
)
from ptk.sim.people.models import Personality


def _items(values: Any) -> list[list[Any]]:
    return [[k, v] for k, v in values.items]


def _attrs(raw: list[list[Any]]) -> tuple[tuple[str, float], ...]:
    return tuple((str(k), float(v)) for k, v in raw)


# --- Clients and judges (written once) --------------------------------------------------------


def _client_data(c: Client) -> str:
    return json.dumps(
        {
            "country": c.country,
            "revenue_bn": c.revenue_bn,
            "size_class": c.size_class,
            "price_sensitivity": c.price_sensitivity,
            "loyalty": c.loyalty,
            "panel": list(c.panel),
            "gc": {
                "first_name": c.gc.first_name,
                "last_name": c.gc.last_name,
                "birth_turn": c.gc.birth_turn,
                "personality": _items(c.gc.personality),
            },
        }
    )


@lru_cache(maxsize=1 << 14)
def _client(cid: int, name: str, sector: str, real: bool, data_json: str) -> Client:
    """Memoised on the row's content (clients never change after game creation)."""
    d = json.loads(data_json)
    gc = d["gc"]
    return Client(
        id=cid,
        name=name,
        sector=sector,
        country=d["country"],
        real=real,
        revenue_bn=float(d["revenue_bn"]),
        size_class=d["size_class"],
        price_sensitivity=float(d["price_sensitivity"]),
        loyalty=float(d["loyalty"]),
        gc=GeneralCounsel(
            first_name=gc["first_name"],
            last_name=gc["last_name"],
            birth_turn=int(gc["birth_turn"]),
            personality=Personality(_attrs(gc["personality"])),
        ),
        panel=tuple(d["panel"]),
    )


def insert_market(session: Session, market: MarketState) -> None:
    """Game creation: the client universe and judges, then the current-state tables."""
    session.execute(
        insert(ClientRow),
        [
            {
                "id": c.id,
                "name": c.name,
                "sector": c.sector,
                "real": c.real,
                "data_json": _client_data(c),
            }
            for c in market.clients
        ],
    )
    if market.judges:
        session.execute(
            insert(JudgeRow),
            [
                {
                    "id": j.id,
                    "court": j.court,
                    "first_name": j.first_name,
                    "last_name": j.last_name,
                    "traits_json": json.dumps(_items(j.traits)),
                    "real": j.real,
                }
                for j in market.judges
            ],
        )
    write_market(session, market, append_hours=False)


# --- Relationships and matters ------------------------------------------------------------------


def _rel_data(r: Relationship) -> str:
    return json.dumps(
        {
            "practices": list(r.practices),
            "since_turn": r.since_turn,
            "last_instructed_turn": r.last_instructed_turn,
            "advance_waiver": r.advance_waiver,
            "lost_share": r.lost_share,
            "fees": list(r.fees),
            "intro_turns": [[p, t] for p, t in r.intro_turns],
        }
    )


def _relationship(row: RelationshipRow) -> Relationship:
    d = json.loads(row.data_json)
    return Relationship(
        client_id=row.client_id,
        firm_id=row.firm_id,
        score=row.score,
        partner_id=row.partner_id,
        practices=tuple(d["practices"]),
        since_turn=int(d["since_turn"]),
        last_instructed_turn=d["last_instructed_turn"],
        advance_waiver=bool(d["advance_waiver"]),
        lost_share=float(d["lost_share"]),
        fees=tuple(int(x) for x in d["fees"]),
        intro_turns=tuple((str(p), int(t)) for p, t in d["intro_turns"]),
    )


_MATTER_SCALARS = (
    "kind_key",
    "kind",
    "name",
    "planned_months",
    "expected_fees_cents",
    "hours_needed_tenths",
    "adverse_client_id",
    "adverse_name",
    "critical",
    "flagged",
    "checked",
    "waiver",
    "hidden_conflict",
    "originator_id",
    "lead_id",
    "auto_staff",
    "phase_index",
    "phase_progress",
    "worked_tenths",
    "wip_cents",
    "craft_hours",
    "craft_weight",
    "under_months",
    "errors_caught",
    "errors_escaped",
    "missed_deadlines",
    "court",
    "judge_id",
    "stakes_cents",
    "merits",
    "opposing_quality",
    "outcome",
    "quality",
)


def _matter_data(m: Matter) -> str:
    d: dict[str, Any] = {k: getattr(m, k) for k in _MATTER_SCALARS}
    d["team"] = [[t.person_id, t.role, t.planned_tenths] for t in m.team]
    s = m.settlement
    d["settlement"] = None if s is None else [s.fraction_bp, s.made_turn, s.expires_turn]
    return json.dumps(d)


def _matter(row: MatterRow) -> Matter:
    d = json.loads(row.data_json)
    s = d.pop("settlement")
    team = d.pop("team")
    return Matter(
        id=row.id,
        firm_id=row.firm_id,
        client_id=row.client_id,
        practice=row.practice,
        status=row.status,  # type: ignore[arg-type]
        opened_turn=row.opened_turn,
        closed_turn=row.closed_turn,
        team=tuple(TeamMember(person_id=p, role=r, planned_tenths=t) for p, r, t in team),
        settlement=None if s is None else SettlementOffer(*s),
        **d,
    )


def write_market(session: Session, market: MarketState, *, append_hours: bool = True) -> None:
    """Rewrite the current-state tables; append the month's hours to the log."""
    for table in (RelationshipRow, MatterRow, AppearanceRow, OriginationRow, MarketDemandRow):
        session.execute(delete(table))
    if market.relationships:
        session.execute(
            insert(RelationshipRow),
            [
                {
                    "client_id": r.client_id,
                    "firm_id": r.firm_id,
                    "score": r.score,
                    "partner_id": r.partner_id,
                    "data_json": _rel_data(r),
                }
                for r in market.relationships
            ],
        )
    if market.matters:
        session.execute(
            insert(MatterRow),
            [
                {
                    "id": m.id,
                    "firm_id": m.firm_id,
                    "client_id": m.client_id,
                    "practice": m.practice,
                    "status": m.status,
                    "opened_turn": m.opened_turn,
                    "closed_turn": m.closed_turn,
                    "data_json": _matter_data(m),
                }
                for m in market.matters
            ],
        )
    if market.appearances:
        session.execute(
            insert(AppearanceRow),
            [
                {"person_id": a.person_id, "judge_id": a.judge_id, "tenths": a.tenths}
                for a in market.appearances
            ],
        )
    if market.originations:
        session.execute(
            insert(OriginationRow),
            [
                {"person_id": o.person_id, "year": o.year, "cents": o.cents}
                for o in market.originations
            ],
        )
    if market.demand_cents:
        session.execute(
            insert(MarketDemandRow),
            [
                {"practice": f"{i:02d}", "demand_cents": c}
                for i, c in enumerate(market.demand_cents)
            ],
        )
    if append_hours and market.hours:
        last = session.scalar(select(func.max(HoursLogRow.turn)))
        if last is None or last < market.hours[0].turn:  # an action re-writing the month adds none
            session.execute(
                insert(HoursLogRow),
                [
                    {
                        "turn": h.turn,
                        "person_id": h.person_id,
                        "client_id": h.client_id,
                        "practice": h.practice,
                        "matter_id": h.matter_id,
                        "tenths": h.tenths,
                        "substantive_tenths": h.substantive_tenths,
                        "value_cents": h.value_cents,
                    }
                    for h in market.hours
                ],
            )


def load_market(session: Session, current_turn: int) -> MarketState:
    """The market; `hours` holds the last month played's (turn current_turn - 1) records."""
    rows = session.execute(
        select(
            ClientRow.id, ClientRow.name, ClientRow.sector, ClientRow.real, ClientRow.data_json
        ).order_by(ClientRow.id)
    )
    clients = tuple(_client(*row) for row in rows)
    if not clients:
        return MarketState()
    last = session.scalar(select(func.max(HoursLogRow.turn)))
    hours: tuple[HoursRecord, ...] = ()
    if last is not None and last == current_turn - 1:
        hours = tuple(
            HoursRecord(
                turn=h.turn,
                person_id=h.person_id,
                client_id=h.client_id,
                practice=h.practice,
                matter_id=h.matter_id,
                tenths=h.tenths,
                substantive_tenths=h.substantive_tenths,
                value_cents=h.value_cents,
            )
            for h in session.scalars(
                select(HoursLogRow).where(HoursLogRow.turn == last).order_by(HoursLogRow.id)
            )
        )
    return MarketState(
        clients=clients,
        relationships=tuple(
            _relationship(r)
            for r in session.scalars(
                select(RelationshipRow).order_by(RelationshipRow.client_id, RelationshipRow.firm_id)
            )
        ),
        matters=tuple(
            _matter(r) for r in session.scalars(select(MatterRow).order_by(MatterRow.id))
        ),
        judges=tuple(
            Judge(
                id=j.id,
                court=j.court,
                first_name=j.first_name,
                last_name=j.last_name,
                traits=JudgeTraits(_attrs(json.loads(j.traits_json))),
                real=j.real,
            )
            for j in session.scalars(select(JudgeRow).order_by(JudgeRow.id))
        ),
        appearances=tuple(
            Appearance(person_id=a.person_id, judge_id=a.judge_id, tenths=a.tenths)
            for a in session.scalars(
                select(AppearanceRow).order_by(AppearanceRow.person_id, AppearanceRow.judge_id)
            )
        ),
        originations=tuple(
            Origination(person_id=o.person_id, year=o.year, cents=o.cents)
            for o in session.scalars(
                select(OriginationRow).order_by(OriginationRow.person_id, OriginationRow.year)
            )
        ),
        hours=hours,
        demand_cents=tuple(
            d.demand_cents
            for d in session.scalars(select(MarketDemandRow).order_by(MarketDemandRow.practice))
        ),
    )
