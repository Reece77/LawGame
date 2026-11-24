"""PT-M9's balance variant `steady_automated` (brief sub-task 8): steady with every area that
can be automated given to its owner under sensible limits, the player answering only one-offs
(approving each proposal: their central case is the steady plan's own) and keeping the moves
no area of spec 9.4 covers (the MP election's answer, the comp system and December's comp
round, the firm's practice groups). An area that cannot be automated yet (its seat is vacant
or opens at a later stage: before stage 3 the pricing director's and the executive
committee's) is the player's, so the script plays steady's move for it as steady would.

Registered in `ptk.balance.strategies.VARIANTS` in one line (lane A owns the runner). It reads
only what the player can see (the Automation view's figures, the inbox) and acts through
`Game.act`.
"""

from __future__ import annotations

from typing import Final

from ptk.balance import moves as mv
from ptk.balance.game import Game
from ptk.sim.automation import owners
from ptk.sim.automation.actions import AnswerProposal, GiveArea, SetAreaSettings

LIMIT_SHARE_BP: Final = 1_000  # a decision's limit: 10% of last year's fees (sensible limits)
LIMIT_FLOOR_CENTS: Final = 50_000_000  # and at least $500,000 (a lateral associate plan)
RFPS: Final = 2  # steady pitches two RFPs a month
CAMPUS_SHARE: Final = 10  # steady's class: a tenth of its lawyers a year


def _limit(g: Game) -> int:
    fees = g.months[-1].revenue_12m_cents if g.months else 0
    return max(LIMIT_FLOOR_CENTS, fees * LIMIT_SHARE_BP // 10_000)


def _class_size(g: Game) -> int:
    groups = sum(
        1
        for u in g.state.org.firm_units(g.state.player.id)
        if u.kind == "practice_group" and u.leader_id is not None
    )
    total = max(2, len(g.lawyers()) // CAMPUS_SHARE)
    return max(1, -(-total // max(1, groups)))


def automated(g: Game, area: str) -> bool:
    firm = g.state.player.id
    slots = owners.area_slots(g.state, firm, area, g.balance)
    return bool(slots) and all(g.state.automation.owner(firm, area, s) is not None for s in slots)


def automate(g: Game) -> None:
    """Give every area that can be automated to its best displayed fit; keep limits sensible
    as the firm grows (each January) and the guardrails at steady's settings."""
    state, b, data = g.state, g.balance, g.data
    firm = state.player.id
    limit = _limit(g)
    rails = {
        "bd": (("rfps_per_month", RFPS),),
        "hiring": (("class_size", min(30, _class_size(g))),),
    }
    for area in owners.area_keys(b):
        for slot in owners.area_slots(state, firm, area, b):
            o = g.state.automation.owner(firm, area, slot)
            want = rails.get(area, ())
            if o is None:
                people = owners.eligible_people(g.state, firm, area, slot, b, data)
                if not people:
                    continue
                best = max(
                    people,
                    key=lambda p: (owners.shown_area_score(g.state, firm, area, p, b, data), -p),
                )
                g.act(GiveArea(g.founder_id, area, best, slot, limit, 3 * limit, guardrails=want))
            elif g.ym[1] == mv.JANUARY and (
                o.limit_cents < limit or dict(o.guardrails) != dict(want)
            ):
                g.act(SetAreaSettings(g.founder_id, area, slot, limit, 3 * limit, guardrails=want))


def approve(g: Game) -> int:
    """The player's one-offs: every proposal waiting is approved."""
    made = 0
    for p in g.state.automation.pending(g.state.player.id):
        made += g.act(AnswerProposal(g.founder_id, p.id, True))
    return made


def steady_automated(g: Game) -> None:
    from ptk.balance import strategies as st

    automate(g)
    approve(g)
    mv.answer_election(g)
    mv.comp_system(g, "modified_lockstep")  # a change to the agreement: a one-off
    if not automated(g, "development"):
        mv.december_votes(g, st._admissions(g, 4.0))
    mv.comp_round(g)
    held = mv.practices_held(g)
    lawyers = len(g.lawyers())
    mv.practice_groups(g)
    if not automated(g, "hiring"):
        st._campus_split(g, held, max(2, lawyers // 10), delegated=True)
        if mv.utilisation(g) >= 0.80:
            st._grow(g, held, max(2, lawyers // 8))
    # PT-M7c (Reece, 2026-11-24; rule 2): steady's layoff rule, the managing partner's own call
    mv.lay_off_idle(g, st.STEADY_LAYOFF_BELOW, st.STEADY_LAYOFF_TARGET, st.STEADY_LAYOFF_MAX)
    if not automated(g, "laterals"):
        wanted = 2 + lawyers // 30
        missing = [p for p in st.STEADY_ADDS if p not in held]
        leverage = mv.associates_per_partner(g)
        if len(held) < wanted and missing:
            mv.lateral_partner(g, missing[0], mv.LateralRule(min_book_cents=100_000_000))
        elif (
            (leverage > 4.0 or st._per_equity(g) > 5.0)
            and mv.utilisation(g) >= 0.80
            and mv.bank_quiet(g)
        ):
            mv.lateral_partner(
                g, st._busiest(g, held)[-1], mv.LateralRule(min_book_cents=100_000_000)
            )
    if not automated(g, "billing"):
        fees = g.months[-1].revenue_cents if g.months else 0
        mv.revolver_cap(g, fees)
    if not automated(g, "bd"):
        mv.pitch_rfps(g)
        mv.cross_sell(g, 1)
    if not automated(g, "pricing"):
        mv.set_rates(g, None)
