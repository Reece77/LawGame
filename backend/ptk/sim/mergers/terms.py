"""Terms, the other partnership's answer and both votes (spec 8.8; ADR PT-0007 2, PT-0016).

The merged profit pool is the two firms' trailing profits. A side's expected PEP change under
a points ratio s (the player's share) is

    ours:   s x pool / our equity partners / our PEP - 1
    theirs: (1 - s) x pool / their equity partners / their PEP - 1

The other firm's partners each vote yes when pep_change_weight x their change + bias(terms) +
N(0, noise_sd) > 0 (stream `merger_answer`, key (deal, round), one draw per partner in order),
where bias(terms) subtracts `mp_weight` if they lose the MP, `name_weight` if their name goes
(half for a combined name), `comp_weight` if their comp system changes and `rate_weight` x the
card rise their clients face. The deal passes their side with `mergers.vote_bp` of the count.
Failing, they counter once per round with the share that gives their median partner
`counter_margin` of PEP rise net of bias; after `max_rounds` talks end.

The player's partners vote through PT-M4's `governance` (a vote of kind "merger"), each with
the same utility on their own side's change (`our_utility`), plus confidence, lobbying and
noise from stream `vote`. A verein's answer reads `verein.talk_bias` and the region a member
brings; its PEP changes are nil (each member keeps its own pool).
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from simcore.kernel.money import BP_DENOMINATOR

from ptk.sim.data_models import Balance, GameData
from ptk.sim.log import LogItem, inbox_item
from ptk.sim.mergers import streams
from ptk.sim.mergers.models import Deal, Terms, with_deal
from ptk.sim.mergers.profile import Side, player_side, rival_side
from ptk.sim.mergers.talks import bias, put_mergers, size_gap
from ptk.sim.rivals.models import RivalFirm
from ptk.sim.state import GameState
from ptk.sim.streams import RngFactory

MAX_VOTERS = 60  # tunable-exempt: the other partnership's count is sampled at most this wide
SHARE_MIN, SHARE_MAX = 500, 9500  # tunable-exempt: a share between 5% and 95%


def pool_cents(ours: Side, theirs: Side, synergy_bp: int = 0) -> int:
    """The merged pool the partners expect: the two pools and `answer.synergy_bp` on top."""
    base = max(0, ours.profit_cents) + max(0, theirs.profit_cents)
    return base * (BP_DENOMINATOR + synergy_bp) // BP_DENOMINATOR


def our_change(ours: Side, theirs: Side, share_bp: int, synergy_bp: int = 0) -> float:
    pool = pool_cents(ours, theirs, synergy_bp)
    new = pool * share_bp / BP_DENOMINATOR / max(1, ours.equity)
    return new / max(ours.pep_cents, 1) - 1.0


def their_change(ours: Side, theirs: Side, share_bp: int, synergy_bp: int = 0) -> float:
    pool = pool_cents(ours, theirs, synergy_bp)
    new = pool * (BP_DENOMINATOR - share_bp) / BP_DENOMINATOR / max(1, theirs.equity)
    return new / max(theirs.pep_cents, 1) - 1.0


def card_rise(ours: Side, theirs: Side, rates: str) -> tuple[float, float]:
    """(rise for their clients, rise for ours) under the merged card (0 when it falls)."""
    hi = max(ours.rate_index, theirs.rate_index)
    merged = {
        "ours": ours.rate_index,
        "theirs": theirs.rate_index,
        "higher": hi,
        "blend": (ours.rate_index + theirs.rate_index) / 2,
    }[rates]
    return (
        max(0.0, merged / max(theirs.rate_index, 1e-6) - 1.0),
        max(0.0, merged / max(ours.rate_index, 1e-6) - 1.0),
    )


def merged_card(ours: Side, theirs: Side, rates: str) -> float:
    return {
        "ours": ours.rate_index,
        "theirs": theirs.rate_index,
        "higher": max(ours.rate_index, theirs.rate_index),
        "blend": (ours.rate_index + theirs.rate_index) / 2,
    }[rates]


def their_bias(terms: Terms, ours: Side, theirs: Side, balance: Balance) -> float:
    cfg = balance.mergers.answer
    b = 0.0
    if terms.mp == "ours":
        b -= cfg.mp_weight
    if terms.name == "ours":
        b -= cfg.name_weight
    elif terms.name == "combined":
        b -= cfg.name_weight / 2
    if terms.comp_system != theirs.comp_system:
        b -= cfg.comp_weight
    b -= cfg.rate_weight * card_rise(ours, theirs, terms.rates)[0]
    return b


def our_bias(terms: Terms, ours: Side, theirs: Side, balance: Balance) -> float:
    cfg = balance.mergers.answer
    b = 0.0
    if terms.mp == "theirs":
        b -= cfg.mp_weight
    if terms.name == "theirs":
        b -= cfg.name_weight
    elif terms.name == "combined":
        b -= cfg.name_weight / 2
    if terms.comp_system != ours.comp_system:
        b -= cfg.comp_weight
    b -= cfg.rate_weight * card_rise(ours, theirs, terms.rates)[1]
    return b


def our_utility(state: GameState, deal: Deal, data: GameData, balance: Balance) -> float:
    """A player's partner's utility for the deal before confidence and noise (governance adds
    them); engine-only."""
    firm = state.rivals.firm(deal.rival_id)
    if firm is None or deal.terms is None:
        return -1.0
    ours, theirs = player_side(state, data, balance), rival_side(firm, data)
    cfg = balance.mergers.answer
    if deal.form == "verein":
        region = 1.0 if ours.region != theirs.region else 0.0
        return cfg.region_weight * region
    return cfg.pep_change_weight * our_change(
        ours, theirs, deal.terms.our_share_bp, cfg.synergy_bp
    ) + our_bias(deal.terms, ours, theirs, balance)


def is_absorption(terms: Terms, balance: Balance) -> bool:
    """ADR PT-0016 1: the player's firm is the absorbed one when it takes the other firm's name
    and managing partner, or brings its partners under `mergers.absorbed_below_bp` of the pool."""
    if terms.name == "theirs" and terms.mp == "theirs":
        return True
    return terms.our_share_bp < balance.mergers.absorbed_below_bp


def passes(yes: int, voters: int, threshold_bp: int) -> bool:
    """A partnership's count passes with at least `threshold_bp` of the votes cast (PT-M4's
    rule for governance votes: 7 of 9 pass two thirds at 6,667 bp, 6 of 9 do not)."""
    return voters > 0 and yes * BP_DENOMINATOR >= threshold_bp * voters


@dataclass(frozen=True, slots=True)
class Answer:
    yes_bp: int
    passed: bool
    counter_share_bp: int | None


def their_answer(
    state: GameState, deal: Deal, firm: RivalFirm, rng: RngFactory, data: GameData, balance: Balance
) -> Answer:
    assert deal.terms is not None
    cfg = balance.mergers.answer
    ours, theirs = player_side(state, data, balance), rival_side(firm, data)
    gen = streams.answer(rng, state.turn, deal.id, deal.rounds + 1)
    if deal.form == "verein":
        b = bias(firm, "verein", balance)
        mean = (
            None
            if b is None
            else b
            + cfg.region_weight * (ours.region != theirs.region)
            - size_gap(ours, theirs, balance)
        )
    else:
        b = bias(firm, "merger", balance)
        mean = (
            None
            if b is None
            else cfg.pep_change_weight
            * their_change(ours, theirs, deal.terms.our_share_bp, cfg.synergy_bp)
            + their_bias(deal.terms, ours, theirs, balance)
            + b / 2
        )
    if mean is None:
        return Answer(0, False, None)
    n = max(1, min(MAX_VOTERS, theirs.equity))
    yes = sum(1 for _ in range(n) if mean + float(gen.normal(0.0, cfg.noise_sd)) > 0)
    yes_bp = yes * BP_DENOMINATOR // n
    passed = passes(yes, n, balance.mergers.vote_bp)
    counter = None
    if not passed and deal.form == "merger":
        # the share whose expected utility is counter_margin x weight for the median partner
        others = mean - cfg.pep_change_weight * their_change(
            ours, theirs, deal.terms.our_share_bp, cfg.synergy_bp
        )
        needed = cfg.counter_margin - others / cfg.pep_change_weight
        pool = pool_cents(ours, theirs, cfg.synergy_bp)
        theirs_needed = (1.0 + needed) * max(theirs.pep_cents, 1) * theirs.equity
        share = round(BP_DENOMINATOR * (1.0 - theirs_needed / max(pool, 1)))
        counter = max(SHARE_MIN, min(SHARE_MAX, share))
        if counter >= deal.terms.our_share_bp:
            counter = None
    return Answer(yes_bp, passed, counter)


def answer_terms(
    state: GameState, rng: RngFactory, data: GameData, balance: Balance
) -> tuple[GameState, tuple[LogItem, ...]]:
    """Phase 1 (before the partnership's votes are counted): the other partnership answers the
    terms put; a yes opens the player's own vote (counted the same phase)."""
    from ptk.sim.mergers.actions import end_deal
    from ptk.sim.partnership.governance import open_vote

    logs: list[LogItem] = []
    pid = state.player.id
    for deal in state.mergers.open_deals():
        if deal.stage != "terms" or deal.terms is None:
            continue
        firm = state.rivals.firm(deal.rival_id)
        if firm is None or not firm.active:
            state = end_deal(state, deal, "the other firm no longer exists", balance)
            continue
        ans = their_answer(state, deal, firm, rng, data, balance)
        deal = replace(deal, rounds=deal.rounds + 1, their_yes_bp=ans.yes_bp)
        if ans.passed:
            state, vote = open_vote(
                state,
                pid,
                "merger",
                None,
                {"deal_id": deal.id, "threshold_bp": balance.mergers.vote_bp, "form": deal.form},
            )
            deal = replace(deal, stage="voting", stage_turn=state.turn, our_vote_id=vote.id)
            state = put_mergers(state, with_deal(state.mergers, deal))
            template = "merger_their_yes"
        elif ans.counter_share_bp is not None and deal.rounds < balance.mergers.answer.max_rounds:
            deal = replace(
                deal,
                stage="countered",
                stage_turn=state.turn,
                counter_share_bp=ans.counter_share_bp,
            )
            state = put_mergers(state, with_deal(state.mergers, deal))
            template = "merger_countered"
        else:
            state = put_mergers(state, with_deal(state.mergers, deal))
            state = end_deal(state, deal, "the other partnership voted no", balance)
            template = "merger_their_no"
        logs.append(
            inbox_item(
                state.turn,
                pid,
                template,
                link_kind="mergers",
                link_id=deal.id,
                firm=firm.name,
                yes_pct=ans.yes_bp // 100,
                counter_pct=(ans.counter_share_bp or 0) // 100,
            )
        )
    return state, tuple(logs)
