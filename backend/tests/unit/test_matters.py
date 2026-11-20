"""PT-M3a engine: clients, intake, conflicts, staffing, outcomes, judges, relationships."""

from __future__ import annotations

import inspect
import statistics
from dataclasses import replace

import numpy as np
import pytest

from ptk.sim.actions import apply_action
from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import MatterActionError, NotFoundError, OverCapacityError, StaffingError
from ptk.sim.matters import formulas as fx
from ptk.sim.matters.actions import (
    AssignToMatter,
    ChooseForum,
    Introduce,
    RemoveFromMatter,
    RespondSettlement,
    SeekWaiver,
    SetConflictChecks,
)
from ptk.sim.matters.conflicts import conflict_index, open_conflicts
from ptk.sim.matters.intake import intake, key_clients, open_checked, with_matter
from ptk.sim.matters.market import monthly_demand
from ptk.sim.matters.models import HoursRecord, Matter, SettlementOffer
from ptk.sim.matters.phase import intake_and_staffing
from ptk.sim.matters.progress import assign_judge, resolve, surface_hidden_conflicts, team_month
from ptk.sim.matters.setup import new_market
from ptk.sim.matters.staffing import fee_earners, month_hours, staff_matter
from ptk.sim.people.models import Person
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState
from tests.matters_support import game, play

CASES = 1000  # acceptance: printed over 1,000 seeded cases


def _act(
    state: GameState, action: object, data: GameData, balance: Balance, seq: int = 1
) -> GameState:
    return apply_action(
        state,
        action,
        seq=seq,
        rng=RngFactory(7),
        balance=balance,
        data=data,
        ledger_balances={},  # type: ignore[arg-type]
    ).state


def _matter(state: GameState, **kw: object) -> Matter:
    rel = state.market.relationships[0]
    base = Matter(
        id=state.market.next_matter_id,
        firm_id=state.player.id,
        client_id=rel.client_id,
        practice="commercial_litigation",
        kind_key="commercial_case",
        kind="case",
        name="Test case",
        opened_turn=state.turn,
        planned_months=12,
        expected_fees_cents=60_000_000,
        hours_needed_tenths=12_000,
        originator_id=rel.partner_id,
        court="sdny",
        stakes_cents=300_000_000,
    )
    return replace(base, **kw)  # type: ignore[arg-type]


# --- Formulas --------------------------------------------------------------------------------


def test_normal_cdf_and_poisson_inversion() -> None:
    assert fx.normal_cdf(0.0) == pytest.approx(0.5, abs=1e-12)
    assert fx.normal_cdf(1.959963984540054) == pytest.approx(0.975, abs=1e-9)
    assert fx.poisson_from_uniform(0.0, 0.9) == 0
    gen = RngFactory(3).stream(0, "misc", 1)
    draws = [fx.poisson_from_uniform(2.5, float(u)) for u in gen.random(20_000)]
    assert statistics.mean(draws) == pytest.approx(2.5, abs=0.05)
    p_tail, fee_tail, cdf = fx.tail_split(100.0, 1.0, 100.0)
    assert p_tail == pytest.approx(0.5) and cdf == pytest.approx(0.5)
    assert fee_tail == pytest.approx(fx.normal_cdf(1.0), abs=1e-12)  # E[X; X>=median]/E[X]


def test_judge_never_enters_p_win() -> None:
    assert list(inspect.signature(fx.p_win).parameters) == ["q_us", "q_them", "merits", "outcomes"]


# --- Setup -------------------------------------------------------------------------------------


