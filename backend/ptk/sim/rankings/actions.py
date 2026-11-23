"""The March directory submission (spec 12.3; PT-M16): an action in the submission window
(March-April) choosing up to `max_matters` of the firm's public matters to showcase and up to
`max_referees` clients to name. Each referee spends `referee_cost` relationship points. Its
strength (0-1, public) is 0.7 x the showcased matters' mean weight (each matter's size against
`matter_full_cents`, full for a won, closed, settled or completed matter, a third for one still
open, none for one lost or collapsed; empty slots count 0) plus 0.3 x the referees' mean
relationship (empty slots 0). One submission a year."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Final, Literal

from ptk.sim.calendar import turn_to_ym
from ptk.sim.data_models import Balance
from ptk.sim.errors import InvalidActionError
from ptk.sim.hiring.actions import Outcome, acting_firm, spend_energy
from ptk.sim.interfaces import bump_relationship, relationship_score
from ptk.sim.log import inbox_item
from ptk.sim.rankings.models import Submission
from ptk.sim.state import GameState

MATTER_SHARE: Final = 0.7  # tunable-exempt: the submission's matters against its referees
OPEN_WEIGHT: Final = 1 / 3  # tunable-exempt: an open matter showcases a third as well
GOOD: Final = frozenset({"won", "closed", "settled", "done"})
SHOWCASE_MONTHS: Final = 18  # tunable-exempt: closed matters this recent may be showcased


@dataclass(frozen=True, slots=True)
class MakeSubmission:
    actor_id: int
    matter_ids: tuple[int, ...]
    referee_ids: tuple[int, ...]  # client ids
    kind: Literal["make_submission"] = "make_submission"


def matter_weight(state: GameState, firm_id: int, matter_id: int, balance: Balance) -> float:
    m = state.market.matter(matter_id)
    if m is None or m.firm_id != firm_id or m.pro_bono or m.status not in ("open", "closed"):
        raise InvalidActionError(f"matter {matter_id} is not one of the firm's matters")
    if m.status == "closed" and (
        m.closed_turn is None or m.closed_turn < state.turn - SHOWCASE_MONTHS
    ):
        raise InvalidActionError(f"matter {matter_id} closed too long ago to showcase")
    size = min(1.0, m.expected_fees_cents / balance.rankings.directory.matter_full_cents)
    if m.status == "open":
        return size * OPEN_WEIGHT
    return size if m.outcome in GOOD else 0.0


def strength(state: GameState, a: MakeSubmission, firm_id: int, balance: Balance) -> float:
    db = balance.rankings.directory
    matters = sum(matter_weight(state, firm_id, mid, balance) for mid in a.matter_ids)
    refs = 0.0
    for cid in a.referee_ids:
        if state.market.relationship(cid, firm_id) is None:
            raise InvalidActionError(f"client {cid} does not instruct the firm")
        refs += relationship_score(state, cid, firm_id) / 100
    ref_part = refs / db.max_referees if db.max_referees else 0.0
    return MATTER_SHARE * matters / db.max_matters + (1 - MATTER_SHARE) * ref_part


def make_submission(state: GameState, a: MakeSubmission, balance: Balance) -> Outcome:
    db = balance.rankings.directory
    firm = acting_firm(state, a.actor_id)
    year, month = turn_to_ym(state.turn, state.save_meta.start_ym)
    lo, hi = db.submission_months
    if not lo <= month <= hi:
        raise InvalidActionError("directory submissions are made in March and April")
    sub = state.standing.rankings.submission
    if sub is not None and sub.year == year:
        raise InvalidActionError(f"the firm has already made its {year} submission")
    if not a.matter_ids or len(a.matter_ids) > db.max_matters:
        raise InvalidActionError(f"a submission showcases 1 to {db.max_matters} matters")
    if len(a.referee_ids) > db.max_referees:
        raise InvalidActionError(f"a submission names at most {db.max_referees} referees")
    if len(set(a.matter_ids)) != len(a.matter_ids) or len(set(a.referee_ids)) != len(a.referee_ids):
        raise InvalidActionError("a matter or referee is named twice")
    value = strength(state, a, firm, balance)
    state = spend_energy(state, a.actor_id, "submission", balance)
    for cid in a.referee_ids:
        state = bump_relationship(state, cid, firm, -db.referee_cost)
    record = Submission(
        year=year,
        turn=state.turn,
        matter_ids=tuple(a.matter_ids),
        referee_ids=tuple(a.referee_ids),
        strength=round(value, 4),
    )
    rk = replace(state.standing.rankings, submission=record)
    state = replace(state, standing=replace(state.standing, rankings=rk))
    log = inbox_item(
        state.turn,
        firm,
        "submission_made",
        link_kind="rankings",
        link_id=0,
        matters=len(a.matter_ids),
        referees=len(a.referee_ids),
        strength=f"{round(value * 100)}%",
    )
    return Outcome(state=state, log=(log,))
