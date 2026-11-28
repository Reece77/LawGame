"""Confidence and votes (ADR PT-0007 1-2; spec 5.5's utility).

Ported from backend/tst/sim/finance/board.py @ 02fba2aa (Tech Startup Tycoon), the monthly
confidence step of `board_month`; changed: equity partners instead of directors, confidence
in the managing partner; the months-below counter becomes the no-confidence petition (an
average below `petition_below` for `petition_months` brings an election, not a removal); no
board meetings (the whip count is always shown); votes are Partner Track's own.

Confidence: each equity partner but the managing partner holds a confidence 0-100 in the
MP, moved monthly by TST 14.6's rule toward a target (formulas.confidence_target). Shown as
a whip count with ranges, never the number.

Votes: a vote is opened by an action and counted in phase 1 of the same turn. Each equity
partner votes yes when their utility (the proposal's effect on them, their confidence, the
MP's lobbying and promises, and noise from stream `vote` keyed (vote_id, person_id)) is above
zero; the MP votes for their own proposals. Votes are weighted per the agreement (one
partner one vote, or by points); a vote passes with at least its threshold of votes cast.
The player sees a predicted range only (`predicted`).
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, replace

from simcore.kernel.money import BP_DENOMINATOR

from ptk.sim.data_models import Balance, GameData
from ptk.sim.ledger import LedgerEntry
from ptk.sim.log import LogItem, inbox_item
from ptk.sim.partnership import formulas as fx
from ptk.sim.partnership.common import (
    book_cents,
    firm_partnership,
    home_practice,
    profit_12m,
    put,
    queue_event,
)
from ptk.sim.partnership.models import (
    FirmPartnership,
    Param,
    Partner,
    Vote,
    with_partner,
    with_vote,
)
from ptk.sim.state import GameState
from ptk.sim.streams import RngFactory

PARTNERSHIP = "partnership"


def vote_noise(rng: RngFactory, turn: int, vote_id: int, person_id: int, sd: float) -> float:
    """The one call site of stream `vote` (ADR PT-0012)."""
    return float(rng.stream(turn, "vote", vote_id, person_id).normal(0.0, sd))


# --- Confidence -----------------------------------------------------------------------------


def mp_skill(state: GameState, fp: FirmPartnership) -> float:
    if fp.mp_id is None:
        return 10.0
    mp = state.person(fp.mp_id)
    return (mp.skills["leadership"] + mp.skills["communication"]) / 2


def pep_trend(fp: FirmPartnership) -> float:
    """The firm's PEP run rate (trailing twelve months) against the last allocated year's."""
    if not fp.last_pep_cents or fp.last_pep_cents <= 0 or not fp.equity_partners:
        return 0.0
    run = profit_12m(fp) / len(fp.equity_partners)
    return run / fp.last_pep_cents - 1


def departures_12m(fp: FirmPartnership, turn: int) -> int:
    return sum(1 for d in fp.departures if d.equity and turn - d.turn < fx.MONTHS_PER_YEAR)


def voters(fp: FirmPartnership) -> tuple[Partner, ...]:
    return fp.equity_partners


def confidence_month(state: GameState, balance: Balance) -> GameState:
    cfg = balance.partnership.confidence
    for fp in state.partnership.firms:
        skill = mp_skill(state, fp)
        trend = pep_trend(fp)
        trouble = fp.breach_months > 0 or fp.called_turn is not None
        suspended = fp.draws_suspended
        gone = departures_12m(fp, state.turn)
        for p in fp.equity_partners:
            if p.person_id == fp.mp_id:
                continue
            target = fx.confidence_target(
                p.satisfaction, trend, skill, suspended, trouble, gone, cfg
            )
            b = fx.next_confidence(fx.clamp_confidence(p.confidence + p.nudge), target, cfg)
            fp = with_partner(fp, replace(p, confidence=b, nudge=0.0))
        confs = [p.confidence for p in fp.equity_partners if p.person_id != fp.mp_id]
        low = bool(confs) and statistics.fmean(confs) < cfg.petition_below
        fp = replace(fp, low_confidence_months=fp.low_confidence_months + 1 if low else 0)
        state = put(state, fp)
        if fp.low_confidence_months == cfg.petition_months:
            state = queue_event(state, fp.firm_id, "no_confidence_petition", balance)
    return state


def whip_count(fp: FirmPartnership, balance: Balance) -> dict[str, tuple[int, int]]:
    confs = [p.confidence for p in fp.equity_partners if p.person_id != fp.mp_id]
    return fx.whip_range(confs, balance.partnership.confidence)


def confidence_band(p: Partner, balance: Balance) -> tuple[int, int]:
    """A partner's confidence as the MP sees it: a band, never the number."""
    hw = balance.partnership.confidence.range_half_width
    centre = round(p.confidence / 5) * 5  # tunable-exempt: shown in steps of 5
    return max(0, round(centre - hw)), min(100, round(centre + hw))


