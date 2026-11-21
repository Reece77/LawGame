"""Panels and RFPs (spec 7.2): panel reviews, big-matter RFPs, pitches and awards.

**Panel reviews.** A large client reviews its panel every `rfp.review_years` years, in the
month (client id x 7) mod (12 x years): the RFP opens, covers the client's three biggest
practices by its sector's mix, and is awarded `rfp.pitch_months` later. The incumbents (its
panel firms, and the player's firm if it holds a relationship in any of those practices)
compete with 2-4 bidding rivals (New York offices only, drawn by size). The player's firm is
invited if it is an incumbent or its reputation in a covered practice reaches
`rfp.player_reputation_min`.

**Big-matter RFPs.** Each month a large client runs one with chance `rfp.matter_rfp_bp`:
one practice (drawn by its sector's mix), `rfp.matter_min_cents` up to three times that in
expected fees, one seat. Its panel firms bid; the player's firm is invited as above and
competes only if it pitches (an incumbent on a panel review competes for its seat unpitched).

**Awards** (stream `rfp`, key `(1, rfp_id)`): each contender's score is its appeal (a
rival's New York panel appeal in the RFP's practices, averaged; the player's relationship and
reputation) + `w_incumbent` if an incumbent + N(0, `noise_sd`), drawn in contender order
(incumbents, then bidders, then the player). The player's pitch adds `w_pitch` x (quality -
10), where quality is the team's mean of business development, communication, client care
and familiarity in the RFP's practices, plus `w_claim` for each substantiated claim and minus
it for each that is not. The best `seats` scores win. A panel's winners become its panel; a
player's pitched win adds the practices to its relationship (or opens one at
`rfp.start_score`); an unpitched incumbent's win keeps what it had; a loss as an incumbent
removes the practices. A player's big-matter win opens the named matter, through
the conflicts check. The opening rolls use stream `rfp`, key `(0, client_id)`.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Final

import numpy as np

from ptk.sim.calendar import turn_to_ym
from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import InvalidActionError
from ptk.sim.log import LogItem, inbox_item
from ptk.sim.matters.models import Client, Relationship
from ptk.sim.rivals import streams
from ptk.sim.rivals.models import PLAYER_PANEL_KEY, Pitch, Rfp, RfpKind, RivalsState
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState

CLAIMS: Final = ("references", "track_record", "continuity")  # tunable-exempt: claim keys
OPEN_KEY, AWARD_KEY = 0, 1  # tunable-exempt: rfp stream key tags
PANEL_PRACTICES = 3  # tunable-exempt: a panel review covers the client's top three practices
MONTHS = 12  # tunable-exempt
PITCH_SKILLS = ("business_development", "communication", "client_care")  # tunable-exempt


def sector_practices(client: Client, data: GameData, n: int) -> tuple[str, ...]:
    mix = data.clients.sector(client.sector).mix
    ranked = sorted(
        data.practice_keys, key=lambda p: (-mix.get(p, 0.0), data.practice_keys.index(p))
    )
    return tuple(sorted(ranked[:n], key=data.practice_keys.index))


def player_reputation(state: GameState, practices: tuple[str, ...]) -> float:
    from ptk.sim.matters.market import firm_reputation

    return max((firm_reputation(state, state.player.id, p) for p in practices), default=0.0)


def _bidders(
    state: GameState, client: Client, n_lo: int, n_hi: int, gen: np.random.Generator
) -> tuple[str, ...]:
    pool = [f for f in state.rivals.active if f.ny_office and f.key not in client.panel]
    pool.sort(key=lambda f: f.id)
    n = int(gen.integers(n_lo, n_hi + 1))
    chosen: list[str] = []
    weights = [max(f.revenue_12m, 1) for f in pool]
    for _ in range(min(n, len(pool))):
        total = sum(w for f, w in zip(pool, weights, strict=True) if f.key not in chosen)
        u = float(gen.random()) * total
        for f, w in zip(pool, weights, strict=True):
            if f.key in chosen:
                continue
            if u < w:
                chosen.append(f.key)
                break
            u -= w
    return tuple(sorted(chosen))


def open_rfps(
    state: GameState, rng: RngFactory, data: GameData, balance: Balance
) -> tuple[GameState, tuple[LogItem, ...]]:
    """Phase 4 (before intake): this month's panel reviews and big-matter RFPs."""
    rb = balance.rivals.rfp
    turn = state.turn
    cycle = rb.review_years * MONTHS
    rivals = state.rivals
    logs: list[LogItem] = []
    open_clients = {r.client_id for r in rivals.rfps if r.status == "open"}
    player = state.player.id
    for client in state.market.clients:
        if client.size_class != "large" or client.id in open_clients:
            continue
        gen = streams.rfp(rng, turn, OPEN_KEY, client.id)
        review = (client.id * 7) % cycle == turn % cycle  # tunable-exempt: staggering
        matter_roll = float(gen.random())
        if not review and matter_roll >= rb.matter_rfp_bp / 10_000:
            continue
        rel = state.market.relationship(client.id, player)
        kind: RfpKind
        if review:
            practices = sector_practices(client, data, PANEL_PRACTICES)
            kind, seats, cents = "panel", max(1, len(client.panel)), 0
            bidders = _bidders(state, client, int(rb.bidders.lo), int(rb.bidders.hi), gen)
        else:
            mix = data.clients.sector(client.sector).mix
            keys = [p for p in data.practice_keys if mix.get(p, 0.0) > 0]
            u = float(gen.random()) * sum(mix[p] for p in keys)
            practice = keys[-1]
            for p in keys:
                if u < mix[p]:
                    practice = p
                    break
                u -= mix[p]
            practices = (practice,)
            kind, seats = "matter", 1
            cents = round(rb.matter_min_cents * (1 + 2 * float(gen.random())))
            bidders = ()
        incumbent = rel is not None and bool(set(rel.practices) & set(practices))
        invited = incumbent or player_reputation(state, practices) >= rb.player_reputation_min
        incumbents = tuple(sorted(client.panel)) + ((PLAYER_PANEL_KEY,) if incumbent else ())
        rfp = Rfp(
            id=rivals.next_rfp_id,
            client_id=client.id,
            kind=kind,
            practices=practices,
            opened_turn=turn,
            award_turn=turn + rb.pitch_months,
            seats=seats,
            incumbents=incumbents,
            bidders=bidders,
            player_invited=invited,
            matter_cents=cents,
        )
        rivals = replace(rivals, rfps=(*rivals.rfps, rfp), next_rfp_id=rivals.next_rfp_id + 1)
        if invited:
            logs.append(
                inbox_item(
                    turn,
                    player,
                    "rfp_open",
                    link_kind="rfp",
                    link_id=rfp.id,
                    client=client.name,
                    kind="panel review" if kind == "panel" else "matter RFP",
                    practices=", ".join(data.practice(p).label for p in practices),
                )
            )
    return replace(state, rivals=rivals), tuple(logs)


