"""Phase 3: knowledge and AI adoption (PT-M14; ADR PT-0011 3, 6; spec 13, 9.1).

Each month, for the player's firm, every era it has touched:

- **Costs** (6100): the subscription (lawyers x the era's per-lawyer subscription x the
  firm's coverage), the platform's amortisation (1500 -> 6100 over
  `tech.adoption.platform_months`), and the training programme (trainees x a month's programme
  hours x `tech.training.cost_cents_per_hour`).
- **Adoption** moves toward a target: coverage x (1 - training_share + training_share x
  training) x (buyin_floor + (1 - buyin_floor) x buy-in), where training = programme hours
  x (1 + cko_training x e) / training_full_hours (at most 1), buy-in = the equity partners'
  mean (adaptability + technology) / 2 between `buyin_from` and `buyin_to`, and e the CKO's
  seat effect. No platform
  (for an era that has one) means a target of 0; without a firm-wide rollout the target is at
  most `pilot_cap`. Up at `speed` x (1 + cko_speed x e) of the gap, down at `decay` of it:
  adoption decays without upkeep.

A firm-wide rollout is put to the equity partners (`interfaces` reads, no partnership code is
edited): each supports when (adaptability + technology) / 2 + N(0, vote_sd) >= support_score
(stream `tech_vote`, 111, keyed by the era's index), and it passes with more than
`rollout_threshold_bp` of them.
"""

from __future__ import annotations

from dataclasses import replace

from ptk.sim.data_models import Balance, GameData
from ptk.sim.interfaces import equity_partner_ids, seat_effect
from ptk.sim.ledger import CASH, LedgerEntry
from ptk.sim.log import LogItem, inbox_item
from ptk.sim.money import Cents
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState
from ptk.sim.tech import efficiency as ef
from ptk.sim.tech.models import EraAdoption, FirmTech, with_era, with_firm

TECHNOLOGY = "6100_technology"
PPE = "1500_ppe"
CKO = "cko"
BP = 10000  # tunable-exempt


def lawyer_count(state: GameState, firm_id: int, data: GameData) -> int:
    staff = set(state.staff_ids(firm_id))
    return sum(1 for p in state.people if p.id in staff and data.role(p.role).kind == "lawyer")


def partner_score(state: GameState, person_id: int) -> float:
    p = state.person(person_id)
    return (p.personality["adaptability"] + p.skills["technology"]) / 2


def buyin(state: GameState, firm_id: int, balance: Balance) -> float:
    """0-1: the equity partners' mean (adaptability + technology) / 2 between the bounds."""
    cfg = balance.tech.adoption
    ids = equity_partner_ids(state, firm_id)
    if not ids:
        return 0.0
    mean = sum(partner_score(state, pid) for pid in ids) / len(ids)
    return min(1.0, max(0.0, (mean - cfg.buyin_from) / (cfg.buyin_to - cfg.buyin_from)))


def training_level(firm: FirmTech, cko: float, balance: Balance) -> float:
    cfg = balance.tech.adoption
    hours = firm.training_hours * (1.0 + cfg.cko_training * cko)
    return min(1.0, max(0.0, hours / cfg.training_full_hours))


def target(
    era: EraAdoption, firm: FirmTech, platform_needed: bool, b: float, cko: float, balance: Balance
) -> float:
    cfg = balance.tech.adoption
    if platform_needed and not era.platform:
        return 0.0
    coverage = era.subscription_bp / BP
    share = cfg.training_share
    t = coverage * (1.0 - share + share * training_level(firm, cko, balance))
    t *= cfg.buyin_floor + (1.0 - cfg.buyin_floor) * b
    if not era.rolled_out:
        t = min(t, cfg.pilot_cap)
    return min(1.0, max(0.0, t))


def step(current: float, goal: float, cko: float, balance: Balance) -> float:
    cfg = balance.tech.adoption
    if goal > current:
        speed = min(1.0, cfg.speed * max(0.0, 1.0 + cfg.cko_speed * cko))
        return min(1.0, current + speed * (goal - current))
    return max(0.0, current - cfg.decay * (current - goal))