def test_client_universe_is_seeded_and_complete(data: GameData, balance: Balance) -> None:
    a, b = game(data, balance, seed=11), game(data, balance, seed=11)
    assert a.market == b.market
    c = game(data, balance, seed=12)
    assert c.market.clients[:300] != a.market.clients[:300]  # panels and GCs differ by seed
    assert [x.name for x in c.market.clients[:300]] == [x.name for x in a.market.clients[:300]]
    m = a.market
    assert len(m.clients) == 300 + balance.clients.generated_count
    assert sum(1 for x in m.clients if x.real) == 300
    assert len({x.name for x in m.clients}) == len(m.clients)
    # PT-M5: courts with real judges (judges.yaml) seat them; the others stay generated
    real_courts = {j.court for j in data.rivals.people.judges}
    generated = [j for j in m.judges if j.court not in real_courts]
    assert len(generated) == sum(c.judges for c in data.courts.courts if c.key not in real_courts)
    assert all(j.real or j.from_turn > 0 for j in m.judges if j.court in real_courts)
    for j in m.judges:
        assert all(1.0 <= v <= 20.0 for _, v in j.traits.items)
        assert set(j.traits.keys()) == {t.key for t in data.courts.judge_traits}


def test_founders_books_come_with_their_clients(data: GameData, balance: Balance) -> None:
    for seed in (1, 2, 3):
        state = game(data, balance, seed=seed)
        rels = state.market.relationships
        founders = {p.id: p for p in state.people if p.founding_partner}
        assert rels and {r.partner_id for r in rels} <= set(founders)
        for r in rels:
            assert (
                balance.books.start_relationship.lo
                <= r.score
                <= balance.books.start_relationship.hi
            )
        # a year's fees at standard value come out near the books
        played, _ = play(state, data, balance, 12, seed)
        fees = sum(r.fees_12m for r in played.market.relationships)
        books = sum(p.book_cents for p in founders.values())
        assert 0.35 * books < fees < 1.5 * books, (seed, fees, books)


def test_new_market_without_founders_book_has_no_panels(data: GameData, balance: Balance) -> None:
    state = game(data, balance)
    poor = replace(state, people=tuple(replace(p, book_cents=0) for p in state.people))
    market = new_market(poor, state.player.id, RngFactory(1), data, balance)
    assert market.relationships == ()


# --- Demand and intake ---------------------------------------------------------------------------


def test_monthly_demand_is_seeded_and_near_the_base(data: GameData, balance: Balance) -> None:
    state = game(data, balance)
    rng = RngFactory(5)
    assert monthly_demand(rng, 3, state, data) == monthly_demand(rng, 3, state, data)
    year = [monthly_demand(rng, t, state, data) for t in range(12)]
    total = sum(sum(m) for m in year)
    assert total == pytest.approx(1_235_000_000_000, rel=0.05)


def test_intake_is_seeded_and_named_matters_meet_the_threshold(
    data: GameData, balance: Balance
) -> None:
    state = game(data, balance, seed=4)
    a, _ = play(state, data, balance, 18, seed=4)
    b, _ = play(state, data, balance, 18, seed=4)
    assert a.market.matters == b.market.matters and a.market.relationships == b.market.relationships
    assert a.market.matters
    key = key_clients(a.market, a.player.id, balance)
    for m in a.market.matters:
        floor = (
            balance.matters.key_named_min_cents
            if m.client_id in key
            else balance.matters.named_min_cents
        )
        assert m.expected_fees_cents >= min(floor, balance.matters.key_named_min_cents)


def test_a_client_we_are_adverse_to_sends_no_work(data: GameData, balance: Balance) -> None:
    state = game(data, balance)
    target = state.market.relationships[0].client_id
    other = state.market.relationships[1]
    against = _matter(state, client_id=other.client_id, adverse_client_id=target, waiver=True)
    state = replace(state, market=with_matter(state.market, against))
    result = intake(state, state.player.id, RngFactory(1), state.market.demand_cents, data, balance)
    assert all(cid != target for cid, _ in result.flow_tenths)


# --- Conflicts (ADR PT-0009) ---------------------------------------------------------------------


def _conflicted(data: GameData, balance: Balance) -> tuple[GameState, Matter]:
    state = game(data, balance)
    current, other = state.market.relationships[0], state.market.relationships[1]
    matter = _matter(state, client_id=other.client_id, adverse_client_id=current.client_id)
    index = conflict_index(state.market, state.player.id, state.turn, balance)
    state, logs = open_checked(state, matter, index, data, balance, frozenset())
    opened = state.market.matter(matter.id)
    assert opened is not None
    assert [i.kind for i in logs] == ["matter_conflicted"]
    return state, opened


