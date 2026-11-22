"""The rankings' lists (spec 12.3; PT-M16), each a pure function of public figures.

- **Tables** (each `tables.month`, for the prior fiscal year): revenue (an Am Law 100 and 200
  analogue, `revenue_places`) and profit per equity partner (`pep_places`), every firm whose
  revenue is at least `min_revenue_cents`, the player included once it is that large. Rivals'
  fiscal years are their December records; the player's is recorded each December.
- **League tables** (each quarter's last month, by practice and region): deals and their
  transaction value. The player's are its named matters of a deal kind (`league.kinds`) that
  closed in the quarter, valued at fees x `value_per_fee`; a rival's come from its flow: a
  quarter of its trailing revenue in the practice x `rival_deal_share`, counted in deals of the
  practice's typical size (its deal kinds' weighted median fees).
- **Directory bands** (October, 1-6 per practice and region): the score is the firm's
  reputation; the player's adds its key matters (the last year's public outcomes) and its March
  submission, or loses `no_submission` without one (a weak submission loses bands). Bands by
  `thresholds`; below band 6 a firm is not ranked. Individuals: rivals' real notables by their
  standing; the player's partners who led `people_min_matters` public matters in three years.
- **Best places to work** (`places.month`): the player's associates' morale, hours, pay against
  the scale and training (partners per associate); rivals' from their personality and hours.

Ties break by firm id. Ported in part from backend/tst/sim/modes/rankings.py @ 80a3807 (Tech
Startup Tycoon): the list-building pattern (measure, order, cut) and the tie rule; changed:
Partner Track's lists and measures.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Final

from ptk.sim.calendar import turn_to_ym
from ptk.sim.data_models import PARTNER_LEVELS, Balance, GameData
from ptk.sim.hiring.pay import on_scale
from ptk.sim.interfaces import RivalStandingView, rival_standing
from ptk.sim.rankings.models import BandRow, LeagueRow, PersonBand, PlacesRow, TableRow
from ptk.sim.reputation.formulas import reputation
from ptk.sim.reputation.models import REGION_NEW_YORK
from ptk.sim.state import GameState

QUARTER: Final = 3  # tunable-exempt: calendar
YEAR: Final = 12  # tunable-exempt: calendar
PCT: Final = 100.0  # tunable-exempt: the 0-100 scales
BP: Final = 10_000  # tunable-exempt: basis points
UTIL_FREE: Final = 0.85  # tunable-exempt: utilisation a survey takes as normal


def _ranked[T](rows: Iterable[tuple[float, int, T]], n: int | None = None) -> list[T]:
    """Best first by value, ties by firm id; the first n."""
    ordered = [r for _, _, r in sorted(rows, key=lambda x: (-x[0], x[1]))]
    return ordered if n is None else ordered[:n]


# --- Tables ------------------------------------------------------------------------------------


def player_year(state: GameState, year: int) -> tuple[int, int, int, int]:
    """The player's fiscal year at December's month end: (year, revenue, lawyers, PEP)."""
    from ptk.sim.reputation.formulas import player_pep

    pid = state.player.id
    revenue = sum(
        m.fees_cents
        for m in state.billing.months
        if m.firm_id == pid and turn_to_ym(m.turn, state.save_meta.start_ym)[0] == year
    )
    lawyers = len(state.staff_ids(pid))
    pep = player_pep(state, pid)
    return (year, revenue, lawyers, round(pep) if pep else 0)


def tables(
    state: GameState, year: int, rivals: tuple[RivalStandingView, ...], balance: Balance
) -> tuple[TableRow, ...]:
    tb = balance.rankings.tables
    entries: list[tuple[int, str, int, int, int]] = []  # firm, name, revenue, lawyers, pep
    for r in rivals:
        rec = next((y for y in r.years if y[0] == year), None)
        if rec is not None:
            entries.append((r.firm_id, r.name, rec[1], rec[2], rec[3]))
    mine = next((y for y in state.standing.rankings.years if y[0] == year), None)
    if mine is not None:
        entries.append((state.player.id, state.player.name, mine[1], mine[2], mine[3]))
    big = [e for e in entries if e[2] >= tb.min_revenue_cents]
    revenue = _ranked(((float(e[2]), e[0], e) for e in big), tb.revenue_places)
    pep = _ranked(((float(e[4]), e[0], e) for e in big if e[4] > 0), tb.pep_places)
    rows = [TableRow(year, "revenue", i + 1, e[0], e[1], e[2], e[3]) for i, e in enumerate(revenue)]
    rows += [TableRow(year, "pep", i + 1, e[0], e[1], e[4], e[3]) for i, e in enumerate(pep)]
    return tuple(rows)


# --- League tables -----------------------------------------------------------------------------


def league_practices(data: GameData, balance: Balance) -> tuple[str, ...]:
    kinds = set(balance.rankings.league.kinds)
    return tuple(p.key for p in data.practices if any(k.kind in kinds for k in p.matter_kinds))


def typical_deal_cents(practice: str, data: GameData, balance: Balance) -> float:
    kinds = set(balance.rankings.league.kinds)
    deals = [k for k in data.practice(practice).matter_kinds if k.kind in kinds]
    weight = sum(k.weight for k in deals)
    return sum(k.weight * k.median_cents for k in deals) / weight


def league(
    state: GameState, rivals: tuple[RivalStandingView, ...], data: GameData, balance: Balance
) -> tuple[LeagueRow, ...]:
    """This quarter's tables (state.turn is the quarter's last month)."""
    lb = balance.rankings.league
    kinds = set(lb.kinds)
    since = state.turn - QUARTER
    pid = state.player.id
    rows: list[LeagueRow] = []
    for practice in league_practices(data, balance):
        size = typical_deal_cents(practice, data, balance)
        entries: list[tuple[float, int, tuple[int, str, int, int]]] = []
        mine = [
            m
            for m in state.market.matters
            if m.firm_id == pid
            and m.practice == practice
            and m.kind in kinds
            and m.outcome in ("closed", "done", "won", "settled")
            and m.closed_turn is not None
            and since < m.closed_turn <= state.turn
        ]
        if mine:
            value = round(sum(m.expected_fees_cents for m in mine) * lb.value_per_fee)
            entries.append((float(value), pid, (pid, state.player.name, len(mine), value)))
        for r in rivals:
            total = r.total_lawyers
            if total <= 0:
                continue
            fees = r.revenue_12m_cents / 4 * r.in_practice(practice) / total * lb.rival_deal_share
            deals = round(fees / size)
            if deals <= 0:
                continue
            value = round(fees * lb.value_per_fee)
            entries.append((float(value), r.firm_id, (r.firm_id, r.name, deals, value)))
        ordered = _ranked(entries)
        for i, (fid, name, deals, value) in enumerate(ordered):
            if i < lb.places or fid == pid:
                rows.append(
                    LeagueRow(state.turn, practice, REGION_NEW_YORK, i + 1, fid, name, deals, value)
                )
    return tuple(rows)


# --- Directory bands ---------------------------------------------------------------------------


def band_for(score: float, balance: Balance) -> int | None:
    for i, threshold in enumerate(balance.rankings.directory.thresholds):
        if score >= threshold:
            return i + 1
    return None


def key_matter_points(state: GameState, practice: str, balance: Balance) -> float:
    """The player's key matters: the last year's public outcome points in the practice, toward
    the directory's key_matters points (a third of the full record in a year scores them all)."""
    rb = balance.reputation
    since = state.turn - YEAR
    points = sum(
        o.points
        for o in state.standing.reputation.outcomes
        if o.practice == practice and o.turn > since
    )
    full = rb.record_full / 3
    return balance.rankings.directory.key_matters * max(0.0, min(1.0, points / full))


