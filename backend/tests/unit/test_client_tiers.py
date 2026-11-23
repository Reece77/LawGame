"""PT-M7c (Reece, 2026-11-23): client-tier pricing. Large clients pay the practice's card (the
full card only in the reputation's top decile), mid-market clients at most `mid_max_bp`, the
founders' book the founders' rates for `book_months`, then fading to its tier's card."""

from __future__ import annotations

from dataclasses import replace

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ptk.sim.data_models import Balance, GameData
from ptk.sim.matters.rates import ClientCards, client_indexes
from tests.partnership_support import start

BOOK, LARGE, MID, LARGE_BOOK = 1, 2, 3, 4


def _cards(fade: float = 0.0, card: int = 8000) -> ClientCards:
    return ClientCards(
        rate_index=1.5,
        cards={"corporate_ma": card},
        book=frozenset({BOOK, LARGE_BOOK}),
        large=frozenset({LARGE, LARGE_BOOK}),
        mid_max_bp=6000,
        book_bp=9850,
        fade=fade,
    )


def test_each_tier_pays_its_card() -> None:
    c = _cards()
    assert c.bp("corporate_ma", BOOK) == 9850
    assert c.bp("corporate_ma", LARGE) == 8000
    assert c.bp("corporate_ma", MID) == 6000
    assert c("corporate_ma", LARGE) == pytest.approx(1.5 * 0.8)


def test_mid_market_pays_less_than_its_cap_when_the_card_is_lower() -> None:
    assert _cards(card=5000).bp("corporate_ma", MID) == 5000


def test_the_book_fades_to_its_tier() -> None:
    half = _cards(fade=0.5)
    assert half.bp("corporate_ma", BOOK) == round(9850 + (6000 - 9850) * 0.5)  # to the mid cap
    assert half.bp("corporate_ma", LARGE_BOOK) == round(9850 + (8000 - 9850) * 0.5)
    done = _cards(fade=1.0)
    assert done.bp("corporate_ma", BOOK) == 6000
    assert done.bp("corporate_ma", LARGE_BOOK) == 8000  # the practice's card
    assert done.reference(LARGE_BOOK) == 1.0  # and priced as a large client
    assert done.reference(BOOK) == pytest.approx(0.6)


def test_the_price_reference_is_the_tiers() -> None:
    c = _cards()
    assert c.reference(LARGE) == 1.0
    assert c.reference(MID) == pytest.approx(0.6)
    assert c.reference(BOOK) == pytest.approx(0.985)


def test_a_save_without_a_card_bills_the_full_card() -> None:
    c = replace(_cards(), full=True)
    assert c.bp("corporate_ma", MID) == 10_000
    assert c("corporate_ma", MID) == 1.5


def test_a_new_firms_book_is_its_founders_clients(data: GameData, balance: Balance) -> None:
    g = start(data, balance, 3)
    cards = client_indexes(g.state, g.state.player, balance)
    book = {r.client_id for r in g.state.market.relationships if r.firm_id == g.state.player.id}
    assert book and cards.book == frozenset(book)
    later = replace(
        g.state, turn=balance.rates.card.book_months + balance.rates.card.book_fade_months
    )
    assert not client_indexes(later, later.player, balance).book


@given(
    card=st.integers(1, 10_000),
    fade=st.floats(0.0, 1.0),
    client=st.sampled_from([BOOK, LARGE, MID, LARGE_BOOK]),
)
def test_a_clients_share_stays_between_its_tier_and_the_founders_rates(
    card: int, fade: float, client: int
) -> None:
    c = _cards(fade=fade, card=card)
    bp = c.bp("corporate_ma", client)
    assert 0 < bp <= 10_000
    if client == MID:
        assert bp <= 6000
    tier = card if client == LARGE_BOOK else min(card, 6000)
    if client in (BOOK, LARGE_BOOK):
        assert min(tier, 9850) <= bp <= max(tier, 9850)