# --- Votes ----------------------------------------------------------------------------------


def threshold_for(fp: FirmPartnership, kind: str, params: dict[str, Param]) -> int:
    a = fp.agreement
    if kind == "admission":
        if params.get("track") == "equity" and a.comp_system in ("lockstep", "modified_lockstep"):
            return a.equity_lockstep_bp
        return a.admission_bp
    if kind == "terms":
        return a.terms_bp
    if kind == "capital_call":
        return a.capital_call_bp
    if kind == "deequity":
        return a.deequity_bp
    if kind == "merger":  # PT-M13: mergers.vote_bp, carried on the vote (spec 8.8)
        value = params.get("threshold_bp")
        return value if isinstance(value, int) else a.terms_bp
    return a.admission_bp  # election: a simple majority


def open_vote(
    state: GameState,
    firm_id: int,
    kind: str,
    subject_id: int | None,
    params: dict[str, Param],
) -> tuple[GameState, Vote]:
    fp = firm_partnership(state, firm_id)
    vid = state.partnership.next_vote_id
    vote = Vote(
        id=vid,
        firm_id=firm_id,
        kind=kind,  # type: ignore[arg-type]
        subject_id=subject_id,
        params=tuple(sorted(params.items())),
        opened_turn=state.turn,
        threshold_bp=threshold_for(fp, kind, params),
    )
    state = put(state, with_vote(fp, vote))
    return replace(state, partnership=replace(state.partnership, next_vote_id=vid + 1)), vote


def _weight(fp: FirmPartnership, p: Partner) -> float:
    return p.points if fp.agreement.voting == "points" else 1.0


def contribution(state: GameState, fp: FirmPartnership, balance: Balance) -> dict[int, float]:
    from ptk.sim.partnership.comp import credits

    return fx.contribution_shares(credits(state, fp, balance), balance.partnership)


def practice_utilisation(
    state: GameState, firm_id: int, practice: str, balance: Balance, data: GameData
) -> float:
    from ptk.sim.interfaces import month_hours

    people = {
        e.person_id
        for e in state.staff(firm_id)
        if home_practice(state.person(e.person_id), data) == practice
    }
    if not people:
        return 0.0
    worked = sum(r.tenths for r in month_hours(state, firm_id) if r.person_id in people)
    cap = sum(
        balance.people.levels[state.person(pid).level].capacity_hours * 10 / fx.MONTHS_PER_YEAR
        for pid in people
    )
    return worked / cap if cap else 0.0


def candidate_quality(state: GameState, firm_id: int, person_id: int, data: GameData) -> float:
    """The candidate's ability as the firm sees it (displayed ranges, never true values)."""
    from ptk.sim.people.reveal import shown_rating

    person = state.person(person_id)
    reveal = state.reveal(firm_id, person_id)
    role = data.role(person.role)
    if reveal is None:
        return 10.0
    return shown_rating(person, reveal, role.primary)


