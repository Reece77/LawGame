"""Helpers for PT-M3a tests: games with clients, and a grown firm built directly."""

from __future__ import annotations

from dataclasses import replace

from ptk.sim.calendar import turn_to_ym
from ptk.sim.data_models import Balance, GameData
from ptk.sim.decisions import Decisions
from ptk.sim.hiring.models import PersonState
from ptk.sim.hiring.phases import firm_pay_cents, starting_pay
from ptk.sim.matters.intake import with_relationship
from ptk.sim.matters.market import base_monthly_demand, firm_reputation, player_share, wallets
from ptk.sim.matters.models import Relationship
from ptk.sim.people.generator import generate_person, people_gen_stream
from ptk.sim.people.models import Employment
from ptk.sim.rng import RngFactory
from ptk.sim.setup import new_game
from ptk.sim.state import GameState, with_person_states
from ptk.sim.turn import TurnResult, advance_turn

GROW_SEARCH = 900  # people_gen search id for test-built staff (never a real search's)
# A grown firm's mix by practice: (practice, partners, associates by level)
MIX = (
    (
        "corporate_ma",
        3,
        ("associate_1", "associate_2", "associate_4", "associate_6", "associate_7"),
    ),
    ("private_equity", 1, ("associate_2", "associate_5")),
    ("banking_finance", 1, ("associate_1", "associate_4")),
    ("commercial_litigation", 2, ("associate_1", "associate_3", "associate_5", "associate_7")),
    ("white_collar", 1, ("associate_2", "associate_6")),
    ("ip", 1, ("associate_3",)),
    ("employment", 1, ("associate_2",)),
    ("real_estate", 1, ("associate_4",)),
)


def game(
    data: GameData, balance: Balance, seed: int = 1, scenario: str = "biglaw_spinout"
) -> GameState:
    return new_game(
        name="t",
        firm_name="Founders LLP",
        master_seed=seed,
        scenario_id=scenario,
        difficulty="standard",
        data=data,
        balance=balance,
    ).state


def play(
    state: GameState,
    data: GameData,
    balance: Balance,
    turns: int,
    seed: int = 1,
    *,
    write_events: bool = False,
) -> tuple[GameState, list[TurnResult]]:
    """`write_events` (PT-M6): write each turn's events with the mock adapter, as a save does
    (round trips against a save); without it events stay unwritten and have no effect."""
    results = []
    for _ in range(turns):
        result = advance_turn(
            state, Decisions(), RngFactory(seed), balance, data, {}, answer_critical=write_events
        )
        results.append(result)
        state = result.new_state
        if write_events:
            from tests.hiring_helpers import mock_events

            state = mock_events(state, balance, data)
    return state, results


def grown_firm(
    data: GameData,
    balance: Balance,
    lawyers: int,
    seed: int = 1,
    per_lawyer_cents: int = 75_000_000,
) -> GameState:
    """The group-lift firm grown to `lawyers` lawyers by MIX, on panels worth its capacity.

    Partners join as income partners; new clients are added (largest expected fees first,
    none above $3m a year) with a new partner as relationship partner in their practice,
    until expected fees reach the firm's capacity at standard value."""
    state = game(data, balance, seed, "group_lift")
    rng = RngFactory(seed)
    firm = state.player.id
    people, employments = list(state.people), list(state.employments)
    n = 0
    while sum(1 for p in people if data.role(p.role).kind == "lawyer") < lawyers:
        practice, partners, associates = MIX[n % len(MIX)]
        for level in ("income_partner",) * partners + associates:
            if sum(1 for p in people if data.role(p.role).kind == "lawyer") >= lawyers:
                break
            pid = max(p.id for p in people) + 1
            person = generate_person(
                people_gen_stream(rng, 0, GROW_SEARCH, pid),
                data,
                balance,
                0,
                data.practice_role(practice),
                level,
                person_id=pid,
                city="new_york",
                jurisdiction="us_ny",
            )
            people.append(person)
            employments.append(Employment(id=pid, person_id=pid, firm_id=firm, start_turn=0))
        n += 1
    state = replace(state, people=tuple(people), employments=tuple(employments))
    state = starting_pay(state, balance, data)
    # panels worth the firm's capacity (about $750k a lawyer a year at standard value)
    target = lawyers * per_lawyer_cents
    demand = base_monthly_demand(data)
    shares = wallets(state.market.clients, data, balance)
    reps = {p: firm_reputation(state, firm, p) for p in data.practice_keys}
    have = {r.client_id for r in state.market.relationships}
    partners = [p for p in state.people if p.level in ("income_partner", "equity_partner")]
    total = 0.0
    market = state.market
    for rel in market.relationships:
        total += _expected(market.client(rel.client_id), rel, shares, demand, reps, data, balance)
    i = 0
    for client in sorted(market.clients, key=lambda c: (-c.revenue_bn, c.id)):
        if total >= target:
            break
        if client.id in have:
            continue
        partner = partners[i % len(partners)]
        home = data.role(partner.role).practice
        assert home is not None
        rel = Relationship(
            client_id=client.id,
            firm_id=firm,
            score=60.0,
            partner_id=partner.id,
            practices=(home,),
            since_turn=0,
            last_instructed_turn=0,
        )
        fees = _expected(client, rel, shares, demand, reps, data, balance)
        if not 0 < fees <= 300_000_000:
            continue
        market = with_relationship(market, rel)
        total += fees
        i += 1
    return replace(state, market=market)


def _expected(client, rel, shares, demand, reps, data, balance) -> float:  # type: ignore[no-untyped-def]
    keys = data.practice_keys
    return sum(
        shares.wallet(client.id, keys.index(p), demand)
        * 12
        * player_share(client, rel, p, reps[p], False, data, balance)
        for p in rel.practices
    )


def top_up(state: GameState, data: GameData, balance: Balance, like: GameState) -> GameState:
    """Replace each lawyer who left since `like` with a new one of the same role and level
    (keeps a test firm at its size; resignations run at PT-M1b's ~18% a year)."""
    staff = set(state.staff_ids(state.player.id))
    gone = [p for p in like.people if p.id in set(like.staff_ids(like.player.id)) - staff]
    if not gone:
        return state
    rng = RngFactory(state.save_meta.master_seed)
    people, employments = list(state.people), list(state.employments)
    moods: list[PersonState] = []
    for old in gone:
        pid = max(p.id for p in people) + 1
        person = generate_person(
            people_gen_stream(rng, state.turn, GROW_SEARCH, pid),
            data,
            balance,
            state.turn,
            data.role(old.role),
            old.level,
            person_id=pid,
            city="new_york",
            jurisdiction="us_ny",
        )
        people.append(person)
        firm = state.player
        salary = firm_pay_cents(
            data,
            balance,
            old.level,
            turn_to_ym(state.turn, state.save_meta.start_ym),
            firm.home_city,
            firm.pay_policy,
        )
        employments.append(
            Employment(
                id=max(e.id for e in employments) + 1,
                person_id=pid,
                firm_id=firm.id,
                start_turn=state.turn,
                salary_cents=salary,
            )
        )
        moods.append(PersonState(person_id=pid, morale=balance.morale.new_hire))
    state = replace(state, people=tuple(people), employments=tuple(employments))
    return with_person_states(state, moods)
