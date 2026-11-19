"""Generation and CA (formulas.md 1-2 adapted; spec 5.1-5.2). Seeded (ADR-0002)."""

from __future__ import annotations

import pytest

from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import InvalidPersonError
from ptk.sim.people.formulas import current_ability
from ptk.sim.people.generator import generate_person, people_gen_stream
from ptk.sim.people.models import Person
from ptk.sim.rng import RngFactory
from ptk.sim.scale import ATTR_MAX, ATTR_MIN


def make(
    data: GameData,
    balance: Balance,
    role: str,
    level: str,
    *,
    seed: int = 42,
    n: int = 0,
    practice: str | None = None,
) -> Person:
    gen = people_gen_stream(RngFactory(seed), 0, 0, n)
    return generate_person(
        gen,
        data,
        balance,
        0,
        data.role(role),
        level,
        person_id=100 + n,
        city="new_york",
        jurisdiction="us_ny",
        practice=practice,
    )


def test_ca_worked_example() -> None:
    # A corporate lawyer: primaries deal structuring 15, negotiation 14, writing 13;
    # secondaries commercial awareness 12, project management 10, client care 11:
    # 10 x (3 x 42 + 33) / 12 = 132.5
    skills = {
        "deal_structuring": 15,
        "negotiation": 14,
        "writing": 13,
        "commercial_awareness": 12,
        "project_management": 10,
        "client_care": 11,
    }
    primary = ("deal_structuring", "negotiation", "writing")
    secondary = ("commercial_awareness", "project_management", "client_care")
    assert current_ability(skills, primary, secondary) == pytest.approx(132.5)


def test_same_seed_same_person(data: GameData, balance: Balance) -> None:
    a = make(data, balance, "commercial_litigation", "associate_3")
    b = make(data, balance, "commercial_litigation", "associate_3")
    assert a == b
    assert make(data, balance, "commercial_litigation", "associate_3", n=1) != a
    assert make(data, balance, "commercial_litigation", "associate_3", seed=43) != a


def test_lawyer_has_tier_familiarity_and_bar(data: GameData, balance: Balance) -> None:
    for n in range(50):
        p = make(data, balance, "ip", "associate_5", n=n)
        assert p.school_tier in {"t14", "national", "regional"}
        assert p.bar_admissions == ("us_ny",)
        assert 12 <= p.familiarity["ip"] <= 13
        assert all(1 <= p.familiarity[k] <= 6 for k in data.practice_keys if k != "ip")
        assert p.familiarity_peak == p.familiarity
        assert p.portability_bp is None
        values = [*p.skills.as_dict().values(), *p.personality.as_dict().values()]
        values += [*p.hidden.as_dict().values(), *p.familiarity.as_dict().values()]
        assert all(ATTR_MIN <= v <= ATTR_MAX for v in values)
        assert 10 <= p.potential_ability <= 200
        assert p.potential_ability >= current_ability(p.skills.as_dict(), *_role(data, "ip"))


def _role(data: GameData, key: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    role = data.role(key)
    return role.primary, role.secondary


def test_partners_draw_portability_trainees_unadmitted(data: GameData, balance: Balance) -> None:
    partner = make(data, balance, "corporate_ma", "equity_partner")
    assert partner.portability_bp is not None and 2000 <= partner.portability_bp <= 8000
    assert make(data, balance, "corporate_ma", "trainee").bar_admissions == ()


def test_paralegal_and_business_services(data: GameData, balance: Balance) -> None:
    para = make(data, balance, "paralegal", "paralegal", practice="real_estate")
    assert para.school_tier is None and para.bar_admissions == ()
    assert 10 <= para.familiarity["real_estate"] <= 12
    staff = make(data, balance, "it", "manager")
    assert all(v == 1.0 for v in staff.familiarity.as_dict().values())


def test_role_must_fit_level(data: GameData, balance: Balance) -> None:
    with pytest.raises(InvalidPersonError):
        make(data, balance, "it", "associate_1")
    with pytest.raises(InvalidPersonError):
        make(data, balance, "corporate_ma", "paralegal")


def test_ca_tracks_level_and_school_tier(data: GameData, balance: Balance) -> None:
    people = [make(data, balance, "corporate_ma", "associate_1", n=n) for n in range(400)]
    cas = {
        tier: [
            current_ability(p.skills.as_dict(), *_role(data, "corporate_ma"))
            for p in people
            if p.school_tier == tier
        ]
        for tier in ("t14", "national", "regional")
    }
    mean_all = sum(sum(v) for v in cas.values()) / len(people)
    assert 76 <= mean_all <= 84  # level mean 80
    means = {k: sum(v) / len(v) for k, v in cas.items()}
    assert means["t14"] > means["national"] > means["regional"]
    senior = [make(data, balance, "corporate_ma", "equity_partner", n=n) for n in range(100)]
    mean_senior = sum(
        current_ability(p.skills.as_dict(), *_role(data, "corporate_ma")) for p in senior
    ) / len(senior)
    assert 145 <= mean_senior <= 156  # level mean 150 plus the tier mix (+0.3)