def submission_points(state: GameState, year: int, balance: Balance) -> float:
    db = balance.rankings.directory
    sub = state.standing.rankings.submission
    if sub is None or sub.year != year:
        return -db.no_submission
    return db.submission_points * sub.strength


def bands(
    state: GameState,
    year: int,
    rivals: tuple[RivalStandingView, ...],
    data: GameData,
    balance: Balance,
) -> tuple[BandRow, ...]:
    pid = state.player.id
    names = {r.firm_id: r.name for r in rivals} | {pid: state.player.name}
    sub = submission_points(state, year, balance)
    rows = []
    for practice in data.practice_keys:
        scored = []
        for fid in sorted(names):
            score = reputation(state, fid, practice, balance)
            if fid == pid:
                score += key_matter_points(state, practice, balance) + sub
            band = band_for(score, balance)
            if band is not None:
                scored.append((band, fid, score))
        for band, fid, score in sorted(scored):
            rows.append(
                BandRow(year, practice, REGION_NEW_YORK, fid, names[fid], band, round(score, 2))
            )
    return tuple(rows)


def people_bands(
    state: GameState,
    year: int,
    firm_bands: tuple[BandRow, ...],
    rivals: tuple[RivalStandingView, ...],
    data: GameData,
    balance: Balance,
) -> tuple[PersonBand, ...]:
    """Named individuals (spec 12.3): rivals' real notables by their standing; the player's
    partners with a public record of leading matters in their practice."""
    from ptk.sim.interfaces import rival_key_people

    db = balance.rankings.directory
    out: list[PersonBand] = []
    for r in rivals:
        if r.kind != "real":
            continue
        for v in rival_key_people(state, r.firm_id, data, balance):
            if v.notable_standing is not None and v.notable_standing in db.standing_band:
                band = db.standing_band[v.notable_standing]
                out.append(PersonBand(year, v.practice, v.person_id, r.firm_id, band))
    pid = state.player.id
    staff = set(state.staff_ids(pid))
    since = state.turn - 3 * YEAR
    led: dict[int, int] = {}
    for m in state.market.matters:
        if (
            m.firm_id == pid
            and m.lead_id in staff
            and m.closed_turn is not None
            and m.closed_turn > since
            and m.outcome in balance.reputation.outcomes
            and not m.pro_bono
        ):
            led[m.lead_id] = led.get(m.lead_id, 0) + 1
    mine = {(b.practice): b.band for b in firm_bands if b.firm_id == pid}
    for person in state.people:
        n = led.get(person.id, 0)
        if (
            person.id not in staff
            or person.level not in PARTNER_LEVELS
            or n < db.people_min_matters
        ):
            continue
        firm_band = mine.get(person.role, len(db.thresholds))
        band = firm_band + db.people_offset - (n - db.people_min_matters)
        band = max(1, min(len(db.thresholds), band))
        out.append(PersonBand(year, person.role, person.id, pid, band))
    return tuple(sorted(out, key=lambda b: (b.practice, b.band, b.person_id)))


