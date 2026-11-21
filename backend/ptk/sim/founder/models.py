"""PT-M17 state (spec 2.2-2.5, 8.4; TST formulas.md 32): the founding partner's life around
the firm, kept for every person the player has played (the founder, then each successor).

Ported from backend/tst/sim/founder/models.py @ 121d318a (Tech Startup Tycoon); changed:
Partner Track's personal chart (draws, the true-up, capital in the firm and its loan, tax,
annuities); a `PersonalBook` holds each player's running balances (the personal entries go
to their own table, like the client-money book); stress is the person's strain (ADR PT-0006);
influence is bar politics with no hidden scandal risk; a player's status (managing partner to
retired) and the annuities owed to retired partners (account 2600) live here.

Everything here is public (TST 32.8) apart from nothing: the persona, the personal account,
influence, the foundation and annuities are all shown.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace
from typing import Final, Literal

from ptk.sim.errors import UnbalancedEntryError

type Cause = tuple[int, str, float, str]  # (turn, trait, change, cause in words)
type Status = Literal["managing_partner", "partner", "senior_partner", "retired", "left"]

# The founder's personal book (TST 32.2, ADR PT-0003 4-5): never in a firm entry (ledger.py
# refuses any 9-account there).
PERSONAL_CASH: Final = "9100_personal_cash"
INVESTMENTS: Final = "9110_investments"
FIRM_CAPITAL: Final = "9120_firm_capital"
FAMILY_OFFICE: Final = "9130_family_office"
TRUST: Final = "9140_family_trust"
ENDOWMENT: Final = "9200_foundation_endowment"
SPENDING: Final = "9300_personal_spending"
INCOME_TAX: Final = "9310_income_tax"
LOAN_INTEREST: Final = "9320_loan_interest"
EDUCATION: Final = "9330_education"
ESTATE_TAX: Final = "9340_estate_tax"
GRANTS: Final = "9350_foundation_grants"
DIVORCE: Final = "9360_divorce_settlement"
DRAWS: Final = "9400_draws"
TRUE_UP: Final = "9410_true_up"
GAINS: Final = "9420_investment_gains"
LOSSES: Final = "9430_investment_losses"
ANNUITY: Final = "9440_annuity_income"
CAPITAL_LOAN: Final = "9500_capital_loan"
TAX_PAYABLE: Final = "9510_tax_payable"
OPENING: Final = "9900_opening_net_worth"
PERSONAL_ACCOUNTS: Final = (
    PERSONAL_CASH,
    INVESTMENTS,
    FIRM_CAPITAL,
    FAMILY_OFFICE,
    TRUST,
    ENDOWMENT,
    SPENDING,
    INCOME_TAX,
    LOAN_INTEREST,
    EDUCATION,
    ESTATE_TAX,
    GRANTS,
    DIVORCE,
    DRAWS,
    TRUE_UP,
    GAINS,
    LOSSES,
    ANNUITY,
    CAPITAL_LOAN,
    TAX_PAYABLE,
    OPENING,
)
ASSETS: Final = (PERSONAL_CASH, INVESTMENTS, FIRM_CAPITAL, FAMILY_OFFICE, TRUST)
INCOME: Final = (DRAWS, TRUE_UP, ANNUITY)  # cash from the firm (and annuities)


@dataclass(frozen=True, slots=True)
class PersonalLine:
    account: str
    amount: int  # debit positive, credit negative


@dataclass(frozen=True, slots=True)
class PersonalEntry:
    """One balanced entry in a player's own book: integer cents, personal accounts only."""

    turn: int
    person_id: int
    memo: str
    source: str  # draws, true_up, tax, loan, capital, invest, gift, grant, education, ...
    lines: tuple[PersonalLine, ...]

    def __post_init__(self) -> None:
        if len(self.lines) < 2:  # tunable-exempt: double entry
            raise UnbalancedEntryError(f"personal entry {self.memo!r} needs two lines")
        for line in self.lines:
            if isinstance(line.amount, bool) or not isinstance(line.amount, int):
                raise UnbalancedEntryError(f"personal entry {self.memo!r}: int cents only")
            if line.account not in PERSONAL_ACCOUNTS:
                raise UnbalancedEntryError(
                    f"personal entry {self.memo!r} posts to {line.account}, not a personal account"
                )
        if sum(line.amount for line in self.lines) != 0:
            raise UnbalancedEntryError(f"personal entry {self.memo!r} does not balance")

    @classmethod
    def transfer(
        cls, turn: int, person_id: int, memo: str, source: str, debit: str, credit: str, cents: int
    ) -> PersonalEntry:
        return cls(
            turn,
            person_id,
            memo,
            source,
            (PersonalLine(debit, cents), PersonalLine(credit, -cents)),
        )


