"""PT-M15 sub-task 7: the general counsel's checks and the risk area (spec 9.1, 9.4)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from ptk.sim.automation.limits import is_one_off
from ptk.sim.risk import claims as cl
from ptk.sim.risk import discipline as dc
from ptk.sim.risk.actions import RespondClaim
from ptk.sim.risk.models import with_claim
from tests.risk_support import a_claim, busy_firm, loaded


@pytest.mark.parametrize("module", [cl, dc])
def test_a_strong_gc_lowers_the_chances_and_a_vacant_seat_raises_them(
    module: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    data, balance = loaded()
    state = busy_firm()
    person = next(p for p in state.people if not p.is_founder)

    def read(e: float) -> float:
        monkeypatch.setattr(module, "gc_effect", lambda *_: e)
        if module is cl:
            return cl.conversion(state, state.player.id, balance, data)
        return dc.chance_mult(state, person, balance, data)

    vacant, none, strong = read(-0.5), read(0.0), read(1.0)
    assert vacant > none > strong


def test_lax_supervision_and_checks_off_raise_conversion() -> None:
    data, balance = loaded()
    state = busy_firm()
    base = cl.conversion(state, state.player.id, balance, data)
    lax = replace(
        state, risk=replace(state.risk, firms=(replace(state.risk.firm(1), supervision="lax"),))
    )
    off = replace(state, firms=tuple(replace(f, conflict_checks=False) for f in state.firms))
    assert cl.conversion(lax, 1, balance, data) > base
    assert cl.conversion(off, 1, balance, data) > base


def test_settling_above_the_deductible_is_a_one_off() -> None:
    _, balance = loaded()
    state = busy_firm()
    claim = replace(
        a_claim(state, cid=77), stage="offer", offer_cents=50_000_000, deductible_cents=10_000_000
    )
    state = replace(state, risk=with_claim(state.risk, claim))
    assert is_one_off(state, RespondClaim(1, 77, "settle"), balance)
    assert not is_one_off(state, RespondClaim(1, 77, "contest"), balance)
    small = replace(claim, offer_cents=5_000_000)
    state = replace(state, risk=with_claim(state.risk, small))
    assert not is_one_off(state, RespondClaim(1, 77, "settle"), balance)
