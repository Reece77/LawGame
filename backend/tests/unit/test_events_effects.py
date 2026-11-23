"""PT-M6 effects: each effect type moves what it names, clamped to its severity's cap; cash is a
balanced ledger entry; effects on someone or something gone are skipped; WIP write-downs,
reputation and confidence go through interfaces' hooks (write-downs reach PT-M3b's billing;
reputation and confidence are no-ops until PT-M5 and PT-M4);
modifiers start, multiply and expire."""

from __future__ import annotations

from dataclasses import replace

import pytest

from ptk.sim import interfaces
from ptk.sim.data_models import Balance, GameData
from ptk.sim.events import effects as fx
from ptk.sim.events.colleagues import (
    colleagues_month,
    relationship_label,
    relationship_start,
    relationship_step,
)
from ptk.sim.events.effects import apply_choice
from ptk.sim.events.models import ColleaguePair, Effect, with_pairs
from ptk.sim.events.modifiers import expire, person_factor
from ptk.sim.ledger import CASH, GENERAL_ADMIN
from ptk.sim.state import GameState
from tests.events_support import open_event, played


@pytest.fixture(scope="module")
def base(data: GameData, balance: Balance) -> GameState:
    return played(data, balance, seed=3, turns=8)


def _with_morale(state: GameState) -> int:
    return next(
        e.person_id
        for e in state.staff(state.player.id)
        if state.person_state(e.person_id).morale is not None
    )


def _apply(
    state: GameState, balance: Balance, data: GameData, *effects: Effect, **kw: object
) -> tuple[GameState, tuple[object, ...]]:
    state, event = open_event(state, *effects, **kw)  # type: ignore[arg-type]
    new, entries, _ = apply_choice(state, event, "A", balance, data, auto=False)
    assert new.events.event(event.id).status == "answered"  # type: ignore[union-attr]
    return new, entries


def test_morale_and_strain_clamped(base: GameState, data: GameData, balance: Balance) -> None:
    pid = _with_morale(base)
    cap = balance.events.cap("morale_delta", "major")
    before = base.person_state(pid).morale
    assert before is not None
    new, _ = _apply(base, balance, data, Effect("morale_delta", f"person:{pid}", 999.0))
    assert new.person_state(pid).morale == pytest.approx(min(100.0, before + cap))
    strain = base.person(pid).strain
    new, _ = _apply(base, balance, data, Effect("strain_delta", f"person:{pid}", -999.0))
    assert new.person(pid).strain == pytest.approx(
        max(0.0, strain - balance.events.cap("strain_delta", "major"))
    )


def test_firm_morale_reaches_every_employee(
    base: GameState, data: GameData, balance: Balance
) -> None:
    new, _ = _apply(base, balance, data, Effect("morale_delta", f"firm:{base.player.id}", 2.0))
    for e in base.staff(base.player.id):
        old = base.person_state(e.person_id).morale
        if old is not None:
            assert new.person_state(e.person_id).morale == pytest.approx(min(100.0, old + 2.0))


def test_client_relationship(base: GameState, data: GameData, balance: Balance) -> None:
    rel = base.market.relationships[0]
    new, _ = _apply(
        base, balance, data, Effect("relationship_delta", f"client:{rel.client_id}", 5.0)
    )
    after = new.market.relationship(rel.client_id, rel.firm_id)
    assert after is not None and after.score == pytest.approx(min(100.0, rel.score + 5.0))


def test_cash_is_a_balanced_entry(base: GameState, data: GameData, balance: Balance) -> None:
    fid = base.player.id
    _, entries = _apply(base, balance, data, Effect("cash_delta", f"firm:{fid}", -123_456.0))
    (entry,) = entries
    lines = {ln.account: ln.amount for ln in entry.lines}  # type: ignore[attr-defined]
    assert lines == {GENERAL_ADMIN: 123_456, CASH: -123_456}
    # capped at the severity's bp of the cash base
    cap = round(100_000_000 * balance.events.cap("cash_delta", "major") / 10_000)
    _, entries = _apply(base, balance, data, Effect("cash_delta", f"firm:{fid}", -(10**12)))
    assert sum(ln.amount for ln in entries[0].lines if ln.account == GENERAL_ADMIN) == cap  # type: ignore[attr-defined]


