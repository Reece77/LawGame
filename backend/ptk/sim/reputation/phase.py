"""Reputation's month (spec 12.1; PT-M16), in phase 10 after the partnership's stage checks:
the player's practice revenue rolls, its public outcomes and stars are counted, rivals' key
partners' departures cost them, every (firm, practice) moves toward its long-run mean, firms
that appear are seeded and firms that end are dropped, and prestige is recomputed.

Seeding (`seed`): at game creation and on the first month of a save from before PT-M16.
"""

from __future__ import annotations

from ptk.sim.data_models import PARTNER_LEVELS, Balance, GameData
from ptk.sim.fastcopy import replace
from ptk.sim.reputation import formulas as fx
from ptk.sim.reputation.models import (
    REGION_NEW_YORK,
    PublicOutcome,
    Rep,
    RepCause,
    ReputationState,
)
from ptk.sim.state import GameState

MONTHS = 12  # tunable-exempt: calendar


def seed(state: GameState, data: GameData, balance: Balance) -> GameState:
    """Every firm's starting reputation: rivals at their long-run mean (their 2005 standing),
    the player at its start values (spec 12.1)."""
    funds = fx.fundamentals(state, data)
    means = fx.means(state, data, balance, funds)
    player = state.player.id
    entries = []
    for (firm_id, practice), mean in sorted(means.items()):
        value = fx.start_value(state, firm_id, practice, balance) if firm_id == player else mean
        entries.append(Rep(firm_id, practice, REGION_NEW_YORK, fx.clamp_rep(value), mean))
    rep = replace(state.standing.reputation, entries=tuple(entries))
    state = fx.with_reputation(state, rep)
    return _prestige(state, data, balance, funds)


def _roll_value(rep: ReputationState, state: GameState, data: GameData) -> ReputationState:
    """The player's standard value of work by practice this month joins the 12-month window."""
    player = state.player.id
    month: dict[str, int] = {}
    staff = set(state.staff_ids(player))
    for h in state.market.hours:
        if h.person_id in staff and h.client_id != 0:  # 0: pro bono (no value)
            month[h.practice] = month.get(h.practice, 0) + h.value_cents
    old = dict(rep.practice_value)
    rows = []
    for p in data.practice_keys:
        window = (*old.get(p, ()), month.get(p, 0))[-MONTHS:]
        if any(window):
            rows.append((p, window))
    return replace(rep, practice_value=tuple(rows))


def _outcomes(state: GameState, balance: Balance) -> tuple[GameState, list[PublicOutcome]]:
    """The player's named matters that ended in public this month (spec 12.1)."""
    rb = balance.reputation
    player = state.player.id
    found = []
    for m in state.market.matters:
        if (
            m.firm_id == player
            and m.closed_turn == state.turn
            and m.outcome in rb.outcomes
            and not m.pro_bono
        ):
            size = min(1.0, m.expected_fees_cents / rb.big_cents)
            points = rb.outcomes[m.outcome] * size
            if points:
                found.append(PublicOutcome(state.turn, m.practice, m.id, m.outcome, points))
    return state, found


def _stars(state: GameState, data: GameData, balance: Balance) -> tuple[tuple[int, str], ...]:
    """The player's partners whose book makes them stars (spec 12.1: lateral stars)."""
    rb = balance.reputation
    staff = set(state.staff_ids(state.player.id))
    keys = set(data.practice_keys)
    return tuple(
        (p.id, p.role)
        for p in state.people
        if p.id in staff
        and p.level in PARTNER_LEVELS
        and p.role in keys
        and p.book_cents >= rb.star_book_cents
    )


def month(state: GameState, data: GameData, balance: Balance) -> GameState:
    if state.ended:
        return state
    if not state.standing.reputation.entries:
        state = seed(state, data, balance)
    rb = balance.reputation
    player = state.player.id
    rep = _roll_value(state.standing.reputation, state, data)
    state, found = _outcomes(state, balance)
    window_from = state.turn - rb.record_months
    rep = replace(rep, outcomes=tuple(o for o in (*rep.outcomes, *found) if o.turn > window_from))
    stars = _stars(state, data, balance)
    joined = [s for s in stars if s not in rep.stars]
    left = [s for s in rep.stars if s not in stars]
    rep = replace(rep, stars=stars)
    state = fx.with_reputation(state, rep)

    # pulses: (firm, practice) -> points, and the player's causes
    pulses: dict[tuple[int, str], float] = {}
    causes: list[RepCause] = []

    def add(firm_id: int, practice: str, points: float, cause: str) -> None:
        pulses[(firm_id, practice)] = pulses.get((firm_id, practice), 0.0) + points
        if firm_id == player:
            causes.append(RepCause(state.turn, practice, round(points, 2), cause))

    for o in found:
        add(player, o.practice, rb.pulse * o.points, f"matter {o.outcome}")
    for _, practice in joined:
        add(player, practice, rb.star_join, "a star partner joined")
    for _, practice in left:
        add(player, practice, -rb.star_leave, "a star partner left")

    from ptk.sim.interfaces import rival_standing

    for r in rival_standing(state, data):
        if r.departures:
            for practice, _ in r.lawyers:
                add(r.firm_id, practice, -rb.rival_departure * r.departures, "partners left")

    funds = fx.fundamentals(state, data)
    means = fx.means(state, data, balance, funds)
    table = fx.index(rep.entries)
    entries = []
    for (firm_id, practice), mean in sorted(means.items()):
        old = table.get((firm_id, practice, REGION_NEW_YORK))
        if old is None:  # a firm that appeared this month (a boutique, a successor)
            value = fx.start_value(state, firm_id, practice, balance) if firm_id == player else mean
        else:
            value = old.value + rb.speed * (mean - old.value)
        value += pulses.get((firm_id, practice), 0.0)
        entries.append(Rep(firm_id, practice, REGION_NEW_YORK, fx.clamp_rep(value), mean))
    rep = replace(rep, entries=tuple(entries))
    for c in causes:
        rep = fx.remember(rep, c, balance)
    state = fx.with_reputation(state, rep)
    return _prestige(state, data, balance, funds)


def _prestige(
    state: GameState,
    data: GameData,
    balance: Balance,
    funds: tuple[fx.Fundamentals, ...] | None = None,
) -> GameState:
    funds = fx.fundamentals(state, data) if funds is None else funds
    peps = fx.pep_percentiles(funds)
    grouped: dict[int, list[Rep]] = {}
    for e in state.standing.reputation.entries:
        grouped.setdefault(e.firm_id, []).append(e)
    prestige = tuple(
        (
            f.firm_id,
            round(
                fx.prestige_of(grouped.get(f.firm_id, ()), f, peps.get(f.firm_id, 0.0), balance), 4
            ),
        )
        for f in funds
    )
    return fx.with_reputation(state, replace(state.standing.reputation, prestige=prestige))
