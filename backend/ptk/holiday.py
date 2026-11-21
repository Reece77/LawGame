"""Holiday and "continue until" (PT-M7a; spec 4.2; TST 17.1's pattern, synchronous).

Outside the sim: each month is `saves.run_turn`, its own transaction with its events written
after the commit, exactly as a Continue (ADR-0004). A holiday plays up to `months` months, or
until the date `until_turn`, and stops after a month when, in this order:

1. the game is over (`game_over`);
2. a written critical event waits (`critical_event`): never answered for the player;
3. the next month is December and the partnership has a December decision: an associate
   eligible for the vote or a vote open (`vote`); any open vote stops it in other months;
4. a rival made one of the firm's partners an approach during the holiday (`approach`);
5. the other side made a settlement offer on one of the firm's cases during it
   (`settlement_offer`);
6. the date was reached (`date`) or the months played (`months`).

A holiday cannot start while a critical event waits (409 `critical_event_open`, as Continue).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

from ptk.db import saves
from ptk.llm.base import LLMAdapter
from ptk.sim.calendar import turn_to_ym
from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import SimError
from ptk.sim.events.effects import check_continue, critical_open
from ptk.sim.partnership.careers import eligible
from ptk.sim.state import GameState

type StopReason = Literal[
    "game_over", "critical_event", "vote", "approach", "settlement_offer", "date", "months"
]

DECEMBER: Final = 12  # tunable-exempt: the vote month (spec 5.5)

REASON_TEXT: Final[dict[str, str]] = {
    "game_over": "the game is over",
    "critical_event": "a critical decision needs your answer",
    "vote": "the partnership has a vote to prepare",
    "approach": "a rival approached one of your partners",
    "settlement_offer": "the other side made a settlement offer",
    "date": "the date you chose has come",
    "months": "the months you chose have passed",
}


class HolidayError(SimError):
    code = "invalid_holiday"


@dataclass(frozen=True, slots=True)
class HolidayResult:
    months_played: int
    reason: StopReason
    start_turn: int
    end_turn: int


def vote_waiting(state: GameState, balance: Balance) -> bool:
    """A vote is open, or December comes with associates eligible for the vote."""
    fp = state.partnership.of(state.player.id)
    if fp is None:
        return False
    if any(v.status == "open" for v in fp.votes):
        return True
    if turn_to_ym(state.turn, state.save_meta.start_ym)[1] != DECEMBER:
        return False
    return any(eligible(state, fp, pid, balance) for pid in state.staff_ids(state.player.id))


def stop_reason(
    state: GameState,
    start_turn: int,
    played: int,
    months: int,
    until_turn: int | None,
    balance: Balance,
) -> StopReason | None:
    """The first stop reason after a month (module docstring), or None to play on."""
    firm = state.player.id
    if state.ended:
        return "game_over"
    if critical_open(state):
        return "critical_event"
    if vote_waiting(state, balance):
        return "vote"
    fp = state.partnership.of(firm)
    if fp is not None and any(
        a.status == "open" and a.made_turn >= start_turn for a in fp.approaches
    ):
        return "approach"
    if any(
        m.settlement is not None
        and m.settlement.made_turn >= start_turn
        and m.settlement.expires_turn >= state.turn
        for m in state.market.open_matters(firm)
    ):
        return "settlement_offer"
    if until_turn is not None and state.turn >= until_turn:
        return "date"
    if played >= months:
        return "months"
    return None


def run_holiday(
    path: Path,
    balance: Balance,
    data: GameData,
    *,
    months: int | None = None,
    until_turn: int | None = None,
    adapter: LLMAdapter | None = None,
) -> HolidayResult:
    """Play Continues until a stop reason. `months` defaults to the most a holiday plays."""
    limit = balance.holiday.max_months
    months = limit if months is None else months
    if not 1 <= months <= limit:
        raise HolidayError(f"a holiday lasts 1 to {limit} months, not {months}")
    state = saves.read_state(path)[0]
    start = state.turn
    if until_turn is not None and not start < until_turn <= start + limit:
        raise HolidayError(f"continue until a month after now and within {limit} months")
    if state.ended:
        raise HolidayError("the game is over")
    check_continue(state)  # a critical event waits: 409, as Continue
    played = 0
    while True:
        saves.run_turn(path, balance, data, adapter=adapter)
        played += 1
        state = saves.read_state(path)[0]
        reason = stop_reason(state, start, played, months, until_turn, balance)
        if reason is not None:
            return HolidayResult(played, reason, start, state.turn)
