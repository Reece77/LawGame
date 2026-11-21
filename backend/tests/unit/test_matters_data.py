"""PT-M3a data: practices market, clients and courts (sub-task 1)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from ptk.loader import load_game_data
from ptk.sim.data_models import RATE_BANDS, GameData
from ptk.sim.errors import InvalidDataError
from tests.unit.test_data import _copy, _edit


def test_new_york_demand_base_is_the_dossiers_12_35bn(data: GameData) -> None:
    total = sum(p.demand_cents for p in data.practices)
    assert total == 1_235_000_000_000
    assert [p.key for p in data.practices][:3] == [
        "corporate_ma",
        "private_equity",
        "capital_markets",
    ]


def test_rate_card_and_practice_rates_are_integer_cents(data: GameData) -> None:
    card = data.market.rate_card
    assert card["partner"].median == 70_000 and card["junior"].median == 26_500
    for p in data.practices:
        assert sorted(p.rates) == sorted(RATE_BANDS)
        assert all(isinstance(v, int) and v > 0 for v in p.rates.values())
        assert p.rates["partner"] > p.rates["counsel"] > p.rates["senior"] > p.rates["mid"]
        assert p.rates["mid"] > p.rates["junior"] > p.rates["paralegal"]


def test_three_hundred_real_clients_and_courts(data: GameData) -> None:
    assert len(data.clients.real_clients) == 301  # PT-M7: Chrysler
    assert {c.key for c in data.courts.courts} >= {"sdny", "edny", "ddel", "del_chancery", "aaa"}


def test_every_number_in_practices_yaml_has_a_source_tag() -> None:
    text = (Path(__file__).resolve().parents[2] / "data" / "practices.yaml").read_text()
    for line in text.splitlines():
        if not line.lstrip().startswith("#") and ("demand_cents:" in line or "rates: {" in line):
            assert any(tag in line for tag in ("[A]", "[D/A]", "[D]", "[S]")), line


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d["practices"][0]["rates"].pop("junior"),
        lambda d: d["practices"][0].update(seasonality=[2.0] * 12),
        lambda d: d["practices"][0]["matter_kinds"][0].update(forums={"sdny": 1.0}),
        lambda d: d["kinds"]["deal"]["phases"][0].update(share=0.9),
        lambda d: d["tasks"][0]["skills"].update(charm=1.0),
        lambda d: d["practices"][5]["matter_kinds"][0]["forums"].update(mars=1.0),
    ],
)
def test_invalid_practices_fail_at_load(tmp_path: Path, change: object) -> None:
    data_dir = _copy(tmp_path)
    _edit(data_dir / "practices.yaml", change)  # type: ignore[arg-type]
    with pytest.raises(InvalidDataError):
        load_game_data(data_dir)


def test_invalid_clients_fail_at_load(tmp_path: Path) -> None:
    data_dir = _copy(tmp_path)
    path = data_dir / "clients.yaml"
    raw = yaml.safe_load(path.read_text())
    raw["real_clients"][0]["sector"] = "mining"
    path.write_text(yaml.safe_dump(raw))
    with pytest.raises(InvalidDataError):
        load_game_data(data_dir)