def test_conflicted_matter_waits_and_a_waiver_opens_it(data: GameData, balance: Balance) -> None:
    state, matter = _conflicted(data, balance)
    assert matter.status == "conflicted" and not matter.team
    assert open_conflicts(state.market, state.player.id, state.turn, balance) == []
    founder = state.founder_of(state.player.id)
    assert founder is not None
    granted = refused = 0
    for seq in range(1, 41):
        after = _act(state, SeekWaiver(founder, matter.id), data, balance, seq)
        m = after.market.matter(matter.id)
        assert m is not None
        if m.status == "open":
            granted += 1
            assert m.waiver and m.team
        else:
            refused += 1
            assert m.status == "declined"
        assert open_conflicts(after.market, after.player.id, after.turn, balance) == []
    assert granted and refused  # a chance, from the relationship and the GC
    with pytest.raises(NotFoundError):
        _act(state, SeekWaiver(founder, 999), data, balance)


def test_advance_waiver_covers_later_conflicts(data: GameData, balance: Balance) -> None:
    state, matter = _conflicted(data, balance)
    founder = state.founder_of(state.player.id)
    assert founder is not None
    for seq in range(1, 200):
        after = _act(state, SeekWaiver(founder, matter.id, advance=True), data, balance, seq)
        if after.market.matter(matter.id).status == "open":  # type: ignore[union-attr]
            break
    else:
        pytest.fail("no advance waiver in 200 tries")
    assert after.market.relationship(matter.adverse_client_id, after.player.id).advance_waiver  # type: ignore[arg-type,union-attr]
    again = _matter(after, client_id=matter.client_id, adverse_client_id=matter.adverse_client_id)
    index = conflict_index(after.market, after.player.id, after.turn, balance)
    after, _ = open_checked(after, again, index, data, balance, frozenset())
    assert after.market.matter(again.id).status == "open"  # type: ignore[union-attr]


def test_skipped_checks_hide_a_conflict_that_can_surface(data: GameData, balance: Balance) -> None:
    state = game(data, balance)
    founder = state.founder_of(state.player.id)
    assert founder is not None
    state = _act(state, SetConflictChecks(founder, False), data, balance)
    current, other = state.market.relationships[0], state.market.relationships[1]
    matter = _matter(state, client_id=other.client_id, adverse_client_id=current.client_id)
    index = conflict_index(state.market, state.player.id, state.turn, balance)
    state, _ = open_checked(state, matter, index, data, balance, frozenset())
    m = state.market.matter(matter.id)
    assert m is not None and m.status == "open" and m.hidden_conflict and not m.checked
    assert open_conflicts(state.market, state.player.id, state.turn, balance) == []
    sure = balance.model_copy(
        update={"conflicts": balance.conflicts.model_copy(update={"hidden_surface_bp": 10000})}
    )
    market, logs = surface_hidden_conflicts(state, RngFactory(1), sure)
    gone = market.matter(matter.id)
    assert gone is not None and gone.outcome == "disqualified"
    assert [i.kind for i in logs] == ["matter_disqualified"]
    assert market.relationship(current.client_id, state.player.id).score < current.score  # type: ignore[union-attr]


# --- Staffing ------------------------------------------------------------------------------------


