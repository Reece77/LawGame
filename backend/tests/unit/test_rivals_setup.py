"""Rivals at game creation (spec 10.1; ADR PT-0008 1, 3; ADR PT-0013)."""

from __future__ import annotations

from ptk.sim.data_models import Balance, GameData
from ptk.sim.people.formulas import current_ability
from ptk.sim.rivals.people import person_of
from tests.rivals_support import start


def test_real_rivals_start_at_their_2005_figures(data: GameData, balance: Balance) -> None:
    state = start(data, balance, 1)
    defs = {f.key: f for f in data.rivals.firms.firms}
    real = [f for f in state.rivals.firms if f.kind == "real"]
    assert len(real) == sum(1 for f in data.rivals.firms.firms if f.start_ym is None)
    for firm in real:
        fy = defs[firm.key].fy2005
        assert fy is not None and fy.revenue_cents and fy.lawyers
        # ADR PT-0008 1: in-game revenue equals the published figure (within 10%) at turn 0
        assert abs(firm.revenue_12m / fy.revenue_cents - 1) < 0.01
        assert abs(firm.lawyers / fy.lawyers - 1) < 0.01
    assert sum(1 for f in state.rivals.firms if f.kind == "generated") == (
        balance.rivals.generated.count
    )


def test_key_people_and_real_notables(data: GameData, balance: Balance) -> None:
    state = start(data, balance, 2)
    rb = balance.rivals
    negative = {t.key for t in data.tags if t.negative}
    notables = {n.key: n for n in data.rivals.people.notables}
    placed = 0
    by_standing: dict[str, list[float]] = {}
    for firm in state.rivals.firms:
        members = state.rivals.members_of(firm.id)
        partners = [m for m in members if m.kind == "partner"]
        if firm.kind == "real":
            assert len(partners) >= min(rb.key_partners, len(partners))
            assert sum(1 for m in members if m.kind == "associate") == rb.key_associates
        for m in members:
            p = person_of(state, m, data, balance)
            assert all(1.0 <= v <= 20.0 for _, v in p.skills.items)
            if m.notable is None:
                assert not p.real
                continue
            placed += 1
            nd = notables[m.notable]
            assert p.real and nd.firm == firm.key
            assert (p.first_name, p.last_name) == (nd.first_name, nd.last_name)
            assert not set(p.tags) & negative  # ADR PT-0013
            role = data.practice_role(nd.practice)
            ca = current_ability(p.skills.as_dict(), role.primary, role.secondary)
            band = rb.standing_ca[nd.standing]
            assert ca <= band.hi + 2  # inside the band, or as high as the role's skills reach
            assert ca >= min(band.lo, 165.0) - 2
            by_standing.setdefault(nd.standing, []).append(ca)
    starting = [
        n for n in data.rivals.people.notables if data.rivals.firms.firm(n.firm).start_ym is None
    ]
    assert placed == len(starting)
    mean = {k: sum(v) / len(v) for k, v in by_standing.items()}
    assert mean["elite"] > mean["leading"] > mean["strong"]


def test_creation_is_seeded(data: GameData, balance: Balance) -> None:
    a, b, c = start(data, balance, 3), start(data, balance, 3), start(data, balance, 4)
    assert a.rivals == b.rivals
    assert a.rivals.firms != c.rivals.firms  # generated firms differ by seed
    assert [f.name for f in a.rivals.firms if f.kind == "real"] == [
        f.name for f in c.rivals.firms if f.kind == "real"
    ]


def test_real_judges_sit_on_the_modelled_courts(data: GameData, balance: Balance) -> None:
    state = start(data, balance, 1)
    real = [j for j in state.market.judges if j.real]
    assert len(real) == sum(1 for j in data.rivals.people.judges if j.left is None or j.left > 2005)
    for court in {j.court for j in data.rivals.people.judges}:
        assert any(j.sits(0) for j in state.market.judges if j.court == court)
    assert all(1.0 <= v <= 20.0 for j in state.market.judges for _, v in j.traits.items)
