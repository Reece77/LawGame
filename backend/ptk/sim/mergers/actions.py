"""The player's merger and verein actions (spec 8.8; ADR-0014; ADR PT-0016).

- **Approach a firm** (energy `merger_approach`, the managing partner): a merger or a verein.
  The other firm talks or declines at once (`talks.approach`); talks open a confidentiality
  window (`mergers.confidential_months`).
- **Answer a rival's approach**: open talks (its terms stand as the first proposal) or decline.
- **Commission due diligence** (energy `merger_diligence`): a level's professional fees and
  months (`ptk.sim.mergers.diligence`).
- **Put terms** (energy `merger_terms`): the points ratio, name, managing partner, comp
  system and rate card; the other partnership answers in phase 1 (`ptk.sim.mergers.terms`).
- **Walk away**: talks end, with the cooldown.

Every action is the managing partner's (PT-M4's `require_mp`).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

from ptk.sim.data_models import COMP_SYSTEMS, Balance, GameData
from ptk.sim.errors import InvalidActionError
from ptk.sim.hiring.actions import Outcome, acting_firm, spend_energy
from ptk.sim.log import inbox_item
from ptk.sim.mergers.models import Deal, Terms, with_cooldown, with_deal
from ptk.sim.mergers.talks import approach, book_for, eligible, put_mergers
from ptk.sim.partnership.common import require_mp
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState


@dataclass(frozen=True, slots=True)
class ApproachFirm:
    actor_id: int
    rival_key: str
    form: Literal["merger", "verein"] = "merger"
    kind: Literal["merger_approach"] = "merger_approach"


@dataclass(frozen=True, slots=True)
class AnswerApproach:
    actor_id: int
    deal_id: int
    accept: bool
    kind: Literal["merger_answer"] = "merger_answer"


@dataclass(frozen=True, slots=True)
class CommissionDiligence:
    actor_id: int
    deal_id: int
    kind: Literal["merger_diligence"] = "merger_diligence"


@dataclass(frozen=True, slots=True)
class PutTerms:
    actor_id: int
    deal_id: int
    our_share_bp: int = 5000
    name: Literal["ours", "theirs", "combined"] = "ours"
    mp: Literal["ours", "theirs"] = "ours"
    comp_system: str = "modified_lockstep"
    rates: Literal["ours", "theirs", "higher", "blend"] = "ours"
    kind: Literal["merger_terms"] = "merger_terms"


@dataclass(frozen=True, slots=True)
class WalkAway:
    actor_id: int
    deal_id: int
    kind: Literal["merger_walk_away"] = "merger_walk_away"


type MergerAction = ApproachFirm | AnswerApproach | CommissionDiligence | PutTerms | WalkAway

MERGER_ACTION_TYPES: dict[str, type[MergerAction]] = {
    "merger_approach": ApproachFirm,
    "merger_answer": AnswerApproach,
    "merger_diligence": CommissionDiligence,
    "merger_terms": PutTerms,
    "merger_walk_away": WalkAway,
}


def _err(msg: str) -> InvalidActionError:
    return InvalidActionError(msg)


def _mp(state: GameState, actor_id: int) -> int:
    firm_id = acting_firm(state, actor_id)
    if firm_id != state.player.id:
        raise _err("only the player's firm makes merger moves")
    require_mp(state, firm_id, actor_id)
    return firm_id


def _deal(state: GameState, deal_id: int) -> Deal:
    deal = state.mergers.deal(deal_id)
    if deal is None or not deal.is_open:
        raise _err(f"no open talks {deal_id}")
    return deal


def end_deal(state: GameState, deal: Deal, reason: str, balance: Balance) -> GameState:
    done = replace(deal, stage="ended", ended_turn=state.turn, ended_reason=reason)
    ms = with_cooldown(
        with_deal(state.mergers, done), deal.rival_key, state.turn + balance.mergers.cooldown_months
    )
    return put_mergers(state, ms)


def approach_firm(
    state: GameState, a: ApproachFirm, rng: RngFactory, balance: Balance, data: GameData
) -> Outcome:
    _mp(state, a.actor_id)
    firm = state.rivals.by_key(a.rival_key)
    if firm is None:
        raise _err(f"no firm {a.rival_key!r}")
    why = eligible(state, firm, a.form, balance)
    if why:
        raise _err(f"{firm.name}: {why}")
    if a.form == "verein":
        from ptk.sim.geo.cities import rival_region

        if rival_region(data, firm.hq) not in ("us", "uk"):
            raise _err("a verein member must sit in a region the game models")
    state = spend_energy(state, a.actor_id, "merger_approach", balance)
    state, _deal_made, log = approach(state, firm, a.form, rng, data, balance)
    return Outcome(state, (), log)


def answer_approach(
    state: GameState, a: AnswerApproach, rng: RngFactory, balance: Balance, data: GameData
) -> Outcome:
    firm_id = _mp(state, a.actor_id)
    deal = _deal(state, a.deal_id)
    if deal.stage != "approached":
        raise _err("that approach has been answered")
    firm = state.rivals.firm(deal.rival_id)
    name = firm.name if firm is not None else deal.rival_key
    if not a.accept:
        state = end_deal(state, deal, "the player declined", balance)
        return Outcome(state)
    opened = replace(deal, stage="talks", stage_turn=state.turn)
    if deal.form == "merger" and firm is not None and not deal.book:
        state, book = book_for(state, deal.id, firm, rng, data, balance)
        opened = replace(opened, book=book)
    state = put_mergers(state, with_deal(state.mergers, opened))
    log = inbox_item(
        state.turn,
        firm_id,
        "merger_talks",
        link_kind="mergers",
        link_id=deal.id,
        firm=name,
        form=deal.form,
    )
    return Outcome(state, (), (log,))


def put_terms(state: GameState, a: PutTerms, balance: Balance, data: GameData) -> Outcome:
    _mp(state, a.actor_id)
    deal = _deal(state, a.deal_id)
    if deal.stage not in ("talks", "countered"):
        raise _err("terms can be put only while talks are open (answer an approach first)")
    if deal.form == "merger":
        if not 500 <= a.our_share_bp <= 9500:  # tunable-exempt: a share between 5% and 95%
            raise _err("the points ratio gives each side between 5% and 95%")
        if a.comp_system not in COMP_SYSTEMS:
            raise _err(f"unknown comp system {a.comp_system!r}")
        if deal.diligence_due_turn is not None:
            raise _err("diligence is still running")
    state = spend_energy(state, a.actor_id, "merger_terms", balance)
    terms = Terms(
        our_share_bp=a.our_share_bp,
        name=a.name,
        mp=a.mp,
        comp_system=a.comp_system,
        rates=a.rates,
    )
    from ptk.sim.mergers.terms import is_absorption

    absorbed = deal.form == "merger" and is_absorption(terms, balance)
    put = replace(deal, terms=terms, stage="terms", stage_turn=state.turn, absorbed=absorbed)
    return Outcome(put_mergers(state, with_deal(state.mergers, put)))


def walk_away(state: GameState, a: WalkAway, balance: Balance) -> Outcome:
    _mp(state, a.actor_id)
    deal = _deal(state, a.deal_id)
    if deal.stage in ("voting", "clearance"):
        raise _err("the partnerships have voted: the deal closes")
    return Outcome(end_deal(state, deal, "the player walked away", balance))


def apply_merger_action(
    state: GameState, action: MergerAction, rng: RngFactory, balance: Balance, data: GameData
) -> Outcome:
    if isinstance(action, ApproachFirm):
        return approach_firm(state, action, rng, balance, data)
    if isinstance(action, AnswerApproach):
        return answer_approach(state, action, rng, balance, data)
    if isinstance(action, CommissionDiligence):
        from ptk.sim.mergers.diligence import commission

        _mp(state, action.actor_id)
        deal = _deal(state, action.deal_id)
        state = spend_energy(state, action.actor_id, "merger_diligence", balance)
        return commission(state, deal, rng, balance, data)
    if isinstance(action, PutTerms):
        return put_terms(state, action, balance, data)
    return walk_away(state, action, balance)
