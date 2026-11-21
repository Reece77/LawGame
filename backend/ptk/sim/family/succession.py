"""Succession (spec 2.5; TST formulas.md 45.5; ADR PT-0007 3): the player names a successor
among the equity partners, the partnership elects them, and the player plays them as MP.

Ported from backend/tst/sim/family/succession.py @ 121d318a (Tech Startup Tycoon); changed:
any equity partner may succeed (a child who made partner included), not only heirs or a
professional CEO; the partnership elects the successor through PT-M4's vote functions
(`ptk.sim.interfaces`), and a weak candidate can lose to a rival nominee (PT-M4's most
ambitious partner); play passes through PT-M4's `hand_over`; the old player becomes senior
partner (TST 45.5's adviser, `ptk.sim.family.adviser`) until they reach the agreement's
retirement age, then a retired partner (an annuity if the agreement grants one); estate tax at
a health succession (TST 45.6).

Triggers: by choice (an action); at mandatory retirement (the agreement's age: a successor by
the end of `grace_months`, else the plan's or the strongest candidate is named); after a lost
MP election (PT-M4's hand-over, no vote: the partnership has already chosen its MP); on
health grounds (each January from `step_back_from`, chance `step_back_rate x (age - from +
1)`, stream `family` keyed (head_id, 2, 0); never for a person flagged real). Ironman: losing
the succession vote when the player must go ends the game, as losing the MP election does.

The vote (stream `vote` through PT-M4's `vote_noise`, keyed (vote_id, person_id)): each
equity partner but the MP, the successor and the rival backs the successor when
`endorse_weight x u_PT-M4 + quality_weight x (rating - rival's rating) / quality_scale +
noise > 0`, where u_PT-M4 is PT-M4's election utility (their confidence in the MP, lobbying)
and ratings are as the firm sees them. It passes with the agreement's election threshold.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Final

from ptk.sim import interfaces as ix
from ptk.sim.calendar import MONTHS_PER_YEAR, turn_to_ym
from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import SuccessionError
from ptk.sim.family.models import CHILD
from ptk.sim.family.people import family_stream
from ptk.sim.founder import personal
from ptk.sim.founder.models import (
    PersonalEntry,
    Succession,
    with_book,
    with_life,
)
from ptk.sim.founder.persona import heir_life, new_life
from ptk.sim.ledger import AccountCode, LedgerEntry
from ptk.sim.log import LogItem, inbox_item
from ptk.sim.money import BP_DENOMINATOR, Cents
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState

HEALTH_KEY: Final = 2  # stream family's (head_id, 2, 0): the health step-back draw
JANUARY: Final = 1  # tunable-exempt: calendar month
TRIGGERS: Final = ("choice", "retirement", "election", "health")
FORCED: Final = frozenset({"retirement", "health"})


@dataclass(frozen=True, slots=True)
class Prediction:
    """The player's predicted vote: the weight for the successor as a range, the total and
    what passing needs; the rival nominee if any. Never the utilities."""

    yes_lo: float
    yes_hi: float
    total: float
    needed: float
    rival_id: int | None


@dataclass(frozen=True, slots=True)
class Month:
    state: GameState
    entries: tuple[LedgerEntry, ...] = ()
    personal: tuple[PersonalEntry, ...] = ()
    log: tuple[LogItem, ...] = ()


def player_id(state: GameState) -> int | None:
    return state.founder_of(state.player.id)


def candidates(state: GameState) -> tuple[int, ...]:
    """Equity partners who may succeed (the player aside), by person id."""
    you = player_id(state)
    return tuple(p for p in ix.equity_partner_ids(state, state.player.id) if p != you)


def _rival(state: GameState, successor_id: int, balance: Balance) -> int | None:
    you = player_id(state)
    exclude = frozenset(x for x in (you, successor_id) if x is not None)
    return ix.rival_nominee(state, state.player.id, balance, exclude)


def _quality(
    state: GameState, successor_id: int, rival_id: int | None, balance: Balance, data: GameData
) -> float:
    sb = balance.succession
    if rival_id is None:
        return 0.0
    firm = state.player.id
    gap = ix.candidate_rating(state, firm, successor_id, data) - ix.candidate_rating(
        state, firm, rival_id, data
    )
    return sb.quality_weight * gap / sb.quality_scale


def _utility(
    state: GameState,
    vote_id: int,
    pid: int,
    successor_id: int,
    rival_id: int | None,
    balance: Balance,
    data: GameData,
) -> float:
    base = ix.election_utility(state, state.player.id, vote_id, pid, balance, data)
    return balance.succession.endorse_weight * base + _quality(
        state, successor_id, rival_id, balance, data
    )


def predict(state: GameState, successor_id: int, balance: Balance, data: GameData) -> Prediction:
    """Partners within PT-M4's band of indifference count either way (a range)."""
    firm = state.player.id
    you = player_id(state)
    rival = _rival(state, successor_id, balance)
    k = ix.predict_k(balance)
    lo = hi = total = 0.0
    # utilities without a stored vote: PT-M4's election utility is confidence-based, read
    # here through a provisional vote that is never written back
    probe, vid = ix.open_partnership_vote(state, firm, "election", successor_id, {"succession": 1})
    for pid in ix.equity_partner_ids(probe, firm):
        w = ix.vote_weight(probe, firm, pid)
        total += w
        if pid in (you, successor_id):
            lo += w
            hi += w
            continue
        if pid == rival:
            continue
        u = _utility(probe, vid, pid, successor_id, rival, balance, data)
        if u > k:
            lo += w
            hi += w
        elif u > -k:
            hi += w
    threshold = ix.vote_threshold_bp(probe, firm, vid)
    return Prediction(lo, hi, total, total * threshold / BP_DENOMINATOR, rival)


