"""PT-M8: the balance scripts fill vacant seats as a sensible player would (CLAUDE.md 9,
decision rule 2): each month, every open seat with no eligible holder gets the best
candidate by displayed fit who holds no other seat. The do-nothing script never does."""

from __future__ import annotations

from ptk.balance.game import Game
from ptk.sim.org.seat_models import EXCO
from ptk.sim.org.seats import (
    AppointSeat,
    candidates,
    exco_elected,
    in_play,
    managing_partner,
    seated_holder,
    slots,
)


def fill_seats(g: Game) -> None:
    state, b, data = g.state, g.balance, g.data
    firm = state.player.id
    actor = managing_partner(state, firm)
    if actor is None or actor != g.founder_id:
        return
    for seat in data.seats.seats:
        if seat.who == "player" or not in_play(g.state, firm, seat):
            continue
        if seat.key == EXCO and exco_elected(g.state, firm, b, data):
            continue
        for slot in slots(g.state, firm, seat, b):
            if seated_holder(g.state, firm, seat, slot, b) is not None:
                continue
            seated = {h.person_id for h in g.state.leadership.holders if h.seat != EXCO}
            seated |= {u.leader_id for u in g.state.org.firm_units(firm) if u.leader_id}
            if seat.key == EXCO:
                seated = {h.person_id for h in g.state.leadership.holders if h.seat == EXCO}
            for pid, _ in candidates(g.state, firm, seat, b):
                if pid in seated:
                    continue
                if g.act(AppointSeat(actor, seat.key, slot, pid)):
                    break
