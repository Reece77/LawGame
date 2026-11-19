"""Ledger invariants (ADR-0003, ADR PT-0003): every entry balances; separate books stay apart;
assets = liabilities + equity once income and expense close to equity."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import UnbalancedEntryError
from ptk.sim.ledger import LedgerEntry, LedgerLine, apply_entries
from ptk.sim.setup import new_game

FIRM_CODES = [
    "1000_cash",
    "1100_unbilled_wip",
    "1200_receivables",
    "2300_revolver",
    "3000_partners_capital",
    "4000_fees",
    "5000_associate_salaries",
    "6000_rent",
]


@given(
    st.lists(
        st.tuples(st.sampled_from(FIRM_CODES), st.integers(-(10**12), 10**12)),
        min_size=1,
        max_size=8,
    )
)
def test_balanced_entries_post_and_unbalanced_fail(lines: list[tuple[str, int]]) -> None:
    total = sum(a for _, a in lines)
    balanced = (*[LedgerLine(c, a) for c, a in lines], LedgerLine("1000_cash", -total))
    entry = LedgerEntry(turn=0, firm_id=1, memo="t", lines=balanced)
    assert sum(apply_entries({}, [entry]).values()) == 0
    with pytest.raises(UnbalancedEntryError):
        LedgerEntry(turn=0, firm_id=1, memo="t", lines=(*balanced, LedgerLine("1000_cash", 1)))


@pytest.mark.parametrize("code", ["C1000_client_bank", "9100_personal_cash"])
def test_separate_books_never_enter_a_firm_entry(code: str) -> None:
    with pytest.raises(UnbalancedEntryError):
        LedgerEntry.transfer(
            turn=0, firm_id=1, memo="x", debit="1000_cash", credit=code, amount=100
        )


def test_float_amounts_are_refused() -> None:
    with pytest.raises(UnbalancedEntryError):
        LedgerEntry(
            turn=0,
            firm_id=1,
            memo="x",
            lines=(LedgerLine("1000_cash", 1.5), LedgerLine("4000_fees", -1.5)),
        )  # type: ignore[arg-type]


@given(st.integers(0, 2**64 - 1), st.sampled_from(["easy", "standard", "hard", "ironman"]))
def test_new_game_balance_sheet_balances(
    data: GameData, balance: Balance, seed: int, difficulty: str
) -> None:
    game = new_game(
        name="p",
        firm_name="F",
        master_seed=seed,
        scenario_id="biglaw_spinout",
        difficulty=difficulty,
        data=data,
        balance=balance,
    )
    balances = apply_entries({}, game.ledger_entries)
    types = data.account_types()

    def total(*kinds: str) -> int:
        return sum(v for (_, a), v in balances.items() if types[a] in kinds)

    # Debits positive: assets = liabilities + equity + (income - expenses), with signs flipped.
    assert total("asset") == -(total("liability", "equity") + total("income", "expense"))