def name_successor(
    state: GameState, successor_id: int, trigger: str, balance: Balance
) -> GameState:
    """Name a successor: the election opens (counted this turn, phase 10). After a lost MP
    election the hand-over needs no vote (the partnership chose its MP already)."""
    you = player_id(state)
    if you is None:
        raise SuccessionError("there is no player to succeed")
    if trigger not in TRIGGERS:
        raise SuccessionError(f"unknown trigger {trigger!r}")
    if successor_id not in candidates(state):
        raise SuccessionError("the successor must be another equity partner of the firm")
    fl = state.founder_life
    last = fl.last_succession
    if last is not None and last.result == "open":
        raise SuccessionError("a succession vote is already open")
    if (
        trigger == "choice"
        and last is not None
        and last.result == "lost"
        and last.founder_id == you
        and state.turn - last.turn < balance.succession.retry_months
    ):
        raise SuccessionError("the partnership voted this down recently; try again later")
    firm = state.player.id
    ousted = ix.ousted_founder(state, firm) or ix.managing_partner(state, firm) != you
    if ousted:
        trigger = "election"
        rec = Succession(state.turn, trigger, you, successor_id)
        return replace(state, founder_life=replace(fl, successions=(*fl.successions, rec)))
    rival = _rival(state, successor_id, balance)
    state, vid = ix.open_partnership_vote(
        state, firm, "election", successor_id, {"succession": 1, "rival_id": rival or 0}
    )
    rec = Succession(state.turn, trigger, you, successor_id, vote_id=vid, rival_id=rival)
    fl = state.founder_life
    return replace(state, founder_life=replace(fl, successions=(*fl.successions, rec)))


