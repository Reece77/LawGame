"""The founding partner build (spec 2.1; formulas.md 5 adapted). Seeded."""

from __future__ import annotations

import pytest

from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import InvalidFounderError
from ptk.sim.people.founder import FounderSpec, build_founder, preview_founder
from ptk.sim.people.models import Person, current_ability
from ptk.sim.setup import new_game
from ptk.sim.streams import RngFactory


def build(data: GameData, balance: Balance, spec: FounderSpec, seed: int = 5) -> Person:
    return build_founder(
        spec,
        RngFactory(seed),
        data,
        balance,
        0,
        person_id=1,
        founder_index=0,
        city="new_york",
        jurisdiction="us_ny",
    )


@pytest.mark.parametrize(
    "background",
    [
        "biglaw_ma_partner",
        "trial_lawyer",
        "patent_litigator",
        "regional_generalist",
        "government_lawyer",
    ],
)
def test_each_background_builds_a_partner(
    data: GameData, balance: Balance, background: str
) -> None:
    bg = data.background(background)
    assert bg is not None
    p = build(data, balance, FounderSpec(background=background))
    assert p.role == data.practice_role(bg.home_practice).key and p.level == "equity_partner"
    assert p.is_founder and p.founding_partner and p.background == background
    assert 135 <= current_ability(p, data) <= 160
    assert max(p.skills.as_dict().values()) <= balance.founder.skill_cap
    assert p.age(0) == balance.founder.default_age
    lo, hi = bg.book_cents
    assert lo <= p.book_cents <= hi and p.book_cents % balance.founder.book_round_to_cents == 0
    for key in data.practice_keys:
        f = p.familiarity[key]
        assert 15 <= f <= 17 if key in bg.familiar_practices else 1 <= f <= 6
    assert p.bar_admissions == tuple(sorted({"us_ny", *bg.bar_admissions}))
    assert p.strain == balance.strain.founder_start
    assert p.portability_bp is not None
    assert build(data, balance, FounderSpec(background=background)) == p  # seeded


def test_skills_lean_the_background_way(data: GameData, balance: Balance) -> None:
    ma = build(data, balance, FounderSpec(background="biglaw_ma_partner"))
    trial = build(data, balance, FounderSpec(background="trial_lawyer"))
    assert ma.skills["negotiation"] > trial.skills["negotiation"]
    assert trial.skills["advocacy"] > ma.skills["advocacy"]
    patent = build(data, balance, FounderSpec(background="patent_litigator"))
    assert patent.skills["technical"] == 18 and "uspto" in patent.bar_admissions


def test_book_ranges_differ_by_background(data: GameData, balance: Balance) -> None:
    books = {
        seed: build(data, balance, FounderSpec(background="biglaw_ma_partner"), seed).book_cents
        for seed in range(20)
    }
    assert len(set(books.values())) > 3  # drawn, not fixed
    gov = build(data, balance, FounderSpec(background="government_lawyer"))
    assert gov.book_cents == 20_000_000  # $0.2M (spec 2.1)


def test_choices_are_honoured(data: GameData, balance: Balance) -> None:
    spec = FounderSpec(
        background="trial_lawyer",
        personality_preset="operator",
        age=50,
        first_name="Ada",
        last_name="Lovelace",
        interests=("policy", "ai"),
        work_style="seller",
    )
    p = build(data, balance, spec)
    assert (p.first_name, p.last_name, p.age(0)) == ("Ada", "Lovelace", 50)
    assert p.personality["professionalism"] == 17 and p.interests == ("policy", "ai")
    assert p.work_style == "seller"


@pytest.mark.parametrize(
    ("spec", "problem"),
    [
        (FounderSpec(background="astronaut"), "unknown background"),
        (FounderSpec(background="trial_lawyer", age=30), "age must be"),
        (FounderSpec(background="trial_lawyer", allocation={"advocacy": 10}), "spend all"),
        (FounderSpec(background="trial_lawyer", allocation={"advocacy": 111}), "only 110"),
        (
            FounderSpec(background="trial_lawyer", allocation={"advocacy": 15, "writing": 95}),
            "above the cap",
        ),
        (FounderSpec(background="trial_lawyer", personality_preset="saint"), "preset"),
    ],
)
def test_invalid_builds_are_refused(
    data: GameData, balance: Balance, spec: FounderSpec, problem: str
) -> None:
    preview = preview_founder(spec, data, balance)
    assert any(problem in p for p in preview.problems), preview.problems
    with pytest.raises(InvalidFounderError):
        build(data, balance, spec)


def test_new_game_people(data: GameData, balance: Balance) -> None:
    game = new_game(
        name="t",
        firm_name="F",
        master_seed=9,
        scenario_id="biglaw_spinout",
        difficulty="standard",
        data=data,
        balance=balance,
    )
    state = game.state
    assert [p.id for p in state.people] == [1, 2, 3, 4]
    founder, cofounder, assoc_a, assoc_b = state.people
    assert founder.is_founder and founder.background == "biglaw_ma_partner"
    assert cofounder.founding_partner and not cofounder.is_founder
    assert cofounder.background == "trial_lawyer" and cofounder.age(0) == 46
    assert (assoc_a.role, assoc_a.level) == ("corporate_ma", "associate_4")  # PT-M7a
    assert (assoc_b.role, assoc_b.level) == ("commercial_litigation", "associate_2")
    assert 10 <= assoc_a.strain <= 30 and not assoc_a.founding_partner
    assert state.staff_ids(1) == (1, 2, 3, 4)
    own = state.reveal(1, 1)
    assert own is not None and own.record("advocacy").hw == 0
    staff = state.reveal(1, 3)
    assert staff is not None and 0 < staff.record("advocacy").hw < balance.reveal.initial_hw.skill
    solo = new_game(
        name="s",
        firm_name="S",
        master_seed=9,
        scenario_id="solo_founder",
        difficulty="standard",
        data=data,
        balance=balance,
    ).state
    assert [(p.role, p.level) for p in solo.people] == [
        ("corporate_ma", "equity_partner"),
        ("paralegal", "paralegal"),
    ]
    assert solo.people[0].background == "regional_generalist"
