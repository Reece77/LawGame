from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

import pytest
import yaml

from ptk.loader import load_balance, load_game_data
from ptk.sim.data_models import LEVELS, Balance, GameData
from ptk.sim.errors import InvalidDataError
from ptk.sim.ledger import ENGINE_ACCOUNTS
from tests.conftest import DATA_DIR

V1_PRACTICES = (
    "corporate_ma",
    "private_equity",
    "capital_markets",
    "banking_finance",
    "restructuring",
    "commercial_litigation",
    "white_collar",
    "ip",
    "employment",
    "real_estate",
)
BUSINESS_SERVICES = (
    "finance",
    "human_resources",
    "it",
    "marketing_bd",
    "operations",
    "records_and_conflicts",
)


def test_engine_accounts_exist(data: GameData) -> None:
    codes = {a.code for a in data.accounts}
    assert set(ENGINE_ACCOUNTS) <= codes


def test_client_book_is_separate(data: GameData) -> None:
    client = [a for a in data.accounts if a.book == "client"]
    assert client and all(a.code.startswith("C") for a in client)


def test_default_scenario_starts_in_2005(data: GameData) -> None:
    scenario = data.scenario("biglaw_spinout")
    assert scenario is not None and scenario.start_ym == (2005, 1)


# --- PT-M1a people data -----------------------------------------------------------------------


def test_skills_are_in_group_order(data: GameData) -> None:
    groups = [s.group for s in data.skills]
    order = ["legal", "client", "working", "leadership", "business_services"]
    assert sorted(groups, key=order.index) == groups
    assert {"stamina", "technology", "judgment_of_talent", "advocacy"} <= set(data.skill_keys)


def test_v1_practices_and_roles(data: GameData) -> None:
    assert data.practice_keys == V1_PRACTICES
    lawyers = [r for r in data.roles if r.kind == "lawyer"]
    assert [r.practice for r in lawyers] == list(V1_PRACTICES)
    assert [r.key for r in data.roles if r.kind == "paralegal"] == ["paralegal"]
    assert tuple(r.key for r in data.roles if r.kind == "business_services") == BUSINESS_SERVICES


def test_levels_follow_the_spec(balance: Balance) -> None:
    levels = balance.people.levels
    assert tuple(levels) == LEVELS
    assert levels["associate_1"].ca.mean == 80 and levels["associate_3"].ca.mean == 100
    assert levels["associate_6"].ca.mean == 120 and levels["equity_partner"].ca.sd == 15
    assert levels["associate_1"].capacity_hours == 2300
    assert levels["counsel"].billable_target_hours == 1700
    chain = ["associate_1"]
    while (nxt := levels[chain[-1]].next_level) is not None:
        chain.append(nxt)
    assert chain == [f"associate_{k}" for k in range(1, 9)]
    for level in levels.values():  # home practice familiarity 10-16 (brief, sub-task 2)
        if level.home_familiarity is not None:
            assert 10 <= level.home_familiarity.lo <= level.home_familiarity.hi <= 16


def test_school_tier_weights_name_drawable_tiers(data: GameData, balance: Balance) -> None:
    drawable = {t.key for t in data.school_tiers if t.available_in == "v1"}
    assert set(balance.people.school_tier_weights) == drawable


def test_tags_carry_the_new_tags_and_negatives(data: GameData) -> None:
    keys = [t.key for t in data.tags]
    new = ["rainmaker", "grinder", "client_whisperer", "cowboy", "rule_bender", "lifer"]
    assert keys[-7:] == [*new, "free_agent"]
    negative = {t.key for t in data.tags if t.negative}
    assert negative == {"credit_taker", "toxic_high_performer", "cowboy", "rule_bender"}


def test_backgrounds_spend_exactly_the_points(data: GameData, balance: Balance) -> None:
    assert len([b for b in data.backgrounds if b.selectable]) == 5
    for bg in data.backgrounds:
        assert sum(bg.default_allocation.values()) == balance.founder.skill_points, bg.key


def test_starting_staff_roles_fit_their_levels(data: GameData, balance: Balance) -> None:
    for scenario in data.scenarios:
        for staff in scenario.starting_staff:
            kind = balance.people.levels[staff.level].kind
            assert data.role(staff.role).kind == kind


# --- invalid data fails at load ----------------------------------------------------------------


def _copy(tmp_path: Path) -> Path:
    target = tmp_path / "data"
    shutil.copytree(DATA_DIR, target)
    return target


def _edit(path: Path, change: Callable[[dict[str, object]], None]) -> None:
    doc = yaml.safe_load(path.read_text())
    change(doc)
    path.write_text(yaml.safe_dump(doc))


def test_invalid_account_fails_at_load(tmp_path: Path) -> None:
    data_dir = _copy(tmp_path)
    (data_dir / "accounts.yaml").write_text(
        "accounts:\n  - { code: C1000_x, name: x, type: asset }\n"  # client code, firm book
    )
    with pytest.raises(InvalidDataError):
        load_game_data(data_dir)


def _first(key: str) -> Callable[[dict[str, object]], dict[str, object]]:
    def get(doc: dict[str, object]) -> dict[str, object]:
        items = doc[key]
        assert isinstance(items, list)
        first = items[0]
        assert isinstance(first, dict)
        return first

    return get


@pytest.mark.parametrize(
    ("file", "change"),
    [
        ("roles.yaml", lambda d: _first("roles")(d).update(primary=["no_such_skill"])),
        ("roles.yaml", lambda d: _first("roles")(d).update(practice=None)),
        ("roles.yaml", lambda d: _first("roles")(d).update(practice="tax")),
        ("tags.yaml", lambda d: _first("tags")(d)["boost"]["when"][0].update(attr="charm")),
        ("tags.yaml", lambda d: _first("tags")(d).update(excludes=["nope"])),
        ("backgrounds.yaml", lambda d: _first("backgrounds")(d).update(home_practice="tax")),
        ("backgrounds.yaml", lambda d: _first("backgrounds")(d).update(book_cents=[5, 1])),
        ("backgrounds.yaml", lambda d: _first("backgrounds")(d).update(bar_admissions=["mars"])),
        ("skills.yaml", lambda d: d["skills"].append(dict(_first("skills")(d)))),
        (
            "practices.yaml",
            lambda d: d["practices"].append({"key": "tax", "label": "Tax", "short_label": "Tax"}),
        ),
        ("scenarios.yaml", lambda d: _first("scenarios")(d).update(home_jurisdiction="mars")),
        ("names.yaml", lambda d: d.update(names={})),
    ],
)
def test_invalid_people_data_fails_at_load(
    tmp_path: Path, file: str, change: Callable[[dict[str, object]], None]
) -> None:
    data_dir = _copy(tmp_path)
    _edit(data_dir / file, change)
    with pytest.raises(InvalidDataError):
        load_game_data(data_dir)


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d["people"]["levels"].pop("counsel"),
        lambda d: d["people"]["levels"]["associate_1"].update(next_level="associate_99"),
        lambda d: d["people"]["levels"]["staff"].update(home_familiarity=[10, 12]),
        lambda d: d["strain"].update(burnout_exit=90),
        lambda d: d["reveal"]["strength"].pop("interview"),
        lambda d: d["founder"].update(default_age=70),
    ],
)
def test_invalid_balance_fails_at_load(
    tmp_path: Path, change: Callable[[dict[str, object]], None]
) -> None:
    data_dir = _copy(tmp_path)
    _edit(data_dir / "balance.yaml", change)
    with pytest.raises(InvalidDataError):
        load_balance(data_dir)