# --- Best places to work -----------------------------------------------------------------------


def player_survey(state: GameState, data: GameData, balance: Balance) -> float | None:
    """The player's associates' survey score 0-100, or None with too few associates."""
    pb = balance.rankings.places
    pid = state.player.id
    staff = set(state.staff_ids(pid))
    associates = [p for p in state.people if p.id in staff and on_scale(p.level)]
    partners = sum(1 for p in state.people if p.id in staff and p.level in PARTNER_LEVELS)
    if len(associates) < pb.min_associates:
        return None
    morale = [m for p in associates if (m := state.person_state(p.id).morale) is not None]
    m = sum(morale) / len(morale) / PCT if morale else 0.5
    months = [x for x in state.billing.months if x.firm_id == pid]
    lawyers = max(1, len(staff))
    tenths = sum(x.billable_tenths for x in months)
    hours = tenths / 10 / lawyers * YEAR / max(1, len(months))  # tunable-exempt: tenths
    h = max(0.0, min(1.0, (pb.hours_worst - hours) / (pb.hours_worst - pb.hours_best)))
    pay = max(
        0.0, min(1.0, (state.player.pay_policy.pct_bp / BP - 0.9) / 0.2)
    )  # tunable-exempt: lag 90% scores 0, lead 110% scores 1
    t = min(1.0, partners / len(associates) * 10 / pb.training_full)  # tunable-exempt: per ten
    w = pb.weights
    return PCT * (w["morale"] * m + w["hours"] * h + w["pay"] * pay + w["training"] * t)


def places(
    state: GameState,
    year: int,
    rivals: tuple[RivalStandingView, ...],
    data: GameData,
    balance: Balance,
) -> tuple[PlacesRow, ...]:
    pb = balance.rankings.places
    entries: list[tuple[float, int, tuple[int, str, float]]] = []
    mine = player_survey(state, data, balance)
    pid = state.player.id
    if mine is not None:
        entries.append((mine, pid, (pid, state.player.name, mine)))
    for r in rivals:
        if r.associates < pb.min_associates:
            continue
        base = pb.rival_base.get(r.personality, PCT / 2)
        score = max(0.0, base - pb.rival_utilisation * PCT * max(0.0, r.utilisation - UTIL_FREE))
        entries.append((score, r.firm_id, (r.firm_id, r.name, score)))
    ordered = _ranked(entries)
    return tuple(
        PlacesRow(year, i + 1, fid, name, round(score, 2))
        for i, (fid, name, score) in enumerate(ordered)
        if i < pb.places or fid == pid
    )


def rivals_now(state: GameState, data: GameData) -> tuple[RivalStandingView, ...]:
    return rival_standing(state, data)


def names_of(rows: Iterable[TableRow | LeagueRow | PlacesRow], n: int) -> str:
    return ", ".join(f"{r.place}. {r.name}" for r in list(rows)[:n]) or "nobody yet"


def by_practice[T: (LeagueRow, BandRow)](rows: Iterable[T]) -> Mapping[str, list[T]]:
    out: dict[str, list[T]] = {}
    for r in rows:
        out.setdefault(r.practice, []).append(r)
    return out
