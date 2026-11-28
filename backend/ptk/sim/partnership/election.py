"""The managing partner's election (ADR PT-0007 3).

From stage 2 the agreement sets the MP's term (default 4 years). At the term's end, or after
`petition_months` with average confidence below `petition_below` (a no-confidence petition),
an election runs in phase 10: the MP stands; the most ambitious partner (ambition at least
`rival_ambition_min`, then leadership) stands against them. Each equity partner votes by
their confidence in the MP plus noise (stream `vote`). Losing is not game over: the player
stays as a partner (their own practice and votes; MP-only actions are refused) and stands
again at the next term's end, or hands over to a partner and plays them. Ironman makes losing
final.
"""

from __future__ import annotations

from dataclasses import replace

from simcore.kernel.money import BP_DENOMINATOR

from ptk.sim.data_models import Balance, GameData
from ptk.sim.log import LogItem, inbox_item
from ptk.sim.partnership import formulas as fx
from ptk.sim.partnership.common import name, put
from ptk.sim.partnership.governance import vote_noise
from ptk.sim.partnership.models import FirmPartnership, Vote, with_vote
from ptk.sim.state import GameState
from ptk.sim.streams import RngFactory

IRONMAN = "ironman"


def rival_candidate(
    state: GameState, fp: FirmPartnership, balance: Balance, exclude: set[int]
) -> int | None:
    best: tuple[float, float, int] | None = None
    for p in fp.equity_partners:
        if p.person_id in exclude:
            continue
        person = state.person(p.person_id)
        ambition = person.personality["ambition"]
        if ambition < balance.partnership.election.rival_ambition_min:
            continue
        key = (-ambition, -person.skills["leadership"], p.person_id)
        if best is None or key < best:
            best = key
    return best[2] if best else None


def election_month(
    state: GameState, rng: RngFactory, balance: Balance, data: GameData
) -> tuple[GameState, tuple[LogItem, ...]]:
    logs: list[LogItem] = []
    cfg = balance.partnership
    for fp in state.partnership.firms:
        firm = state.firm(fp.firm_id)
        term_months = fp.agreement.mp_term_years * fx.MONTHS_PER_YEAR
        if fp.term_ends_turn is None:
            if firm.stage >= cfg.election.stage:
                fp = replace(fp, term_ends_turn=state.turn + term_months)
                state = put(state, fp)
                logs.append(
                    inbox_item(
                        state.turn,
                        fp.firm_id,
                        "mp_term_set",
                        link_kind=None,
                        years=fp.agreement.mp_term_years,
                    )
                )
            continue
        petition = fp.low_confidence_months >= cfg.confidence.petition_months
        if state.turn < fp.term_ends_turn and not petition:
            continue
        state, more = _run(state, fp, petition, rng, balance)
        logs += more
    return state, tuple(logs)


def _run(
    state: GameState, fp: FirmPartnership, petition: bool, rng: RngFactory, balance: Balance
) -> tuple[GameState, list[LogItem]]:
    cfg = balance.partnership
    player = state.founder_of(fp.firm_id)
    term_months = fp.agreement.mp_term_years * fx.MONTHS_PER_YEAR
    incumbent = fp.mp_id
    ousted = player is not None and incumbent != player
    if ousted:
        challenger: int | None = player  # the player stands again against the sitting MP
    else:
        challenger = rival_candidate(state, fp, balance, {x for x in (incumbent,) if x is not None})
    logs: list[LogItem] = []
    if challenger is None or incumbent is None:
        fp = replace(fp, term_ends_turn=state.turn + term_months, low_confidence_months=0)
        logs.append(inbox_item(state.turn, fp.firm_id, "mp_unopposed", link_kind=None))
        return put(state, fp), logs
    vid = state.partnership.next_vote_id
    yes = no = 0.0  # yes: for the sitting MP
    ballots: list[tuple[int, bool]] = []
    w = cfg.votes.election_weight
    for p in fp.equity_partners:
        weight = p.points if fp.agreement.voting == "points" else 1.0
        if p.person_id == incumbent:
            ok = True
        elif p.person_id == challenger:
            ok = False
        else:
            u = w * (p.confidence - 50) / 50
            if p.lobbied_turn == state.turn:
                u += cfg.votes.lobby_points * (-1 if ousted else 1)
            ok = u + vote_noise(rng, state.turn, vid, p.person_id, cfg.votes.noise_sd) > 0
        ballots.append((p.person_id, ok))
        yes, no = (yes + weight, no) if ok else (yes, no + weight)
    mp_wins = (
        yes * BP_DENOMINATOR >= fp.agreement.admission_bp * (yes + no) if not ousted else yes >= no
    )
    vote = Vote(
        id=vid,
        firm_id=fp.firm_id,
        kind="election",
        subject_id=challenger,
        params=(("incumbent", incumbent), ("petition", petition)),
        opened_turn=state.turn,
        threshold_bp=fp.agreement.admission_bp,
        status="passed" if mp_wins else "failed",
        resolved_turn=state.turn,
        yes_weight=yes,
        no_weight=no,
        ballots=tuple(ballots),
    )
    fp = with_vote(fp, vote)
    fp = replace(fp, term_ends_turn=state.turn + term_months, low_confidence_months=0)
    state = replace(state, partnership=replace(state.partnership, next_vote_id=vid + 1))
    winner = incumbent if mp_wins else challenger
    fp = replace(fp, mp_id=winner)
    if winner == player:
        fp = replace(fp, ousted_mp_id=None, election_lost_turn=None)
        logs.append(
            inbox_item(
                state.turn,
                fp.firm_id,
                "election_won",
                link_kind=None,
                rival=name(state.person(challenger if not ousted else incumbent)),
            )
        )
        # partners start the new term with a clean slate toward the start value
        for p in fp.equity_partners:
            if p.person_id != winner:
                fp = with_partner_conf(fp, p.person_id, max(p.confidence, cfg.confidence.restless))
    elif player is not None and incumbent == player:
        fp = replace(fp, ousted_mp_id=player, election_lost_turn=state.turn)
        for p in fp.equity_partners:
            if p.person_id != winner:
                fp = with_partner_conf(fp, p.person_id, cfg.confidence.start)
        logs.append(
            inbox_item(
                state.turn,
                fp.firm_id,
                "election_lost",
                link_kind=None,
                rival=name(state.person(winner)),
            )
        )
        if state.save_meta.difficulty == IRONMAN:
            meta = replace(state.save_meta, game_state="election_lost", ended_turn=state.turn)
            state = replace(state, save_meta=meta)
    else:
        logs.append(
            inbox_item(
                state.turn,
                fp.firm_id,
                "election_lost_again",
                link_kind=None,
                rival=name(state.person(winner)),
            )
        )
    return put(state, fp), logs


def with_partner_conf(fp: FirmPartnership, person_id: int, confidence: float) -> FirmPartnership:
    from ptk.sim.partnership.models import with_partner

    p = fp.partner(person_id)
    return fp if p is None else with_partner(fp, replace(p, confidence=confidence))