# --- The player's pitch (an action; ADR-0014) -------------------------------------------------


def pitch_quality(state: GameState, team: tuple[int, ...], practices: tuple[str, ...]) -> float:
    if not team:
        return 10.0  # tunable-exempt: neutral (no pitch term)
    values = []
    for pid in team:
        p = state.person(pid)
        skills = sum(p.skills[k] for k in PITCH_SKILLS) / len(PITCH_SKILLS)
        fam = sum(p.familiarity[x] for x in practices) / len(practices)
        values.append((skills + fam) / 2)
    return sum(values) / len(values)


def substantiated(state: GameState, rfp: Rfp, claim: str, team: tuple[int, ...]) -> bool:
    client = state.market.client(rfp.client_id)
    firm = state.player.id
    closed = [m for m in state.market.matters if m.firm_id == firm and m.status == "closed"]
    if claim == "references":
        sector = client.sector
        return any(state.market.client(m.client_id).sector == sector for m in closed)
    if claim == "track_record":
        return sum(1 for m in closed if m.practice in rfp.practices) >= 3  # tunable-exempt: matters
    if claim == "continuity":
        rel = state.market.relationship(client.id, firm)
        return rel is not None and bool(team) and rel.partner_id == team[0]
    return False


def pitch(
    state: GameState, rfp_id: int, team: tuple[int, ...], claims: tuple[str, ...], balance: Balance
) -> GameState:
    rb = balance.rivals.rfp
    rfp = state.rivals.rfp(rfp_id)
    if rfp is None or rfp.status != "open" or not rfp.player_invited:
        raise InvalidActionError(f"no open RFP {rfp_id} that the firm is invited to")
    if not team or len(team) > rb.team_max or len(set(team)) != len(team):
        raise InvalidActionError(f"a pitch team needs 1 to {rb.team_max} different people")
    staff = set(state.staff_ids(state.player.id))
    if any(pid not in staff for pid in team):
        raise InvalidActionError("the pitch team must be the firm's own people")
    if bad := sorted(set(claims) - set(CLAIMS)):
        raise InvalidActionError(f"unknown claims {bad}")
    done = replace(rfp, pitch=Pitch(team=team, claims=tuple(claims), turn=state.turn))
    rfps = tuple(done if r.id == rfp_id else r for r in state.rivals.rfps)
    return replace(state, rivals=replace(state.rivals, rfps=rfps))


