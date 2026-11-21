"""The moves strategy scripts are made of (PT-M7): hiring, laterals, rates, December votes,
practice groups and delegates, the revolver. Each reads only what the player can see (asks,
revealed ranges, book ranges, the inbox) and acts through `Game.act`, so a refused move is
simply not made."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from ptk.balance.game import PLAYER, Game, is_associate
from ptk.sim.hiring.actions import Interview, MakeOffer, OpenSearch
from ptk.sim.ledger import REVOLVER
from ptk.sim.matters.actions import Introduce, SetHoursPolicy, SetMatterHours, SetRatePolicy
from ptk.sim.money import BP_DENOMINATOR
from ptk.sim.org.actions import CreatePlan, CreateUnit, MovePerson, SetLeader
from ptk.sim.partnership.actions import (
    CapitalCall,
    CompRound,
    Diligence,
    ElectionChoice,
    LateralOffer,
    LateralSearch,
    ProposePartner,
    ProposeTerms,
    RepayRevolver,
    SetDraws,
)
from ptk.sim.partnership.careers import eligible, tracks_for
from ptk.sim.partnership.models import FirmPartnership
from ptk.sim.people.reveal import shown_rating
from ptk.sim.rivals.actions import PitchRfp

CAMPUS_OPEN = 1  # January: register for the campus season
CAMPUS_OFFERS = 8  # August: offers
DECEMBER = 12
TENTHS = 10  # hours are integer tenths (ADR PT-0005)
CAPITAL_CALL_CENTS = 100_000_000  # T9's response: $1M from the partners (PT-M4's exodus test)
JANUARY = 1


def practice_of(g: Game, person_id: int) -> str:
    p = g.state.person(person_id)
    return g.data.role(p.role).practice or ""


def headcount(g: Game, practice: str | None = None) -> int:
    return sum(1 for p in g.lawyers() if practice is None or practice_of(g, p.id) == practice)


def practices_held(g: Game) -> list[str]:
    """Practices with at least one partner, in practices.yaml order."""
    held = {
        practice_of(g, p.id) for p in g.lawyers() if p.level in ("equity_partner", "income_partner")
    }
    return [k for k in g.data.practice_keys if k in held]


def _score(g: Game, person_id: int) -> float:
    """What the firm can see of a person: their shown rating on their role's primary skills
    (the revealed ranges' midpoints, ADR-0007)."""
    rec = g.state.reveal(PLAYER, person_id)
    if rec is None:
        return 0.0
    person = g.state.person(person_id)
    return shown_rating(person, rec, g.data.role(person.role).primary)


def unit_of(g: Game, practice: str) -> int | None:
    """The practice's live group, if the firm has one."""
    return next(
        (
            u.id
            for u in g.state.org.units
            if u.firm_id == PLAYER and u.status == "active" and u.practice == practice
        ),
        None,
    )


def _open_search(g: Game, role: str, channel: str) -> bool:
    return any(
        s.firm_id == PLAYER and s.status == "open" and s.role == role and s.channel == channel
        for s in g.state.searches
    )


def campus(g: Game, practice: str, n: int, premium_bp: int = 10_000) -> None:
    """A campus class: register in January; in August interview the best `n` summer
    associates the firm has seen and offer each their ask (x premium)."""
    month = g.ym[1]
    role = g.data.practice_role(practice).key
    if month == CAMPUS_OPEN and not _open_search(g, role, "campus"):
        g.act(OpenSearch(g.founder_id, role, "campus"))
    if month != CAMPUS_OFFERS or n <= 0:
        return
    summers = [
        c
        for c in g.state.candidates
        if c.firm_id == PLAYER
        and c.channel == "campus"
        and c.status == "open"
        and g.state.person(c.person_id).role == role
    ]
    summers.sort(key=lambda c: (-_score(g, c.person_id), c.person_id))
    for c in summers[:n]:
        if g.act(Interview(g.founder_id, c.person_id)):
            g.act(MakeOffer(g.founder_id, c.person_id, c.ask_cents * premium_bp // 10_000))


def lateral_associates(g: Game, practice: str, n: int, channel: str = "job_post") -> int:
    """Hire up to `n` lateral associates in a practice: keep a search open; interview the
    best open candidates and offer their ask. Returns offers made."""
    if n <= 0:
        return 0
    role = g.data.practice_role(practice).key
    if not _open_search(g, role, channel):
        g.act(OpenSearch(g.founder_id, role, channel))  # type: ignore[arg-type]
        return 0
    pending = {o.candidate_id for o in g.state.offers if o.status == "pending"}
    cands = [
        c
        for c in g.state.candidates
        if c.firm_id == PLAYER
        and c.channel == channel
        and c.status == "open"
        and c.person_id not in pending
        and g.state.person(c.person_id).role == role
        and is_associate(g.state.person(c.person_id).level)
    ]
    cands.sort(key=lambda c: (-_score(g, c.person_id), c.person_id))
    made = 0
    for c in cands[:n]:
        if g.act(Interview(g.founder_id, c.person_id)) and g.act(
            MakeOffer(g.founder_id, c.person_id, c.ask_cents)
        ):
            made += 1
    return made


@dataclass(frozen=True, slots=True)
class LateralRule:
    min_book_cents: int  # the book range's low end must reach this
    guarantee_years: int = 0
    premium_bp: int = 10_000  # comp offered, bp of the ask


def lateral_partner(g: Game, practice: str, rule: LateralRule) -> bool:
    """A lateral partner with a book: search, diligence the best candidate, offer. One step a
    month (a search this month, diligence and the offer when candidates are there)."""
    fp = g.state.partnership.of(PLAYER)
    if fp is None:
        return False
    open_ = [c for c in fp.laterals if c.status == "open" and c.practice == practice]
    if not open_:
        return g.act(LateralSearch(g.founder_id, practice))
    best = max(open_, key=lambda c: (c.book_lo_cents, -c.person_id))
    if not best.diligence:
        g.act(Diligence(g.founder_id, best.person_id))
        best = fp_lateral(g, best.person_id) or best
    if best.book_lo_cents < rule.min_book_cents:
        return False
    return g.act(
        LateralOffer(
            g.founder_id,
            best.person_id,
            best.ask_cents * rule.premium_bp // 10_000,
            rule.guarantee_years,
        )
    )


def fp_lateral(g: Game, person_id: int):
    fp = g.state.partnership.of(PLAYER)
    return None if fp is None else fp.lateral(person_id)


def set_rates(g: Game, rise_bp: int | None) -> None:
    """Each January before the rise (phase 4 reads the policy): the strategy's rise."""
    if g.ym[1] == DECEMBER and rise_bp is not None and g.state.player.rate_rise_bp != rise_bp:
        g.act(SetRatePolicy(g.founder_id, rise_bp))


KEEP_GAP: Final = 0.25  # a partner this far under their market value moves two gate steps


def comp_system(g: Game, system: str, two_tier: bool | None = None) -> None:
    """Put the strategy's comp system (and tiering) to the partnership once."""
    fp = g.state.partnership.of(PLAYER)
    if fp is None:
        return
    if fp.agreement.comp_system != system and not g.notes.get(f"terms:{system}"):
        g.notes[f"terms:{system}"] = 1
        g.act(ProposeTerms(g.founder_id, "comp_system", system))
    if two_tier is not None and fp.agreement.two_tier != two_tier and not g.notes.get("tier"):
        g.notes["tier"] = 1
        g.act(ProposeTerms(g.founder_id, "two_tier", two_tier))


def december_votes(g: Game, admit: int, track: str = "equity") -> None:
    """In December propose the best `admit` eligible candidates on `track` (equity, income or
    counsel, as the agreement allows; equity when the track is not open); the rest are left
    to up or out."""
    if g.ym[1] != DECEMBER:
        return
    fp = g.state.partnership.of(PLAYER)
    if fp is None:
        return
    year = g.ym[0]
    cands = [
        p
        for p in g.lawyers()
        if eligible(g.state, fp, p.id, g.balance)
        and (fp.candidacy(p.id) is None or fp.candidacy(p.id).year != year)  # type: ignore[union-attr]
    ]
    cands.sort(key=lambda p: (-_score(g, p.id), p.id))
    for i, p in enumerate(cands):
        tracks = tracks_for(g.state, fp, p.id)
        if i < admit:
            choice = track if track in tracks else "equity"
        elif _first_look(g, fp, p.id) and "not_this_year" in tracks:
            choice = "not_this_year"  # a candidate in their first eligible year gets a second look
        else:
            continue  # up or out
        g.act(ProposePartner(g.founder_id, p.id, choice))  # type: ignore[arg-type]


def comp_round(g: Game) -> int:
    """PT-M7b: December's comp round, the partners the strategy would keep, by its comp system:
    under modified lockstep an equity partner whose market value is above what the firm pays
    them moves up the gate (two steps when 25% above); under committee their share moves up by
    the gap (at most the round's cap). Lockstep and eat what you kill have no lever. Returns
    the partners moved."""
    from ptk.sim.partnership.flight import FLIGHT_HOOK, firm_comp_cents

    if g.ym[1] != DECEMBER:
        return 0
    fp = g.state.partnership.of(PLAYER)
    if fp is None or fp.agreement.comp_system not in ("modified_lockstep", "committee"):
        return 0
    cfg = g.balance.partnership
    moved = 0
    for p in fp.equity_partners:
        if p.person_id == g.founder_id:
            continue
        market = FLIGHT_HOOK.market_value_cents(g.state, p.person_id, g.balance, g.data)
        paid = firm_comp_cents(p)
        if market <= paid:
            continue
        gap = market / paid - 1
        if fp.agreement.comp_system == "modified_lockstep":
            steps = min(cfg.modified.gate_max_steps, 2 if gap > KEEP_GAP else 1)
            action = CompRound(g.founder_id, p.person_id, gate_steps=steps)
        else:
            adjust = min(cfg.committee.adjust_max_bp, round(gap * BP_DENOMINATOR))
            action = CompRound(g.founder_id, p.person_id, adjust_bp=adjust)
        moved += g.act(action)
    return moved


def _first_look(g: Game, fp: FirmPartnership, person_id: int) -> bool:
    """An associate in the first class year the agreement's track makes eligible."""
    from ptk.sim.partnership.careers import class_year

    year = class_year(g.state.person(person_id).level)
    return year is not None and year <= fp.agreement.track_years


def answer_election(g: Game) -> None:
    """After a lost MP election, hand over to the winner and play on as them (ADR PT-0007 3;
    TST 45.5's heir): the strategy keeps the firm's levers."""
    fp = g.state.partnership.of(PLAYER)
    if fp is not None and fp.election_lost_turn is not None and fp.mp_id != g.founder_id:
        g.act(ElectionChoice(g.founder_id, "hand_over", fp.mp_id))


def practice_groups(g: Game) -> None:
    """Once practice groups unlock, one group per practice held, its lawyers moved in and its
    senior partner (never the founder, who leads the firm) as leader."""
    if len(g.lawyers()) < g.balance.org.practice_group_unlock_lawyers:
        return
    for practice in practices_held(g):
        unit = unit_of(g, practice)
        if unit is None:
            if not g.act(CreateUnit(g.founder_id, "practice_group", practice=practice)):
                continue
            unit = unit_of(g, practice)
            if unit is None:
                continue
        members = {m.person_id for m in g.state.org.members if m.unit_id == unit}
        for p in g.lawyers():
            if practice_of(g, p.id) == practice and p.id not in members and not p.is_founder:
                g.act(MovePerson(g.founder_id, p.id, unit))
        u = g.state.org.unit(unit)
        staff = set(g.state.staff_ids(PLAYER))
        if u is not None and (u.leader_id is None or u.leader_id not in staff):
            leader = _senior_partner(g, practice)
            if leader is not None:
                if u.leader_id is not None:
                    g.act(SetLeader(g.founder_id, unit, None))  # the leader has left
                g.act(SetLeader(g.founder_id, unit, leader))


def _senior_partner(g: Game, practice: str) -> int | None:
    partners = [
        p
        for p in g.lawyers()
        if practice_of(g, p.id) == practice
        and p.level in ("equity_partner", "income_partner")
        and not p.is_founder
    ]
    if not partners:
        return None
    return max(partners, key=lambda p: (p.level == "equity_partner", -p.id)).id


def delegate(g: Game, practice: str, n: int, channel: str = "campus") -> bool:
    """A hiring plan for a practice's group (its leader hires `n`); False when the group or
    its leader is not there yet (the script hires itself)."""
    unit = unit_of(g, practice)
    u = g.state.org.unit(unit) if unit is not None else None
    if u is None or u.leader_id is None or n <= 0:
        return False
    if any(
        pl.status == "active" and pl.unit_id == unit and pl.channel == channel
        for pl in g.state.org.plans
    ):
        return True
    role = g.data.practice_role(practice).key
    return g.act(CreatePlan(g.founder_id, u.leader_id, role, n, channel, 10_000, unit))  # type: ignore[arg-type]


def revolver_cap(g: Game, cap_cents: int) -> None:
    """Repay the revolver down to `cap_cents` from cash above a month's costs."""
    drawn = -g.bal(REVOLVER)
    spare = g.cash - monthly_costs(g)
    if drawn > cap_cents and spare > 0:
        g.act(RepayRevolver(g.founder_id, min(drawn - cap_cents, spare)))


def monthly_costs(g: Game) -> int:
    """Last month's expenses (what the firm spends a month), from the month record."""
    if not g.months:
        return 0
    m = g.months[-1]
    return max(0, m.revenue_cents - max(0, m.profit_12m_cents // 12))


def bank_quiet(g: Game, months: int = 6, cash_months: float = 2.0) -> bool:
    """No warning from the bank or the CFO for `months`, and cash above `cash_months` of
    costs: the revolver has headroom to its covenant limit (T9's rocket borrows to it, not
    past it)."""
    quiet = g.warned_turn is None or g.state.turn - g.warned_turn > months
    return quiet and g.cash > cash_months * monthly_costs(g)


def heed_warning(g: Game) -> bool:
    """T9's rule: when the CFO warns (PT-M7b: the forecast warning first) or a covenant breaks,
    stop guarantees, suspend draws and repay the revolver from spare cash. Returns whether the
    warning has come."""
    if not g.notes.get("warned") and any(
        t in ("cfo_forecast", "cfo_warning", "covenant_breach", "revolver_called", "insolvent")
        for t in g.templates()
    ):
        g.notes["warned"] = 1
        g.act(SetDraws(g.founder_id, True))
        g.act(CapitalCall(g.founder_id, CAPITAL_CALL_CENTS))
    if g.notes.get("warned"):
        revolver_cap(g, 0)
        return True
    return False


def associates_per_partner(g: Game) -> float:
    staff = g.lawyers()
    partners = sum(1 for p in staff if p.level in ("equity_partner", "income_partner"))
    return sum(1 for p in staff if is_associate(p.level)) / max(1, partners)


def utilisation(g: Game, months: int = 3) -> float:
    vals = [m.utilisation_bp for m in g.months[-months:] if m.utilisation_bp is not None]
    return sum(vals) / len(vals) / 10_000 if vals else 0.0


# --- Business development (spec 7.2) -------------------------------------------------------


def pitch_rfps(g: Game, n: int = 2, team_size: int = 4) -> int:
    """Pitch up to `n` open RFPs the firm is invited to and has not pitched (biggest first):
    the best partners and lawyers in its practices, the lead first. Returns pitches made."""
    made = 0
    rfps = sorted(
        (
            r
            for r in g.state.rivals.rfps
            if r.status == "open" and r.player_invited and r.pitch is None
        ),
        key=lambda r: (r.kind != "panel", -r.matter_cents, r.id),
    )
    for rfp in rfps:
        if made >= n or g.energy() < g.balance.energy.cost["pitch"]:
            break
        people = sorted(
            g.lawyers(),
            key=lambda p: (
                practice_of(g, p.id) not in rfp.practices,
                p.level not in ("equity_partner", "income_partner"),
                -_score(g, p.id),
                p.id,
            ),
        )
        team = tuple(p.id for p in people[:team_size])
        if team and g.act(PitchRfp(g.founder_id, rfp.id, team)):
            made += 1
    return made


def cross_sell(g: Game, n: int, min_score: float = 50.0) -> int:
    """Introduce colleagues to the firm's best clients in practices they do not yet use, by
    affinity (spec 7.2). Returns introductions made."""
    held = set(practices_held(g))
    lawyers = g.lawyers()
    options = []
    for rel in g.state.market.relationships:
        if rel.firm_id != PLAYER or rel.score < min_score or not rel.practices:
            continue
        for practice in held - set(rel.practices):
            affinity = max(g.data.practice(p).cross_sell.get(practice, 0.0) for p in rel.practices)
            if affinity > 0:
                options.append((-(affinity * rel.score), rel.client_id, practice))
    made = 0
    for _, client_id, practice in sorted(options):
        if made >= n or g.energy() < g.balance.energy.cost["introduce"]:
            break
        colleague = next(
            (
                p
                for p in sorted(lawyers, key=lambda p: (-_score(g, p.id), p.id))
                if practice_of(g, p.id) == practice
            ),
            None,
        )
        if colleague is not None and g.act(
            Introduce(g.founder_id, client_id, colleague.id, practice)
        ):
            made += 1
    return made


def hours_policy(g: Game, hours: int | None) -> None:
    """PT-M7b: the firm's billable target (hours a year), set when it differs."""
    if g.state.player.billable_target_hours != hours:
        g.act(SetHoursPolicy(g.founder_id, hours))


def push_hours(g: Game, monthly_hours: int) -> int:
    """Pyramid's billable-hours target: each associate's planned hours on their open named
    matters raised toward `monthly_hours` a month (on their biggest matter; the engine's
    capacity check refuses what does not fit). Returns the plans changed."""
    planned: dict[int, int] = {}
    biggest: dict[int, tuple[int, int]] = {}  # person -> (planned tenths, matter id)
    for m in g.state.market.open_matters(PLAYER):
        for t in m.team:
            planned[t.person_id] = planned.get(t.person_id, 0) + t.planned_tenths
            if t.planned_tenths > biggest.get(t.person_id, (-1, 0))[0]:
                biggest[t.person_id] = (t.planned_tenths, m.id)
    changed = 0
    target = monthly_hours * TENTHS
    for p in g.lawyers():
        if not is_associate(p.level) or p.id not in biggest:
            continue
        short = target - planned.get(p.id, 0)
        if short <= 0:
            continue
        tenths, matter_id = biggest[p.id]
        if g.act(SetMatterHours(g.founder_id, matter_id, p.id, (tenths + short) // TENTHS)):
            changed += 1
    return changed
