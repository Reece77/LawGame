"""The player's answer to a press moment (spec 12.2; TST 29.1-29.2; PT-M16): a tone, and with
a bold or measured answer an optional public claim. Taken at once (ADR-0014) while the moment
is open (its month); energy `press.energy_answer`."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import InvalidActionError
from ptk.sim.hiring.actions import Outcome, acting_firm, spend_energy
from ptk.sim.log import LogItem, inbox_item
from ptk.sim.press import claims, moments
from ptk.sim.press.config import TONES
from ptk.sim.rankings.actions import MakeSubmission, make_submission
from ptk.sim.state import GameState


@dataclass(frozen=True, slots=True)
class AnswerPress:
    actor_id: int
    moment_id: int
    tone: str  # bold, measured, deflect
    claim: str | None = None  # press.config.CLAIM_KINDS
    practice: str | None = None  # a band claim's practice
    target: int | None = None  # headcount: lawyers; band: the band
    months: int | None = None  # a timed claim's deadline, months out
    kind: Literal["answer_press"] = "answer_press"


type StandingAction = AnswerPress | MakeSubmission

STANDING_ACTION_TYPES: dict[str, type[StandingAction]] = {
    "answer_press": AnswerPress,
    "make_submission": MakeSubmission,
}


def answer_press(state: GameState, a: AnswerPress, balance: Balance, data: GameData) -> Outcome:
    acting_firm(state, a.actor_id)
    moment = moments.press_of(state).moment(a.moment_id)
    if moment is None or moment.status != "open" or moment.due_turn != state.turn:
        raise InvalidActionError(f"press moment {a.moment_id} is not open to answer")
    if a.tone not in TONES:
        raise InvalidActionError(f"a tone is one of {TONES}")
    if a.claim is not None and a.tone == "deflect":
        raise InvalidActionError("a claim is made with a bold or measured answer")
    state = spend_energy(state, a.actor_id, "press_answer", balance)
    logs: list[LogItem] = []
    if a.claim is not None:  # checked first, so a refused claim changes nothing
        state, claim = claims.make(
            state,
            moment.id,
            a.claim,
            balance,
            data,
            practice=a.practice,
            target=a.target,
            months=a.months,
        )
        words = claims.claim_words(claim, data, state.save_meta.start_ym)
        logs.append(
            inbox_item(
                state.turn,
                state.player.id,
                "claim_made",
                link_kind="press",
                link_id=claim.id,
                claim=words,
            )
        )
    state, logged = moments.apply_tone(state, moment, a.tone, balance, data)
    return Outcome(state=state, log=(*logged, *logs))


def apply_standing_action(
    state: GameState, action: StandingAction, balance: Balance, data: GameData
) -> Outcome:
    if isinstance(action, AnswerPress):
        return answer_press(state, action, balance, data)
    return make_submission(state, action, balance)