@dataclass(frozen=True, slots=True)
class PersonalBook:
    """A player's running balances (debits positive), equal to the sum of their entries (a
    property test holds this), and the firm-side marks the next month's mirror reads."""

    person_id: int
    opened_turn: int
    balances: tuple[tuple[str, int], ...] = ()  # (account, cents), by account
    mandate: str | None = None  # the family office's mandate, once formed
    # what the partnership showed at the last mirror (ADR PT-0003 6): the mirror posts the
    # difference each month
    seen_drawn_ytd: int = 0
    seen_current: int = 0
    seen_capital: int = 0
    seen_return_current: int = 0
    seen_return_capital: int = 0

    def bal(self, account: str) -> int:
        return next((v for a, v in self.balances if a == account), 0)

    def posted(self, entries: Iterable[PersonalEntry]) -> PersonalBook:
        values = dict(self.balances)
        for entry in entries:
            if entry.person_id != self.person_id:
                continue
            for line in entry.lines:
                values[line.account] = values.get(line.account, 0) + line.amount
        return replace(self, balances=tuple(sorted((k, v) for k, v in values.items() if v)))

    @property
    def cash(self) -> int:
        return self.bal(PERSONAL_CASH)

    @property
    def net_worth(self) -> int:
        """Assets less the loan and tax owed (the endowment is the foundation's)."""
        return sum(self.bal(a) for a in ASSETS) + self.bal(CAPITAL_LOAN) + self.bal(TAX_PAYABLE)


@dataclass(frozen=True, slots=True)
class FounderLife:
    """A player's life around the firm (spec 2.3; TST 32.4): persona, influence, status."""

    person_id: int
    visionary: float
    ruthless: float
    beloved: float
    reckless: float
    status: Status = "managing_partner"
    since_turn: int = 0  # the turn they became the player
    until_turn: int | None = None  # the turn play passed to a successor
    causes: tuple[Cause, ...] = ()
    leverage_year: int | None = None  # the calendar year of `leverage_points`
    leverage_points: float = 0.0
    influence: float = 0.0  # bar politics, 0-100
    committee: bool = False  # sits on a bar committee (energy each month)
    bar_spend_cents: int = 0  # a month on bar politics (6950, the firm's)
    standing: bool = False  # stands for bar office at the next election
    office_until_turn: int | None = None  # bar president until this turn
    office_turns: tuple[int, ...] = ()  # the turns they were elected
    successor_plan: int | None = None  # the successor-designate (the plan, spec 2.5)

    def trait(self, key: str) -> float:
        value: float = getattr(self, key)
        return value


@dataclass(frozen=True, slots=True)
class Foundation:
    """TST 32.3: the founder's foundation; its endowment is the personal book's 9200."""

    person_id: int
    name: str
    cause: str  # config.CAUSES
    created_turn: int
    grants_cents: int = 0  # lifetime
    last_grant_cents: int = 0
    last_grant_turn: int | None = None
    gifts_cents: int = 0  # lifetime