def test_default_staffing_and_over_capacity_refusal(data: GameData, balance: Balance) -> None:
    state = game(data, balance)
    matter = staff_matter(state, _matter(state), data, balance)
    state = replace(state, market=with_matter(state.market, matter))
    assert matter.lead_id is not None and matter.member(matter.lead_id).role == "lead"  # type: ignore[union-attr]
    lead = state.person(matter.lead_id)
    assert data.role(lead.role).practice == "commercial_litigation"
    founder = state.founder_of(state.player.id)
    assert founder is not None
    outsider = next(e for e in fee_earners(state, 1, data, balance) if matter.member(e.id) is None)
    with pytest.raises(OverCapacityError):
        _act(state, AssignToMatter(founder, matter.id, outsider.id, 390), data, balance)
    with pytest.raises(StaffingError):
        _act(state, RemoveFromMatter(founder, matter.id, matter.lead_id), data, balance)
    after = _act(state, AssignToMatter(founder, matter.id, outsider.id, 20), data, balance)
    staffed = after.market.matter(matter.id)
    assert (
        staffed is not None and staffed.member(outsider.id) is not None and not staffed.auto_staff
    )


def test_month_hours_cap_named_work_and_absorb_flow(data: GameData, balance: Balance) -> None:
    state = game(data, balance)
    founder = state.founder_of(state.player.id)
    assert founder is not None
    huge = replace(
        _matter(state, practice="corporate_ma", kind="deal", kind_key="public_ma", court=None),
        lead_id=founder,
        team=(),
    )
    huge = replace(huge, team=(replace_member(founder, 3000),))
    state = replace(state, market=with_matter(state.market, huge))
    month = month_hours(
        state, 1, {(state.market.relationships[0].client_id, "corporate_ma"): 5000}, data, balance
    )
    earner = next(e for e in fee_earners(state, 1, data, balance) if e.id == founder)
    named = sum(r.tenths for r in month.records if r.person_id == founder and r.matter_id)
    assert named <= balance.matters.max_load * earner.capacity - earner.other
    flow = [r for r in month.records if r.matter_id is None]
    assert flow and all(r.practice == "corporate_ma" for r in flow)
    for pid, w in month.work.items():
        assert w.total_tenths - w.other_tenths == sum(
            r.tenths for r in month.records if r.person_id == pid
        )


def replace_member(person_id: int, tenths: int):  # type: ignore[no-untyped-def]
    from ptk.sim.matters.models import TeamMember

    return TeamMember(person_id=person_id, role="lead", planned_tenths=tenths)


# --- Outcomes (acceptance) -----------------------------------------------------------------------


def _with_skills(person: Person, value: float, practice: str) -> Person:
    skills = person.skills.updated(dict.fromkeys(person.skills.keys(), value))
    fam = person.familiarity.updated({practice: 20.0})
    return replace(person, skills=skills, familiarity=fam, strain=10.0, tags=())


def _team(state: GameState, person: Person, matter: Matter, data: GameData, balance: Balance):  # type: ignore[no-untyped-def]
    record = HoursRecord(0, person.id, matter.client_id, matter.practice, matter.id, 1000, 0, 0)
    return team_month(matter, [record], {person.id: person}, None, {}, 0, {}, data, balance)


def test_a_stronger_team_wins_at_least_15_points_more(
    data: GameData, balance: Balance, capsys: pytest.CaptureFixture[str]
) -> None:
    state = game(data, balance)
    base = state.person(2)
    weak, strong = (_with_skills(base, v, "commercial_litigation") for v in (10.0, 13.0))
    out = balance.outcomes
    wins = {10.0: 0, 13.0: 0}
    for i in range(CASES):
        gen = RngFactory(2024).stream(0, "misc", i)
        merits = out.merits_sd * float(gen.standard_normal())
        opposing = out.opposing_mean + out.opposing_sd * float(gen.standard_normal())
        u = float(gen.random())
        for level, person in ((10.0, weak), (13.0, strong)):
            m = _matter(state, merits=merits, opposing_quality=opposing, lead_id=person.id)
            team = _team(state, person, m, data, balance)
            m = replace(m, craft_hours=team.craft * team.hours, craft_weight=team.hours)
            outcome, _ = resolve(m, 1.0, u, {person.id: person}, data, balance)
            wins[level] += outcome == "won"
    weak_rate, strong_rate = wins[10.0] / CASES, wins[13.0] / CASES
    with capsys.disabled():
        print(
            f"\nlitigation wins over {CASES} seeded cases: effective skill 10 "
            f"{weak_rate:.1%}, 13 {strong_rate:.1%}"
        )
    assert strong_rate - weak_rate >= 0.15


