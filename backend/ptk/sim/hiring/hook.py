"""PT-M1b's implementation of the delegate hiring hook (`ptk.sim.interfaces`).

Each request becomes the same hiring action the player takes, with the delegate as actor,
so energy, the interview rule (ADR-0016), campus months and the offer pitch all apply
(ADR-0015). Views carry what the firm can see only.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import replace

import numpy as np
from simcore.kernel.money import Cents

from ptk.sim.data_models import Balance, GameData
from ptk.sim.hiring.actions import (
    CloseSearch,
    HiringAction,
    Interview,
    MakeOffer,
    OpenSearch,
    ReferenceCheck,
    Scout,
    apply_hiring,
)
from ptk.sim.hiring.formulas import energy_cost
from ptk.sim.interfaces import (
    CandidateView,
    CloseSearchRequest,
    DelegateHiringHook,
    HireView,
    HiringRequest,
    HookResult,
    InterviewRequest,
    OfferRequest,
    OpenSearchRequest,
    ReferenceCheckRequest,
    ScoutRequest,
    SearchView,
)
from ptk.sim.ledger import AccountCode
from ptk.sim.state import GameState, with_person_states


def _energy_key(request: HiringRequest) -> str:
    match request:
        case OpenSearchRequest():
            return request.channel
        case CloseSearchRequest():
            return "close_search"
        case InterviewRequest():
            return "interview"
        case ReferenceCheckRequest():
            return "reference_check"
        case ScoutRequest():
            return "scout"
        case OfferRequest():
            return "offer"


def to_action(request: HiringRequest, actor_id: int) -> HiringAction:
    match request:
        case OpenSearchRequest():
            return OpenSearch(
                actor_id=actor_id,
                role=request.role,
                channel=request.channel,
                level=request.level,
                school_tiers=request.school_tiers,
                plan_id=request.plan_id,
            )
        case CloseSearchRequest():
            return CloseSearch(actor_id=actor_id, search_id=request.search_id)
        case InterviewRequest():
            return Interview(actor_id=actor_id, candidate_id=request.candidate_id)
        case ReferenceCheckRequest():
            return ReferenceCheck(actor_id=actor_id, candidate_id=request.candidate_id)
        case ScoutRequest():
            return Scout(actor_id=actor_id, search_id=request.search_id)
        case OfferRequest():
            return MakeOffer(
                actor_id=actor_id,
                candidate_id=request.candidate_id,
                salary_cents=request.salary_cents,
                plan_id=request.plan_id,
                unit_id=request.unit_id,
            )


class HiringHook:
    def energy_cost(self, request: HiringRequest, balance: Balance) -> int:
        return energy_cost(_energy_key(request), balance)

    def energy_left(self, state: GameState, person_id: int) -> int | None:
        return state.person_state(person_id).energy

    def set_energy(self, state: GameState, person_id: int, energy: int) -> GameState:
        return with_person_states(state, [replace(state.person_state(person_id), energy=energy)])

    def searches(self, state: GameState, firm_id: int) -> tuple[SearchView, ...]:
        return tuple(
            SearchView(
                search_id=s.id,
                firm_id=s.firm_id,
                role=s.role,
                channel=s.channel,
                opened_turn=s.opened_turn,
                plan_id=s.plan_id,
            )
            for s in state.searches
            if s.firm_id == firm_id and s.status == "open"
        )

    def candidates(
        self, state: GameState, firm_id: int, role: str | None = None
    ) -> tuple[CandidateView, ...]:
        out = []
        for c in state.candidates:
            if c.firm_id != firm_id or c.status != "open":
                continue
            person = state.person(c.person_id)
            if role is not None and person.role != role:
                continue
            search = state.search(c.search_id)
            pending = state.pending_offer_for(c.person_id)
            out.append(
                CandidateView(
                    candidate_id=c.person_id,
                    search_id=c.search_id,
                    role=person.role,
                    level=person.level,
                    channel=c.channel,
                    ask_cents=c.ask_cents,
                    interviewed=c.interviewed_turn is not None,
                    pending_offer_id=pending.id if pending is not None else None,
                    # a campus candidate's last month is the offer month (campus_pools)
                    offer_allowed=c.channel != "campus" or state.turn == c.expires_turn,
                    plan_id=search.plan_id if search is not None else None,
                )
            )
        return tuple(out)

    def apply(
        self,
        state: GameState,
        request: HiringRequest,
        *,
        actor_id: int,
        draws: Callable[[], np.random.Generator],
        balance: Balance,
        data: GameData,
        balances: Mapping[tuple[int, AccountCode], Cents],
    ) -> HookResult:
        out = apply_hiring(state, to_action(request, actor_id), draws, balance, data, balances)
        return HookResult(state=out.state, entries=out.entries, log=out.log)

    def hires(self, state: GameState, firm_id: int, turn: int) -> tuple[HireView, ...]:
        return tuple(
            HireView(
                offer_id=o.id,
                person_id=o.candidate_id,
                firm_id=o.firm_id,
                plan_id=o.plan_id,
                unit_id=o.unit_id,
                accepted_turn=turn,
                start_turn=o.start_turn,
            )
            for o in state.offers
            if o.firm_id == firm_id and o.status == "accepted" and o.resolved_turn == turn
        )


HIRING_HOOK: DelegateHiringHook = HiringHook()
