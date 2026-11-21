"""Authority, pitches and reports (PT-M8; TST formulas.md 24, 27.1, 27.2; ADR-0015)."""

from __future__ import annotations

from dataclasses import asdict, replace

import pytest

from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import OneOffError
from ptk.sim.matters.actions import SeekWaiver
from ptk.sim.org.authority import (
    AUTHORITY_KINDS,
    ONE_OFF_KINDS,
    apply_authorised,
    quality,
)
from ptk.sim.org.pitches import AnswerPitch, answer_pitch, chance
from ptk.sim.org.reports import report_requests, report_text
from ptk.sim.partnership.actions import ProposePartner
from ptk.sim.rng import RngFactory
from tests.seats_support import led_firm, mp, run, steady


@pytest.fixture(scope="module")
def led(data: GameData, balance: Balance):  # type: ignore[no-untyped-def]
    b = steady(balance)
    return led_firm(data, b), b


def test_no_one_off_is_within_authority(led, data: GameData) -> None:  # type: ignore[no-untyped-def]
    state, b = led
    assert not (AUTHORITY_KINDS & ONE_OFF_KINDS)
    holder = next(h.person_id for h in state.leadership.holders if h.seat == "cfo")
    rng = RngFactory(1)
    with pytest.raises(OneOffError):
        apply_authorised(
            state,
            ProposePartner(holder, holder, "equity"),  # type: ignore[arg-type]
            lambda: rng.stream(0, "misc"),
            b,
            data,
        )


def test_a_waiver_adverse_to_a_key_client_is_a_one_off(led, data: GameData) -> None:  # type: ignore[no-untyped-def]
    from ptk.sim.matters.intake import key_clients, with_matter

    state, b = led
    state, _, _ = run(state, data, b, 2)  # trailing fees make key clients
    firm = state.player.id
    keys = sorted(key_clients(state.market, firm, b))
    if not keys:
        pytest.skip("no key clients in the fixture")
    matter = next(m for m in state.market.matters if m.firm_id == firm)
    held = replace(matter, status="conflicted", adverse_client_id=keys[0])
    state = replace(state, market=with_matter(state.market, held))
    gc = next(h.person_id for h in state.leadership.holders if h.seat == "general_counsel")
    rng = RngFactory(1)
    with pytest.raises(OneOffError):
        apply_authorised(state, SeekWaiver(gc, held.id), lambda: rng.stream(0, "misc"), b, data)


def test_decision_quality_bounds(balance: Balance) -> None:
    assert quality(1.0, balance) == pytest.approx(0.6)
    assert quality(20.0, balance) == pytest.approx(0.98)
    assert quality(10.0, balance) == pytest.approx(0.85)
    assert chance(10.0, balance) == pytest.approx(balance.pitches.base)
    assert chance(60.0, balance) == pytest.approx(balance.pitches.chance_clamp[1])


def test_holders_act_and_replay_identically(led, data: GameData) -> None:  # type: ignore[no-untyped-def]
    state, b = led
    a, results_a, _ = run(state, data, b, 7)
    again, results_b, _ = run(state, data, b, 7)
    decisions_a = [asdict(d) for r in results_a for d in r.seat_decisions]
    decisions_b = [asdict(d) for r in results_b for d in r.seat_decisions]
    assert decisions_a, "nobody acted under authority in seven months"
    assert decisions_a == decisions_b  # recomputed on replay (ADR-0015 5)
    assert a.leadership == again.leadership
    acted = {d["action"] for d in decisions_a}
    assert acted <= AUTHORITY_KINDS
    # every decision belongs to a holder of that seat
    for d in decisions_a:
        assert d["person_id"] in {h.person_id for h in state.leadership.holders} | {
            u.leader_id for u in state.org.units
        }


def test_at_most_one_pitch_a_quarter_per_holder_and_answers(led, data: GameData) -> None:  # type: ignore[no-untyped-def]
    state, b = led
    after, _, balances = run(state, data, b, 12)
    pitches = after.leadership.pitches
    assert pitches, "no pitches in a year"
    seen: set[tuple[int, int]] = set()
    for p in pitches:
        key = (p.person_id, p.made_turn // 3)
        assert key not in seen
        seen.add(key)
        assert p.made_turn % 3 == 0
        assert p.low <= p.central <= p.high
    pending = [p for p in pitches if p.status == "pending"]
    if not pending:
        pytest.skip("every pitch lapsed this year")
    p = pending[0]
    holder = p.person_id
    rng = RngFactory(after.save_meta.master_seed)
    declined = answer_pitch(
        after,
        AnswerPitch(mp(after), p.id, "decline"),
        rng,
        lambda: rng.stream(after.turn, "actions", 1),
        b,
        data,
        balances,
    )
    assert declined.state.leadership.pitch(p.id).status == "declined"  # type: ignore[union-attr]
    assert any(n.person_id == holder and n.points < 0 for n in declined.state.org.nudges)
    approved = answer_pitch(
        after,
        AnswerPitch(mp(after), p.id, "approve"),
        rng,
        lambda: rng.stream(after.turn, "actions", 1),
        b,
        data,
        balances,
    )
    assert approved.state.leadership.pitch(p.id).status in ("approved", "failed")  # type: ignore[union-attr]


def test_reports_are_requested_quarterly_and_carry_no_hidden_values(led, data: GameData) -> None:  # type: ignore[no-untyped-def]
    state, b = led
    after, results, _ = run(state, data, b, 3)
    requests = [t for r in results for t in r.text_requests if t.kind == "seat_report"]
    assert requests and {t.turn for t in requests} == {2}  # March
    holder = requests[0].ref_id
    assert holder is not None
    title, text, facts = report_text(after, 2, after.player.id, holder, data, b)
    assert "quarterly report" in title
    person = after.person(holder)
    for value in [*person.skills.as_dict().values(), *person.hidden.as_dict().values()]:
        assert f"{value:.2f}" not in text  # no true value leaks into the words
    assert "score" not in text.lower()
    assert report_requests(after, b, data) == ()  # April: not a quarter's end
    del facts