@dataclass(frozen=True, slots=True)
class Annuity:
    """A retired partner's annuity (spec 8.4): booked to 2600 at retirement, paid monthly."""

    person_id: int
    firm_id: int
    monthly_cents: int
    remaining_cents: int  # what 2600 still owes them
    start_turn: int
    end_turn: int


@dataclass(frozen=True, slots=True)
class AnnuityTerms:
    """The agreement's annuity term (spec 8.6), kept here beside PT-M4's agreement."""

    granted: bool
    share_bp: int
    years: int


@dataclass(frozen=True, slots=True)
class Succession:
    """A succession in progress or done (spec 2.5): why, who was named, the vote."""

    turn: int
    trigger: str  # choice, retirement, election, health
    founder_id: int
    successor_id: int
    vote_id: int | None = None
    rival_id: int | None = None
    result: str = "open"  # open, elected, lost, handed_over


@dataclass(frozen=True, slots=True)
class Opinion:
    """The senior partner's view of a vote (TST 45.5's adviser): in their voice, from their
    persona; overruled when the vote passed against it."""

    turn: int
    adviser_id: int
    vote_id: int
    title: str
    stance: str  # support or oppose
    text: str
    overruled: bool = False


@dataclass(frozen=True, slots=True)
class FounderLifeState:
    lives: tuple[FounderLife, ...] = ()  # by person id: every person the player has played
    books: tuple[PersonalBook, ...] = ()  # by person id
    foundations: tuple[Foundation, ...] = ()  # by person id
    annuities: tuple[Annuity, ...] = ()  # by person id
    annuity_terms: AnnuityTerms | None = None  # None: the balance default
    successions: tuple[Succession, ...] = ()  # by turn
    retirement_due_turn: int | None = None  # the player must go: a successor by this turn
    due_trigger: str | None = None  # retirement or health
    opinions: tuple[Opinion, ...] = ()  # the adviser's, the last succession.adviser_memory
    best_revenue_cents: int = 0  # the firm's best year (legacy)
    # personal entries of actions taken since the last turn; the turn takes them and they are
    # persisted then (never saved in the state's JSON)
    pending: tuple[PersonalEntry, ...] = ()

    def life(self, person_id: int) -> FounderLife | None:
        return next((x for x in self.lives if x.person_id == person_id), None)

    def book(self, person_id: int) -> PersonalBook | None:
        return next((b for b in self.books if b.person_id == person_id), None)

    def foundation(self, person_id: int) -> Foundation | None:
        return next((f for f in self.foundations if f.person_id == person_id), None)

    def annuity(self, person_id: int) -> Annuity | None:
        return next((a for a in self.annuities if a.person_id == person_id), None)

    @property
    def last_succession(self) -> Succession | None:
        return self.successions[-1] if self.successions else None


EMPTY_FOUNDER_LIFE: Final = FounderLifeState()


def _upsert[T](items: tuple[T, ...], item: T, key: str) -> tuple[T, ...]:
    rest = [x for x in items if getattr(x, key) != getattr(item, key)]
    return tuple(sorted([*rest, item], key=lambda x: getattr(x, key)))


def with_life(fl: FounderLifeState, life: FounderLife) -> FounderLifeState:
    return replace(fl, lives=_upsert(fl.lives, life, "person_id"))


def with_book(fl: FounderLifeState, book: PersonalBook) -> FounderLifeState:
    return replace(fl, books=_upsert(fl.books, book, "person_id"))


def with_foundation(fl: FounderLifeState, f: Foundation) -> FounderLifeState:
    return replace(fl, foundations=_upsert(fl.foundations, f, "person_id"))


def with_annuity(fl: FounderLifeState, a: Annuity) -> FounderLifeState:
    rest = [x for x in fl.annuities if x.person_id != a.person_id]
    if a.remaining_cents > 0:
        rest.append(a)
    return replace(fl, annuities=tuple(sorted(rest, key=lambda x: x.person_id)))
