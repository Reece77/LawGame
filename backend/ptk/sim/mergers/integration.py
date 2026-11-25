"""Integration (TST formulas.md 28.5, re-cast; spec 8.7-8.8; ADR PT-0016).

For `integration.months` after closing:

- **Flight.** PT-M4's monthly flight chance (`partnership.flight`) of an equity partner is
  multiplied (`flight_multiplier`) by 1 + `flight_mult` x clash for the other side's partners;
  by 1 + `pep_fall_mult` for any partner whose budgeted share is below the PEP they expected
  before (the points ratio took from them); by 1 + `subordinated_mult` for a partner whose side
  holds less than `subordinated_share` of their practice's lawyers (the other side runs it).
  Departures then follow PT-M4's machinery (approaches, counters, clients following; the spiral
  can follow).
- **Clients balk.** A book client facing a card rise leaves with a monthly chance `balk_bp` x
  rise x price sensitivity / 10 (bp) for `balk_months` (stream `integration`).
- **Records.** Equity partners gone and clients lost are recorded for the Mergers screen and T13.
"""

from __future__ import annotations

from dataclasses import replace

from ptk.sim.data_models import Balance, GameData
from ptk.sim.log import LogItem, inbox_item
from ptk.sim.mergers import streams
from ptk.sim.mergers.models import Integration, with_integration
from ptk.sim.mergers.talks import put_mergers
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState

_SHARES: dict[int, tuple[object, object, dict[str, float]]] = {}  # deal -> (staff, people, share)
_KEEP = 16  # tunable-exempt: memoised integrations (a cache, not a rule)


def active(state: GameState) -> tuple[Integration, ...]:
    return tuple(i for i in state.mergers.integrations if i.until_turn >= state.turn)


def their_share_by_practice(
    state: GameState, integ: Integration, data: GameData
) -> dict[str, float]:
    """The other side's share of each practice's lawyers now (memoised per staff tuple)."""
    from ptk.sim.partnership.common import home_practice

    staff = state.staff_ids(state.player.id)
    hit = _SHARES.get(integ.deal_id)
    if hit is not None and hit[0] is staff and hit[1] is state.people:
        return hit[2]
    theirs = set(integ.their_people)
    total: dict[str, int] = {}
    mine: dict[str, int] = {}
    for pid in staff:
        person = state.person(pid)
        if data.role(person.role).kind != "lawyer":
            continue
        p = home_practice(person, data)
        total[p] = total.get(p, 0) + 1
        if pid in theirs:
            mine[p] = mine.get(p, 0) + 1
    out = {p: mine.get(p, 0) / n for p, n in total.items()}
    if len(_SHARES) >= _KEEP:
        _SHARES.clear()
    _SHARES[integ.deal_id] = (staff, state.people, out)
    return out


def flight_multiplier(state: GameState, person_id: int, balance: Balance, data: GameData) -> float:
    """PT-M4's flight chance multiplier for an equity partner (1 outside integration)."""
    integrations = active(state)
    if not integrations:
        return 1.0
    from ptk.sim.partnership.common import home_practice

    cfg = balance.mergers.integration
    fp = state.partnership.of(state.player.id)
    partner = fp.partner(person_id) if fp is not None else None
    mult = 1.0
    for integ in integrations:
        theirs = person_id in integ.their_partners
        if not theirs and person_id not in integ.our_partners:
            continue
        if theirs:
            mult *= 1.0 + cfg.flight_mult * integ.clash
        before = dict(integ.pep_before).get(person_id)
        if (
            partner is not None
            and before
            and partner.budget_cents < before * (1.0 - cfg.pep_fall_tolerance)
        ):
            mult *= 1.0 + cfg.pep_fall_mult
        share = their_share_by_practice(state, integ, data).get(
            home_practice(state.person(person_id), data), 0.0
        )
        side = share if theirs else 1.0 - share
        if side < cfg.subordinated_share:
            mult *= 1.0 + cfg.subordinated_mult
    return mult


def month(
    state: GameState, rng: RngFactory, balance: Balance
) -> tuple[GameState, tuple[LogItem, ...]]:
    """Phase 8 (after flight): record partners gone; book clients balk at the merged card."""
    cfg = balance.mergers.integration
    pid = state.player.id
    logs: list[LogItem] = []
    ms = state.mergers
    for integ in active(state):
        gone = {p for p, _ in integ.lost_partners}
        lost = list(integ.lost_partners)
        for person_id in (*integ.our_partners, *integ.their_partners):
            if person_id in gone:
                continue
            e = state.employment_of(person_id)
            if e is None or e.firm_id != pid:
                lost.append((person_id, state.turn))
        clients = list(integ.lost_clients)
        market = state.market
        if integ.card_rise > 0 and state.turn - integ.closed_turn < cfg.balk_months:
            left = {c for c, _ in clients}
            for cid in integ.balk_clients:
                if cid in left or market.relationship(cid, pid) is None:
                    continue
                client = market.client(cid)
                p = cfg.balk_bp / 10_000 * integ.card_rise * client.price_sensitivity / 10.0
                if float(streams.integration(rng, state.turn, integ.deal_id, cid).random()) < p:
                    market = replace(
                        market,
                        relationships=tuple(
                            r
                            for r in market.relationships
                            if (r.client_id, r.firm_id) != (cid, pid)
                        ),
                    )
                    clients.append((cid, state.turn))
                    logs.append(
                        inbox_item(
                            state.turn,
                            pid,
                            "merger_client_balked",
                            link_kind="client",
                            link_id=cid,
                            client=client.name,
                        )
                    )
        state = replace(state, market=market)
        ms = with_integration(
            ms,
            replace(
                integ,
                lost_partners=tuple(sorted(lost, key=lambda x: (x[1], x[0]))),
                lost_clients=tuple(sorted(clients, key=lambda x: (x[1], x[0]))),
            ),
        )
        if state.turn == integ.until_turn:
            logs.append(
                inbox_item(
                    state.turn,
                    pid,
                    "merger_integrated",
                    link_kind="mergers",
                    link_id=integ.deal_id,
                    firm=integ.name,
                    partners=len(lost),
                    clients=len(clients),
                )
            )
    return put_mergers(state, ms), tuple(logs)


def partners_lost_share(integ: Integration, months: int) -> float:
    """T13: the share of the combined equity partnership at closing gone within `months`."""
    base = len(integ.our_partners) + len(integ.their_partners)
    if base == 0:
        return 0.0
    lost = sum(1 for _, t in integ.lost_partners if t - integ.closed_turn <= months)
    return lost / base
