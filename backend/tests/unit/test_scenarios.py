"""PT-M7a sub-task 1: the biglaw spin-out's corporate associate reaches the December 2008
vote at the default track of 8 years."""

from __future__ import annotations

from dataclasses import replace

from ptk.sim.calendar import turn_to_ym
from ptk.sim.data_models import Balance, GameData
from ptk.sim.partnership.careers import eligible
from ptk.sim.people.phase import advance_class_year
from tests.partnership_support import start


def test_biglaw_spinout_corporate_associate_is_eligible_in_december_2008(
    data: GameData, balance: Balance
) -> None:
    g = start(data, balance, scenario="biglaw_spinout")
    state = g.state
    fp = state.partnership.of(state.player.id)
    assert fp is not None and fp.agreement.track_years == 8
    start_ym = state.save_meta.start_ym
    corp = next(
        p for p in state.people if p.role == "corporate_ma" and p.level.startswith("associate")
    )
    assert corp.level == "associate_4"  # class 4 in January 2005
    person = corp
    turn = 0
    while turn_to_ym(turn, start_ym) != (2008, 12):
        turn += 1
        person = advance_class_year(person, turn, start_ym, balance)
        if turn_to_ym(turn, start_ym) == (2008, 11):
            assert person.level == "associate_8"
    people = tuple(person if p.id == person.id else p for p in state.people)
    assert eligible(replace(state, people=people), fp, person.id, balance)
