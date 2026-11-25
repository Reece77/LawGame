"""Litigation funding of contingency cases (PT-M12; spec 7.7; ADR PT-0018).

From `billing.funding.from_ym` (January 2010) a funder may fund an open contingency case: on
the player's acceptance it advances `funded_bp` of the case's WIP to date and then of each
month's WIP (at standard value) to the firm, non-recourse. When the case closes:

- **a recovery**: the firm's contingency fee arrives from the client account; the funder is
  paid first, out of that fee, `return_bp` of its advances (2-3x), never more than the fee;
- **a loss** (or a fee below the advances): the funder bears it. The advances it is not
  repaid are released to the firm's income (4400), so a funded loss costs the firm only the
  WIP the funder did not carry.

Accounts (ADR PT-0018): advances are a non-recourse liability (2800) until the case closes;
the funder's return above its advances is a funding cost (6750). Pure arithmetic here; the
billing phase posts it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ptk.sim.calendar import turn_to_ym
from ptk.sim.money import pct_of
from ptk.sim.rng import RngFactory

if TYPE_CHECKING:
    from ptk.sim.billing.models import Engagement
    from ptk.sim.data_models import FundingBalance


@dataclass(frozen=True, slots=True)
class FundingClose:
    """What a funded case's close moves (all cents, each >= 0)."""

    repaid_cents: int  # advances repaid to the funder (debit 2800, credit cash)
    cost_cents: int  # the funder's return above its advances (debit 6750, credit cash)
    released_cents: int  # advances the funder bears (debit 2800, credit 4400)

    @property
    def paid_cents(self) -> int:
        """Cash paid to the funder."""
        return self.repaid_cents + self.cost_cents


def advance_cents(wip_cents: int, funded_bp: int) -> int:
    """The funder's advance on a month's (or the case's) WIP at standard value."""
    return pct_of(max(0, wip_cents), funded_bp) if funded_bp > 0 else 0


def close_funding(advances_cents: int, fee_cents: int, return_bp: int) -> FundingClose:
    """The waterfall at the case's close: the funder takes `return_bp` of its advances first,
    out of the firm's fee, capped at the fee; what it does not recover of its advances it bears
    (non-recourse)."""
    if advances_cents <= 0:
        return FundingClose(0, 0, 0)
    due = pct_of(advances_cents, return_bp)
    paid = min(max(0, fee_cents), due)
    repaid = min(paid, advances_cents)
    return FundingClose(
        repaid_cents=repaid,
        cost_cents=paid - repaid,
        released_cents=advances_cents - repaid,
    )


def unfunded_cents(wip_cents: int, advances_cents: int) -> int:
    """The case's WIP the funder did not carry (a loss's cost to the firm, at standard)."""
    return max(0, wip_cents - advances_cents)


def funded_share(advances_cents: int, wip_cents: int) -> float:
    """The share of the case's WIP the funder has advanced (0-1), for the Matter screen."""
    return advances_cents / wip_cents if wip_cents > 0 else 0.0


@dataclass(frozen=True, slots=True)
class FundingOffer:
    """A funder's terms for one contingency case (drawn once, at the case's opening)."""

    funded_bp: int  # share of the case's WIP it advances
    return_bp: int  # its return, bp of its advances, paid first from the fee


def funding_offer(
    e: Engagement, turn: int, start: tuple[int, int], rng: RngFactory, cfg: FundingBalance
) -> FundingOffer | None:
    """The funder's offer on an open, unfunded contingency case from `cfg.from_ym`; None
    otherwise. Stream `funding` (120), keyed (matter_id,) at the case's opening month, so the
    terms do not change while the offer stands."""
    if e.model != "contingency" or e.closed or e.funded_turn is not None:
        return None
    if turn_to_ym(turn, start) < cfg.from_ym:
        return None
    gen = rng.stream(e.opened_turn, "funding", e.matter_id)
    u_fund, u_return = (float(x) for x in gen.random(2))
    lo, hi = cfg.funded_bp
    rlo, rhi = cfg.return_bp
    return FundingOffer(
        funded_bp=round(lo + (hi - lo) * u_fund), return_bp=round(rlo + (rhi - rlo) * u_return)
    )