def count(
    state: GameState,
    rng: RngFactory,
    balance: Balance,
    data: GameData,
    balances: Mapping[tuple[int, AccountCode], Cents],
) -> Month:
    """Phase 10: an open succession is decided (an election counted, or a hand-over)."""
    fl = state.founder_life
    rec = fl.last_succession
    if rec is None or rec.result != "open":
        return Month(state)
    firm = state.player.id
    if player_id(state) != rec.founder_id or rec.successor_id not in candidates(state):
        # the successor left, or play already passed: the vote lapses
        if rec.vote_id is not None:
            state = ix.withdraw_vote(state, firm, rec.vote_id)
        return Month(_set_result(state, "lapsed"))
    if rec.vote_id is None:  # after a lost MP election: no vote
        return hand_over(state, rec.successor_id, rec.trigger, rng, balance, data, balances)
    vid = rec.vote_id
    yes = no = 0.0
    ballots: list[tuple[int, bool]] = []
    for pid in ix.equity_partner_ids(state, firm):
        w = ix.vote_weight(state, firm, pid)
        if pid in (rec.founder_id, rec.successor_id):
            ok = True
        elif pid == rec.rival_id:
            ok = False
        else:
            u = _utility(state, vid, pid, rec.successor_id, rec.rival_id, balance, data)
            ok = u + ix.election_noise(rng, state.turn, vid, pid, balance) > 0
        ballots.append((pid, ok))
        yes, no = (yes + w, no) if ok else (yes, no + w)
    threshold = ix.vote_threshold_bp(state, firm, vid)
    passed = rec.rival_id is None or (
        yes + no > 0 and yes * BP_DENOMINATOR >= threshold * (yes + no)
    )
    state = ix.record_vote(state, firm, vid, tuple(ballots), yes, no, passed)
    name = _name(state, rec.successor_id)
    if passed:
        state = _set_result(state, "elected")
        done = hand_over(state, rec.successor_id, rec.trigger, rng, balance, data, balances)
        won = inbox_item(
            state.turn,
            firm,
            "succession_elected",
            link_kind="person",
            link_id=rec.successor_id,
            name=name,
            yes=f"{yes:g}",
            no=f"{no:g}",
        )
        return replace(done, log=(won, *done.log))
    state = _set_result(state, "lost")
    rival = rec.rival_id
    assert rival is not None
    logs: list[LogItem] = [
        inbox_item(
            state.turn,
            firm,
            "succession_lost",
            link_kind="person",
            link_id=rival,
            name=name,
            rival=_name(state, rival),
            yes=f"{yes:g}",
            no=f"{no:g}",
        )
    ]
    if rec.trigger not in FORCED:
        return Month(state, log=tuple(logs))
    if state.save_meta.difficulty == "ironman":
        meta = replace(state.save_meta, game_state="election_lost", ended_turn=state.turn)
        return Month(replace(state, save_meta=meta), log=tuple(logs))
    # the player must go: the partnership's choice, the rival, becomes MP and is played
    done = hand_over(state, rival, rec.trigger, rng, balance, data, balances)
    return replace(done, log=(*logs, *done.log))


def _name(state: GameState, pid: int) -> str:
    p = state.person(pid)
    return f"{p.first_name} {p.last_name}"


def _set_result(state: GameState, result: str) -> GameState:
    fl = state.founder_life
    rec = fl.last_succession
    assert rec is not None
    return replace(
        state,
        founder_life=replace(fl, successions=(*fl.successions[:-1], replace(rec, result=result))),
    )


def hand_over(
    state: GameState,
    successor_id: int,
    trigger: str,
    rng: RngFactory,
    balance: Balance,
    data: GameData,
    balances: Mapping[tuple[int, AccountCode], Cents],
) -> Month:
    """Play passes to the successor (TST 45.5's play the heir). Changes only the MP seat, the
    player flag (and the month's energy, PT-M4's hand-over), the old player's status and the
    lives and books of the two: the firm's state is otherwise untouched. A player at or past
    the retirement age retires as they hand over (spec 2.5)."""
    firm = state.player.id
    old = player_id(state)
    assert old is not None
    state = ix.hand_over(state, firm, old, successor_id, balance)
    if trigger == "election":  # the partnership's elected MP keeps the seat (ADR PT-0007 3)
        state = ix.clear_election_result(state, firm)
    else:
        state = ix.set_managing_partner(state, firm, successor_id)
    fl = state.founder_life
    old_life = fl.life(old) or new_life(old, state.turn, balance)
    member = state.family.member(successor_id)
    child = member is not None and member.relation == CHILD and old in member.parent_ids
    heir = (
        heir_life(successor_id, old_life, state.turn, balance)
        if child or not balance.succession.persona_reset
        else new_life(successor_id, state.turn, balance)
    )
    fl = with_life(
        fl,
        replace(
            old_life,
            status="senior_partner",
            until_turn=state.turn,
            committee=False,
            bar_spend_cents=0,
            standing=False,
        ),
    )
    fl = with_life(fl, heir)
    entries: list[PersonalEntry] = []
    if fl.book(successor_id) is None:
        book, opened = personal.open_book(
            successor_id,
            state.turn,
            balance.founder_life.personal.successor_start_cents,
            ix.partner_account(state, firm, successor_id),
        )
        fl = with_book(fl, book)
        entries += opened
    last = fl.last_succession
    if last is not None and last.result in ("open", "elected", "lost"):
        done = replace(last, result="handed_over", successor_id=successor_id)
        fl = replace(fl, successions=(*fl.successions[:-1], done))
    else:  # a hand-over with no record (tests, scripts)
        fl = replace(
            fl,
            successions=(
                *fl.successions,
                Succession(state.turn, trigger, old, successor_id, result="handed_over"),
            ),
        )
    fl = replace(fl, retirement_due_turn=None, due_trigger=None)
    state = replace(state, founder_life=fl)
    logs: list[LogItem] = [
        inbox_item(
            state.turn,
            firm,
            "succession_handover",
            link_kind="person",
            link_id=successor_id,
            name=_name(state, successor_id),
            founder=_name(state, old),
        )
    ]
    firm_entries: list[LedgerEntry] = []
    if trigger == "health":
        from ptk.sim.family.estate import pay_estate_tax

        old_book = state.founder_life.book(old)
        if old_book is not None:
            taxed, fs, paid = pay_estate_tax(
                old_book, state.family, state.turn, state.save_meta.start_ym, balance
            )
            state = replace(state, family=fs, founder_life=with_book(state.founder_life, taxed))
            entries += paid
    person = state.person(old)
    if person.age(state.turn) >= ix.retirement_age(state, firm, balance) or trigger == "health":
        from ptk.sim.founder.retirement import retire

        res = retire(state, old, rng, balance, data, balances)
        state = res.state
        firm_entries += res.entries
        logs += res.log
    return Month(state, tuple(firm_entries), tuple(entries), tuple(logs))


