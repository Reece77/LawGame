"""PT-M14: legal technology and AI (spec 13; ADR PT-0011, PT-0006 4).

Eras and their seeded paths, efficiency by task, adoption (investment, training, buy-in, the
rollout vote, decay), client expectations on hourly bills, fixed-fee products, learning, the
actions' rules, and the hooks' exact no-ops for a firm with no technology.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from ptk.sim.calendar import ym_to_turn
from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import TechActionError
from ptk.sim.interfaces import NO_TECH_BILLING, NO_TECH_HOURS, tech_billing, tech_hours
from ptk.sim.matters import formulas as mfx
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState
from ptk.sim.tech import adoption as ad
from ptk.sim.tech import efficiency as ef
from ptk.sim.tech.actions import (
    InvestInEra,
    LaunchProduct,
    RetireProduct,
    RolloutEra,
    SetTrainingProgramme,
    apply_tech_action,
)
from ptk.sim.tech.eras import efficiencies, era_world
from ptk.sim.tech.models import EraAdoption, FirmTech, with_era, with_firm
from tests.matters_support import grown_firm


def at(state: GameState, year: int, month: int = 1) -> GameState:
    return replace(state, turn=ym_to_turn(year, month, state.save_meta.start_ym))


def adopted(state: GameState, data: GameData, level: float, **kw: object) -> GameState:
    firm = state.tech.firm(state.player.id) or FirmTech(firm_id=state.player.id)
    for key in data.legal_eras.keys:
        era = EraAdoption(era=key, adoption=level, platform=True, subscription_bp=10000, **kw)  # type: ignore[arg-type]
        firm = with_era(firm, era, data.legal_eras.keys)
    return replace(state, tech=with_firm(state.tech, firm))


@pytest.fixture(scope="module")
def firm(data: GameData, balance: Balance) -> GameState:
    return grown_firm(data, balance, 20, 1)


def act(state: GameState, action: object, data: GameData, balance: Balance):  # type: ignore[no-untyped-def]
    rng = RngFactory(state.save_meta.master_seed)
    return apply_tech_action(
        state,
        action,  # type: ignore[arg-type]
        lambda: rng.stream(state.turn, "actions", 0),
        rng,
        data,
        balance,
    )


# --- eras ---------------------------------------------------------------------------------


def test_eras_match_history_and_seed_after(data: GameData) -> None:
    eras = data.legal_eras
    a, b, a2 = era_world(eras, 1), era_world(eras, 2), era_world(eras, 1)
    genai = eras.keys.index("genai")
    for ym in ((2005, 1), (2016, 6), (2023, 12), (2025, 12)):
        assert a.strength(genai, ym) == b.strength(genai, ym)
        assert a.market(genai, ym) == b.market(genai, ym)
    assert a.strength(genai, (2022, 11)) == 0.0  # before ChatGPT
    assert a.strength(genai, (2030, 12)) != b.strength(genai, (2030, 12))  # seeded worlds
    assert a.strength(genai, (2030, 12)) == a2.strength(genai, (2030, 12))  # same seed, same
    lo, hi = 0.65, 0.85
    assert lo <= a.strength(genai, (2034, 12)) <= hi
    # the spec: generative AI's strength is about 0.5 by 2026
    assert 0.45 <= a.strength(genai, (2026, 12)) <= 0.55
    agentic = eras.keys.index("agentic")
    assert 0.6 <= a.strength(agentic, (2032, 12)) <= 0.8


def test_eras_before_2016_are_weak_for_the_market(data: GameData) -> None:
    """What clients expect before 2016 barely moves, and pressure starts in 2016 (T1-T12)."""
    w = era_world(data.legal_eras, 3)
    for year in range(2005, 2016):
        assert w.strength(data.legal_eras.keys.index("genai"), (year, 6)) == 0.0
        assert w.strength(data.legal_eras.keys.index("contract_analysis"), (year, 6)) == 0.0


@pytest.mark.parametrize("seed", range(1, 11))
def test_fully_adopted_exposed_tasks_take_40_to_70_pct_fewer_hours_by_2030(
    seed: int, data: GameData, balance: Balance, firm: GameState
) -> None:
    state = replace(firm, save_meta=replace(firm.save_meta, master_seed=seed))
    eff = ef.full_efficiency(state, data, (2030, 12))
    exposed = [t.key for t in data.market.tasks if t.ai_exposure >= balance.tech.exposed_min]
    saving = 1 - sum(eff[t] for t in exposed) / len(exposed)
    assert 0.40 <= saving <= 0.70, (seed, saving)


# --- efficiency and the hours hook -----------------------------------------------------------


def test_no_technology_is_an_exact_no_op(data: GameData, balance: Balance, firm: GameState) -> None:
    assert tech_hours(firm, firm.player.id, data, balance) is NO_TECH_HOURS
    assert tech_billing(firm, firm.player.id, data, balance) is NO_TECH_BILLING
    later = at(firm, 2015, 12)
    assert tech_billing(later, firm.player.id, data, balance) is NO_TECH_BILLING
    assert NO_TECH_HOURS.factor({"review": 1.0}) == 1.0


def test_hours_scale_by_efficiency(data: GameData, balance: Balance, firm: GameState) -> None:
    state = adopted(at(firm, 2027), data, 1.0, rolled_out=True)
    view = tech_hours(state, state.player.id, data, balance)
    eff = ef.firm_efficiency(state, state.player.id, data)
    kind = data.market.kinds["case"]
    for phase in kind.phases:
        total = sum(phase.tasks.values())
        expected = sum(w * eff[t] for t, w in phase.tasks.items()) / total
        assert view.factor(phase.tasks) == pytest.approx(expected)
        assert view.factor(phase.tasks) < 1.0
    # advocacy is barely exposed; review is
    assert eff["review"] < eff["research"] < eff["advocacy"] <= 1.0


def test_team_output_per_hour_is_divided_by_the_factor(
    data: GameData, balance: Balance, firm: GameState
) -> None:
    """Hours a phase needs = base hours x efficiency: the same hours make 1 / factor the
    progress."""
    from ptk.sim.matters.models import HoursRecord, Matter
    from ptk.sim.matters.progress import team_month

    rel = firm.market.relationships[0]
    matter = Matter(
        id=firm.market.next_matter_id,
        firm_id=firm.player.id,
        client_id=rel.client_id,
        practice="commercial_litigation",
        kind_key="commercial_case",
        kind="case",
        name="Test case",
        opened_turn=0,
        planned_months=12,
        expected_fees_cents=60_000_000,
        hours_needed_tenths=12_000,
    )
    person = next(p for p in firm.people if p.id in set(firm.staff_ids(firm.player.id)))
    rec = HoursRecord(
        turn=0,
        person_id=person.id,
        client_id=matter.client_id,
        practice=matter.practice,
        matter_id=matter.id,
        tenths=1000,
        substantive_tenths=0,
        value_cents=0,
    )
    people = {person.id: person}
    base = team_month(matter, [rec], people, None, {}, 0, {}, data, balance)
    fast = team_month(matter, [rec], people, None, {}, 0, {}, data, balance, 0.4)
    assert fast.output == pytest.approx(base.output / 0.4)
    assert fast.hours == base.hours


def test_efficiency_formula(data: GameData) -> None:
    exposure = {t.key: t.ai_exposure for t in data.market.tasks}
    strengths = ({"review": 0.5}, {"review": 0.4, "drafting": 0.2})
    eff = efficiencies(exposure, strengths, (1.0, 0.5))
    # 1 - 0.9 x (1 - (1 - 0.5)(1 - 0.2))
    assert eff["review"] == pytest.approx(1 - 0.9 * (1 - 0.5 * 0.8))
    assert eff["drafting"] == pytest.approx(1 - 0.5 * 0.1)
    assert eff["advocacy"] == 1.0


# --- adoption -------------------------------------------------------------------------------


def test_adoption_rises_with_upkeep_and_decays_without(
    data: GameData, balance: Balance, firm: GameState
) -> None:
    state = at(firm, 2024)
    actor = state.founder_of(state.player.id)
    assert actor is not None
    out = act(state, InvestInEra(actor, "genai", 10000), data, balance)
    assert out.entries and out.entries[0].lines[0].account == "1500_ppe"
    state = act(out.state, SetTrainingProgramme(actor, 40), data, balance).state
    levels = []
    for _ in range(24):
        state, entries, _ = ad.month(state, data, balance)
        assert all(sum(x.amount for x in e.lines) == 0 for e in entries)
        state = replace(state, turn=state.turn + 1)
        levels.append(state.tech.firm(state.player.id).era("genai").adoption)  # type: ignore[union-attr]
    assert levels == sorted(levels) and levels[-1] > 0
    assert levels[-1] <= balance.tech.adoption.pilot_cap + 1e-9  # no rollout: a pilot
    state = act(state, InvestInEra(actor, "genai", 0), data, balance).state  # stop paying
    before = levels[-1]
    for _ in range(12):
        state, _, _ = ad.month(state, data, balance)
        state = replace(state, turn=state.turn + 1)
    after = state.tech.firm(state.player.id).era("genai").adoption  # type: ignore[union-attr]
    assert 0 <= after < before


def test_rollout_vote_is_seeded_and_lifts_the_cap(
    data: GameData, balance: Balance, firm: GameState
) -> None:
    state = at(firm, 2024)
    actor = state.founder_of(state.player.id)
    assert actor is not None
    state = act(state, InvestInEra(actor, "genai", 10000), data, balance).state
    a = act(state, RolloutEra(actor, "genai"), data, balance)
    b = act(state, RolloutEra(actor, "genai"), data, balance)
    assert a.state.tech == b.state.tech and a.log == b.log
    assert a.log[0].template in ("ai_rollout_passed", "ai_rollout_failed")
    with pytest.raises(TechActionError):  # too soon to ask again (or already rolled out)
        act(a.state, RolloutEra(actor, "genai"), data, balance)


def test_action_rules(data: GameData, balance: Balance, firm: GameState) -> None:
    actor = firm.founder_of(firm.player.id)
    assert actor is not None
    with pytest.raises(TechActionError):  # generative AI does not exist in 2005
        act(firm, InvestInEra(actor, "genai", 10000), data, balance)
    with pytest.raises(TechActionError):
        act(firm, SetTrainingProgramme(actor, 10_000), data, balance)
    with pytest.raises(TechActionError):  # products open at stage 3
        act(firm, LaunchProduct(actor, "corporate_ma", "private_ma", 10000), data, balance)
    big = replace(firm, firms=tuple(replace(f, stage=3) for f in firm.firms))
    out = act(big, LaunchProduct(actor, "corporate_ma", "private_ma", 9000), data, balance)
    with pytest.raises(TechActionError):  # one product a kind
        act(out.state, LaunchProduct(actor, "corporate_ma", "private_ma", 9000), data, balance)
    pid = out.state.tech.firm(firm.player.id).products[0].id  # type: ignore[union-attr]
    gone = act(out.state, RetireProduct(actor, pid), data, balance).state
    assert not gone.tech.firm(firm.player.id).products[0].active  # type: ignore[union-attr]


# --- client expectations and products ---------------------------------------------------------


def test_clients_cut_a_non_adopter_more_than_an_adopter(
    data: GameData, balance: Balance, firm: GameState
) -> None:
    state = at(firm, 2028)
    never = tech_billing(state, state.player.id, data, balance)
    leader = tech_billing(adopted(state, data, 1.0), state.player.id, data, balance)
    tasks = mfx.kind_tasks(data.market.kinds["case"])
    assert never.cut_bp(tasks) > leader.cut_bp(tasks) > 0
    assert never.cut_bp({"advocacy": 1.0}) < never.cut_bp({"review": 1.0})


def test_product_price_follows_the_market(
    data: GameData, balance: Balance, firm: GameState
) -> None:
    state = at(replace(firm, firms=tuple(replace(f, stage=3) for f in firm.firms)), 2028)
    actor = state.founder_of(state.player.id)
    assert actor is not None
    state = act(
        state, LaunchProduct(actor, "corporate_ma", "private_ma", 10000), data, balance
    ).state
    view = tech_billing(state, state.player.id, data, balance)
    assert 0.3 < view.products["private_ma"] < 1.0  # the market expects AI's saving


# --- learning -------------------------------------------------------------------------------


def test_ai_lowers_learning_and_training_restores_at_least_half(
    data: GameData, balance: Balance, firm: GameState
) -> None:
    state = adopted(at(firm, 2030), data, 1.0, rolled_out=True)
    pid = state.player.id
    mine = mfx.person_tasks(data.market.kinds["case"].phases[1].tasks, 1, data)
    without = tech_hours(state, pid, data, balance).learning(mine)
    trained = replace(state.tech.firm(pid), training_hours=balance.tech.training.full_hours)  # type: ignore[arg-type]
    with_training = tech_hours(
        replace(state, tech=with_firm(state.tech, trained)), pid, data, balance
    ).learning(mine)
    assert without < 1.0
    assert (with_training - without) >= 0.5 * (1.0 - without)


def test_product_take_up_falls_from_100_to_150_pct(balance: Balance) -> None:
    """Reece's decision on criterion 3 (2026-11-23): every client takes a product at or below
    the market's cost, none at 150%, linearly between."""
    assert ef.acceptance(6000, balance) == 1.0
    assert ef.acceptance(10000, balance) == 1.0
    assert ef.acceptance(11000, balance) == pytest.approx(0.8)
    assert ef.acceptance(12500, balance) == pytest.approx(0.5)
    assert ef.acceptance(15000, balance) == 0.0