def test_an_over_strained_team_makes_twice_the_errors(
    data: GameData, balance: Balance, capsys: pytest.CaptureFixture[str]
) -> None:
    state = game(data, balance)
    base = _with_skills(state.person(2), 10.0, "commercial_litigation")
    rested = replace(base, strain=10.0)
    strained = replace(base, strain=85.0, burnout_since=0, last_burnout_turn=0)
    counts = {}
    for label, person in (("rested", rested), ("strained", strained)):
        m = _matter(state, lead_id=person.id)
        team = _team(state, person, m, data, balance)
        p = fx.error_chance(team.skill, team.strain_mult, team.cowboy, team.shortfall, balance)
        gen = RngFactory(77).stream(0, "misc", 0)
        counts[label] = int(np.sum(gen.random(20_000) < p))
    with capsys.disabled():
        print(
            f"\nerrors over 20,000 matter-months: rested {counts['rested']}, "
            f"strain 85 {counts['strained']}"
        )
    assert counts["strained"] >= 2 * counts["rested"]


def test_swapping_the_judge_moves_path_and_time_never_the_side(
    data: GameData, balance: Balance
) -> None:
    state = game(data, balance)
    person = _with_skills(state.person(2), 11.0, "commercial_litigation")
    judges = [j for j in state.market.judges if j.court == "sdny" and j.sits(0)]
    moved = 0
    for i in range(200):
        gen = RngFactory(9).stream(0, "misc", i)
        base = _matter(
            state,
            merits=float(gen.standard_normal()),
            opposing_quality=12 + 2 * float(gen.standard_normal()),
            lead_id=person.id,
        )
        u = float(gen.random())
        results = set()
        months = set()
        for k, judge in enumerate(judges):
            m = assign_judge(base, state.market, (k + 0.5) / len(judges), data, balance)
            assert m.judge_id == judge.id
            months.add((m.planned_months, m.hours_needed_tenths))
            team = team_month(
                m,
                [HoursRecord(0, person.id, m.client_id, m.practice, m.id, 1000, 0, 0)],
                {person.id: person},
                judge,
                {},
                0,
                {},
                data,
                balance,
            )
            m = replace(m, craft_hours=team.craft * team.hours, craft_weight=team.hours)
            q = fx.case_quality(team.craft, 1.0, person.hidden["big_moments"], balance.outcomes)
            p = fx.p_win(q, m.opposing_quality, m.merits, balance.outcomes)
            results.add((resolve(m, 1.0, u, {person.id: person}, data, balance)[0], round(p, 12)))
        assert len(results) == 1  # same side, same chance, whatever the judge
        moved += len(months) > 1
    assert moved == 200  # but the path and timing move


def test_settlement_offer_accept_closes_the_case(data: GameData, balance: Balance) -> None:
    state = game(data, balance)
    founder = state.founder_of(state.player.id)
    assert founder is not None
    m = staff_matter(state, _matter(state), data, balance)
    m = replace(m, settlement=SettlementOffer(fraction_bp=6000, made_turn=0, expires_turn=1))
    state = replace(state, market=with_matter(state.market, m))
    after = _act(state, RespondSettlement(founder, m.id, True), data, balance)
    closed = after.market.matter(m.id)
    assert closed is not None and closed.outcome == "settled" and closed.status == "closed"
    rejected = _act(state, RespondSettlement(founder, m.id, False), data, balance)
    assert rejected.market.matter(m.id).settlement is None  # type: ignore[union-attr]
    with pytest.raises(MatterActionError):
        _act(rejected, RespondSettlement(founder, m.id, True), data, balance)


