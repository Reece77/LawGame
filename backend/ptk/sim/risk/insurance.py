"""Professional indemnity insurance (spec 11.3; ADR PT-0017 3).

A policy year runs 12 months from the firm's first risk month and renews at its end. The
premium for the next year = the fees it covers (the trailing year's fees, at least
`exposure_floor_cents` a lawyer) x the market's rate that year (insurance.yaml's dated rate
path, held after its last point) x the practice mix (lawyers' home practices against
`practice_rating`) x the experience modifier (claims notified and losses incurred over the
last `history_years`, `formulas.experience_mod`) x the insurer's factor x the limit's and the
deductible's factors, at least the insurer's minimum. The premium is paid in twelve monthly
instalments to 6300 (replacing PT-M7's per-lawyer overhead and PT-M11's flat England and Wales
cost). A mutual insurer takes only firms of `min_lawyers` and declines a modifier above its
`max_mod`; the firm then renews with the cheapest commercial insurer that will have it.

England and Wales (bar_rules.yaml's compulsory cover, PT-M11): while the firm has an open
office there, the limit is at least the minimum terms (an LLP's); a policy below it is endorsed
up at once and its remaining instalments re-priced.
"""

from __future__ import annotations

import itertools
from dataclasses import replace

from simcore.kernel.calendar import turn_to_ym

from ptk.sim.data_models import Balance, GameData
from ptk.sim.risk import formulas as fx
from ptk.sim.risk.common import Books, lawyers, practice_of, with_risk
from ptk.sim.risk.config import Insurer
from ptk.sim.risk.models import Policy, PolicyTerms, take_id, with_policy
from ptk.sim.state import GameState

INSURANCE = "6300_insurance"
MONTHS = 12  # tunable-exempt: a policy year


def rate_bp(data: GameData, ym: tuple[int, int]) -> int:
    """The market's premium rate at a month (linear between dated points, held outside)."""
    pts = data.insurance.rates
    if ym <= pts[0].ym:
        return pts[0].rate_bp
    for a, b in itertools.pairwise(pts):
        if a.ym <= ym <= b.ym:
            span = (b.ym[0] - a.ym[0]) * MONTHS + b.ym[1] - a.ym[1]
            at = (ym[0] - a.ym[0]) * MONTHS + ym[1] - a.ym[1]
            return round(a.rate_bp + (b.rate_bp - a.rate_bp) * at / max(1, span))
    return pts[-1].rate_bp


def practice_mix(state: GameState, firm_id: int, data: GameData) -> float:
    """The lawyers' home practices' mean rating (insurance.yaml; 1 when not rated)."""
    people = lawyers(state, firm_id, data)
    if not people:
        return 1.0
    ratings = data.insurance.practice_rating
    return sum(ratings.get(practice_of(p, data), 1.0) for p in people) / len(people)


def exposure_cents(state: GameState, firm_id: int, balance: Balance, data: GameData) -> int:
    fees = sum(m.fees_cents for m in state.billing.months if m.firm_id == firm_id)
    floor = len(lawyers(state, firm_id, data)) * balance.risk.insurance.exposure_floor_cents
    return max(fees, floor)


def experience(state: GameState, firm_id: int, balance: Balance) -> float:
    """The experience modifier for a renewal at `state.turn`."""
    cfg = balance.risk.insurance
    since = state.turn - cfg.history_years * MONTHS
    claims = [
        c
        for c in state.risk.claims
        if c.firm_id == firm_id and c.noticed_turn is not None and c.noticed_turn >= since
    ]
    past = [
        p
        for p in state.risk.policies
        if p.firm_id == firm_id and p.end_turn > since and p.start_turn < state.turn
    ]
    lawyer_years = float(sum(p.lawyers for p in past))  # each policy is a year
    return fx.experience_mod(
        claims=len(claims),
        lawyer_years=lawyer_years,
        expected_per_100=cfg.expected_per_100,
        losses_cents=sum(c.paid_cents for c in claims),
        premiums_cents=sum(p.paid_cents for p in past),
        count_weight=cfg.count_weight,
        loss_weight=cfg.loss_weight,
        loss_target=cfg.loss_target,
        lo=cfg.mod.lo,
        hi=cfg.mod.hi,
    )


def compulsory_limit_cents(state: GameState, firm_id: int, data: GameData) -> int:
    """The highest compulsory minimum cover among the firm's open offices' jurisdictions."""
    need = 0
    for office in state.geo.offices:
        if office.firm_id != firm_id or not office.is_open:
            continue
        rules = data.geo.rules(data.geo.city(office.city).jurisdiction)
        if rules is not None and rules.insurance.compulsory:
            ins = rules.insurance
            need = max(need, ins.llp_min_cover_cents if rules.llp else ins.min_cover_cents)
    return need


def default_terms(
    state: GameState, firm_id: int, balance: Balance, data: GameData
) -> tuple[int, int]:
    """(limit, deductible): the smallest limit of at least lawyers x the default a lawyer
    (and the compulsory minimum), and the deductible option one step below it in the list's
    order (deductibles grow with the firm)."""
    ins = data.insurance
    n = max(1, len(lawyers(state, firm_id, data)))
    want = max(
        n * balance.risk.insurance.default_limit_per_lawyer_cents,
        compulsory_limit_cents(state, firm_id, data),
    )
    limit = next((x.cents for x in ins.limits if x.cents >= want), ins.limits[-1].cents)
    index = min(len(ins.deductibles) - 1, [x.cents for x in ins.limits].index(limit))
    return limit, ins.deductibles[index].cents