def base_utility(
    state: GameState, fp: FirmPartnership, vote: Vote, p: Partner, balance: Balance, data: GameData
) -> float:
    """A partner's utility before noise (engine-only: never shown)."""
    cfg = balance.partnership.votes
    u = cfg.confidence_weight * (p.confidence - 50) / 50
    if p.lobbied_turn == state.turn:
        u += cfg.lobby_points
    u += cfg.promise_per_point * p.promised_points
    if vote.kind == "admission" and vote.subject_id is not None:
        track = vote.param("track")
        rating = candidate_quality(state, fp.firm_id, vote.subject_id, data)
        # shown_rating is the 1-20 mean of primaries; on the CA scale x 10 (formulas.md 1)
        quality = (rating * 10 - cfg.quality_ref) / cfg.quality_scale
        practice = home_practice(state.person(vote.subject_id), data)
        need = 2 * (practice_utilisation(state, fp.firm_id, practice, balance, data) - cfg.need_ref)
        total = sum(q.points for q in fp.equity_partners)
        start = balance.partnership.lockstep.start_points
        dilution = start / (total + start)
        if track == "income":
            dilution *= cfg.income_dilution_bp / BP_DENOMINATOR
        sponsor = vote.param("sponsor_id")
        rel = 0.0
        if sponsor == p.person_id:
            rel = cfg.sponsor_weight
        elif isinstance(sponsor, int) and home_practice(
            state.person(sponsor), data
        ) == home_practice(state.person(p.person_id), data):
            rel = cfg.sponsor_weight / 2
        u += (
            cfg.quality_weight * quality
            + cfg.need_weight * need
            - cfg.dilution_weight * dilution
            + rel
        )
    elif vote.kind == "terms":
        term, value = vote.param("term"), vote.param("value")
        if term == "comp_system" and isinstance(value, str):
            from ptk.sim.partnership.comp import comp_shares

            pool = max(fp.last_profit_cents or 0, profit_12m(fp), 1)
            now = comp_shares(state, fp, pool, balance).get(p.person_id, 0)
            new = comp_shares(state, fp, pool, balance, system=value).get(p.person_id, 0)
            u += cfg.terms_weight * (new - now) / max(now, 1)
        else:
            u += cfg.terms_bias
    elif vote.kind == "capital_call":
        amount = vote.param("amount_cents")
        total = sum(q.points for q in fp.equity_partners) or 1.0
        mine = (amount if isinstance(amount, int) else 0) * p.points / total
        u -= cfg.capital_call_weight * mine / max(p.capital_cents, 1)
        stressed = fp.breach_months > 0 or fp.called_turn is not None or fp.insolvent_months > 0
        u += cfg.capital_call_stress if stressed else 0.0
    elif vote.kind == "deequity" and vote.subject_id is not None:
        if p.person_id == vote.subject_id:
            return -10.0  # tunable-exempt: the subject always votes against
        shares = contribution(state, fp, balance)
        median = statistics.median(shares.values()) if shares else 0.0
        target = shares.get(vote.subject_id, 0.0)
        u += cfg.deequity_weight * (median - target) / max(median, 1e-9)
    elif vote.kind == "merger":  # PT-M13: the expected PEP change and the terms
        from ptk.sim.mergers.terms import our_utility

        deal = state.mergers.deal(int(vote.param("deal_id") or 0))
        if deal is not None:
            u += our_utility(state, deal, data, balance)
    elif vote.kind == "election":
        u = cfg.election_weight * (p.confidence - 50) / 50
        if p.lobbied_turn == state.turn:
            u += cfg.lobby_points
    return u


@dataclass(frozen=True, slots=True)
class Prediction:
    yes_lo: float
    yes_hi: float
    total: float
    needed: float  # yes weight needed to pass


def predicted(
    state: GameState, fp: FirmPartnership, vote: Vote, balance: Balance, data: GameData
) -> Prediction:
    """The player's predicted range: partners within predict_k of indifference count either
    way. The MP votes for their own proposals (an election: for themselves)."""
    k = balance.partnership.votes.predict_k
    lo = hi = total = 0.0
    for p in voters(fp):
        w = _weight(fp, p)
        total += w
        if p.person_id == fp.mp_id:
            lo += w
            hi += w
            continue
        u = base_utility(state, fp, vote, p, balance, data)
        if u > k:
            lo += w
            hi += w
        elif u > -k:
            hi += w
    return Prediction(lo, hi, total, total * vote.threshold_bp / BP_DENOMINATOR)


