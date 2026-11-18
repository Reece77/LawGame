"""Double-entry ledger (ADR-0003, ADR PT-0003). Debits are positive, credits negative;
every entry sums to 0.

Ported from tst/sim/ledger.py @ 02fba2aa; changed: Partner Track's chart of accounts;
reporting dimensions are practice and office; client money (C-prefixed accounts) is a
separate book and can never appear in a firm entry.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Final

from ptk.sim.errors import UnbalancedEntryError
from ptk.sim.money import Cents

type AccountCode = str
# (firm_id, account) -> balance (ADR-0012).
type LedgerBalances = Mapping[tuple[int, AccountCode], Cents]

PERSONAL_DIGIT: Final = "9"  # the founder's personal book (TST 32.2)
CLIENT_PREFIX: Final = "C"  # the client-money book (ADR PT-0003 section 7)

# Account codes the engine posts to. All must exist in data/accounts.yaml (checked by tests).
CASH: Final = "1000_cash"
WIP: Final = "1100_unbilled_wip"
RECEIVABLES: Final = "1200_receivables"
PARTNERS_CAPITAL: Final = "3000_partners_capital"
UNDISTRIBUTED_PROFIT: Final = "3100_undistributed_profit"
DRAWINGS: Final = "3200_drawings"
FEES: Final = "4000_fees"
GENERAL_ADMIN: Final = "6900_general_admin"
ENGINE_ACCOUNTS: Final = (
    CASH,
    WIP,
    RECEIVABLES,
    PARTNERS_CAPITAL,
    UNDISTRIBUTED_PROFIT,
    DRAWINGS,
    FEES,
    GENERAL_ADMIN,
)


@dataclass(frozen=True, slots=True)
class LedgerLine:
    account: AccountCode
    amount: Cents  # debit positive, credit negative
    practice: str | None = None  # reporting dimension: practice key; None = firm-wide
    office_id: int | None = None  # reporting dimension: office; None = firm-wide


@dataclass(frozen=True, slots=True)
class LedgerEntry:
    turn: int
    firm_id: int
    memo: str
    lines: tuple[LedgerLine, ...]

    def __post_init__(self) -> None:
        if len(self.lines) < 2:
            raise UnbalancedEntryError(f"entry {self.memo!r} needs at least two lines")
        for line in self.lines:
            if isinstance(line.amount, bool) or not isinstance(line.amount, int):
                raise UnbalancedEntryError(
                    f"entry {self.memo!r}: amount for {line.account} must be int cents"
                )
            if line.account[0] in (PERSONAL_DIGIT, CLIENT_PREFIX):
                # The founder's personal book and the client-money book are separate books
                # (ADR PT-0003 section 7): never in a firm entry.
                raise UnbalancedEntryError(
                    f"entry {self.memo!r}: {line.account} belongs to a separate book, not a firm's"
                )
        total = sum(line.amount for line in self.lines)
        if total != 0:
            raise UnbalancedEntryError(
                f"entry {self.memo!r} does not balance: lines sum to {total}"
            )

    @classmethod
    def transfer(
        cls,
        *,
        turn: int,
        firm_id: int,
        memo: str,
        debit: AccountCode,
        credit: AccountCode,
        amount: Cents,
    ) -> LedgerEntry:
        """A two-line entry moving `amount` from the credit account to the debit account."""
        return cls(
            turn=turn,
            firm_id=firm_id,
            memo=memo,
            lines=(LedgerLine(debit, amount), LedgerLine(credit, -amount)),
        )


def apply_entries(
    balances: LedgerBalances, entries: Iterable[LedgerEntry]
) -> dict[tuple[int, AccountCode], Cents]:
    """Return a new balance mapping with the entries posted. The input is not modified."""
    result = dict(balances)
    for entry in entries:
        for line in entry.lines:
            key = (entry.firm_id, line.account)
            result[key] = result.get(key, 0) + line.amount
    return result


def account_balance(balances: LedgerBalances, firm_id: int, account: AccountCode) -> Cents:
    return balances.get((firm_id, account), 0)
