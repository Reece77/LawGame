"""Conflicts clearance (ADR PT-0009 4; ADR PT-0016 3).

Every client of both firms is checked. A merger's conflicts are (a) the player's open matters
adverse to a book client and (b) book engagements adverse to a client of the player's firm. A
verein's are the player's open matters adverse to a client on a member's panel.

Each asks the affected client for a waiver (an advance waiver always holds; otherwise
`waiver_base` + `waiver_rel` x relationship / 100, at most `waiver_max`; stream `merger_clear`,
one uniform per conflict in order). Without one, the merged firm keeps the better relationship:
the book client is not taken on (kept_ours), or the player's client leaves and its open matters
end `disqualified` (kept_theirs). A verein cannot drop its member's client: the player's matter
ends. Afterwards no open matter of the firm is adverse to one of its clients without a waiver.
"""

from __future__ import annotations

from dataclasses import replace

from ptk.sim.data_models import Balance
from ptk.sim.log import LogItem, inbox_item
from ptk.sim.matters.intake import with_matter
from ptk.sim.matters.models import MarketState
from ptk.sim.mergers import streams
from ptk.sim.mergers.models import BookClient, Conflict, Deal
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState

type Found = tuple[int, int, int | None]  # (our client, their client, our matter or None)


def member_clients(state: GameState, keys: frozenset[str]) -> frozenset[int]:
    if not keys:
        return frozenset()
    return frozenset(c.id for c in state.market.clients if keys.intersection(c.panel))


def find_conflicts(state: GameState, deal: Deal) -> list[Found]:
    firm_id = state.player.id
    market = state.market
    if deal.form == "verein":
        firm = state.rivals.firm(deal.rival_id)
        theirs = member_clients(state, frozenset({firm.key})) if firm is not None else frozenset()
        return [
            (m.client_id, m.adverse_client_id, m.id)
            for m in market.open_matters(firm_id)
            if m.adverse_client_id in theirs and not m.waiver
        ]
    book = {b.client_id for b in deal.book if b.kept}
    ours = {r.client_id for r in market.relationships if r.firm_id == firm_id}
    out: list[Found] = []
    for m in market.open_matters(firm_id):
        if m.adverse_client_id in book and not m.waiver:
            out.append((m.client_id, m.adverse_client_id, m.id))
    for b in deal.book:
        if b.kept and b.adverse_client_id is not None and b.adverse_client_id in ours:
            out.append((b.adverse_client_id, b.client_id, None))
    return out


def _drop_client(
    market: MarketState, firm_id: int, client_id: int, turn: int
) -> tuple[MarketState, list[int]]:
    """The player's client leaves: its relationship goes and its open matters end."""
    ended = []
    for m in market.open_matters(firm_id):
        if m.client_id == client_id or m.adverse_client_id == client_id:
            market = with_matter(
                market,
                replace(
                    m, status="closed", outcome="disqualified", closed_turn=turn, settlement=None
                ),
            )
            ended.append(m.id)
    market = replace(
        market,
        relationships=tuple(
            r for r in market.relationships if (r.client_id, r.firm_id) != (client_id, firm_id)
        ),
    )
    return market, ended


def clear(
    state: GameState, deal: Deal, rng: RngFactory, balance: Balance
) -> tuple[GameState, Deal, tuple[LogItem, ...]]:
    """Resolve every conflict found now that the deal has not resolved yet."""
    cfg = balance.mergers.clearance
    firm_id = state.player.id
    gen = streams.clear(rng, state.turn, deal.id)
    market = state.market
    book = {b.client_id: b for b in deal.book}
    conflicts = list(deal.conflicts)
    dropped_ours: set[int] = set()
    logs: list[LogItem] = []
    for our, their, matter_id in find_conflicts(state, deal):
        if our in dropped_ours or (their in book and not book[their].kept):
            continue
        rel = market.relationship(our, firm_id)
        u = float(gen.random())
        if matter_id is not None:  # our matter is adverse to their client: they must waive
            affected_score = book[their].score if their in book else 0.0
            advance = False
        else:  # their engagement is adverse to our client: ours must waive
            affected_score = rel.score if rel is not None else 0.0
            advance = rel is not None and rel.advance_waiver
        p = min(cfg.waiver_max, cfg.waiver_base + cfg.waiver_rel * affected_score / 100.0)
        if advance or u < p:
            outcome = "waived"
            if matter_id is not None:
                m = market.matter(matter_id)
                if m is not None:
                    market = with_matter(market, replace(m, waiver=True))
        elif deal.form == "merger" and (rel.score if rel is not None else 0.0) >= book[their].score:
            outcome = "kept_ours"
            book[their] = replace(book[their], kept=False)
        else:
            outcome = "kept_theirs"
            if deal.form == "merger":
                market, _ = _drop_client(market, firm_id, our, state.turn)
                dropped_ours.add(our)
            elif matter_id is not None:  # a verein: our matter against a member's client ends
                m = market.matter(matter_id)
                if m is not None:
                    market = with_matter(
                        market,
                        replace(
                            m,
                            status="closed",
                            outcome="disqualified",
                            closed_turn=state.turn,
                            settlement=None,
                        ),
                    )
        conflicts.append(Conflict(our, their, matter_id, outcome))  # type: ignore[arg-type]
    deal = replace(
        deal,
        book=tuple(book[k] for k in sorted(book)),
        conflicts=tuple(conflicts),
    )
    lost = sum(1 for c in conflicts if c.outcome != "waived")
    logs.append(
        inbox_item(
            state.turn,
            firm_id,
            "merger_cleared",
            link_kind="mergers",
            link_id=deal.id,
            conflicts=len(conflicts),
            lost=lost,
        )
    )
    return replace(state, market=market), deal, tuple(logs)


def kept_book(deal: Deal) -> tuple[BookClient, ...]:
    return tuple(b for b in deal.book if b.kept)
