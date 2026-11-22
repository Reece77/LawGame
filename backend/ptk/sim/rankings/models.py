"""PT-M16 rankings state (spec 12.3): the spring revenue and profit-per-partner tables, the
quarterly league tables, October's directory bands (firms and individuals), the March
submission and the associates' Best places to work survey. All public.

The state keeps each list's latest edition (the engine reads it: bands raise appeal and
recruiting for a year) and the player's own history; every edition is also appended to the
save's `ranking_entry` table when published (`published` names the lists published in a turn),
so the Rankings screen's history never makes the live state grow.

Ported in part from backend/tst/sim/modes/models.py @ 80a3807 (Tech Startup Tycoon): TST's
`Ranking` (one list's place) became the rows below, with Partner Track's lists.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

type TableKind = Literal["revenue", "pep"]
type ListKind = Literal["revenue", "pep", "league", "bands", "people", "places"]


@dataclass(frozen=True, slots=True)
class TableRow:
    """A place in the spring tables for fiscal `year` (an Am Law 100 and 200 analogue)."""

    year: int
    kind: TableKind
    place: int
    firm_id: int
    name: str
    value_cents: int  # revenue, or profit per equity partner
    lawyers: int


@dataclass(frozen=True, slots=True)
class LeagueRow:
    """A quarter's league table by practice and region: deal counts and values."""

    turn: int  # the quarter's last month
    practice: str
    region: int
    place: int
    firm_id: int
    name: str
    deals: int
    value_cents: int  # the deals' transaction value


@dataclass(frozen=True, slots=True)
class BandRow:
    """October's directory band (1-6) for a firm in a practice and region."""

    year: int
    practice: str
    region: int
    firm_id: int
    name: str
    band: int
    score: float  # the directory's score (public: reputation, key matters, the submission)


@dataclass(frozen=True, slots=True)
class PersonBand:
    """A named individual's directory band (spec 12.3)."""

    year: int
    practice: str
    person_id: int
    firm_id: int
    name: str
    band: int


@dataclass(frozen=True, slots=True)
class PlacesRow:
    """Best places to work (spec 12.3): the associates' survey."""

    year: int
    place: int
    firm_id: int
    name: str
    score: float  # 0-100


@dataclass(frozen=True, slots=True)
class Submission:
    """The March-April directory submission (spec 12.3): up to five matters to showcase and
    referees (clients) to name; each referee spent a little of the relationship."""

    year: int
    turn: int
    matter_ids: tuple[int, ...]
    referee_ids: tuple[int, ...]
    strength: float  # 0-1, public: from the matters' public outcomes and the referees


@dataclass(frozen=True, slots=True)
class PlayerPlace:
    """The player's place in one list (the Rankings screen's own history)."""

    turn: int
    kind: ListKind
    practice: str | None
    place: int  # a band for bands and people; a place otherwise


@dataclass(frozen=True, slots=True)
class RankingsState:
    tables: tuple[TableRow, ...] = ()  # the latest spring's, by (kind, place)
    league: tuple[LeagueRow, ...] = ()  # the latest quarter's, by (practice, region, place)
    bands: tuple[BandRow, ...] = ()  # the latest October's, by (practice, region, band, firm)
    people: tuple[PersonBand, ...] = ()  # the latest October's, by (practice, band, person)
    places: tuple[PlacesRow, ...] = ()  # the latest survey's, by place
    submission: Submission | None = None  # this year's, once made
    history: tuple[PlayerPlace, ...] = ()  # the player's places, oldest first
    # the player's fiscal years as recorded each December: (year, revenue, lawyers, pep)
    years: tuple[tuple[int, int, int, int], ...] = ()
    published: tuple[tuple[str, int], ...] = ()  # (list kind, turn) last published, by kind

    def published_turn(self, kind: str) -> int | None:
        return next((t for k, t in self.published if k == kind), None)

    def band(self, firm_id: int, practice: str, region: int = 0) -> int | None:
        return next(
            (
                b.band
                for b in self.bands
                if b.firm_id == firm_id and b.practice == practice and b.region == region
            ),
            None,
        )


EMPTY_RANKINGS = RankingsState()