# --- Awards -----------------------------------------------------------------------------------


def rival_score(rivals: RivalsState, key: str, rfp: Rfp, data: GameData) -> float:
    table = dict(rivals.appeals)
    values = table.get(key)
    if values is None:
        return 0.0
    idx = [data.practice_keys.index(p) for p in rfp.practices]
    return sum(values[i] for i in idx) / len(idx)


def player_score(state: GameState, rfp: Rfp, data: GameData, balance: Balance) -> float:
    rb = balance.rivals.rfp
    rel = state.market.relationship(rfp.client_id, state.player.id)
    client = state.market.client(rfp.client_id)
    from ptk.sim.matters.market import appeal_weights

    w = appeal_weights(client, balance)
    score = rb.w_relationship * (rel.score / 100.0 if rel else 0.0)
    score += w.reputation * player_reputation(state, rfp.practices)
    if rfp.pitch is not None:
        quality = pitch_quality(state, rfp.pitch.team, rfp.practices)
        score += rb.w_pitch * (quality - 10.0)  # tunable-exempt: the 1-20 midpoint
        for claim in rfp.pitch.claims:
            score += rb.w_claim if substantiated(state, rfp, claim, rfp.pitch.team) else -rb.w_claim
    return score


def award_due(
    state: GameState, rng: RngFactory, data: GameData, balance: Balance
) -> tuple[GameState, tuple[LogItem, ...]]:
    """Phase 4 (before intake): RFPs whose award month is now are awarded."""
    rb = balance.rivals.rfp
    logs: list[LogItem] = []
    turn = state.turn
    player = state.player.id
    for rfp in [r for r in state.rivals.rfps if r.status == "open" and r.award_turn <= turn]:
        gen = streams.rfp(rng, turn, AWARD_KEY, rfp.id)
        active = {f.key for f in state.rivals.active}
        scores: list[tuple[float, str]] = []
        for key in (*rfp.incumbents, *rfp.bidders):
            if key == PLAYER_PANEL_KEY:
                continue
            noise = float(gen.normal(0.0, rb.noise_sd))
            if key not in active:
                continue
            bonus = rb.w_incumbent if key in rfp.incumbents else 0.0
            scores.append((rival_score(state.rivals, key, rfp, data) + bonus + noise, key))
        noise = float(gen.normal(0.0, rb.noise_sd))
        # a panel's incumbent competes for its seat even unpitched; a big matter needs a pitch
        player_in = rfp.player_invited and (
            rfp.pitch is not None or (rfp.kind == "panel" and PLAYER_PANEL_KEY in rfp.incumbents)
        )
        if player_in:
            bonus = rb.w_incumbent if PLAYER_PANEL_KEY in rfp.incumbents else 0.0
            scores.append(
                (player_score(state, rfp, data, balance) + bonus + noise, PLAYER_PANEL_KEY)
            )
        scores.sort(key=lambda s: (-s[0], s[1]))
        winners = tuple(k for _, k in scores[: rfp.seats])
        state = _apply_award(state, rfp, winners, gen, data, balance)
        done = replace(rfp, status="awarded", winners=winners)
        rfps = tuple(done if r.id == rfp.id else r for r in state.rivals.rfps)
        state = replace(state, rivals=replace(state.rivals, rfps=rfps))
        if player_in:
            client = state.market.client(rfp.client_id)
            won = PLAYER_PANEL_KEY in winners
            logs.append(
                inbox_item(
                    turn,
                    player,
                    "rfp_won" if won else "rfp_lost",
                    link_kind="rfp",
                    link_id=rfp.id,
                    client=client.name,
                )
            )
    return state, tuple(logs)


