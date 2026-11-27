"""PT-M11's office strategies (registered in `ptk.balance.strategies.VARIANTS` with one line).

Both play steady and, in January 2007, open a London office:

- `london-lift`: a team lift of three partners and seven associates (ten lawyers) from Clifford
  Chance into a 15-seat lease, then a class of training contracts each year;
- `london-organic`: an organic start: steady's non-founding equity partner with the smallest book
  (not leaving) moves into a five-seat lease (registered as a foreign lawyer), and the office
  hires locally once it has work (a London lateral search when its lawyers are busy).

`office_run` plays one and reads the London office's P&L each month (`ptk.sim.geo.offices`):
the months from opening until its profit since opening (fit-out and lease included, as each
month's amortisation and rent) turns positive, and until its trailing twelve months' is.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field, fields
from typing import Final

from ptk.balance.game import Game, start_game
from ptk.sim.data_models import Balance, GameData
from ptk.sim.geo.actions import OfferTrainingContracts, OpenOffice
from ptk.sim.geo.offices import office_pnl
from ptk.sim.hiring.actions import OpenSearch
from ptk.sim.ledger import LedgerEntry

OPEN_YM: Final = (2007, 1)  # the brief's "opens London in 2007"
CITY: Final = "london"
PRACTICE: Final = "banking_finance"  # London's largest practice by mix (cities.yaml)
RIVAL: Final = "clifford_chance"
LIFT_PARTNERS: Final = 3
LIFT_ASSOCIATES: Final = 7  # ten lawyers in all (the brief)
LIFT_SEATS: Final = 15
ORGANIC_SEATS: Final = 5
CONTRACTS: Final = 4  # training contracts a year from the lift's office
BUSY_HOURS: Final = 140  # hours a month a London lawyer works before the office hires
WINDOW: Final = 12  # months of office profit summed (trailing twelve months)


@dataclass(slots=True)
class OfficeGame(Game):
    """A Game that keeps every month's entries (the office P&L reads them)."""

    entries: list[LedgerEntry] = field(default_factory=list)

    def _post(self, entries: Iterable[LedgerEntry]) -> None:
        entries = list(entries)
        self.entries += entries
        Game._post(self, entries)


def _office(g: Game) -> int | None:
    o = next((o for o in g.state.geo.firm_offices(1) if o.city == CITY), None)
    return o.id if o is not None else None


def _open(g: Game, how: str) -> None:
    if g.ym < OPEN_YM or g.ym[0] > OPEN_YM[0] or _office(g) is not None:
        return  # from January 2007 until it opens (a month the rules refuse, the next)
    mp = g.founder_id
    if how == "team_lift":
        g.act(
            OpenOffice(
                actor_id=mp,
                city=CITY,
                seats=LIFT_SEATS,
                how="team_lift",
                practice=PRACTICE,
                rival_key=RIVAL,
                partners=LIFT_PARTNERS,
                associates=LIFT_ASSOCIATES,
            )
        )
        return
    partners = sorted(
        (
            p
            for p in g.lawyers()
            if p.level == "equity_partner"
            and p.id != mp
            and (e := g.state.employment_of(p.id)) is not None
            and e.status == "active"
        ),
        key=lambda p: (p.book_cents, p.id),  # the partner with the smallest book (least poachable)
    )
    if partners:
        g.act(
            OpenOffice(
                actor_id=mp,
                city=CITY,
                seats=ORGANIC_SEATS,
                how="organic",
                partner_id=partners[0].id,
            )
        )


def _grow_london(g: Game) -> None:
    oid = _office(g)
    if oid is None:
        return
    office = g.state.geo.office(oid)
    assert office is not None
    if g.ym[1] == 1 and office.how == "team_lift":  # January: next year's trainees
        g.act(OfferTrainingContracts(actor_id=g.founder_id, office_id=oid, count=CONTRACTS))
    hours: dict[int, int] = {}
    for r in g.state.market.hours:
        hours[r.person_id] = hours.get(r.person_id, 0) + r.tenths
    london = [p for p in g.lawyers() if p.city == CITY]
    if not london or len(london) >= office.seats:
        return
    busy = sum(hours.get(p.id, 0) for p in london) / len(london) / 10
    if busy >= BUSY_HOURS and g.ym[1] in (3, 9):
        role = g.data.practice_role(PRACTICE).key
        g.act(OpenSearch(actor_id=g.founder_id, role=role, channel="recruiter", city=CITY))


def london_lift(g: Game) -> None:
    from ptk.balance.strategies import steady  # registered there (no import cycle)

    _open(g, "team_lift")  # before steady's moves spend the month's energy
    _grow_london(g)
    steady(g)


def london_organic(g: Game) -> None:
    from ptk.balance.strategies import steady

    _open(g, "organic")
    _grow_london(g)
    steady(g)


OFFICE_VARIANTS: Final = {"london-lift": london_lift, "london-organic": london_organic}


@dataclass(frozen=True, slots=True)
class OfficeRun:
    seed: int
    how: str
    opened: bool
    monthly: tuple[int, ...]  # the London office's profit each month from opening, cents
    lawyers: int  # London's lawyers at the end
    reached: bool = True  # PT-M18: the firm was alive in January 2007, when the office opens

    def payback_months(self) -> int | None:
        """Months from opening until the office's cumulative profit since opening is positive."""
        total = 0
        for k, v in enumerate(self.monthly):
            total += v
            if total > 0:
                return k + 1
        return None

    def months_to_profit(self) -> int | None:
        """Months from opening until the trailing twelve months' office profit is positive."""
        for k in range(len(self.monthly)):
            if sum(self.monthly[max(0, k + 1 - WINDOW) : k + 1]) > 0 and k + 1 >= WINDOW:
                return k + 1
        return None


def office_run(
    data: GameData, balance: Balance, seed: int, how: str, months: int = 60
) -> OfficeRun:
    """Steady to January 2007, then the office strategy for `months` months."""
    base = start_game(data, balance, seed)
    g = OfficeGame(**{f.name: getattr(base, f.name) for f in fields(Game)})
    script = london_lift if how == "team_lift" else london_organic
    monthly: list[int] = []
    reached = False  # PT-M18: the firm was alive in OPEN_YM (it may dissolve before)
    last = g.state.turn + (OPEN_YM[0] - g.ym[0] + 1) * 12 + months  # tunable-exempt: months
    while not g.state.ended and len(monthly) < months and g.state.turn < last:
        reached = reached or g.ym >= OPEN_YM
        script(g)
        g.entries = [e for e in g.entries if e.turn == g.state.turn]  # this month's actions
        g.turn()
        oid = _office(g)
        if oid is not None:
            monthly.append(office_pnl(g.entries, 1, g.data).get(oid, 0))
        g.entries = []
    london = [p for p in g.lawyers() if p.city == CITY]
    return OfficeRun(seed, how, bool(monthly), tuple(monthly), len(london), reached)
