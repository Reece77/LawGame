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

PT-M7b: a new firm's **card by practice**. The firm starts each practice at `rates.card.start_bp`
of the top card (practices.yaml's 2005 cards; times the difficulty's `card_mult_bp`) and each
January moves at most `step_bp` toward its target, which rises with its reputation in the
practice (PT-M16: `reputation.formulas.card_progress`; PT-M7c: the firm's percentile among all
firms in the practice over `reputation.card.top_quantile`):
start + (1 - start) x progress^curve, so only a firm near the top of the market's reputation
bills at the top card. A practice's effective index is the firm's rate index times
its share: every hour's standard value, blended rates and new matters' expected fees use it, and
the price term reads it against the market's index. Rival firms keep their own rates.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

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


def card_bp(firm: FirmState, practice: str) -> int:
    """PT-M7b: the firm's share of a practice's top card (bp); a practice not on its card bills
    at the full card (a save from before PT-M7b)."""
    for key, bp in firm.rate_card:
        if key == practice:
            return bp
    return BP_DENOMINATOR


def practice_index(firm: FirmState, practice: str) -> float:
    """PT-M7b: the index a practice bills at: the firm's rate index times its card share."""
    bp = card_bp(firm, practice)
    return firm.rate_index if bp == BP_DENOMINATOR else firm.rate_index * bp / BP_DENOMINATOR


def start_card_bp(difficulty: str, data: GameData, balance: Balance) -> int:
    """A new firm's share in every practice: the start share times the difficulty's card."""
    level = data.difficulty(difficulty)
    mult = level.card_mult_bp if level is not None else BP_DENOMINATOR
    return min(BP_DENOMINATOR, round(balance.rates.card.start_bp * mult / BP_DENOMINATOR))


def starting_card(difficulty: str, data: GameData, balance: Balance) -> tuple[tuple[str, int], ...]:
    """PT-M7b: a new firm's card, every practice at the start share (sorted by key)."""
    start = start_card_bp(difficulty, data, balance)
    return tuple((key, start) for key in sorted(data.practice_keys))


def card_target_bp(progress: float, start_bp: int, balance: Balance) -> int:
    """The share a practice's reputation earns: start + (1 - start) x progress^curve, where
    progress (0-1) is `reputation.formulas.card_progress` (PT-M16)."""
    curved = float(min(1.0, max(0.0, progress)) ** balance.reputation.card.curve)
    return min(BP_DENOMINATOR, round(start_bp + (BP_DENOMINATOR - start_bp) * curved))


def card_moved(
    state: GameState, firm: FirmState, data: GameData, balance: Balance
) -> tuple[tuple[str, int], ...]:
    """January's move of each practice's share toward its reputation's target, at most
    `step_bp` either way."""
    from ptk.sim.reputation.formulas import card_progress

    if not firm.rate_card:
        return firm.rate_card
    start = start_card_bp(state.save_meta.difficulty, data, balance)
    step = balance.rates.card.step_bp
    out = []
    for key, bp in firm.rate_card:
        target = card_target_bp(card_progress(state, firm.id, key, balance), start, balance)
        out.append((key, bp + max(-step, min(step, target - bp))))
    return tuple(out)


@dataclass(frozen=True, slots=True)
class ClientCards:
    """PT-M7c: one firm's card by client for a month, the book clients and tiers looked up
    once (the staffing rule asks for every hours record)."""

    rate_index: float
    cards: dict[str, int]  # practice -> the practice's share (what large clients pay)
    book: frozenset[int]  # the founders' book clients, while they keep the founders' rates
    large: frozenset[int]
    mid_max_bp: int
    book_bp: int
    full: bool = False  # a save from before PT-M7b: the full card for everyone
    fade: float = 0.0  # 0-1: how far the book's rates have fallen to their tiers' cards

    def tier_bp(self, practice: str, client_id: int) -> int:
        bp = self.cards.get(practice, BP_DENOMINATOR)
        return bp if client_id in self.large else min(bp, self.mid_max_bp)

    def bp(self, practice: str, client_id: int) -> int:
        if self.full:
            return BP_DENOMINATOR
        tier = self.tier_bp(practice, client_id)
        if client_id in self.book:
            return round(self.book_bp + (tier - self.book_bp) * self.fade)
        return tier

    def __call__(self, practice: str, client_id: int) -> float:
        """The index the client's work in the practice bills at."""
        bp = self.bp(practice, client_id)
        return self.rate_index if bp == BP_DENOMINATOR else self.rate_index * bp / BP_DENOMINATOR

    def reference(self, client_id: int) -> float:
        """What the market charges the client's tier, as a share of the top card (the price
        term's reference): the founders' rates for their book, the full card for large
        clients, the mid-market cap for the rest."""
        if self.full:
            return 1.0
        tier = 1.0 if client_id in self.large else self.mid_max_bp / BP_DENOMINATOR
        if client_id in self.book:
            book = self.book_bp / BP_DENOMINATOR
            return book + (tier - book) * self.fade
        return tier


def client_indexes(state: GameState, firm: FirmState, balance: Balance) -> ClientCards:
    """PT-M7c: the firm's `ClientCards` this month."""
    from ptk.sim.matters.setup import SETUP_TURN

    cfg = balance.rates.card
    book = (
        frozenset(
            r.client_id
            for r in state.market.relationships
            if r.firm_id == firm.id and r.since_turn == SETUP_TURN
        )
        if firm.id == state.player.id and state.turn < cfg.book_months + cfg.book_fade_months
        else frozenset()
    )
    fade = 0.0
    if state.turn >= cfg.book_months and cfg.book_fade_months > 0:
        fade = min(1.0, (state.turn - cfg.book_months + 1) / (cfg.book_fade_months + 1))
    return ClientCards(
        rate_index=firm.rate_index,
        cards=dict(firm.rate_card),
        book=book,
        large=frozenset(c.id for c in state.market.clients if c.size_class == "large"),
        mid_max_bp=cfg.mid_max_bp,
        book_bp=cfg.book_bp,
        full=not firm.rate_card,
        fade=fade,
    )


def client_price_term(
    state: GameState, firm_id: int, practice: str, client_id: int, data: GameData, balance: Balance
) -> float:
    """PT-M7c: the appeal's price term for one client (spec 7.1): 1 - what the firm charges it
    / what the market charges its tier."""
    market = market_index(state.turn, state.save_meta.start_ym, data, balance)
    cards = client_indexes(state, state.firm(firm_id), balance)
    return 1.0 - cards(practice, client_id) / (market * cards.reference(client_id))


def price_term(
    state: GameState, firm_id: int, data: GameData, balance: Balance, practice: str | None = None
) -> float:
    """The appeal's price term (spec 7.1): 1 - the firm's index / the market's; with `practice`
    (PT-M7b), that practice's card times the index."""
    market = market_index(state.turn, state.save_meta.start_ym, data, balance)
    firm = state.firm(firm_id)
    index = firm.rate_index if practice is None else practice_index(firm, practice)
    return 1.0 - index / market


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
    card = card_moved(state, firm, data, balance)  # PT-M7b: the card earns its reputation
    state = with_firm(state, replace(firm, rate_index=index, rate_card=card))
    item = inbox_item(
        state.turn,
        firm.id,
        "rates_rose",
        link_kind="finance",
        pct=f"{bp / 100:+.1f}%",
        index=f"{index:.3f}",
    )
    return state, (item,)
