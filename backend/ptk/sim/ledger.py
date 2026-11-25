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
# PT-M1b: payroll and operating costs (ADR PT-0003 section 1).
SALARIES: Final = "5000_associate_salaries"
BONUSES: Final = "5010_bonuses"
INCOME_PARTNER_SALARIES: Final = "5020_income_partner_salaries"
STAFF_SALARIES: Final = "5100_staff_salaries"
BENEFITS: Final = "5200_benefits"
RENT: Final = "6000_rent"
RECRUITING: Final = "6200_recruiting"
# PT-M3b: the revenue chain (ADR PT-0003 section 2).
WIP_PROVISION: Final = "1110_wip_provision"
BAD_DEBT_PROVISION: Final = "1210_bad_debt_provision"
DEFERRED_FEES: Final = "2200_deferred_fees"
SUCCESS_FEES: Final = "4100_success_fees"
WRITE_OFFS: Final = "6700_write_offs"
# PT-M4: the partnership (ADR PT-0003 sections 5-6; spec 8.4).
REVOLVER: Final = "2300_revolver"
PARTNER_CURRENT: Final = "2700_partner_current_accounts"
INTEREST: Final = "6800_interest"
PROFESSIONAL_FEES: Final = "6600_professional_fees"
# PT-M17: retired partners' annuities (spec 8.4) and bar politics (TST 32.5's lobbying).
ANNUITIES: Final = "2600_retired_partner_annuities"
LOBBYING: Final = "6950_lobbying"
# PT-M11: offices (spec 8.8): fit-out, leases, right-of-use assets, amortisation, insurance.
PPE: Final = "1500_ppe"
RIGHT_OF_USE: Final = "1510_right_of_use"
LEASES: Final = "2500_leases"
DEPRECIATION: Final = "6050_depreciation"
INSURANCE: Final = "6300_insurance"
# PT-M15: risk (spec 11.3-11.4): claims paid by the firm, client-account shortfalls, fines.
CLAIMS: Final = "6310_claims"
TRUST_SHORTFALLS: Final = "6320_trust_shortfalls"
FINES: Final = "6970_fines"
# The client-money book's accounts (never in a firm entry).
CLIENT_BANK: Final = "C1000_client_bank"
OWED_TO_CLIENTS: Final = "C2000_owed_to_clients"
ENGINE_ACCOUNTS: Final = (
    CASH,
    WIP,
    RECEIVABLES,
    PARTNERS_CAPITAL,
    UNDISTRIBUTED_PROFIT,
    DRAWINGS,
    FEES,
    GENERAL_ADMIN,
    SALARIES,
    BONUSES,
    INCOME_PARTNER_SALARIES,
    STAFF_SALARIES,
    BENEFITS,
    RENT,
    RECRUITING,
    WIP_PROVISION,
    BAD_DEBT_PROVISION,
    DEFERRED_FEES,
    SUCCESS_FEES,
    WRITE_OFFS,
    REVOLVER,
    PARTNER_CURRENT,
    INTEREST,
    PROFESSIONAL_FEES,
    ANNUITIES,
    LOBBYING,
    PPE,
    RIGHT_OF_USE,
    LEASES,
    DEPRECIATION,
    INSURANCE,
    CLAIMS,
    TRUST_SHORTFALLS,
    FINES,
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
