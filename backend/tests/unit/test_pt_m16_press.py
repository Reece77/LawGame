"""PT-M16 sub-task 3: the legal press (spec 12.2; TST formulas.md 29): moments and their cap,
tones, public claims judged at their deadlines with TST 29.8's worked examples in Partner
Track's units, credibility, rival managing partners, and ADR PT-0013 (real lawyers appear only
in professional matters)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import InvalidActionError
from ptk.sim.press import claims, moments
from ptk.sim.press import phase as press_phase
from ptk.sim.press.actions import AnswerPress, answer_press
from ptk.sim.press.config import RESTRICTED
from ptk.sim.press.models import Claim
from ptk.sim.reputation import formulas as fx
from ptk.sim.rng import STREAM_IDS, RngFactory
from ptk.sim.state import GameState, with_firm
from tests.matters_support import game, play


@pytest.fixture(scope="module")
def start(data: GameData, balance: Balance) -> GameState:
    return game(data, balance)


def _mid(state: GameState, practice: str = "corporate_ma", value: float = 40.0) -> GameState:
    """Every practice of the player's at `value`, so effects are not clamped."""
    pid = state.player.id
    rep = state.standing.reputation
    entries = tuple(replace(e, value=value) if e.firm_id == pid else e for e in rep.entries)
    return replace(
        state, standing=replace(state.standing, reputation=replace(rep, entries=entries))
    )


def _with_cred(state: GameState, value: float) -> GameState:
    return moments.with_press(state, replace(moments.press_of(state), credibility=value))


def _open(state: GameState, trigger: str = "verdict") -> tuple[GameState, int]:
    state = moments.queue_moment(state, trigger, {"result": "x"}, practice="corporate_ma")
    state, _ = moments.schedule(state, _bal())
    m = moments.press_of(state).moments[-1]
    assert m.status == "open"
    return replace(state, turn=m.due_turn), m.id  # type: ignore[arg-type]


_BALANCE: list[Balance] = []


def _bal() -> Balance:
    return _BALANCE[0]


@pytest.fixture(autouse=True)
def _keep(balance: Balance) -> None:
    if not _BALANCE:
        _BALANCE.append(balance)


def test_streams_are_registered_in_lane_cs_range() -> None:
    assert STREAM_IDS["press"] == 70 and STREAM_IDS["press_rival"] == 71


def test_a_quarter_keeps_at_most_two_moments_and_one_a_month(
    start: GameState, balance: Balance
) -> None:
    state = start
    for trigger in ("salary_scale", "verdict", "collapse"):
        state = moments.queue_moment(state, trigger, {"result": trigger})
    state, logs = moments.schedule(state, balance)
    ms = moments.press_of(state).moments
    assert [m.status for m in ms if m.trigger == "collapse"] == ["open"]  # highest stakes first
    assert sum(m.status == "open" for m in ms) == 1  # one a month
    assert sum(m.status == "skipped" for m in ms) == 2
    assert len(logs) == 1 and logs[0].link_kind == "press"


def test_tones_move_reputation_and_credibility(
    start: GameState, data: GameData, balance: Balance
) -> None:
    pb = balance.press
    state, mid = _open(_mid(start))
    a = moments.audience(state, balance)
    cf = moments.cred_factor(state, balance)
    pid = state.player.id
    before = fx.reputation(state, pid, "corporate_ma", balance)
    bold, _ = moments.apply_tone(state, moments.press_of(state).moment(mid), "bold", balance, data)  # type: ignore[arg-type]
    assert fx.reputation(bold, pid, "corporate_ma", balance) == pytest.approx(
        before + pb.bold_rep * a * cf
    )
    deflect, _ = moments.apply_tone(
        state, moments.press_of(state).moment(mid), "deflect", balance, data
    )  # type: ignore[arg-type]
    assert moments.credibility(deflect, balance) == pytest.approx(
        pb.cred_start + pb.deflect_cred * a
    )


def test_an_unanswered_moment_gets_the_press_offices_measured_answer(
    start: GameState, data: GameData, balance: Balance
) -> None:
    state, mid = _open(_mid(start))
    state, _ = moments.office_answers(state, balance, data)
    m = moments.press_of(state).moment(mid)
    assert m is not None and m.tone == "measured" and m.by_office


def test_the_answer_action_makes_a_claim_and_spends_energy(
    start: GameState, data: GameData, balance: Balance
) -> None:
    state, mid = _open(_mid(start))
    actor = state.founder_of(state.player.id)
    assert actor is not None
    energy = state.person_state(actor).energy
    out = answer_press(
        state, AnswerPress(actor, mid, "bold", "headcount", target=40, months=24), balance, data
    )
    press = moments.press_of(out.state)
    assert press.open_claims and press.open_claims[0].target == 40
    assert out.state.person_state(actor).energy == energy - balance.energy.cost["press_answer"]
    with pytest.raises(InvalidActionError):  # answered already
        answer_press(out.state, AnswerPress(actor, mid, "measured"), balance, data)
    with pytest.raises(InvalidActionError):  # no claim with a deflect
        answer_press(state, AnswerPress(actor, mid, "deflect", "no_layoffs"), balance, data)
    with pytest.raises(InvalidActionError):  # a headcount below today's
        answer_press(
            state, AnswerPress(actor, mid, "bold", "headcount", target=1, months=12), balance, data
        )


def _claim(state: GameState, **kw: object) -> Claim:
    base: dict[str, object] = {
        "id": 900,
        "kind": "headcount",
        "made_turn": state.turn,
        "deadline_turn": state.turn + 12,
        "audience": 1.0,
    }
    base.update(kw)
    return Claim(**base)  # type: ignore[arg-type]


