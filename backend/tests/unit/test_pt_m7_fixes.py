"""Engine fixes PT-M7's strategy scripts brought to light (each failed before its fix)."""

from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path

from ptk.sim.data_models import Balance, GameData
from ptk.sim.partnership.common import firm_partnership, put
from ptk.sim.partnership.governance import resolve_votes
from ptk.sim.partnership.models import Vote, with_vote
from ptk.sim.rng import RngFactory
from tests.matters_support import game

SIM = Path(__file__).resolve().parents[2] / "ptk" / "sim"


def test_every_template_the_engine_queues_exists(data: GameData) -> None:
    """`queue_event(state, firm, "<template>", ...)` names a template id, not a trigger: the
    no-confidence petition was queued as "no_confidence" and crashed the director."""
    queued = set()
    for path in SIM.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        queued |= set(re.findall(r'queue_event\(\s*[\w.]+,\s*[\w.]+,\s*"(\w+)"', text))
    assert {"no_confidence_petition", "covenant_breach", "partner_group_exit"} <= queued
    for template_id in queued:
        assert data.event_template(template_id).id == template_id


def test_a_vote_on_someone_who_has_left_is_withdrawn(data: GameData, balance: Balance) -> None:
    """A December candidate whose notice ends in phase 1 has no employment when the vote is
    counted: the vote is withdrawn, not applied (it asserted before)."""
    state = game(data, balance)
    fp = firm_partnership(state, state.player.id)
    leaver = next(
        e for e in state.staff(state.player.id) if not state.person(e.person_id).is_founder
    )
    vote = Vote(
        id=99,
        firm_id=fp.firm_id,
        kind="admission",
        subject_id=leaver.person_id,
        params=(("track", "equity"),),
        opened_turn=state.turn,
        threshold_bp=5000,
    )
    state = put(state, with_vote(fp, vote))
    state = replace(state, employments=tuple(e for e in state.employments if e.id != leaver.id))
    month = resolve_votes(state, RngFactory(1), balance, data)
    got = next(v for v in firm_partnership(month.state, fp.firm_id).votes if v.id == 99)
    assert got.status == "withdrawn" and got.resolved_turn == state.turn
