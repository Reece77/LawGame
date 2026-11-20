"""Partnership actions (ADR-0014): immediate, by the player's founding partner. Votes opened
here are counted in phase 1 of the same turn; lateral offers resolve there too.

MP-only (refused after a lost election, ADR PT-0007 3): agreement votes, capital calls,
December proposals, de-equitisation, the comp round, draws, laterals, counter-offers,
repaying the revolver. Any partner may lobby, promise and name sponsors.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, fields, replace
from typing import Any, Literal

import numpy as np

from ptk.sim.data_models import COMP_SYSTEMS, Balance, GameData
from ptk.sim.errors import PartnershipError, UnknownPersonError, UnknownVoteError
from ptk.sim.hiring.actions import Outcome, acting_firm, spend_energy
from ptk.sim.interfaces import CounterOffer
from ptk.sim.ledger import CASH, REVOLVER, LedgerBalances, LedgerEntry, account_balance
from ptk.sim.partnership import laterals
from ptk.sim.partnership.careers import eligible, tracks_for
from ptk.sim.partnership.common import firm_partnership, put, require_mp, ym
from ptk.sim.partnership.governance import open_vote
from ptk.sim.partnership.models import (
    AGREEMENT_TERMS,
    Agreement,
    Candidacy,
    with_candidacy,
    with_partner,
    with_sponsor,
    with_vote,
)
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState, with_people, with_person_states

type Draws = Callable[[], np.random.Generator]
DECEMBER = 12  # tunable-exempt: the December vote (spec 5.5)


@dataclass(frozen=True, slots=True)
class ProposeTerms:
    actor_id: int
    term: str
    value: str | int | bool
    kind: Literal["propose_terms"] = "propose_terms"


@dataclass(frozen=True, slots=True)
class CapitalCall:
    actor_id: int
    amount_cents: int  # in total, shared by points
    kind: Literal["capital_call"] = "capital_call"


@dataclass(frozen=True, slots=True)
class ProposePartner:
    actor_id: int
    person_id: int
    track: Literal["equity", "income", "counsel", "not_this_year"]
    sponsor_id: int | None = None
    kind: Literal["propose_partner"] = "propose_partner"


@dataclass(frozen=True, slots=True)
class Deequitise:
    actor_id: int
    person_id: int
    mode: Literal["income", "out"]
    kind: Literal["deequitise"] = "deequitise"


@dataclass(frozen=True, slots=True)
class Lobby:
    actor_id: int
    person_id: int
    kind: Literal["lobby"] = "lobby"


@dataclass(frozen=True, slots=True)
class PromisePoints:
    actor_id: int
    person_id: int
    points: float
    kind: Literal["promise_points"] = "promise_points"


@dataclass(frozen=True, slots=True)
class WithdrawVote:
    actor_id: int
    vote_id: int
    kind: Literal["withdraw_vote"] = "withdraw_vote"


@dataclass(frozen=True, slots=True)
class SetDraws:
    actor_id: int
    suspended: bool
    kind: Literal["set_draws"] = "set_draws"


@dataclass(frozen=True, slots=True)
class CompRound:
    actor_id: int
    person_id: int
    gate_steps: int = 0  # modified lockstep: hold (-1) or move up (1-2) a step
    adjust_bp: int = 0  # committee or the bonus pool: move the partner's share
    kind: Literal["comp_round"] = "comp_round"


@dataclass(frozen=True, slots=True)
class SetSponsor:
    actor_id: int
    person_id: int
    sponsor_id: int
    kind: Literal["set_sponsor"] = "set_sponsor"


@dataclass(frozen=True, slots=True)
class LateralSearch:
    actor_id: int
    practice: str
    kind: Literal["lateral_search"] = "lateral_search"


@dataclass(frozen=True, slots=True)
class Diligence:
    actor_id: int
    person_id: int
    kind: Literal["diligence"] = "diligence"


@dataclass(frozen=True, slots=True)
class LateralOffer:
    actor_id: int
    person_id: int
    comp_cents: int
    guarantee_years: int = 0
    equity: bool = True
    kind: Literal["lateral_offer"] = "lateral_offer"


@dataclass(frozen=True, slots=True)
class Counter:
    actor_id: int
    approach_id: int
    comp_cents: int = 0
    points: float = 0.0
    guarantee_years: int = 0
    seat: bool = False
    kind: Literal["counter"] = "counter"


@dataclass(frozen=True, slots=True)
class RepayRevolver:
    actor_id: int
    amount_cents: int
    kind: Literal["repay_revolver"] = "repay_revolver"


@dataclass(frozen=True, slots=True)
class ElectionChoice:
    actor_id: int
    choice: Literal["stay", "hand_over"]
    successor_id: int | None = None
    kind: Literal["election_choice"] = "election_choice"


type PartnershipAction = (
    ProposeTerms
    | CapitalCall
    | ProposePartner
    | Deequitise
    | Lobby
    | PromisePoints
    | WithdrawVote
    | SetDraws
    | CompRound
    | SetSponsor
    | LateralSearch
    | Diligence
    | LateralOffer
    | Counter
    | RepayRevolver
    | ElectionChoice
)

PARTNERSHIP_ACTION_TYPES: dict[str, type[Any]] = {
    str(cls.__dataclass_fields__["kind"].default): cls
    for cls in (
        ProposeTerms,
        CapitalCall,
        ProposePartner,
        Deequitise,
        Lobby,
        PromisePoints,
        WithdrawVote,
        SetDraws,
        CompRound,
        SetSponsor,
        LateralSearch,
        Diligence,
        LateralOffer,
        Counter,
        RepayRevolver,
        ElectionChoice,
    )
}

ENERGY = {
    "propose_terms": "propose_terms",
    "capital_call": "capital_call",
    "propose_partner": "propose_partner",
    "deequitise": "deequity",
    "lobby": "lobby",
    "promise_points": "promise",
    "withdraw_vote": "withdraw_vote",
    "set_draws": "draws",
    "comp_round": "comp_round",
    "set_sponsor": "sponsor",
    "lateral_search": "lateral_search",
    "diligence": "diligence",
    "lateral_offer": "lateral_offer",
    "counter": "counter",
    "repay_revolver": "repay_revolver",
    "election_choice": "election_choice",
}
ANY_PARTNER = frozenset({"lobby", "promise_points", "set_sponsor", "election_choice"})


def _coerce_term(term: str, value: str | int | bool) -> str | int | bool:
    if term not in AGREEMENT_TERMS:
        raise PartnershipError(f"unknown agreement term {term!r}")
    kinds = {f.name: f.type for f in fields(Agreement)}
    kind = str(kinds[term])
    if term == "comp_system":
        if value not in COMP_SYSTEMS:
            raise PartnershipError(f"unknown comp system {value!r}")
        return str(value)
    if term == "voting":
        if value not in ("per_capita", "points"):
            raise PartnershipError(f"unknown voting rule {value!r}")
        return str(value)
    if kind == "bool":
        if not isinstance(value, bool):
            raise PartnershipError(f"{term} is yes or no")
        return value
    if isinstance(value, bool) or not isinstance(value, int):
        raise PartnershipError(f"{term} is a whole number")
    limits = {
        "track_years": (6, 12),
        "mp_term_years": (1, 10),
        "retirement_age": (55, 80),
        "notice_months": (0, 12),
        "retain_bp": (0, 5000),
    }  # tunable-exempt: the agreement's own bounds (data_models.AgreementTerms)
    lo, hi = limits.get(term, (1, 10_000))
    if not lo <= value <= hi:
        raise PartnershipError(f"{term} must be {lo}-{hi}")
    return value


def _open(
    state: GameState, firm_id: int, kind: str, subject: int | None, params: dict[str, Any]
) -> GameState:
    fp = firm_partnership(state, firm_id)
    for v in fp.votes:
        if (
            v.status == "open"
            and v.kind == kind
            and v.subject_id == subject
            and (kind != "terms" or v.param("term") == params.get("term"))
        ):
            raise PartnershipError("the same vote is already open")
    state, _ = open_vote(state, firm_id, kind, subject, params)
    return state


def _partner_of(state: GameState, firm_id: int, person_id: int) -> None:
    if firm_partnership(state, firm_id).partner(person_id) is None:
        raise UnknownPersonError(f"person {person_id} is not a partner of the firm")


def apply_partnership_action(
    state: GameState,
    action: PartnershipAction,
    rng: RngFactory,
    draws: Draws,
    balance: Balance,
    data: GameData,
    ledger_balances: LedgerBalances,
) -> Outcome:
    a = action
    firm = acting_firm(state, a.actor_id)
    if a.kind not in ANY_PARTNER:
        require_mp(state, firm, a.actor_id)
    state = spend_energy(state, a.actor_id, ENERGY[a.kind], balance)
    entries: tuple[LedgerEntry, ...] = ()
    fp = firm_partnership(state, firm)
    if isinstance(a, ProposeTerms):
        value = _coerce_term(a.term, a.value)
        if getattr(fp.agreement, a.term) == value:
            raise PartnershipError(f"{a.term} is already {value}")
        state = _open(state, firm, "terms", None, {"term": a.term, "value": value})
    elif isinstance(a, CapitalCall):
        if a.amount_cents <= 0:
            raise PartnershipError("a capital call needs an amount")
        state = _open(state, firm, "capital_call", None, {"amount_cents": a.amount_cents})
    elif isinstance(a, ProposePartner):
        if ym(state)[1] != DECEMBER:
            raise PartnershipError("candidates are proposed in December")
        if state.employer_of(a.person_id) != firm or not eligible(state, fp, a.person_id, balance):
            raise PartnershipError("that lawyer is not eligible for partnership this year")
        if a.track not in tracks_for(state, fp, a.person_id):
            raise PartnershipError(f"{a.track} is not open to that lawyer")
        sponsor = a.sponsor_id or fp.sponsor_of(a.person_id) or fp.mp_id
        if sponsor is not None and fp.partner(sponsor) is None:
            raise PartnershipError("the sponsor must be a partner")
        if fp.candidacy(a.person_id) is not None:
            raise PartnershipError("that lawyer is already proposed this year")
        vote_id = None
        if a.track in ("equity", "income"):
            state, vote = open_vote(
                state,
                firm,
                "admission",
                a.person_id,
                {"track": a.track, "sponsor_id": sponsor if sponsor is not None else 0},
            )
            vote_id = vote.id
        elif a.track == "counsel":
            from ptk.sim.hiring.pay import band_cents
            from ptk.sim.state import with_employment

            person = state.person(a.person_id)
            state = with_people(state, [replace(person, level="counsel")])
            e = state.employment_of(a.person_id)
            assert e is not None
            band = band_cents(data, balance, "counsel", state.firm(firm).home_city)
            state = with_employment(state, replace(e, salary_cents=max(e.salary_cents, band)))
        fp = firm_partnership(state, firm)
        fp = with_candidacy(
            fp, Candidacy(a.person_id, firm, a.track, sponsor, ym(state)[0], vote_id)
        )
        state = put(state, fp)
    elif isinstance(a, Deequitise):
        if ym(state)[1] != DECEMBER:
            raise PartnershipError("de-equitisation is decided in December")
        p = fp.partner(a.person_id)
        if p is None or not p.equity or a.person_id in (fp.mp_id, state.founder_of(firm)):
            raise PartnershipError("only another equity partner can be de-equitised")
        if a.mode == "income" and not fp.agreement.two_tier:
            raise PartnershipError("the agreement has no income partners (two-tier is off)")
        state = _open(state, firm, "deequity", a.person_id, {"mode": a.mode})
    elif isinstance(a, Lobby):
        _partner_of(state, firm, a.person_id)
        p = fp.partner(a.person_id)
        assert p is not None
        if p.lobbied_turn == state.turn:
            raise PartnershipError("you have already spoken to them this month")
        state = put(state, with_partner(fp, replace(p, lobbied_turn=state.turn)))
    elif isinstance(a, PromisePoints):
        _partner_of(state, firm, a.person_id)
        p = fp.partner(a.person_id)
        assert p is not None
        if not 0 < a.points <= balance.partnership.lockstep.step_points * 2:
            raise PartnershipError("a promise is up to two lockstep steps of points")
        state = put(
            state, with_partner(fp, replace(p, promised_points=p.promised_points + a.points))
        )
    elif isinstance(a, WithdrawVote):
        found = fp.vote(a.vote_id)
        if found is None or found.status != "open":
            raise UnknownVoteError(f"no open vote {a.vote_id}")
        vote = found
        state = put(
            state, with_vote(fp, replace(vote, status="withdrawn", resolved_turn=state.turn))
        )
        if vote.kind == "admission" and vote.subject_id is not None:
            fp = firm_partnership(state, firm)
            state = put(
                state,
                replace(
                    fp,
                    candidacies=tuple(c for c in fp.candidacies if c.person_id != vote.subject_id),
                ),
            )
    elif isinstance(a, SetDraws):
        if fp.draws_suspended == a.suspended:
            raise PartnershipError("draws are already " + ("suspended" if a.suspended else "paid"))
        state = put(state, replace(fp, draws_suspended=a.suspended))
    elif isinstance(a, CompRound):
        if ym(state)[1] != DECEMBER:
            raise PartnershipError("the comp round is held in December")
        p = fp.partner(a.person_id)
        if p is None or not p.equity:
            raise PartnershipError("the comp round sets equity partners' comp")
        m = balance.partnership.modified
        cap = balance.partnership.committee.adjust_max_bp
        if not m.gate_min_steps <= a.gate_steps <= m.gate_max_steps or abs(a.adjust_bp) > cap:
            raise PartnershipError("outside the comp round's limits")
        state = put(
            state, with_partner(fp, replace(p, gate_steps=a.gate_steps, adjust_bp=a.adjust_bp))
        )
    elif isinstance(a, SetSponsor):
        if fp.partner(a.sponsor_id) is None or state.employer_of(a.person_id) != firm:
            raise PartnershipError("a sponsor is a partner of the associate's own firm")
        state = put(state, with_sponsor(fp, a.person_id, a.sponsor_id))
    elif isinstance(a, LateralSearch):
        if a.practice not in data.practice_keys:
            raise PartnershipError(f"unknown practice {a.practice!r}")
        need = balance.partnership.lateral.search_cost_cents
        if account_balance(ledger_balances, firm, CASH) < need:
            raise PartnershipError("the recruiter's retainer needs cash")
        state, entries, logs = laterals.search(
            state, firm, a.actor_id, a.practice, rng, balance, data
        )
        return Outcome(state, entries, logs)
    elif isinstance(a, Diligence):
        state, entries = laterals.diligence(state, firm, a.person_id, draws(), balance)
    elif isinstance(a, LateralOffer):
        state = laterals.offer(state, firm, a.person_id, a.comp_cents, a.guarantee_years, a.equity)
    elif isinstance(a, Counter):
        from ptk.sim.partnership.flight import FLIGHT_HOOK

        res = FLIGHT_HOOK.counter(
            state,
            CounterOffer(a.approach_id, a.comp_cents, a.points, a.guarantee_years, a.seat),
            balance=balance,
            data=data,
        )
        state = res.state
    elif isinstance(a, RepayRevolver):
        drawn = -account_balance(ledger_balances, firm, REVOLVER)
        cash = account_balance(ledger_balances, firm, CASH)
        amount = min(a.amount_cents, drawn)
        if amount <= 0 or amount > cash:
            raise PartnershipError("repay up to the drawn balance, from cash in hand")
        entries = (
            LedgerEntry.transfer(
                turn=state.turn,
                firm_id=firm,
                memo="Revolver repaid early",
                debit=REVOLVER,
                credit=CASH,
                amount=amount,
            ),
        )
    elif isinstance(a, ElectionChoice):
        if fp.election_lost_turn is None or state.founder_of(firm) != a.actor_id:
            raise PartnershipError("there is no election result to answer")
        if a.choice == "hand_over":
            state = hand_over(state, firm, a.actor_id, a.successor_id, balance)
        fp = firm_partnership(state, firm)
        state = put(state, replace(fp, election_lost_turn=None))
    return Outcome(state, entries, ())


def hand_over(
    state: GameState, firm_id: int, founder_id: int, successor_id: int | None, balance: Balance
) -> GameState:
    """TST 45.5's 'play the heir': the player plays a partner of their choice from now on;
    the old founding partner stays as a senior partner."""
    fp = firm_partnership(state, firm_id)
    if successor_id is None or successor_id == founder_id:
        raise PartnershipError("name a partner to hand over to")
    p = fp.partner(successor_id)
    if p is None or not p.equity:
        raise PartnershipError("the successor must be an equity partner")
    old = state.person(founder_id)
    new = state.person(successor_id)
    state = with_people(state, [replace(old, is_founder=False), replace(new, is_founder=True)])
    ps_old = state.person_state(founder_id)
    ps_new = state.person_state(successor_id)
    state = with_person_states(
        state,
        [
            replace(
                ps_old,
                energy=None,
                morale=ps_old.morale if ps_old.morale is not None else balance.morale.start,
            ),
            replace(ps_new, energy=balance.energy.per_month, morale=None),
        ],
    )
    fp = firm_partnership(state, firm_id)
    fp = replace(fp, ousted_mp_id=None if fp.mp_id == successor_id else fp.ousted_mp_id)
    return put(state, fp)