def count_vote(
    state: GameState,
    fp: FirmPartnership,
    vote: Vote,
    rng: RngFactory,
    balance: Balance,
    data: GameData,
) -> Vote:
    sd = balance.partnership.votes.noise_sd
    yes = no = 0.0
    ballots: list[tuple[int, bool]] = []
    for p in voters(fp):
        w = _weight(fp, p)
        if p.person_id == fp.mp_id:
            ok = True
        else:
            u = base_utility(state, fp, vote, p, balance, data)
            ok = u + vote_noise(rng, state.turn, vote.id, p.person_id, sd) > 0
        ballots.append((p.person_id, ok))
        yes, no = (yes + w, no) if ok else (yes, no + w)
    total = yes + no
    passed = total > 0 and yes * BP_DENOMINATOR >= vote.threshold_bp * total
    return replace(
        vote,
        status="passed" if passed else "failed",
        resolved_turn=state.turn,
        yes_weight=yes,
        no_weight=no,
        ballots=tuple(ballots),
    )


@dataclass(frozen=True, slots=True)
class VotesMonth:
    state: GameState
    entries: tuple[LedgerEntry, ...]
    log: tuple[LogItem, ...]


def resolve_votes(
    state: GameState, rng: RngFactory, balance: Balance, data: GameData
) -> VotesMonth:
    """Phase 1: count every open vote (elections are run by phase 10) and apply the passed."""
    from ptk.sim.partnership.effects import apply_vote

    entries: list[LedgerEntry] = []
    logs: list[LogItem] = []
    for fp0 in state.partnership.firms:
        for vote in fp0.votes:
            if vote.status != "open" or vote.kind == "election":
                continue
            fp = firm_partnership(state, fp0.firm_id)
            if vote.subject_id is not None and state.employment_of(vote.subject_id) is None:
                # PT-M7: the subject left before the count (a notice that ended in phase 1)
                gone = replace(vote, status="withdrawn", resolved_turn=state.turn)
                state = put(state, with_vote(fp, gone))
                continue
            counted = count_vote(state, fp, vote, rng, balance, data)
            state = put(state, with_vote(fp, counted))
            logs.append(
                inbox_item(
                    state.turn,
                    fp.firm_id,
                    "vote_result",
                    link_kind=None,
                    title=vote_title(state, counted),
                    result="passed" if counted.status == "passed" else "failed",
                    yes=f"{counted.yes_weight:g}",
                    no=f"{counted.no_weight:g}",
                )
            )
            if counted.status == "passed":
                state, more_entries, more_logs = apply_vote(state, counted, rng, balance, data)
                entries += more_entries
                logs += more_logs
    return VotesMonth(state, tuple(entries), tuple(logs))


def vote_title(state: GameState, vote: Vote) -> str:
    who = ""
    if vote.subject_id is not None:
        p = state.person(vote.subject_id)
        who = f"{p.first_name} {p.last_name}"
    if vote.kind == "admission":
        return f"{who} for {vote.param('track')} partner"
    if vote.kind == "terms":
        return f"the agreement: {vote.param('term')} to {vote.param('value')}"
    if vote.kind == "capital_call":
        return "a capital call"
    if vote.kind == "deequity":
        return f"de-equitise {who} ({vote.param('mode')})"
    if vote.kind == "merger":
        from ptk.sim.mergers.views import deal_title

        return deal_title(state, int(vote.param("deal_id") or 0))
    return f"managing partner: the MP against {who}"


def median_book(state: GameState, fp: FirmPartnership) -> int:
    books = [book_cents(state, state.person(p.person_id)) for p in fp.equity_partners]
    return int(statistics.median(books)) if books else 0
