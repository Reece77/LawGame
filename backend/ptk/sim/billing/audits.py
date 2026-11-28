"""Clients' e-billing audits and what makes a dispute likelier (spec 11.6, 7.7; PT-M15).

- **Audits.** From `risk.audits.from_ym`, a large client audits a new fee bill against its
  outside counsel guidelines with chance `audit_bp` (+ `audit_per_point_bp` a price-sensitivity
  point above 10; stream `audit`, keyed by the bill). The audit cuts the bill by a uniform share
  (block billing, staffing, rates: a credit note) and finds any padding in it (the padder comes
  to light, as a dispute would show).
- **Disputes** come likelier on a bill for a matter over its budget (`overrun_mult`) and on a
  bill a guideline rejected part of (`guideline_mult`), beside PT-M3b's padding and the GC's
  temperament.
"""

from __future__ import annotations

from dataclasses import dataclass

from simcore.kernel.calendar import turn_to_ym
from simcore.kernel.money import BP_DENOMINATOR

from ptk.sim.data_models import Balance
from ptk.sim.interfaces import ClientBillingView
from ptk.sim.risk.draws import audit_draws
from ptk.sim.state import GameState
from ptk.sim.streams import RngFactory

NEUTRAL = 10.0  # tunable-exempt: a neutral price sensitivity


@dataclass(frozen=True, slots=True)
class AuditResult:
    cut_cents: int
    finds_padding: bool


def audit(
    state: GameState,
    rng: RngFactory,
    bill_id: int,
    client: ClientBillingView,
    fee: int,
    padding: int,
    balance: Balance,
) -> AuditResult | None:
    """A new fee bill's audit by its client, or None."""
    a = balance.risk.audits
    if not balance.risk.enabled or fee <= 0 or client.size_class != "large":
        return None
    if turn_to_ym(state.turn, state.save_meta.start_ym) < a.from_ym:
        return None
    u = audit_draws(rng, state.turn, bill_id).random(2)
    chance = (
        a.audit_bp + a.audit_per_point_bp * max(0.0, client.price_sensitivity - NEUTRAL)
    ) / BP_DENOMINATOR
    if float(u[0]) >= chance:
        return None
    share = a.cut_share.lo + (a.cut_share.hi - a.cut_share.lo) * float(u[1])
    return AuditResult(cut_cents=min(fee, round(fee * share)), finds_padding=padding > 0)


def dispute_mult(overrun: bool, rejected: bool, balance: Balance) -> float:
    if not balance.risk.enabled:
        return 1.0
    a = balance.risk.audits
    return (a.overrun_mult if overrun else 1.0) * (a.guideline_mult if rejected else 1.0)