def _entry(
    turn: int, firm_id: int, memo: str, debit: str, credit: str, amount: Cents
) -> LedgerEntry:
    return LedgerEntry.transfer(
        turn=turn, firm_id=firm_id, memo=memo, debit=debit, credit=credit, amount=amount
    )


def month(
    state: GameState, data: GameData, balance: Balance
) -> tuple[GameState, tuple[LedgerEntry, ...], tuple[LogItem, ...]]:
    firm_id = state.player.id
    firm = state.tech.firm(firm_id)
    if firm is None or (firm.idle and not any(e.platform for e in firm.eras)):
        return state, (), ()
    turn = state.turn
    ym = ef.ym_of(state)
    order = data.legal_eras.keys
    lawyers = lawyer_count(state, firm_id, data)
    cko = seat_effect(state, firm_id, CKO, balance, data)
    b = buyin(state, firm_id, balance)
    entries: list[LedgerEntry] = []
    for era in firm.eras:
        d = data.legal_eras.era(era.era)
        sub = lawyers * d.subscription_cents * era.subscription_bp // BP
        if sub > 0:
            entries.append(
                _entry(turn, firm_id, f"AI: {d.label} subscription", TECHNOLOGY, CASH, sub)
            )
        new = era
        amort = min(era.amortise_cents, era.capex_left_cents)
        if amort > 0:
            memo = f"AI: {d.label} platform"
            entries.append(_entry(turn, firm_id, memo, TECHNOLOGY, PPE, amort))
            new = replace(new, capex_left_cents=era.capex_left_cents - amort)
        if ym >= d.start:
            goal = target(new, firm, d.platform_cents > 0, b, cko, balance)
            new = replace(new, adoption=step(new.adoption, goal, cko, balance))
        firm = with_era(firm, new, order)
    tenths = ef.monthly_training_tenths(firm)
    if tenths > 0:
        trainees = len(ef.trainee_ids(state, firm_id, balance))
        cost = trainees * tenths * balance.tech.training.cost_cents_per_hour // ef.TENTHS
        if cost > 0:
            entries.append(_entry(turn, firm_id, "AI: training programme", TECHNOLOGY, CASH, cost))
    return replace(state, tech=with_firm(state.tech, firm)), tuple(entries), ()


def rollout_vote(
    state: GameState, firm_id: int, era_key: str, rng: RngFactory, data: GameData, balance: Balance
) -> tuple[GameState, bool, int, int, LogItem]:
    """Put a firm-wide rollout of an era's tools to the equity partners: (state, passed,
    supporters, voters, the inbox line)."""
    cfg = balance.tech.adoption
    firm = state.tech.firm(firm_id) or FirmTech(firm_id=firm_id)
    era = firm.era(era_key) or EraAdoption(era=era_key)
    index = data.legal_eras.keys.index(era_key)
    gen = rng.stream(state.turn, "tech_vote", index)
    ids = sorted(equity_partner_ids(state, firm_id))
    support = 0
    for pid in ids:
        noise = float(gen.normal(0.0, cfg.vote_sd))
        if partner_score(state, pid) + noise >= cfg.support_score:
            support += 1
    passed = bool(ids) and support * BP > cfg.rollout_threshold_bp * len(ids)
    era = replace(era, rolled_out=era.rolled_out or passed, vote_turn=state.turn)
    firm = with_era(firm, era, data.legal_eras.keys)
    item = inbox_item(
        state.turn,
        firm_id,
        "ai_rollout_passed" if passed else "ai_rollout_failed",
        link_kind="tech",
        link_id=index,
        era=data.legal_eras.era(era_key).label,
        support=support,
        voters=len(ids),
    )
    return replace(state, tech=with_firm(state.tech, firm)), passed, support, len(ids), item