def _apply_award(
    state: GameState,
    rfp: Rfp,
    winners: tuple[str, ...],
    gen: np.random.Generator,
    data: GameData,
    balance: Balance,
) -> GameState:
    from ptk.sim.matters.intake import with_relationship

    player = state.player.id
    client = state.market.client(rfp.client_id)
    market = state.market
    rel = market.relationship(client.id, player)
    won = PLAYER_PANEL_KEY in winners
    if rfp.kind == "panel":
        panel = tuple(sorted(k for k in winners if k != PLAYER_PANEL_KEY))
        clients = tuple(replace(c, panel=panel) if c.id == client.id else c for c in market.clients)
        market = replace(market, clients=clients)
        if won:
            market = with_relationship(market, _joined(rel, client, rfp, state, data, balance))
        elif rel is not None and PLAYER_PANEL_KEY in rfp.incumbents:
            kept = tuple(p for p in rel.practices if p not in rfp.practices)
            market = with_relationship(market, replace(rel, practices=kept))
        return replace(state, market=market)
    if not won:
        return state
    market = with_relationship(market, _joined(rel, client, rfp, state, data, balance))
    state = replace(state, market=market)
    return _open_matter(state, rfp, gen, data, balance)


def _joined(
    rel: Relationship | None,
    client: Client,
    rfp: Rfp,
    state: GameState,
    data: GameData,
    balance: Balance,
) -> Relationship:
    lead = rfp.pitch.team[0] if rfp.pitch and rfp.pitch.team else state.founder_of(state.player.id)
    if rel is not None and rfp.pitch is None:
        return rel  # an unpitched incumbent keeps its seat, and only that
    if rel is None:
        return Relationship(
            client_id=client.id,
            firm_id=state.player.id,
            score=balance.rivals.rfp.start_score,
            partner_id=lead,
            practices=rfp.practices,
            since_turn=state.turn,
        )
    practices = tuple(p for p in data.practice_keys if p in set(rel.practices) | set(rfp.practices))
    return replace(rel, practices=practices)


def _open_matter(
    state: GameState, rfp: Rfp, gen: np.random.Generator, data: GameData, balance: Balance
) -> GameState:
    from ptk.sim.matters.conflicts import conflict_index
    from ptk.sim.matters.intake import key_clients, new_matter, open_checked
    from ptk.sim.matters.rates import practice_index

    practice = data.practice(rfp.practices[0])
    kind = max(practice.matter_kinds, key=lambda k: (k.median_cents, k.key))
    client = state.market.client(rfp.client_id)
    rel = state.market.relationship(client.id, state.player.id)
    assert rel is not None
    matter = new_matter(
        state.market.next_matter_id,
        state.player.id,
        client,
        rel,
        practice,
        kind,
        rfp.matter_cents,
        gen,
        state.market,
        state.turn,
        data,
        balance,
        practice_index(state.player, practice.key),  # PT-M7b: fees on the practice's card
    )
    index = conflict_index(state.market, state.player.id, state.turn, balance)
    state, _logs = open_checked(
        state, matter, index, data, balance, key_clients(state.market, state.player.id, balance)
    )
    return state


def prune(rivals: RivalsState, turn: int) -> RivalsState:
    keep = tuple(
        r for r in rivals.rfps if r.status == "open" or r.award_turn > turn - 24
    )  # tunable-exempt: months kept
    return replace(rivals, rfps=keep)


_UNUSED = turn_to_ym
