"""Hiring actions (ADR-0014): they take effect at once, in their own transaction.

Ported from backend/tst/sim/actions/hiring.py @ 02fba2aa (Tech Startup Tycoon); changed:
firms; Partner Track's channels (campus registration in January-April, campus offers only
in August, recruiter, job post, referral) with tier filters and a target level; no equity,
option pool, poach, exec, interest or city searches; scouting a
search's candidates (TST 11.12) and the firm's pay policy are hiring actions here. PT-M10 ports
TST's `Fire` as `LayOff`: the person works a notice month (ended by phase 1, as a resignation
is) and takes `pay.severance_months` of salary at once; everyone remaining loses
`morale.layoff_penalty`. Partners leave through the partnership's own actions, never this one.

Every action names an `actor_id`: the player's founding partner, or a PT-M2 delegate through
the hook in `ptk.sim.interfaces`. The actor's employer is the acting firm. Energy is spent at
once by whoever tracks it; anyone else spends none.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Literal

import numpy as np

from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import (
    CampusSeasonError,
    InsufficientCashError,
    InsufficientEnergyError,
    InterviewRequiredError,
    InvalidActionError,
    OfferExistsError,
    UnknownCandidateError,
    UnknownOfferError,
    UnknownPersonError,
    UnknownRoleError,
    UnknownSearchError,
)
from ptk.sim.hiring.formulas import ROLL_RANGE, energy_cost, monthly_salary_cents, roll_succeeds
from ptk.sim.hiring.models import CHANNELS, Candidate, Offer, PayPolicy, PolicyMode, Search
from ptk.sim.hiring.rules import campus_offers_open, campus_registration_open
from ptk.sim.interfaces import HiringChannel
from ptk.sim.ledger import CASH, LedgerBalances, LedgerEntry, LedgerLine, account_balance
from ptk.sim.log import LogItem, inbox_item
from ptk.sim.people.models import Person
from ptk.sim.people.reveal import apply_knowledge_action
from ptk.sim.scale import clamp_morale
from ptk.sim.state import (
    GameState,
    with_candidates,
    with_employment,
    with_firm,
    with_offer,
    with_person_states,
    with_reveals,
    with_search,
)

LATERAL_PARTNER_LEVELS = frozenset({"income_partner", "equity_partner"})  # PT-M4
SCOUTING = "scouting_month"

# --- Action types ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class OpenSearch:
    actor_id: int
    role: str
    channel: HiringChannel
    level: str | None = None
    school_tiers: tuple[str, ...] = ()
    plan_id: int | None = None
    city: str | None = None  # PT-M11: hire into the firm's office in this city (None: home)
    kind: Literal["open_search"] = "open_search"


@dataclass(frozen=True, slots=True)
class CloseSearch:
    actor_id: int
    search_id: int
    kind: Literal["close_search"] = "close_search"


@dataclass(frozen=True, slots=True)
class Interview:
    actor_id: int
    candidate_id: int
    kind: Literal["interview"] = "interview"


@dataclass(frozen=True, slots=True)
class ReferenceCheck:
    actor_id: int
    candidate_id: int
    kind: Literal["reference_check"] = "reference_check"


@dataclass(frozen=True, slots=True)
class Scout:
    actor_id: int
    search_id: int
    kind: Literal["scout"] = "scout"


@dataclass(frozen=True, slots=True)
class MakeOffer:
    actor_id: int
    candidate_id: int
    salary_cents: int
    plan_id: int | None = None
    unit_id: int | None = None
    kind: Literal["make_offer"] = "make_offer"


@dataclass(frozen=True, slots=True)
class WithdrawOffer:
    actor_id: int
    offer_id: int
    kind: Literal["withdraw_offer"] = "withdraw_offer"


@dataclass(frozen=True, slots=True)
class SetPayPolicy:
    actor_id: int
    mode: PolicyMode
    pct_bp: int = 10_000  # tunable-exempt: 100% of the market
    kind: Literal["set_pay_policy"] = "set_pay_policy"


@dataclass(frozen=True, slots=True)
class LayOff:
    """PT-M10: let an associate, counsel or member of staff go (TST's fire)."""

    actor_id: int
    person_id: int
    kind: Literal["lay_off"] = "lay_off"


type HiringAction = (
    OpenSearch
    | CloseSearch
    | Interview
    | ReferenceCheck
    | Scout
    | MakeOffer
    | WithdrawOffer
    | SetPayPolicy
    | LayOff
)
# The generator for randomness inside one action, created only if the action draws: stream
# `actions` keyed by seq for the player, `delegate` keyed (person, n) for delegates (ADR-0015).
type Draws = Callable[[], np.random.Generator]


@dataclass(frozen=True, slots=True)
class Outcome:
    state: GameState
    entries: tuple[LedgerEntry, ...] = ()
    log: tuple[LogItem, ...] = ()


# --- Shared steps ---------------------------------------------------------------------------


def acting_firm(state: GameState, actor_id: int) -> int:
    employment = state.employment_of(actor_id)
    if employment is None or employment.status != "active":
        raise UnknownPersonError(f"person {actor_id} is not on staff and cannot act")
    return employment.firm_id


def spend_energy(state: GameState, actor_id: int, action: str, balance: Balance) -> GameState:
    """Spend energy.cost[action] from the actor's energy, if they track it."""
    cost = energy_cost(action, balance)
    ps = state.person_state(actor_id)
    if ps.energy is None:
        return state
    if ps.energy < cost:
        raise InsufficientEnergyError(f"{action} needs {cost} energy; {ps.energy} left this month")
    return with_person_states(state, [replace(ps, energy=ps.energy - cost)])


def open_candidate(state: GameState, firm_id: int, candidate_id: int) -> Candidate:
    candidate = state.candidate(candidate_id)
    if candidate is None or candidate.firm_id != firm_id or candidate.status != "open":
        raise UnknownCandidateError(f"no open candidate {candidate_id}")
    return candidate


def judgment(person: Person) -> float:
    return person.skills["judgment_of_talent"]


def _name(person: Person) -> str:
    return f"{person.first_name} {person.last_name}"


# --- Actions --------------------------------------------------------------------------------


def open_search(
    state: GameState,
    action: OpenSearch,
    balance: Balance,
    data: GameData,
    balances: LedgerBalances,
) -> Outcome:
    firm = acting_firm(state, action.actor_id)
    if action.role not in {r.key for r in data.roles}:
        raise UnknownRoleError(f"unknown role {action.role!r}")
    role = data.role(action.role)
    if action.channel not in CHANNELS:
        raise InvalidActionError(f"unknown channel {action.channel!r}")
    tiers = {t.key for t in data.school_tiers if t.available_in == "v1"}
    if bad := sorted(set(action.school_tiers) - tiers):
        raise InvalidActionError(f"unknown or unavailable school tiers {bad}")
    if action.school_tiers and role.kind != "lawyer":
        raise InvalidActionError("only a search for lawyers can filter by law school tier")
    if action.channel == "campus":
        if role.kind != "lawyer":
            raise InvalidActionError("campus searches are for lawyers")
        if action.level is not None:
            raise InvalidActionError("a campus search hires first-years only")
        if not campus_registration_open(state, balance):
            months = balance.campus.register_months
            raise CampusSeasonError(
                f"campus registration is open in months {int(months.lo)}-{int(months.hi)}"
            )
        if any(
            s.firm_id == firm
            and s.channel == "campus"
            and s.role == role.key
            and s.status == "open"
            for s in state.searches
        ):
            raise InvalidActionError(f"a campus search for {role.label} is already open")
    if action.level is not None:
        level = balance.people.levels.get(action.level)
        if level is None or level.kind != role.kind:
            raise InvalidActionError(f"a {role.label} search cannot target {action.level!r}")
        if action.level in LATERAL_PARTNER_LEVELS:
            raise InvalidActionError("lateral partners arrive with PT-M4")
    if action.channel == "job_post":
        fee = balance.hiring.job_post_cost_cents
        if account_balance(balances, firm, CASH) < fee:
            raise InsufficientCashError(
                f"a job post needs at least its first month's fee in cash ({fee} cents)"
            )
    state = spend_energy(state, action.actor_id, action.channel, balance)
    search = Search(
        id=state.next_id("search"),
        firm_id=firm,
        role=role.key,
        channel=action.channel,
        actor_id=action.actor_id,
        opened_turn=state.turn,
        level=action.level,
        school_tiers=tuple(sorted(set(action.school_tiers))),
        plan_id=action.plan_id,
    )
    state = with_search(state, search)
    if action.city is not None and action.city != state.firm(firm).home_city:
        from ptk.sim.geo.cities import office_in  # PT-M11: a local hiring pool

        if action.channel == "campus":
            raise InvalidActionError("campus searches hire into the home office")
        if office_in(state, firm, action.city) is None:
            raise InvalidActionError(f"the firm has no office in {action.city!r}")
        geo = state.geo
        state = replace(
            state,
            geo=replace(geo, search_cities=(*geo.search_cities, (search.id, action.city))),
        )
    return Outcome(state)


def close_search(state: GameState, action: CloseSearch, balance: Balance) -> Outcome:
    firm = acting_firm(state, action.actor_id)
    search = state.search(action.search_id)
    if search is None or search.firm_id != firm or search.status != "open":
        raise UnknownSearchError(f"no open search {action.search_id}")
    state = spend_energy(state, action.actor_id, "close_search", balance)
    return Outcome(with_search(state, replace(search, status="closed", closed_turn=state.turn)))


def _check_tags(
    state: GameState, firm: int, person: Person, draws: Draws, balance: Balance
) -> GameState:
    """One roll per still-hidden tag, in the person's tag order, at reveal_bp_on_check."""
    reveal = state.reveal(firm, person.id)
    if reveal is None:
        return state
    known = {tag for tag, _ in reveal.revealed_tags}
    hidden = [t for t in person.tags if t not in known]
    if not hidden:
        return state
    gen = draws()
    found = [
        t
        for t in hidden
        if roll_succeeds(int(gen.integers(0, ROLL_RANGE)), balance.tags.reveal_bp_on_check)
    ]
    if not found:
        return state
    revealed = reveal.revealed_tags + tuple((t, state.turn) for t in found)
    return with_reveals(state, [replace(reveal, revealed_tags=revealed)])


def check_candidate(
    state: GameState,
    actor_id: int,
    candidate_id: int,
    action: Literal["interview", "reference_check"],
    draws: Draws,
    balance: Balance,
    data: GameData,
) -> Outcome:
    firm = acting_firm(state, actor_id)
    candidate = open_candidate(state, firm, candidate_id)
    state = spend_energy(state, actor_id, action, balance)
    person = state.person(candidate.person_id)
    reveal = state.reveal(firm, person.id)
    if reveal is None:
        raise UnknownCandidateError(f"no knowledge record for candidate {candidate_id}")
    before = {t for t, _ in reveal.revealed_tags}
    reveal = apply_knowledge_action(
        reveal,
        action,
        judgment(state.person(actor_id)),
        balance,
        turn=state.turn,
        skill_keys=frozenset(data.skill_keys),
    )
    state = with_reveals(state, [reveal])
    if action == "interview" and candidate.interviewed_turn is None:
        state = with_candidates(state, [replace(candidate, interviewed_turn=state.turn)])
    state = _check_tags(state, firm, person, draws, balance)
    after = state.reveal(firm, person.id)
    assert after is not None
    log = tuple(
        inbox_item(
            state.turn,
            firm,
            "tag_revealed",
            link_kind="candidate",
            link_id=person.id,
            name=_name(person),
            reveal_text=next(t.reveal_text for t in data.tags if t.key == tag),
        )
        for tag, _ in after.revealed_tags
        if tag not in before
    )
    return Outcome(state, log=log)


def scout(state: GameState, action: Scout, balance: Balance, data: GameData) -> Outcome:
    """A month of scouting on every open candidate of one search (TST 11.12)."""
    firm = acting_firm(state, action.actor_id)
    search = state.search(action.search_id)
    if search is None or search.firm_id != firm:
        raise UnknownSearchError(f"no search {action.search_id}")
    pool = [c for c in state.candidates if c.search_id == search.id and c.status == "open"]
    if not pool:
        raise InvalidActionError(f"search {search.id} has no open candidates to scout")
    state = spend_energy(state, action.actor_id, "scout", balance)
    scout_judgment = judgment(state.person(action.actor_id))
    skill_keys = frozenset(data.skill_keys)
    updated = []
    for candidate in pool:
        reveal = state.reveal(firm, candidate.person_id)
        if reveal is not None:
            updated.append(
                apply_knowledge_action(
                    reveal,
                    SCOUTING,
                    scout_judgment,
                    balance,
                    turn=state.turn,
                    skill_keys=skill_keys,
                )
            )
    return Outcome(with_reveals(state, updated))


def make_offer(state: GameState, action: MakeOffer, balance: Balance) -> Outcome:
    firm = acting_firm(state, action.actor_id)
    candidate = open_candidate(state, firm, action.candidate_id)
    if candidate.interviewed_turn is None:
        raise InterviewRequiredError(
            f"interview candidate {candidate.person_id} before making an offer (ADR-0016)"
        )
    if candidate.channel == "campus" and not campus_offers_open(state, balance):
        raise CampusSeasonError(
            f"campus offers go out in month {balance.campus.offer_month} (spec 5.7)"
        )
    if state.pending_offer_for(candidate.person_id) is not None:
        raise OfferExistsError(
            f"candidate {candidate.person_id} already has a pending offer; withdraw it first"
        )
    if action.salary_cents <= 0:
        raise InvalidActionError("salary must be positive")
    state = spend_energy(state, action.actor_id, "offer", balance)
    offer = Offer(
        id=state.next_id("offer"),
        firm_id=firm,
        candidate_id=candidate.person_id,
        actor_id=action.actor_id,
        salary_cents=action.salary_cents,
        made_turn=state.turn,
        start_turn=state.turn + 1,  # campus: set to next September when it resolves
        plan_id=action.plan_id,
        unit_id=action.unit_id,
    )
    return Outcome(with_offer(state, offer))


def withdraw_offer(state: GameState, action: WithdrawOffer, balance: Balance) -> Outcome:
    """Removes the pending offer; the candidate stays open (TST 7)."""
    firm = acting_firm(state, action.actor_id)
    offer = state.offer(action.offer_id)
    if offer is None or offer.firm_id != firm or offer.status != "pending":
        raise UnknownOfferError(f"no pending offer {action.offer_id}")
    state = spend_energy(state, action.actor_id, "withdraw_offer", balance)
    return Outcome(with_offer(state, replace(offer, status="withdrawn", resolved_turn=state.turn)))


def set_pay_policy(state: GameState, action: SetPayPolicy, balance: Balance) -> Outcome:
    """Match, lag or lead the market scale (spec 5.4). Lag is below 100%, lead above, within
    pay.policy; scale salaries follow from the next scale update and never fall."""
    firm = acting_firm(state, action.actor_id)
    limits = balance.pay.policy
    full = 10_000  # tunable-exempt: 100% in bp
    if action.mode == "lag" and not limits.min_bp <= action.pct_bp < full:
        raise InvalidActionError(f"lag pays {limits.min_bp}-{full - 1} bp of the market")
    if action.mode == "lead" and not full < action.pct_bp <= limits.max_bp:
        raise InvalidActionError(f"lead pays {full + 1}-{limits.max_bp} bp of the market")
    if action.mode not in ("match", "lag", "lead"):
        raise InvalidActionError(f"unknown pay policy {action.mode!r}")
    state = spend_energy(state, action.actor_id, "pay_policy", balance)
    policy = PayPolicy.of(action.mode, action.pct_bp)
    return Outcome(with_firm(state, replace(state.firm(firm), pay_policy=policy)))


PARTNER_LEVELS = frozenset({"income_partner", "equity_partner"})


def lay_off(state: GameState, action: LayOff, balance: Balance) -> Outcome:
    """PT-M10 (TST's fire): a notice month, then gone; severance paid now from cash."""
    from ptk.sim.hiring.phases import salary_account  # phases reads this module's types

    firm = acting_firm(state, action.actor_id)
    employment = state.employment_of(action.person_id)
    if employment is None or employment.firm_id != firm or employment.status != "active":
        raise UnknownPersonError(f"person {action.person_id} is not on the firm's active staff")
    person = state.person(action.person_id)
    if person.is_founder or person.id == action.actor_id:
        raise InvalidActionError("a founding partner or the actor cannot be laid off")
    if person.level in PARTNER_LEVELS:
        raise InvalidActionError("partners leave through the partnership (de-equitisation)")
    state = spend_energy(state, action.actor_id, "lay_off", balance)
    state = with_employment(
        state, replace(employment, status="notice", end_turn=state.turn + 1, end_reason="fired")
    )
    severance = monthly_salary_cents(employment.salary_cents) * balance.pay.severance_months
    account = salary_account(person.level, balance)
    entries: tuple[LedgerEntry, ...] = ()
    if severance > 0 and account is not None:
        entries = (
            LedgerEntry(
                turn=state.turn,
                firm_id=firm,
                memo=f"Severance: {_name(person)}",
                lines=(LedgerLine(account, severance), LedgerLine(CASH, -severance)),
            ),
        )
    penalty = balance.morale.layoff_penalty
    moved = []
    for pid in state.staff_ids(firm):
        ps = state.person_state(pid)
        if pid != person.id and ps.morale is not None:
            moved.append(replace(ps, morale=clamp_morale(ps.morale + penalty)))
    state = with_person_states(state, moved)
    log = (
        inbox_item(
            state.turn,
            firm,
            "laid_off",
            link_kind="person",
            link_id=person.id,
            name=_name(person),
            severance_cents=severance,
        ),
    )
    return Outcome(state, entries, log)


def apply_hiring(
    state: GameState,
    action: HiringAction,
    draws: Draws,
    balance: Balance,
    data: GameData,
    balances: LedgerBalances,
) -> Outcome:
    match action:
        case OpenSearch():
            return open_search(state, action, balance, data, balances)
        case CloseSearch():
            return close_search(state, action, balance)
        case Interview():
            return check_candidate(
                state, action.actor_id, action.candidate_id, "interview", draws, balance, data
            )
        case ReferenceCheck():
            return check_candidate(
                state, action.actor_id, action.candidate_id, "reference_check", draws, balance, data
            )
        case Scout():
            return scout(state, action, balance, data)
        case MakeOffer():
            return make_offer(state, action, balance)
        case WithdrawOffer():
            return withdraw_offer(state, action, balance)
        case SetPayPolicy():
            return set_pay_policy(state, action, balance)
        case LayOff():
            return lay_off(state, action, balance)