def test_forum_choice_only_before_the_case_starts(data: GameData, balance: Balance) -> None:
    state = game(data, balance)
    founder = state.founder_of(state.player.id)
    assert founder is not None
    m = _matter(state)
    state = replace(state, market=with_matter(state.market, m))
    moved = _act(state, ChooseForum(founder, m.id, "del_chancery"), data, balance)
    assert moved.market.matter(m.id).court == "del_chancery"  # type: ignore[union-attr]
    assert moved.market.matter(m.id).planned_months < m.planned_months  # type: ignore[union-attr]
    with pytest.raises(MatterActionError):
        _act(state, ChooseForum(founder, m.id, "icc"), data, balance)  # not a forum for it
    later = replace(state, turn=state.turn + 1)
    with pytest.raises(MatterActionError):
        _act(later, ChooseForum(founder, m.id, "del_chancery"), data, balance)


# --- Relationships and cross-selling -------------------------------------------------------


def test_introductions_add_practices_or_cost_relationship(data: GameData, balance: Balance) -> None:
    state = game(data, balance, scenario="group_lift")
    founder = state.founder_of(state.player.id)
    assert founder is not None
    rel = next(r for r in state.market.relationships if "white_collar" not in r.practices)
    colleague = next(p for p in state.people if data.role(p.role).practice == "white_collar")
    made = failed = 0
    for seq in range(1, 31):
        after = _act(
            state,
            Introduce(founder, rel.client_id, colleague.id, "white_collar"),
            data,
            balance,
            seq,
        )
        new = after.market.relationship(rel.client_id, after.player.id)
        assert new is not None
        if "white_collar" in new.practices:
            made += 1
        else:
            failed += 1
            assert new.score == pytest.approx(max(0.0, rel.score + balance.cross_sell.failure))
            with pytest.raises(MatterActionError):  # cooldown
                _act(
                    after,
                    Introduce(founder, rel.client_id, colleague.id, "white_collar"),
                    data,
                    balance,
                )
    assert made and failed


def test_relationships_move_and_stay_in_range(data: GameData, balance: Balance) -> None:
    state = game(data, balance, seed=3)
    played, _ = play(state, data, balance, 24, seed=3)
    before = {r.client_id: r.score for r in state.market.relationships}
    after = {r.client_id: r.score for r in played.market.relationships}
    # PT-M4: a partner who leaves takes their portable clients with them
    fp = played.partnership.of(played.player.id)
    assert fp is not None
    followed = {c for d in fp.departures for c, _ in d.follows}
    assert after.keys() <= before.keys() and before.keys() - after.keys() <= followed
    assert before != after
    assert all(0.0 <= v <= 100.0 for v in after.values())
    assert any(o.cents > 0 for o in played.market.originations)
    assert {o.person_id for o in played.market.originations} <= {
        r.partner_id for r in played.market.relationships
    } | {m.originator_id for m in played.market.matters} | {d.person_id for d in fp.departures}


def test_hours_feed_growth_and_morale_inputs(data: GameData, balance: Balance) -> None:
    state = game(data, balance)
    month = intake_and_staffing(state, RngFactory(1), data, balance)
    worked = [w for w in month.work.values() if w.total_tenths > 0]
    assert worked and all(w.substantive_tenths <= w.total_tenths for w in worked)
    assert {p for w in worked for p, _ in w.practice_tenths} <= set(data.practice_keys)


# --- Real people (ADR PT-0013) -------------------------------------------------------------


def test_no_negative_item_names_a_real_person(data: GameData, balance: Balance) -> None:
    state = game(data, balance, seed=6)
    state = replace(state, people=tuple(replace(p, real=True) for p in state.people))
    played, results = play(state, data, balance, 24, seed=6)
    names = {f"{p.first_name} {p.last_name}" for p in played.people if p.real}
    negative = {"deadline_missed", "matter_disqualified", "waiver_refused", "introduction_failed"}
    for r in results:
        for item in r.log_items:
            if item.kind in negative:
                assert not any(n in item.message for n in names)
    judges = {f"{j.first_name} {j.last_name}" for j in played.market.judges if j.real}
    assert judges  # PT-M5: real judges sit on the modelled courts
    for r in results:
        for item in r.log_items:
            if item.kind in negative:
                assert not any(n in item.message for n in judges)