def month(state: GameState, rng: RngFactory, balance: Balance) -> Month:
    """Phase 10's triggers: the plan's confidence term from `plan_from_age`; mandatory
    retirement; the health step-back. Returns logs (and the due date in the state)."""
    you = player_id(state)
    if you is None:
        return Month(state)
    firm = state.player.id
    sb = balance.succession
    fl = state.founder_life
    person = state.person(you)
    age = person.age(state.turn)
    is_mp = ix.managing_partner(state, firm) == you
    logs: list[LogItem] = []
    life = fl.life(you)
    plan = life.successor_plan if life is not None else None
    if is_mp and age >= sb.plan_from_age and plan not in candidates(state):
        state = ix.confidence_change(state, firm, sb.no_plan_confidence)
    open_now = fl.last_succession is not None and fl.last_succession.result == "open"
    if fl.retirement_due_turn is None and not open_now:
        trigger = None
        if age >= ix.retirement_age(state, firm, balance):
            trigger = "retirement"
        elif _health(state, you, age, rng, balance):
            trigger = "health"
        if trigger is not None:
            due = state.turn + sb.grace_months
            fl = replace(state.founder_life, retirement_due_turn=due, due_trigger=trigger)
            state = replace(state, founder_life=fl)
            logs.append(
                inbox_item(
                    state.turn,
                    firm,
                    f"succession_due_{trigger}",
                    link_kind=None,
                    months=sb.grace_months,
                    age=age,
                )
            )
    return Month(state, log=tuple(logs))


def _health(state: GameState, pid: int, age: int, rng: RngFactory, balance: Balance) -> bool:
    """TST 45.5: each January from `step_back_from` a seeded health event asks the player to
    step back; never for a person flagged real (ADR PT-0013)."""
    sb = balance.succession
    if state.person(pid).real or age < sb.step_back_from:
        return False
    if turn_to_ym(state.turn, state.save_meta.start_ym)[1] != JANUARY:
        return False
    chance = min(1.0, sb.step_back_rate * (age - sb.step_back_from + 1))
    return float(family_stream(rng, state.turn, pid, HEALTH_KEY, 0).random()) < chance


def due(state: GameState, balance: Balance, data: GameData) -> GameState:
    """At the due turn with nothing named: the plan's successor, else the strongest candidate
    (as the firm sees them), is named. With no other equity partner the agreement cannot
    retire its last partner: the player stays on until one is admitted (the Founder screen
    says so)."""
    fl = state.founder_life
    if fl.retirement_due_turn is None or state.turn < fl.retirement_due_turn:
        return state
    last = fl.last_succession
    if last is not None and last.result == "open":
        return state
    you = player_id(state)
    pool = candidates(state)
    if you is None:
        return state
    if not pool:  # no partner to succeed: the player stays on until one is admitted
        return state
    life = fl.life(you)
    plan = life.successor_plan if life is not None else None
    firm = state.player.id
    pick = (
        plan
        if plan in pool
        else max(pool, key=lambda p: (ix.candidate_rating(state, firm, p, data), -p))
    )
    return name_successor(state, pick, fl.due_trigger or "retirement", balance)


def years_to_retirement(state: GameState, balance: Balance) -> float | None:
    you = player_id(state)
    if you is None:
        return None
    months = ix.retirement_age(state, state.player.id, balance) * MONTHS_PER_YEAR - (
        state.turn - state.person(you).birth_turn
    )
    return months / MONTHS_PER_YEAR
