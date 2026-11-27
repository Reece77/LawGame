"""PT-M12's practice strategies (registered in `ptk.balance.strategies.VARIANTS` with one line).

- `specialist`: a counter-cyclical and regulatory niche (docs/research/practices-v2.md s4: the
  restructuring and financial regulation practices that rise in a crash). It plays steady's
  partnership and money rules, but enters restructuring by a lateral partner in 2005 and
  financial regulation in 2006, grows only those two (campus classes and associates there, a
  partner in the busier one when leverage passes 3.5), and holds the founders' practices
  without adding more. Read against steady: survival on seeds 1-10 and 2009's PEP change.
- `full-service`: steady, and from 2008 a new practice each year (a lateral partner with a
  book, the v2 practices in the order a corporate firm's clients cross-sell them), so it holds
  every practice but plaintiff mass torts by 2016. Read against steady: T3's lawyers and
  revenue in December 2015.
"""

from __future__ import annotations

from typing import Final

from ptk.balance import moves as mv
from ptk.balance.game import Game

NICHE: Final[tuple[str, ...]] = ("restructuring", "financial_regulation")
NICHE_YEARS: Final = (2005, 2006)  # the year each niche practice is entered (from January)
NICHE_LEVERAGE: Final = 3.5  # associates per partner above which the niche hires a partner
FULL_SERVICE_FROM: Final = 2008  # the first year the full-service firm adds a v2 practice
# The v2 practices in the order a corporate firm's clients cross-sell them (practices.yaml's
# cross_sell from M&A: antitrust 0.8, tax 0.7, energy 0.6, ...); plaintiff mass torts never
# (its adverse parties are the firm's corporate clients)
FULL_SERVICE_ADDS: Final = (
    "antitrust",
    "tax",
    "financial_regulation",
    "energy",
    "technology_privacy",
    "healthcare",
    "insurance",
    "international_arbitration",
    "private_client",
)
ENTRY_BOOK_CENTS: Final = 50_000_000  # a new practice's lateral partner: a book of $500k+


def specialist(g: Game) -> None:
    from ptk.balance import strategies as st

    mv.answer_election(g)
    mv.comp_system(g, "modified_lockstep")
    mv.set_rates(g, None)
    mv.december_votes(g, st._admissions(g, st.STEADY_PER_EQUITY))
    mv.comp_round(g)
    held = mv.practices_held(g)
    lawyers = len(g.lawyers())
    mv.practice_groups(g)
    niche: list[str] = [p for p in NICHE if p in held]
    for practice, year in zip(NICHE, NICHE_YEARS, strict=True):
        if practice not in held and g.ym[0] >= year and mv.bank_quiet(g):
            mv.lateral_partner(g, practice, mv.LateralRule(min_book_cents=ENTRY_BOOK_CENTS))
            break
    grow = niche or held
    st._campus_split(g, grow, max(2, lawyers // 10), delegated=True)
    mv.lay_off_idle(g, st.STEADY_LAYOFF_BELOW, st.STEADY_LAYOFF_TARGET, st.STEADY_LAYOFF_MAX)
    if mv.utilisation(g) >= 0.80:
        st._grow(g, grow, max(1, lawyers // 10))
        if niche and mv.associates_per_partner(g) > NICHE_LEVERAGE and mv.bank_quiet(g):
            mv.lateral_partner(
                g, st._busiest(g, niche)[-1], mv.LateralRule(min_book_cents=100_000_000)
            )
    fees = g.months[-1].revenue_cents if g.months else 0
    mv.revolver_cap(g, fees)
    mv.pitch_rfps(g)
    mv.cross_sell(g, 1)


def full_service(g: Game) -> None:
    from ptk.balance import strategies as st

    st.steady(g)
    year = g.ym[0]
    if year < FULL_SERVICE_FROM:
        return
    held = mv.practices_held(g)
    key = f"full_service_{year}"
    if g.notes.get(key):
        return
    target = g.notes.get(f"{key}_target")
    if target is not None and FULL_SERVICE_ADDS[target] in held:
        g.notes[key] = 1  # this year's practice arrived
        return
    missing = [i for i, p in enumerate(FULL_SERVICE_ADDS) if p not in held]
    if not missing:
        return
    g.notes[f"{key}_target"] = missing[0]
    if mv.bank_quiet(g):
        mv.lateral_partner(
            g, FULL_SERVICE_ADDS[missing[0]], mv.LateralRule(min_book_cents=ENTRY_BOOK_CENTS)
        )


PRACTICE_VARIANTS: Final = {"specialist": specialist, "full-service": full_service}
