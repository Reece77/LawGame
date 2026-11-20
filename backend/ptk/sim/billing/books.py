"""Aggregate a month's billing movements into a few balanced entries (one per kind of
movement, lines by account and practice), in the firm's ledger and in the client-money book.

Every movement is added as a balanced pair, so each aggregated entry balances by
construction; `LedgerEntry` and `ClientBookEntry` check it again.
"""

from __future__ import annotations

from ptk.sim.billing.models import ClientBookEntry, ClientBookLine
from ptk.sim.ledger import CLIENT_BANK, OWED_TO_CLIENTS, AccountCode, LedgerEntry, LedgerLine

# Entry memos (statements classify by account, not by memo; memos are for people).
WIP_POSTED = "Work in progress at standard rates"
BILLS = "Bills issued"
RETAINERS = "Retainers: advance bills and months earned"
COLLECTIONS = "Collections"
CLIENT_TRANSFERS = "Bills paid from client money"
CREDIT_NOTES = "Credit notes (disputes and short payments)"
WRITE_OFFS = "Bad debts written off"
CLOSINGS = "Final bills, success and contingency fees"
PROVISIONS = "WIP and bad-debt provisions"


class Books:
    def __init__(self, turn: int, firm_id: int) -> None:
        self.turn = turn
        self.firm_id = firm_id
        self._groups: dict[str, dict[tuple[AccountCode, str | None], int]] = {}

    def move(
        self,
        memo: str,
        debit: AccountCode,
        credit: AccountCode,
        amount: int,
        practice: str | None = None,
    ) -> None:
        """Debit one account and credit another by `amount` (a negative amount reverses)."""
        if amount == 0:
            return
        group = self._groups.setdefault(memo, {})
        group[(debit, practice)] = group.get((debit, practice), 0) + amount
        group[(credit, practice)] = group.get((credit, practice), 0) - amount

    def total(self, *accounts: AccountCode) -> int:
        """The month's net movement on the accounts so far (debits positive)."""
        return sum(
            v for group in self._groups.values() for (a, _), v in group.items() if a in accounts
        )

    def entries(self) -> tuple[LedgerEntry, ...]:
        out = []
        for memo, group in self._groups.items():
            lines = tuple(
                LedgerLine(account=a, amount=v, practice=p)
                for (a, p), v in sorted(group.items(), key=lambda kv: (kv[0][0], kv[0][1] or ""))
                if v != 0
            )
            if len(lines) >= 2:
                out.append(
                    LedgerEntry(turn=self.turn, firm_id=self.firm_id, memo=memo, lines=lines)
                )
        return tuple(out)


# Client-book memos
DEPOSITS = "Money received on account"
RECOVERIES = "Recoveries received for clients"
TRANSFERS = "Transfers to the firm for bills"
REFUNDS = "Money returned to clients"


class ClientBook:
    """The client account's month (ADR PT-0003 section 7): the bank is a debit, what is owed to
    each client a credit; every movement moves both by the same amount."""

    def __init__(self, turn: int, firm_id: int) -> None:
        self.turn = turn
        self.firm_id = firm_id
        self._groups: dict[str, dict[tuple[str, int], int]] = {}

    def receive(self, memo: str, client_id: int, amount: int) -> None:
        self._add(memo, client_id, amount)

    def pay_out(self, memo: str, client_id: int, amount: int) -> None:
        self._add(memo, client_id, -amount)

    def _add(self, memo: str, client_id: int, amount: int) -> None:
        if amount == 0:
            return
        group = self._groups.setdefault(memo, {})
        group[(CLIENT_BANK, client_id)] = group.get((CLIENT_BANK, client_id), 0) + amount
        group[(OWED_TO_CLIENTS, client_id)] = group.get((OWED_TO_CLIENTS, client_id), 0) - amount

    def entries(self) -> tuple[ClientBookEntry, ...]:
        out = []
        for memo, group in self._groups.items():
            lines = tuple(
                ClientBookLine(account=a, client_id=c, amount=v)
                for (a, c), v in sorted(group.items())
                if v != 0
            )
            if len(lines) >= 2:
                out.append(
                    ClientBookEntry(turn=self.turn, firm_id=self.firm_id, memo=memo, lines=lines)
                )
        return tuple(out)
