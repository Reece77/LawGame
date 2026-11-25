"""Approaches and talks (spec 8.8; ADR PT-0016): whether the other firm will talk, opening a
deal (its client book is drawn then), and rivals' approaches to the player.

The other firm talks when U = bias(personality) + complement_weight x complement + pep_weight x
(the player's PEP over its own - 1) + region_weight x [the player brings a region it lacks] +
N(0, noise_sd) > 0 (stream `merger_answer`, round 0). A bias of None never talks (spec 10.1:
the elite lockstep firms never merge). A verein reads `verein.talk_bias` instead.

Rivals approach the player (phase 9, stream `rival_merger` key (0,)): a month's chance
`rival.approach_bp`, at most once in `rival.cooldown_months`; the rival with the highest
utility, at least `rival.approach_min_utility`, makes the approach (with terms at the fair
share of the two profit pools); one too large to integrate offers a verein.
"""

from __future__ import annotations

from dataclasses import replace

from ptk.sim.data_models import Balance, GameData
from ptk.sim.log import LogItem, inbox_item
from ptk.sim.mergers import streams
from ptk.sim.mergers.books import draw_book
from ptk.sim.mergers.models import (
    BookClient,
    Deal,
    DealForm,
    Initiator,
    Terms,
    with_cooldown,
    with_deal,
)
from ptk.sim.mergers.profile import Side, complement, fit, player_side, rival_side
from ptk.sim.rivals.models import RivalFirm
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState


def put_mergers(state: GameState, ms: object) -> GameState:
    return replace(state, mergers=ms)  # type: ignore[arg-type]


def bias(firm: RivalFirm, form: DealForm, balance: Balance) -> float | None:
    cfg = balance.mergers
    table = cfg.verein.talk_bias if form == "verein" else cfg.answer.talk_bias
    return table.get(firm.personality)


def size_gap(ours: Side, theirs: Side, balance: Balance) -> float:
    """A verein's members are firms of some standing to each other: `verein.size_weight` per
    tenfold of the other firm's lawyers over ten times the player's."""
    import math

    ratio = max(theirs.lawyers, 1) / max(ours.lawyers, 1)
    return balance.mergers.verein.size_weight * max(0.0, math.log10(ratio) - 1.0)


def talk_utility(
    ours: Side, theirs: Side, firm: RivalFirm, form: DealForm, balance: Balance
) -> float | None:
    """The other firm's utility for talks, before noise (engine-only); None: never."""
    b = bias(firm, form, balance)
    if b is None:
        return None
    cfg = balance.mergers.answer
    pep = ours.pep_cents / max(theirs.pep_cents, 1) - 1.0
    region = 1.0 if ours.region != theirs.region else 0.0
    if form == "verein":
        return (
            b
            + cfg.region_weight * region
            + cfg.pep_weight * min(pep, 0.5)
            - size_gap(ours, theirs, balance)
        )
    return (
        b
        + cfg.complement_weight * complement(theirs, ours)
        + cfg.pep_weight * max(-1.0, min(pep, 1.0))
        + cfg.region_weight * region
    )


def eligible(state: GameState, firm: RivalFirm, form: DealForm, balance: Balance) -> str:
    """Why the firm cannot be approached now ('' when it can)."""
    ms = state.mergers
    if not firm.active:
        return "it no longer exists"
    if bias(firm, form, balance) is None:  # spec 10.1: the elite lockstep firms never merge
        return "it does not merge" if form == "merger" else "it does not join vereins"
    if ms.open_with(firm.key) is not None:
        return "talks are already open"
    if ms.cooldown(firm.key) > state.turn:
        return "it will not talk again yet"
    if form == "verein":
        if firm.key in ms.member_keys():
            return "it is already a member of the verein"
    elif any(d.is_open and d.form == "merger" for d in ms.deals):
        return "the firm is already in merger talks"
    if ms.exit is not None:
        return "the firm has been absorbed"
    return ""


def book_for(
    state: GameState,
    deal_id: int,
    firm: RivalFirm,
    rng: RngFactory,
    data: GameData,
    balance: Balance,
) -> tuple[GameState, tuple[BookClient, ...]]:
    """The other firm's client book (its city's clients join the world first)."""
    from ptk.sim.geo.markets import make_city_clients

    city = data.geo.city_key(firm.hq)
    if city is not None and city != state.player.home_city:
        state = make_city_clients(state, city, rng, data, balance)
    return state, draw_book(state, deal_id, firm, rng, data, balance)


