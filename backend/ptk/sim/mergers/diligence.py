"""Due diligence (TST formulas.md 28.2, re-cast; ADR PT-0016 4).

A level costs professional fees (`diligence.fee_bp` of the other firm's revenue, at least
`min_fee_cents`, to 6600) and `diligence.months`; when it ends (phase 1) the deal's level
rises. From level 1 the other firm's books are shown exactly (its run-rate P&L and the
closing sheet's WIP, receivables, cash and revolver); its partners' quality, annuity burden,
leases and the conflicts overlap are ranges `[v (1 - h + o), v (1 + h + o)]` with `h` from
`diligence.half_width` by level and the firm's fixed offset `o` (at most `offset_share` x h),
so every range holds the truth and its midpoint is not it. Only these views leave the engine.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

from simcore.kernel.money import BP_DENOMINATOR

from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import InvalidActionError
from ptk.sim.hiring.actions import Outcome
from ptk.sim.ledger import CASH, PROFESSIONAL_FEES, LedgerEntry
from ptk.sim.log import LogItem, inbox_item
from ptk.sim.mergers.books import hidden, sheet
from ptk.sim.mergers.models import Deal, with_deal
from ptk.sim.mergers.profile import annualised, rival_side
from ptk.sim.mergers.talks import put_mergers
from ptk.sim.rivals.models import RivalFirm
from ptk.sim.state import GameState
from ptk.sim.streams import RngFactory

QUALITY, ANNUITIES, LEASES, CONFLICTS = 0, 1, 2, 3  # tunable-exempt: the offsets' order


def fee_cents(firm: RivalFirm, balance: Balance) -> int:
    cfg = balance.mergers.diligence
    return max(cfg.min_fee_cents, annualised(firm.revenue) * cfg.fee_bp // BP_DENOMINATOR)


def max_level(balance: Balance) -> int:
    return len(balance.mergers.diligence.half_width) - 1


def commission(
    state: GameState, deal: Deal, rng: RngFactory, balance: Balance, data: GameData
) -> Outcome:
    if deal.stage not in ("talks", "countered"):
        raise InvalidActionError("diligence runs only while talks are open")
    if deal.diligence_due_turn is not None:
        raise InvalidActionError("a level of diligence is already running")
    if deal.diligence_level >= max_level(balance):
        raise InvalidActionError("diligence is complete")
    firm = state.rivals.firm(deal.rival_id)
    if firm is None or not firm.active:
        raise InvalidActionError("the other firm no longer exists")
    fee = fee_cents(firm, balance)
    # this month and the next `months - 1`: the report arrives in the last of them (phase 1)
    due = state.turn + max(0, balance.mergers.diligence.months - 1)
    deal = replace(
        deal,
        diligence_due_turn=due,
        diligence_fees_cents=deal.diligence_fees_cents + fee,
    )
    state = put_mergers(state, with_deal(state.mergers, deal))
    entry = LedgerEntry.transfer(
        turn=state.turn,
        firm_id=state.player.id,
        memo=f"Due diligence on {firm.name}",
        debit=PROFESSIONAL_FEES,
        credit=CASH,
        amount=fee,
    )
    return Outcome(state, (entry,))


def finish(state: GameState) -> tuple[GameState, tuple[LogItem, ...]]:
    """Phase 1: levels due this month end."""
    logs: list[LogItem] = []
    ms = state.mergers
    for deal in ms.open_deals():
        if deal.diligence_due_turn is None or deal.diligence_due_turn > state.turn:
            continue
        done = replace(deal, diligence_level=deal.diligence_level + 1, diligence_due_turn=None)
        ms = with_deal(ms, done)
        firm = state.rivals.firm(deal.rival_id)
        logs.append(
            inbox_item(
                state.turn,
                state.player.id,
                "merger_diligence",
                link_kind="mergers",
                link_id=deal.id,
                firm=firm.name if firm is not None else deal.rival_key,
                level=done.diligence_level,
            )
        )
    return put_mergers(state, ms), tuple(logs)


# --- What diligence shows ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Range:
    lo: float
    hi: float


def shown_range(value: float, level: int, offset: float, balance: Balance) -> Range:
    cfg = balance.mergers.diligence
    h = cfg.half_width[min(level, len(cfg.half_width) - 1)]
    o = offset * cfg.offset_share * h
    return Range(value * (1.0 - h + o), value * (1.0 + h + o))


def int_range(value: int, level: int, offset: float, balance: Balance) -> tuple[int, int]:
    r = shown_range(float(value), level, offset, balance)
    lo, hi = math.floor(r.lo), math.ceil(r.hi)
    pad = 1 if level < max_level(balance) else 0  # a count is never shown exactly
    return max(0, min(lo, value) - pad), max(hi, value) + pad


def money_range(value: int, level: int, offset: float, balance: Balance) -> tuple[int, int]:
    """A money range rounded outward to two significant figures of its high end (TST 28.11)."""
    r = shown_range(float(value), level, offset, balance)
    hi = max(r.hi, float(value))
    lo = min(r.lo, float(value))
    if hi <= 0:
        return 0, 0
    step = 10 ** max(0, int(math.log10(hi)) - 1)
    return int(math.floor(lo / step) * step), int(math.ceil(hi / step) * step)


def partner_quality(state: GameState, firm: RivalFirm, data: GameData, balance: Balance) -> float:
    """The other firm's key partners' mean current ability (engine-only)."""
    from ptk.sim.people.formulas import current_ability
    from ptk.sim.rivals.people import key_people

    vals = []
    for m, person in key_people(state, firm.id, data, balance):
        if m.kind != "partner":
            continue
        role = data.role(person.role)
        vals.append(current_ability(person.skills.as_dict(), role.primary, role.secondary))
    return sum(vals) / len(vals) if vals else 100.0  # tunable-exempt: the scale's middle


@dataclass(frozen=True, slots=True)
class Reveal:
    level: int
    exact: bool  # the books are shown exactly (level 1 and above)
    revenue_cents: int
    profit_cents: int
    pep_cents: int
    lawyers: int
    equity_partners: int
    wip_cents: int | None
    receivables_cents: int | None
    cash_cents: int | None
    revolver_cents: int | None
    quality: tuple[int, int]  # current ability, 1-200
    annuities_cents: tuple[int, int]
    leases_cents: tuple[int, int]
    conflicts: tuple[int, int]
    book_clients: int


def reveal(
    state: GameState, deal: Deal, firm: RivalFirm, rng: RngFactory, data: GameData, balance: Balance
) -> Reveal:
    from ptk.sim.mergers.clearance import find_conflicts

    level = deal.diligence_level
    side = rival_side(firm, data)
    h = hidden(rng, firm, balance)
    s = sheet(firm, rng, data, balance)
    exact = level >= 1
    q = shown_range(partner_quality(state, firm, data, balance), level, h.offsets[QUALITY], balance)
    true_conflicts = len(find_conflicts(state, deal)) if deal.book else 0
    return Reveal(
        level=level,
        exact=exact,
        revenue_cents=side.revenue_cents,
        profit_cents=side.profit_cents,
        pep_cents=side.pep_cents,
        lawyers=side.lawyers,
        equity_partners=side.equity,
        wip_cents=s.wip if exact else None,
        receivables_cents=s.receivables if exact else None,
        cash_cents=s.cash if exact else None,
        revolver_cents=s.revolver if exact else None,
        quality=(max(1, math.floor(q.lo)), min(200, math.ceil(q.hi))),
        annuities_cents=money_range(s.annuities, level, h.offsets[ANNUITIES], balance),
        leases_cents=money_range(s.leases, level, h.offsets[LEASES], balance),
        conflicts=int_range(true_conflicts, level, h.offsets[CONFLICTS], balance),
        book_clients=len(deal.book),
    )
