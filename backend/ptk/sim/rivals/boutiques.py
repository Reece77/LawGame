"""Spin-off boutiques (TST formulas.md 15.4's startups, for law; spec 10.1).

Phase 9: with chance `rivals.boutique.monthly_bp` a month (stream `rival_gen`, key
`(BOUTIQUE_KEY, n)` where n is the boutiques founded so far; draws in order: the roll, the
source firm, the practice, the group size, the growth bias), a group of 2-6 key partners in
one practice leaves a real rival to found a boutique. Their books follow them at
`boutique.book_share`; each brings `associates_per_partner` associates from the pools. The
source loses the people, the demand and its key partners' count (the departures count toward
its collapse hazard). A litigation, white-collar, IP, arbitration, insurance or mass-tort group founds a
`litigation_boutique`;
any other an `elite_lockstep` boutique. A boutique grows with the market plus its drawn
bias; while its profit over 12 months is negative it fails with chance `failure_bp` a month
(history.collapse_hazard), and its people become free agents.
"""

from __future__ import annotations

from dataclasses import replace

from ptk.sim.rivals import streams
from ptk.sim.rivals.decisions import remove_lawyer
from ptk.sim.rivals.economy import Month
from ptk.sim.rivals.history import record, with_firm
from ptk.sim.rivals.models import BOUTIQUE_KEY, RivalFirm, RivalMove
from ptk.sim.rivals.people import find_person, move_member
from ptk.sim.rivals.setup import BOUTIQUE_ID_OFFSET, build_firm
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState

# PT-M12: arbitration, insurance and mass-tort groups found litigation boutiques too
LITIGATION = frozenset(
    {
        "commercial_litigation",
        "white_collar",
        "ip",
        "international_arbitration",
        "insurance",
        "mass_torts",
    }
)  # tunable-exempt
MIN_GROUP = 2  # tunable-exempt: the smallest group that founds a boutique


def found(state: GameState, rng: RngFactory, month: Month) -> tuple[GameState, list[RivalMove]]:
    bb = month.balance.rivals.boutique
    rivals = state.rivals
    n = rivals.boutiques_founded
    alive = sum(1 for f in rivals.active if f.kind == "boutique")
    gen = streams.rival_gen(rng, month.turn, BOUTIQUE_KEY, n)
    if float(gen.random()) >= bb.monthly_bp / 10_000 or alive >= bb.max_alive:
        return state, []
    from ptk.sim.geo.cities import rival_region

    # PT-M11: spin-offs leave US firms (UK rivals compete in London only)
    sources = [
        f for f in rivals.active if f.kind == "real" and rival_region(month.data, f.hq) == "us"
    ]
    if not sources:
        return state, []
    source = sources[min(int(float(gen.random()) * len(sources)), len(sources) - 1)]
    partners = [m for m in rivals.members_of(source.id) if m.kind == "partner"]
    practices = sorted({m.practice for m in partners})
    if not practices:
        return state, []
    practice = practices[min(int(float(gen.random()) * len(practices)), len(practices) - 1)]
    size = int(gen.integers(int(bb.partners.lo), int(bb.partners.hi) + 1))
    group = [m for m in partners if m.practice == practice][:size]
    bias = float(gen.uniform(bb.growth_bias.lo, bb.growth_bias.hi))
    if len(group) < MIN_GROUP:
        return state, []
    book = sum(m.book_cents for m in group) * bb.book_share
    lawyers = len(group) * (1 + bb.associates_per_partner)
    lead = find_person(state, group[0].person_id, month.data, month.balance)
    surname = lead.last_name if lead else "New"
    personality = "litigation_boutique" if practice in LITIGATION else "elite_lockstep"
    firm = build_firm(
        firm_id=month.balance.rivals.first_firm_id + BOUTIQUE_ID_OFFSET + n,
        rival_key=(BOUTIQUE_KEY, n),
        key=f"btq_{n}",
        name=f"{surname} LLP",
        short=surname,
        personality=personality,
        kind="boutique",
        hq=source.hq,
        ny_office=source.ny_office,
        offices=1,
        strong=(practice,),
        revenue_cents=max(book, 1.0),
        lawyers=lawyers,
        equity_partners=float(len(group)),
        pep_cents=None,
        turn=month.turn,
        data=month.data,
        balance=month.balance,
    )
    pools = tuple(
        replace(
            p,
            equity=float(len(group)),
            partners=0.0,
            associates=len(group) * bb.associates_per_partner,
        )
        if p.practice == practice
        else replace(p, equity=0.0, partners=0.0, associates=0.0)
        for p in firm.pools
    )
    firm = replace(firm, pools=pools, key_target=len(group), people_made=0)
    src = source
    for m in group:
        rivals = move_member(rivals, m.person_id, firm.id, month.turn)
        src = remove_lawyer(src, m.practice, True)
    for _ in range(round(len(group) * bb.associates_per_partner)):
        src = remove_lawyer(src, practice, False)
    if month.pinned(src):
        src = replace(src, offset_cents=src.offset_cents - book)
    else:
        src = replace(src, demand_cents=max(0.0, src.demand_cents - book))
    src = replace(src, departures=(*src.departures, (month.turn, len(group))))
    rivals = with_firm(with_firm(rivals, src), replace(firm, growth_bias=bias))
    rivals = replace(rivals, boutiques_founded=n + 1)
    rivals, move = record(
        rivals,
        firm,
        month.turn,
        "founded",
        f"{len(group)} {month.data.practice(practice).label.lower()} partners leave "
        f"{source.name} to found {firm.name}",
        other=source.id,
    )
    return replace(state, rivals=rivals), [move]


_UNUSED = RivalFirm