def open_deal(
    state: GameState,
    firm: RivalFirm,
    form: DealForm,
    initiator: Initiator,
    rng: RngFactory,
    data: GameData,
    balance: Balance,
    terms: Terms | None = None,
) -> tuple[GameState, Deal]:
    ms = state.mergers
    did = ms.next_deal_id
    # a rival's approach changes nothing in the world until the player opens talks (a firm that
    # never merges plays as before): its book is drawn then (`with_book`)
    book: tuple[BookClient, ...] = ()
    if form == "merger" and initiator == "player":
        state, book = book_for(state, did, firm, rng, data, balance)
    deal = Deal(
        id=did,
        rival_id=firm.id,
        rival_key=firm.key,
        form=form,
        initiator=initiator,
        opened_turn=state.turn,
        stage="approached" if initiator == "rival" else "talks",
        stage_turn=state.turn,
        book=book,
        terms=terms,
    )
    ms = replace(with_deal(state.mergers, deal), next_deal_id=did + 1)
    return put_mergers(state, ms), deal


def approach(
    state: GameState,
    firm: RivalFirm,
    form: DealForm,
    rng: RngFactory,
    data: GameData,
    balance: Balance,
) -> tuple[GameState, Deal, tuple[LogItem, ...]]:
    """The player approaches `firm`: it talks, or declines (the deal ends at once)."""
    ours = player_side(state, data, balance)
    theirs = rival_side(firm, data)
    u = talk_utility(ours, theirs, firm, form, balance)
    state, deal = open_deal(state, firm, form, "player", rng, data, balance)
    gen = streams.answer(rng, state.turn, deal.id, 0)
    noise = float(gen.normal(0.0, balance.mergers.answer.noise_sd))
    talks = u is not None and u + noise > 0
    firm_id = state.player.id
    if not talks:
        deal = replace(
            deal, stage="ended", ended_turn=state.turn, ended_reason="declined to talk", book=()
        )
        ms = with_cooldown(
            with_deal(state.mergers, deal), firm.key, state.turn + balance.mergers.cooldown_months
        )
        state = put_mergers(state, ms)
    log = inbox_item(
        state.turn,
        firm_id,
        "merger_talks" if talks else "merger_declined",
        link_kind="mergers",
        link_id=deal.id,
        firm=firm.name,
        form=form,
    )
    return state, deal, (log,)


def rival_approaches(
    state: GameState, rng: RngFactory, data: GameData, balance: Balance
) -> tuple[GameState, tuple[LogItem, ...]]:
    """Phase 9: at most one rival approaches the player this month (stream `rival_merger`)."""
    cfg = balance.mergers.rival
    ms = state.mergers
    if ms.exit is not None or ms.open_deals():
        return state, ()
    last = ms.last_rival_approach_turn
    if last is not None and state.turn - last < cfg.cooldown_months:
        return state, ()
    ours = player_side(state, data, balance)
    if ours.lawyers < cfg.min_player_lawyers or ours.profit_cents <= 0:
        return state, ()
    gen = streams.rival_merger(rng, state.turn, 0)
    if float(gen.random()) * 10_000 >= cfg.approach_bp:
        return state, ()
    best: tuple[float, int, RivalFirm, DealForm] | None = None
    for firm in state.rivals.active:
        if firm.kind == "boutique" or ms.cooldown(firm.key) > state.turn:
            continue
        f = fit(state, firm, data, balance)
        form: DealForm = "merger" if f.integrable else "verein"
        if form == "verein" and firm.key in ms.member_keys():
            continue
        theirs = rival_side(firm, data)
        # the rival's view: what the player's firm brings it (the player's lawyers in practices
        # it lacks, a stronger PEP, a region it lacks)
        u = talk_utility(ours, theirs, firm, form, balance)
        if u is None or u < cfg.approach_min_utility:
            continue
        if best is None or (u, -firm.id) > (best[0], -best[1]):
            best = (u, firm.id, firm, form)
    if best is None:
        return state, ()
    _, _, firm, form = best
    from ptk.sim.mergers.terms import is_absorption

    terms = None
    if form == "merger":
        share = fit(state, firm, data, balance).fair_share_bp
        # a firm that brings most of the pool proposes its own name and managing partner
        larger = share < cfg.absorb_offer_below_bp
        terms = Terms(
            our_share_bp=share,
            name="theirs" if larger else "combined",
            mp="theirs" if larger else "ours",
            comp_system=rival_side(firm, data).comp_system,
            rates="blend",
        )
    state, deal = open_deal(state, firm, form, "rival", rng, data, balance, terms)
    state = put_mergers(state, replace(state.mergers, last_rival_approach_turn=state.turn))
    absorbed = terms is not None and is_absorption(terms, balance)
    log = inbox_item(
        state.turn,
        state.player.id,
        "merger_approached",
        link_kind="mergers",
        link_id=deal.id,
        firm=firm.name,
        form="absorption" if absorbed else form,
    )
    return state, (log,)
