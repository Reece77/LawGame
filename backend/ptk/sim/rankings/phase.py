"""When the rankings publish (spec 12.3; PT-M16), in phase 10 after reputation's month:
December records the player's fiscal year; each `tables.month` the prior year's tables;
each quarter's last month the league tables (places move reputation); each `places.month`
the associates' survey; each `directory.month` the bands (bands move reputation). Every
publication is an inbox item for the player linked to the Rankings screen, and its rows are
appended to the save's history (`published`)."""

from __future__ import annotations

from dataclasses import replace
from typing import Final

from ptk.sim.calendar import turn_to_ym
from ptk.sim.data_models import Balance, GameData
from ptk.sim.log import LogItem, inbox_item
from ptk.sim.money import format_money
from ptk.sim.rankings import lists
from ptk.sim.rankings.models import PlayerPlace, RankingsState
from ptk.sim.reputation.formulas import apply_pulses
from ptk.sim.state import GameState

DECEMBER: Final = 12  # tunable-exempt: calendar
QUARTER_ENDS: Final = (3, 6, 9, 12)  # tunable-exempt: calendar


def _with(state: GameState, rk: RankingsState) -> GameState:
    return replace(state, standing=replace(state.standing, rankings=rk))


def _published(rk: RankingsState, kind: str, turn: int) -> RankingsState:
    rows = dict(rk.published)
    rows[kind] = turn
    return replace(rk, published=tuple(sorted(rows.items())))


def _place(
    rk: RankingsState, turn: int, kind: str, practice: str | None, place: int
) -> RankingsState:
    return replace(rk, history=(*rk.history, PlayerPlace(turn, kind, practice, place)))  # type: ignore[arg-type]


def month(
    state: GameState, data: GameData, balance: Balance
) -> tuple[GameState, list[LogItem], list[tuple[str, dict[str, str | int]]]]:
    """The month's publications. Returns the state, inbox items and press triggers (a ranking
    day: the trigger and its facts) for the press."""
    year, mon = turn_to_ym(state.turn, state.save_meta.start_ym)
    rb = balance.rankings
    pid = state.player.id
    logs: list[LogItem] = []
    press: list[tuple[str, dict[str, str | int]]] = []
    rk = state.standing.rankings
    if mon == DECEMBER:
        record = lists.player_year(state, year)
        rk = replace(rk, years=(*(y for y in rk.years if y[0] != year), record)[-40:])
    state = _with(state, rk)
    rivals = lists.rivals_now(state, data)

    if mon == rb.tables.month and state.turn > 0:
        rows = lists.tables(state, year - 1, rivals, balance)
        rk = _published(replace(state.standing.rankings, tables=rows), "tables", state.turn)
        rev = next((r for r in rows if r.kind == "revenue" and r.firm_id == pid), None)
        pep = next((r for r in rows if r.kind == "pep" and r.firm_id == pid), None)
        if rev is not None:
            rk = _place(rk, state.turn, "revenue", None, rev.place)
        if pep is not None:
            rk = _place(rk, state.turn, "pep", None, pep.place)
        state = _with(state, rk)
        top = [r for r in rows if r.kind == "revenue"]
        logs.append(
            inbox_item(
                state.turn,
                pid,
                "tables_published",
                link_kind="rankings",
                link_id=0,
                year=str(year - 1),
                place=f"#{rev.place}" if rev else "not yet large enough to rank",
                pep_place=f"#{pep.place}" if pep else "not ranked",
                leader=top[0].name if top else "nobody",
                revenue=format_money(top[0].value_cents) if top else "-",
                top=lists.names_of(top, rb.news_top),
            )
        )
        if rev is not None:
            press.append(("ranking_day", {"result": f"#{rev.place} by revenue for {year - 1}"}))

    if mon in QUARTER_ENDS:
        league_rows = lists.league(state, rivals, data, balance)
        rk = _published(replace(state.standing.rankings, league=league_rows), "league", state.turn)
        lb = balance.reputation.league
        state = _with(state, rk)
        state = apply_pulses(
            state,
            (
                (
                    r.firm_id,
                    r.practice,
                    lb.top3
                    if r.place <= 3
                    else lb.top10
                    if r.place <= 10
                    else 0.0,  # tunable-exempt: the places reputation.league names
                    "a league-table place",
                )
                for r in league_rows
            ),
            balance,
        )
        rk = state.standing.rankings
        own_league = [r for r in league_rows if r.firm_id == pid]
        for r in own_league:
            rk = _place(rk, state.turn, "league", r.practice, r.place)
        state = _with(state, rk)
        if own_league:
            best = min(own_league, key=lambda r: (r.place, r.practice))
            logs.append(
                inbox_item(
                    state.turn,
                    pid,
                    "league_tables",
                    link_kind="rankings",
                    link_id=0,
                    quarter=f"Q{QUARTER_ENDS.index(mon) + 1} {year}",
                    places="; ".join(
                        f"{data.practice(r.practice).short_label} #{r.place}" for r in own_league
                    ),
                    best=f"{data.practice(best.practice).label} #{best.place}",
                )
            )

    if mon == rb.places.month:
        rows_p = lists.places(state, year, rivals, data, balance)
        rk = _published(replace(state.standing.rankings, places=rows_p), "places", state.turn)
        own = next((r for r in rows_p if r.firm_id == pid), None)
        if own is not None:
            rk = _place(rk, state.turn, "places", None, own.place)
        state = _with(state, rk)
        logs.append(
            inbox_item(
                state.turn,
                pid,
                "places_published",
                link_kind="rankings",
                link_id=0,
                year=str(year),
                place=f"#{own.place}" if own else "not surveyed (too few associates)",
                top=lists.names_of(rows_p, rb.news_top),
            )
        )

    if mon == rb.directory.month:
        firm_bands = lists.bands(state, year, rivals, data, balance)
        people = lists.people_bands(state, year, firm_bands, rivals, data, balance)
        rk = _published(
            replace(state.standing.rankings, bands=firm_bands, people=people), "bands", state.turn
        )
        state = _with(state, rk)
        points = balance.reputation.bands
        state = apply_pulses(
            state,
            (
                (b.firm_id, b.practice, points[b.band - 1], f"directory band {b.band}")
                for b in firm_bands
            ),
            balance,
        )
        rk = state.standing.rankings
        own_bands = [b for b in firm_bands if b.firm_id == pid]
        for b in own_bands:
            rk = _place(rk, state.turn, "bands", b.practice, b.band)
        for pb in people:
            if pb.firm_id == pid:
                rk = _place(rk, state.turn, "people", pb.practice, pb.band)
        state = _with(state, rk)
        named = sum(1 for p in people if p.firm_id == pid)
        logs.append(
            inbox_item(
                state.turn,
                pid,
                "directory_bands",
                link_kind="rankings",
                link_id=0,
                year=str(year),
                bands="; ".join(
                    f"{data.practice(b.practice).short_label} band {b.band}" for b in own_bands
                )
                or "no band yet",
                people=named,
                submitted="with" if (s := rk.submission) and s.year == year else "without",
            )
        )
        if own_bands:
            top_band = min(own_bands, key=lambda b: (b.band, b.practice))
            label = data.practice(top_band.practice).label
            press.append(
                (
                    "ranking_day",
                    {
                        "result": f"band {top_band.band} in {label}",
                        "practice": top_band.practice,
                    },
                )
            )
    return state, logs, press