def test_worked_example_a_kept_claim_at_a_large_firm(
    start: GameState, data: GameData, balance: Balance
) -> None:
    """TST 29.8, in Partner Track's units: a = 1.5, ambition 0.4, credibility 60: reputation
    +4 x 1.5 x 1.4 x 1.1 = +9.24 in every practice; credibility +7.5."""
    state = _with_cred(_mid(start), 60.0)
    c = _claim(state, audience=1.5, ambition=0.4)
    state = moments.with_press(state, replace(moments.press_of(state), claims=(c,)))
    pid = state.player.id
    before = {e.practice: e.value for e in state.standing.reputation.of(pid)}
    out, logs = claims.resolve(state, c, "kept", balance, data, 1)
    for e in out.standing.reputation.of(pid):
        assert e.value - before[e.practice] == pytest.approx(9.24)
    assert moments.credibility(out, balance) == pytest.approx(67.5)
    assert logs[0].template == "claim_kept"


def test_worked_example_a_broken_no_layoffs_claim(
    start: GameState, data: GameData, balance: Balance
) -> None:
    """TST 29.8: a = 1.0: reputation -8, credibility -10, everyone's morale -5, and a reminder."""
    state = _with_cred(_mid(start), 50.0)
    c = _claim(state, kind="no_layoffs")
    state = moments.with_press(state, replace(moments.press_of(state), claims=(c,)))
    pid = state.player.id
    before = {e.practice: e.value for e in state.standing.reputation.of(pid)}
    morale = {p.person_id: p.morale for p in state.person_states if p.morale is not None}
    out, _ = claims.resolve(state, c, "broken", balance, data, 2)
    for e in out.standing.reputation.of(pid):
        assert e.value - before[e.practice] == pytest.approx(-8.0)
    assert moments.credibility(out, balance) == pytest.approx(40.0)
    for p in out.person_states:
        if (
            p.person_id in morale
            and morale[p.person_id] >= 5
            and out.person(p.person_id).level != "equity_partner"
        ):
            assert p.morale == pytest.approx(morale[p.person_id] - 5.0)
    reminder = [m for m in moments.press_of(out).moments if m.trigger == "reminder"]
    assert reminder and dict(reminder[0].facts)["due_turn"] == state.turn + 2


def test_claims_are_checked_at_their_deadlines(
    start: GameState, data: GameData, balance: Balance
) -> None:
    lawyers = claims.public_lawyers(start, data)
    open_c = _claim(start, target=lawyers + 50)
    assert claims.verdict(start, open_c, data) is None  # before its deadline
    due = replace(start, turn=open_c.deadline_turn)
    assert claims.verdict(due, open_c, data) == "broken"
    met = _claim(start, target=lawyers)
    assert claims.verdict(start, met, data) == "kept"
    no_layoffs = _claim(start, kind="no_layoffs")
    assert claims.verdict(start, no_layoffs, data, fired=1) == "broken"
    assert claims.verdict(due, no_layoffs, data) == "kept"
    scale = _claim(start, kind="match_scale")
    lagging = with_firm(
        start, replace(start.player, pay_policy=replace(start.player.pay_policy, pct_bp=9500))
    )
    assert claims.verdict(lagging, scale, data) == "broken"
    # the month's check resolves them, each through the press stream
    state = moments.with_press(due, replace(moments.press_of(due), claims=(open_c,)))
    checked, logs = claims.check(state, RngFactory(1), balance, data, 0)
    assert moments.press_of(checked).claims[0].status == "broken" and logs


def test_restricted_moments_never_name_a_real_person(start: GameState, balance: Balance) -> None:
    real = next(p for p in start.people if p.real) if any(p.real for p in start.people) else None
    pid = real.id if real is not None else 12345
    for trigger in sorted(RESTRICTED):
        state = moments.queue_moment(start, trigger, {"result": "x"}, person_id=pid)
        assert moments.press_of(state).moments[-1].person_id is None


def test_a_campaign_keeps_real_lawyers_to_professional_press(
    data: GameData, balance: Balance
) -> None:
    """ADR PT-0013 over two years of play: no restricted moment names anyone, and no jab is in
    a real person's name; every named person is in a professional moment (moves, matters,
    rankings)."""
    state = game(data, balance)
    seen_moments = []
    seen_statements = []
    for _ in range(24):
        state, _ = play(state, data, balance, 1)
        press = moments.press_of(state)
        seen_moments += list(press.moments)
        seen_statements += list(press.statements)
    from ptk.sim.rivals.people import find_person

    def is_real(pid: int) -> bool:
        person = find_person(state, pid, data, balance)
        return person is not None and person.real

    for m in seen_moments:
        if m.trigger in RESTRICTED:
            assert m.person_id is None, m
        elif m.person_id is not None and is_real(m.person_id):
            assert m.trigger in ("lateral", "verdict", "ranking_day"), m
    for s in seen_statements:
        if s.kind == "jab" and s.person_id is not None:
            assert not is_real(s.person_id), s
    assert seen_statements, "two years of real rivals' moves make some statements"


def test_the_press_month_is_seeded(start: GameState, data: GameData, balance: Balance) -> None:
    a, _ = play(start, data, balance, 6, seed=3)
    b, _ = play(start, data, balance, 6, seed=3)
    assert moments.press_of(a) == moments.press_of(b)


def test_layoffs_raise_a_moment(start: GameState, data: GameData, balance: Balance) -> None:
    state = press_phase.raise_moments(start, start, balance, data, (), fired=3, staff=10)
    assert any(m.trigger == "layoffs" for m in moments.press_of(state).moments)
    calm = press_phase.raise_moments(start, start, balance, data, (), fired=0, staff=10)
    assert not any(m.trigger == "layoffs" for m in moments.press_of(calm).moments)
