"""PT-M15 sub-task 3: professional indemnity insurance (spec 11.3)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from ptk.sim.errors import RiskActionError
from ptk.sim.risk import insurance as ins
from ptk.sim.risk.actions import SetPolicyTerms, apply_risk_action
from ptk.sim.risk.common import Books
from ptk.sim.risk.models import EMPTY_RISK, with_claim
from tests.geo_support import london_game
from tests.risk_support import a_claim, busy_firm, loaded


def _renewed(state, firm_id: int = 1):  # type: ignore[no-untyped-def]
    data, balance = loaded()
    books = Books(firm_id, state.turn, 10**12)
    return ins.renew(state, firm_id, books, balance, data)


def test_a_policy_renews_each_year_and_is_paid_in_full() -> None:
    data, balance = loaded()
    state = replace(busy_firm(), risk=EMPTY_RISK)
    firm = state.player.id
    paid = 0
    for _ in range(25):
        books = Books(firm, state.turn, 10**12)
        state = ins.insurance_month(state, firm, books, balance, data)
        paid += sum(
            e.lines[0].amount for e in books.entries if e.lines[0].account == "6300_insurance"
        )
        state = replace(state, turn=state.turn + 1)
    policies = [p for p in state.risk.policies if p.firm_id == firm]
    assert len(policies) == 3
    assert [p.start_turn for p in policies] == [policies[0].start_turn + 12 * i for i in range(3)]
    full = policies[:2]
    assert all(p.paid_cents == p.premium_cents for p in full)
    assert paid == sum(p.paid_cents for p in policies)


def test_worse_claims_history_pays_more_at_renewal() -> None:
    data, balance = loaded()
    clean = _renewed(replace(busy_firm(), risk=EMPTY_RISK))
    later = replace(clean, turn=clean.turn + 12)
    bad = later
    for i in range(4):
        c = replace(
            a_claim(later, cid=500 + i),
            stage="closed",
            noticed_turn=later.turn - 3,
            defence_cents=5_000_000,
        )
        bad = replace(bad, risk=with_claim(bad.risk, c))
    insurer = data.insurance.insurer("national_carrier")
    limit, ded = ins.default_terms(later, later.player.id, balance, data)
    good = ins.quote(later, later.player.id, insurer, limit, ded, balance, data)
    worse = ins.quote(bad, bad.player.id, insurer, limit, ded, balance, data)
    assert worse[1] > good[1] and worse[0] > good[0]


def test_a_small_firm_cannot_join_the_mutual() -> None:
    data, balance = loaded()
    state = replace(busy_firm(), risk=EMPTY_RISK)
    insurer, _, _ = ins.choose(state, state.player.id, EMPTY_RISK.firm(1).terms, balance, data)
    assert insurer.kind == "commercial"


def test_a_london_office_needs_the_minimum_terms() -> None:
    data, balance = loaded()
    state = london_game(data, balance).state
    firm = state.player.id
    need = ins.compulsory_limit_cents(state, firm, data)
    assert need >= data.geo.rules("ew").insurance.llp_min_cover_cents > 0  # type: ignore[union-attr]
    books = Books(firm, state.turn, 10**12)
    state = ins.insurance_month(state, firm, books, balance, data)
    policy = state.risk.policy(firm, state.turn)
    assert policy is not None and policy.limit_cents >= need
    with pytest.raises(RiskActionError):
        apply_risk_action(
            state,
            SetPolicyTerms(state.founder_of(firm) or 0, limit_cents=data.insurance.limits[0].cents),
            balance,
            data,
            0,
        )


def test_policy_terms_are_validated() -> None:
    data, balance = loaded()
    state = busy_firm()
    actor = state.founder_of(state.player.id)
    assert actor is not None
    with pytest.raises(RiskActionError):
        apply_risk_action(state, SetPolicyTerms(actor, insurer="nobody"), balance, data, 0)
    with pytest.raises(RiskActionError):
        apply_risk_action(state, SetPolicyTerms(actor, deductible_cents=1), balance, data, 0)
    out = apply_risk_action(
        state,
        SetPolicyTerms(actor, deductible_cents=data.insurance.deductibles[-1].cents),
        balance,
        data,
        0,
    )
    assert (
        out.state.risk.firm(state.player.id).terms.deductible_cents
        == data.insurance.deductibles[-1].cents
    )