def quote(
    state: GameState,
    firm_id: int,
    insurer: Insurer,
    limit: int,
    deductible: int,
    balance: Balance,
    data: GameData,
) -> tuple[int, float, int, int]:
    """(premium, modifier, rate, exposure) for a year from `state.turn`."""
    ins = data.insurance
    mod = experience(state, firm_id, balance)
    rate = rate_bp(data, turn_to_ym(state.turn, state.save_meta.start_ym))
    exposure = exposure_cents(state, firm_id, balance, data)
    lim, ded = ins.limit(limit), ins.deductible(deductible)
    premium = fx.premium_cents(
        exposure,
        rate,
        practice_mix(state, firm_id, data),
        mod,
        insurer.factor,
        lim.factor if lim is not None else 1.0,
        ded.factor if ded is not None else 1.0,
        insurer.min_premium_cents,
    )
    return premium, mod, rate, exposure


def eligible(state: GameState, firm_id: int, insurer: Insurer, mod: float, data: GameData) -> bool:
    return len(lawyers(state, firm_id, data)) >= insurer.min_lawyers and mod <= insurer.max_mod


def choose(
    state: GameState, firm_id: int, terms: PolicyTerms, balance: Balance, data: GameData
) -> tuple[Insurer, int, int]:
    """The insurer and terms for a renewal: the firm's asks where they stand (an insurer that
    will have it, a limit at least the compulsory minimum), else the defaults, with the
    cheapest eligible insurer."""
    limit, deductible = default_terms(state, firm_id, balance, data)
    need = compulsory_limit_cents(state, firm_id, data)
    if terms.limit_cents is not None and data.insurance.limit(terms.limit_cents) is not None:
        limit = max(terms.limit_cents, limit if terms.limit_cents < need else 0)
    if (
        terms.deductible_cents is not None
        and data.insurance.deductible(terms.deductible_cents) is not None
    ):
        deductible = terms.deductible_cents
    mod = experience(state, firm_id, balance)
    pool = [i for i in data.insurance.insurers if eligible(state, firm_id, i, mod, data)]
    if not pool:
        pool = [max(data.insurance.insurers, key=lambda i: i.max_mod)]  # the market of last resort
    if terms.insurer is not None:
        asked = [i for i in pool if i.key == terms.insurer]
        if asked:
            return asked[0], limit, deductible
    best = min(
        pool, key=lambda i: (quote(state, firm_id, i, limit, deductible, balance, data)[0], i.key)
    )
    return best, limit, deductible


def renew(
    state: GameState, firm_id: int, books: Books, balance: Balance, data: GameData
) -> GameState:
    """A new policy year from this month."""
    risk = state.risk
    terms = risk.firm(firm_id).terms
    insurer, limit, deductible = choose(state, firm_id, terms, balance, data)
    premium, mod, rate, exposure = quote(state, firm_id, insurer, limit, deductible, balance, data)
    risk, pid = take_id(risk)
    old = risk.policy(firm_id, state.turn - 1)
    policy = Policy(
        id=pid,
        firm_id=firm_id,
        insurer=insurer.key,
        start_turn=state.turn,
        end_turn=state.turn + MONTHS,
        limit_cents=limit,
        deductible_cents=deductible,
        premium_cents=premium,
        mod=round(mod, 3),
        rate_bp=rate,
        exposure_cents=exposure,
        lawyers=len(lawyers(state, firm_id, data)),
    )
    books.inbox(
        "policy_renewed",
        pid,
        insurer=insurer.label,
        premium_cents=premium,
        limit_cents=limit,
        deductible_cents=deductible,
        change_pct=0
        if old is None or old.premium_cents <= 0
        else round(100 * (premium / old.premium_cents - 1)),
    )
    return with_risk(state, with_policy(risk, policy))


def endorse(
    state: GameState, firm_id: int, books: Books, balance: Balance, data: GameData
) -> GameState:
    """England and Wales' minimum terms: a policy below the compulsory limit is raised to it at
    once and re-priced for the months left."""
    policy = state.risk.policy(firm_id, state.turn)
    need = compulsory_limit_cents(state, firm_id, data)
    if policy is None or policy.limit_cents >= need:
        return state
    limit = next(
        (x.cents for x in data.insurance.limits if x.cents >= need), data.insurance.limits[-1].cents
    )
    insurer = data.insurance.insurer(policy.insurer)
    premium = quote(state, firm_id, insurer, limit, policy.deductible_cents, balance, data)[0]
    left = policy.end_turn - state.turn
    paid = policy.paid_cents
    year = paid + (premium * left) // MONTHS  # the months left at the new terms
    books.inbox("policy_endorsed", policy.id, limit_cents=limit, premium_cents=year)
    return with_risk(
        state, with_policy(state.risk, replace(policy, limit_cents=limit, premium_cents=year))
    )


def premium_month(state: GameState, firm_id: int, books: Books) -> GameState:
    """A month's instalment: the year's premium in twelve parts, the last one taking the
    remainder."""
    policy = state.risk.policy(firm_id, state.turn)
    if policy is None:
        return state
    months_left = policy.end_turn - state.turn
    due = (policy.premium_cents - policy.paid_cents) // max(1, months_left)
    if months_left <= 1:
        due = policy.premium_cents - policy.paid_cents
    books.pay(INSURANCE, due, f"Professional indemnity premium: policy {policy.id}")
    return with_risk(
        state, with_policy(state.risk, replace(policy, paid_cents=policy.paid_cents + max(0, due)))
    )


def insurance_month(
    state: GameState, firm_id: int, books: Books, balance: Balance, data: GameData
) -> GameState:
    if not data.insurance.insurers:
        return state
    if state.risk.policy(firm_id, state.turn) is None:
        state = renew(state, firm_id, books, balance, data)
    state = endorse(state, firm_id, books, balance, data)
    return premium_month(state, firm_id, books)
