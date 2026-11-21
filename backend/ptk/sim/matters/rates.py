"""The firm's rate card and its yearly rise (PT-M7a; spec 7.1's price term, 4.2).

The practices' cards (practices.yaml) are 2005's. The player's firm bills at the card times its
**rate index**, which rises each `rates.month` (January) by the firm's policy (`rate_rise_bp`,
default the market's: the macro history's `rate_rise` for the year, PT-M7, then
`rivals.rate_inflation`). The market's index is those rises compounded over the Januaries
played. Demand is work valued at the 2005 cards (hours), so a matter's hours come from its size
at the card and its expected fees, every hour's standard value and a blended rate take the
firm's index: the market's rate inflation reaches revenue through the index (PT-M7).

The appeal's price term (spec 7.1) is `1 - firm index / market index`: 0 for a firm that rises
with the market, negative for one above it.
"""

from __future__ import annotations

from dataclasses import replace

from ptk.sim.calendar import turn_to_ym
from ptk.sim.data_models import Balance, GameData
from ptk.sim.log import LogItem, inbox_item
from ptk.sim.macro import market_rise
from ptk.sim.money import BP_DENOMINATOR
from ptk.sim.state import FirmState, GameState, with_firm


def market_rise_bp(year: int, data: GameData, balance: Balance) -> int:
    """The market's rise in January of `year` (PT-M7: the macro history's, then free play's)."""
    return round(market_rise(year, data, balance) * BP_DENOMINATOR)


def rise_bp(firm: FirmState, year: int, data: GameData, balance: Balance) -> int:
    """This firm's yearly rise: its policy, or the market's."""
    return market_rise_bp(year, data, balance) if firm.rate_rise_bp is None else firm.rate_rise_bp


def rises_before(turn: int, start: tuple[int, int], balance: Balance) -> int:
    """Rate months (January) played from turn 1 up to and including `turn`."""
    return sum(1 for t in range(1, turn + 1) if turn_to_ym(t, start)[1] == balance.rates.month)


def market_index(turn: int, start: tuple[int, int], data: GameData, balance: Balance) -> float:
    """The market's rate index at `turn`: each January's rise compounded since turn 0."""
    index = 1.0
    for t in range(1, turn + 1):
        year, month = turn_to_ym(t, start)
        if month == balance.rates.month:
            index *= 1.0 + market_rise_bp(year, data, balance) / BP_DENOMINATOR
    return index


def price_term(state: GameState, firm_id: int, data: GameData, balance: Balance) -> float:
    """The appeal's price term (spec 7.1): 1 - the firm's index / the market's."""
    market = market_index(state.turn, state.save_meta.start_ym, data, balance)
    return 1.0 - state.firm(firm_id).rate_index / market


def indexed_rate(card_cents: int, index: float) -> int:
    """A 2005 card rate (cents an hour) on the firm's card: integer cents, rounded once."""
    return card_cents if index == 1.0 else round(card_cents * index)  # tunable-exempt: unit


def yearly_rise(
    state: GameState, data: GameData, balance: Balance
) -> tuple[GameState, tuple[LogItem, ...]]:
    """In the rate month (never turn 0) the player's firm raises its card by its policy."""
    year, month = turn_to_ym(state.turn, state.save_meta.start_ym)
    if state.turn == 0 or month != balance.rates.month:
        return state, ()
    firm = state.player
    bp = rise_bp(firm, year, data, balance)
    index = firm.rate_index * (1.0 + bp / BP_DENOMINATOR)
    state = with_firm(state, replace(firm, rate_index=index))
    item = inbox_item(
        state.turn,
        firm.id,
        "rates_rose",
        link_kind="finance",
        pct=f"{bp / 100:+.1f}%",
        index=f"{index:.3f}",
    )
    return state, (item,)
