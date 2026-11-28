"""A deterministic stand-in for PT-M1b's hiring behind the delegate hook (ptk.sim.interfaces),
so PT-M2's delegates can be tested before hiring is built.

It follows the hook's contract: energy per person (spent at once, refused when short), a
search generates candidates from the request's `draws` (stream `delegate`), offers need an
interview (ADR-0016), campus offers only in August, and an offer is answered the next turn
(accepted when its draw was under ACCEPT). Its own world lives in the object, so a fresh
fake replays a game exactly.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace

import numpy as np
from simcore.kernel.calendar import turn_to_ym
from simcore.kernel.money import Cents

from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import SimError
from ptk.sim.interfaces import (
    CandidateView,
    CloseSearchRequest,
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
from ptk.sim.people.generator import generate_person
from ptk.sim.people.reveal import apply_knowledge_action, new_reveal_state
from ptk.sim.state import GameState
from ptk.sim.streams import RngFactory

COSTS = {
    "OpenSearchRequest": 10,
    "CloseSearchRequest": 0,
    "InterviewRequest": 6,
    "ReferenceCheckRequest": 4,
    "ScoutRequest": 20,
    "OfferRequest": 0,
}
PER_SEARCH = 4  # candidates a search finds
ACCEPT = 0.7  # an offer's draw under this is accepted next turn
CAMPUS_OFFER_MONTH = 8


class Refused(SimError):
    code = "fake_refused"


@dataclass
class _Offer:
    offer_id: int
    candidate_id: int
    firm_id: int
    plan_id: int | None
    unit_id: int | None
    turn: int
    accepted: bool


@dataclass
class FakeHiring:
    seed: int
    energy: dict[int, int] = field(default_factory=dict)
    searches_: dict[int, SearchView] = field(default_factory=dict)
    pool: dict[int, tuple[int, str, str]] = field(default_factory=dict)  # id -> (search, lvl, ch)
    interviewed: set[int] = field(default_factory=set)
    offers: dict[int, _Offer] = field(default_factory=dict)
    actors: list[tuple[int, int]] = field(default_factory=list)  # (turn, actor) accepted
    # (turn, actor, n, first value) for every request that drew: n = the actor's accepted
    # requests earlier this turn, so the draw must be stream `delegate` keyed (actor, n)
    draw_log: list[tuple[int, int, int, float]] = field(default_factory=list)
    next_id: int = 1

    # --- reads -----------------------------------------------------------------------------

    def energy_cost(self, request: HiringRequest, balance: Balance) -> int:
        return COSTS[type(request).__name__]

    def energy_left(self, state: GameState, person_id: int) -> int | None:
        return self.energy.get(person_id)

    def set_energy(self, state: GameState, person_id: int, energy: int) -> GameState:
        self.energy[person_id] = energy
        return state

    def searches(self, state: GameState, firm_id: int) -> tuple[SearchView, ...]:
        return tuple(s for _, s in sorted(self.searches_.items()) if s.firm_id == firm_id)

    def _pending(self, candidate_id: int) -> _Offer | None:
        for offer in self.offers.values():
            if offer.candidate_id == candidate_id:
                return offer
        return None

    def candidates(
        self, state: GameState, firm_id: int, role: str | None = None
    ) -> tuple[CandidateView, ...]:
        out = []
        august = turn_to_ym(state.turn, state.save_meta.start_ym)[1] == CAMPUS_OFFER_MONTH
        for cid, (sid, level, channel) in sorted(self.pool.items()):
            search = self.searches_.get(sid)
            person = state.person(cid)
            if search is None or search.firm_id != firm_id or (role and person.role != role):
                continue
            offer = self._pending(cid)
            if offer is not None and offer.turn < state.turn:
                continue  # answered: no longer open
            out.append(
                CandidateView(
                    candidate_id=cid,
                    search_id=sid,
                    role=person.role,
                    level=level,
                    channel=channel,  # type: ignore[arg-type]
                    ask_cents=10_000_000 + 1_000 * cid,
                    interviewed=cid in self.interviewed,
                    pending_offer_id=offer.offer_id if offer else None,
                    offer_allowed=channel != "campus" or august,
                    plan_id=search.plan_id,
                )
            )
        return tuple(out)

    def hires(self, state: GameState, firm_id: int, turn: int) -> tuple[HireView, ...]:
        return tuple(
            HireView(o.offer_id, o.candidate_id, firm_id, o.plan_id, o.unit_id, turn, turn)
            for _, o in sorted(self.offers.items())
            if o.firm_id == firm_id and o.turn == turn - 1 and o.accepted
        )

    # --- requests --------------------------------------------------------------------------

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
        cost = self.energy_cost(request, balance)
        left = self.energy.get(actor_id)
        if left is None or left < cost:
            raise Refused("not enough energy")
        firm = state.employer_of(actor_id)
        assert firm is not None
        n = sum(1 for t, a in self.actors if t == state.turn and a == actor_id)

        def stream() -> np.random.Generator:
            value = float(draws().random())
            self.draw_log.append((state.turn, actor_id, n, value))
            return draws()  # a fresh generator: the same draws from the start

        def draw() -> float:
            return float(stream().random())

        match request:
            case OpenSearchRequest():
                state = self._open(state, firm, request, stream, data, balance)
            case InterviewRequest():
                if (
                    request.candidate_id not in self.pool
                    or request.candidate_id in self.interviewed
                ):
                    raise Refused("no such candidate to interview")
                self.interviewed.add(request.candidate_id)
                state = self._narrow(
                    state, firm, request.candidate_id, "interview", actor_id, balance, data
                )
                draw()
            case ScoutRequest():
                ids = [c for c, (s, _, _) in self.pool.items() if s == request.search_id]
                if not ids:
                    raise Refused("nothing to scout")
                for cid in sorted(ids):
                    state = self._narrow(
                        state, firm, cid, "scouting_month", actor_id, balance, data
                    )
                draw()
            case OfferRequest():
                cand = next(
                    (
                        c
                        for c in self.candidates(state, firm)
                        if c.candidate_id == request.candidate_id
                    ),
                    None,
                )
                if cand is None or not cand.interviewed or cand.pending_offer_id is not None:
                    raise Refused("an offer needs an interviewed open candidate")
                if not cand.offer_allowed:
                    raise Refused("campus offers wait for August")
                oid = self._take_id()
                self.offers[oid] = _Offer(
                    oid,
                    request.candidate_id,
                    firm,
                    request.plan_id,
                    request.unit_id,
                    state.turn,
                    draw() < ACCEPT,
                )
            case CloseSearchRequest():
                if request.search_id not in self.searches_:
                    raise Refused("no such search")
                del self.searches_[request.search_id]
                self.pool = {c: v for c, v in self.pool.items() if v[0] != request.search_id}
            case ReferenceCheckRequest():
                raise Refused("not used by delegates")
        self.energy[actor_id] = left - cost
        self.actors.append((state.turn, actor_id))
        return HookResult(state)

    def _take_id(self) -> int:
        self.next_id += 1
        return self.next_id - 1

    def _open(
        self,
        state: GameState,
        firm: int,
        request: OpenSearchRequest,
        draws: Callable[[], np.random.Generator],
        data: GameData,
        balance: Balance,
    ) -> GameState:
        sid = self._take_id()
        self.searches_[sid] = SearchView(
            sid, firm, request.role, request.channel, state.turn, request.plan_id
        )
        gen = draws()
        level = request.level or ("associate_1" if request.channel == "campus" else "associate_3")
        rng = RngFactory(self.seed)
        people, reveals = list(state.people), list(state.reveals)
        for _ in range(PER_SEARCH):
            pid = max(p.id for p in people) + 1
            person = generate_person(
                gen,
                data,
                balance,
                state.turn,
                data.role(request.role),
                level,
                person_id=pid,
                city="new_york",
                jurisdiction="us_ny",
            )
            people.append(person)
            reveals.append(
                new_reveal_state(
                    observer_firm_id=firm,
                    person=person,
                    turn=state.turn,
                    rng=rng,
                    data=data,
                    balance=balance,
                )
            )
            self.pool[pid] = (sid, level, request.channel)
        reveals.sort(key=lambda r: (r.observer_firm_id, r.person_id))
        return replace(state, people=tuple(people), reveals=tuple(reveals))

    def _narrow(
        self,
        state: GameState,
        firm: int,
        person_id: int,
        action: str,
        actor_id: int,
        balance: Balance,
        data: GameData,
    ) -> GameState:
        scout = state.person(actor_id).skills["judgment_of_talent"]
        keys = frozenset(data.skill_keys)
        reveals = tuple(
            apply_knowledge_action(rv, action, scout, balance, turn=state.turn, skill_keys=keys)
            if rv.observer_firm_id == firm and rv.person_id == person_id
            else rv
            for rv in state.reveals
        )
        return replace(state, reveals=reveals)