def test_matter_hours_and_merits(base: GameState, data: GameData, balance: Balance) -> None:
    m = base.market.open_matters(base.player.id)[0]
    new, _ = _apply(base, balance, data, Effect("hours_pct", f"matter:{m.id}", 10.0))
    assert new.market.matter(m.id).hours_needed_tenths == round(m.hours_needed_tenths * 1.1)  # type: ignore[union-attr]
    new, _ = _apply(base, balance, data, Effect("merits_shift", f"matter:{m.id}", 0.2))
    assert new.market.matter(m.id).merits == pytest.approx(m.merits + 0.2)  # type: ignore[union-attr]


def test_hooks_are_called_and_no_op(
    base: GameState, data: GameData, balance: Balance, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Effects through the interfaces hooks: WIP write-downs (PT-M3b, merged), reputation
    (PT-M16's reputation) and confidence (a no-op until PT-M4)."""
    m = base.market.open_matters(base.player.id)[0]
    fid = base.player.id
    calls: list[str] = []
    real_wip, real_rep, real_conf = (
        interfaces.write_down_wip,
        interfaces.reputation_change,
        interfaces.confidence_change,
    )

    def wip(state: GameState, matter_id: int, pct: float, memo: str):  # type: ignore[no-untyped-def]
        calls.append(f"wip {matter_id} {pct}")
        return real_wip(state, matter_id, pct, memo)

    def rep(state: GameState, firm_id: int, points: float, bal: Balance) -> GameState:
        calls.append(f"rep {points}")
        return real_rep(state, firm_id, points, bal)

    def conf(state: GameState, firm_id: int, points: float) -> GameState:
        calls.append(f"conf {points}")
        return real_conf(state, firm_id, points)

    monkeypatch.setattr(interfaces, "write_down_wip", wip)
    monkeypatch.setattr(interfaces, "reputation_change", rep)
    monkeypatch.setattr(interfaces, "confidence_change", conf)
    new, entries = _apply(
        base,
        balance,
        data,
        Effect("wip_writedown", f"matter:{m.id}", 10.0),
        Effect("reputation_delta", f"firm:{fid}", 2.0),
        Effect("confidence_delta", "partnership", 3.0),
    )
    assert calls == [f"wip {m.id} 10.0", "rep 2.0", "conf 3.0"]
    assert entries == ()
    assert new.market == base.market and new.people == base.people


def test_salary_resign_and_retain(base: GameState, data: GameData, balance: Balance) -> None:
    pid = _with_morale(base)
    salary = base.employment_of(pid).salary_cents  # type: ignore[union-attr]
    new, _ = _apply(base, balance, data, Effect("salary_change", f"person:{pid}", 10.0))
    assert new.employment_of(pid).salary_cents == round(salary * 1.1)  # type: ignore[union-attr]
    new, _ = _apply(base, balance, data, Effect("resign", f"person:{pid}"))
    employment = new.employment_of(pid)
    assert employment is not None and employment.status == "notice"
    back, _ = _apply(new, balance, data, Effect("retain", f"person:{pid}"), severity="critical")
    assert back.employment_of(pid).status == "active"  # type: ignore[union-attr]


def test_real_person_never_resigns_by_event(
    base: GameState, data: GameData, balance: Balance
) -> None:
    from ptk.sim.state import with_people

    pid = _with_morale(base)
    state = with_people(base, [replace(base.person(pid), real=True)])
    new, _ = _apply(state, balance, data, Effect("resign", f"person:{pid}"))
    assert new.employment_of(pid).status == "active"  # type: ignore[union-attr]


def test_gone_targets_are_skipped(base: GameState, data: GameData, balance: Balance) -> None:
    new, entries = _apply(
        base,
        balance,
        data,
        Effect("morale_delta", "person:99999", 3.0),
        Effect("hours_pct", "matter:99999", 10.0),
        Effect("pair_delta", "pair:1-99999", 5.0),
    )
    assert entries == () and new.people == base.people and new.market == base.market


def test_follow_up_is_queued(base: GameState, data: GameData, balance: Balance) -> None:
    m = next(x for x in base.market.open_matters(base.player.id))
    new, _ = _apply(
        base,
        balance,
        data,
        Effect("follow_up", ""),
        severity="critical",
        matter_id=m.id,
        template_id="verdict_due_trial",
    )
    # PT-M4's engine events may already be waiting in the base state
    (queued,) = [q for q in new.events.queued if q not in base.events.queued]
    assert queued.template_id == "verdict_aftermath" and queued.due_turn == base.turn + 1


def test_modifier_starts_multiplies_and_expires(
    base: GameState, data: GameData, balance: Balance
) -> None:
    pid = _with_morale(base)
    effect = Effect("modifier", f"person:{pid}", 50.0, "morale_target", 99)
    new, _ = _apply(base, balance, data, effect, severity="minor")
    (m,) = new.events.modifiers
    cap = balance.events.cap("modifier", "minor")
    assert m.value_pct == cap and m.end_turn - m.start_turn == balance.events.max_months("minor")
    assert person_factor(new, pid, "morale_target") == pytest.approx(1 + cap / 100)
    assert person_factor(new, pid, "strain_gain") == 1.0
    later = replace(new, turn=m.end_turn - 1)
    gone, expired = expire(later)
    assert expired == (m,) and not gone.events.modifiers


def test_colleague_formulas(balance: Balance) -> None:
    cfg = balance.colleagues
    assert relationship_start(10, 10, cfg) == cfg.start_clamp.hi
    assert relationship_start(1, 20, cfg) == max(cfg.start_clamp.lo, round(15 - 1.5 * 19))
    assert relationship_step(0.0, 10.0, 0.0, cfg) == pytest.approx(cfg.drift * 10)
    assert relationship_label(-60, cfg) == "hostile" and relationship_label(70, cfg) == "close"


def test_team_mates_form_pairs(base: GameState, balance: Balance, data: GameData) -> None:
    state = replace(base, events=with_pairs(base.events, ()))
    state = colleagues_month(state, balance.colleagues)
    teams = [
        sorted(t.person_id for t in m.team) for m in state.market.open_matters(state.player.id)
    ]
    expected = {(t[i], t[j]) for t in teams for i in range(len(t)) for j in range(i + 1, len(t))}
    assert {p.key for p in state.events.colleagues} == expected
    pair = state.events.colleagues[0]
    new, _ = _apply(state, balance, data, Effect("pair_delta", f"pair:{pair.a}-{pair.b}", 7.0))
    moved = new.events.pair(pair.a, pair.b)
    assert isinstance(moved, ColleaguePair) and moved.value == pytest.approx(pair.value + 7.0)


def test_auto_resolve_skips_written_critical(
    base: GameState, data: GameData, balance: Balance
) -> None:
    state, event = open_event(
        base, Effect("morale_delta", f"firm:{base.player.id}", 1.0), severity="critical"
    )
    kept, _, _ = fx.auto_resolve(state, balance, data)
    assert kept.events.event(event.id).status == "open"  # type: ignore[union-attr]
    done, _, _ = fx.auto_resolve(state, balance, data, critical=True)
    assert done.events.event(event.id).status == "auto"  # type: ignore[union-attr]


def test_wip_writedown_goes_through_billing(data: GameData, balance: Balance) -> None:
    """PT-M3b merged: a write-down sets the matter's next-bill write-down (bp), held to
    billing.writedown_max_bp; matters not billed by the hour are unchanged. PT-M7: its own
    seed 4 (seed 3's firm, in the universe with Chrysler, has no hourly engagement at turn 8)."""
    base = played(data, balance, seed=4, turns=8)
    hourly = [
        e
        for e in base.billing.engagements
        if not e.closed and e.model not in ("fixed", "retainer", "contingency")
    ]
    assert hourly, "an hourly engagement to write down"
    e = hourly[0]
    new, entries = _apply(
        base, balance, data, Effect("wip_writedown", f"matter:{e.matter_id}", 10.0)
    )
    after = new.billing.engagement(e.matter_id)
    assert after is not None and after.writedown_bp == max(e.writedown_bp, 1000)
    assert entries == ()  # the ledger moves when the bill goes out
    other = [x for x in base.billing.engagements if x.model in ("fixed", "retainer", "contingency")]
    for x in other[:1]:
        same, _ = _apply(
            base, balance, data, Effect("wip_writedown", f"matter:{x.matter_id}", 10.0)
        )
        assert same.billing == base.billing
