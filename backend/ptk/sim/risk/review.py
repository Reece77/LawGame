"""The general counsel's billing review (spec 9.1, 11.6; PT-M15 sub-task 7).

Each month a firm whose GC's seat effect e is above 0 reviews its bills before they go out:
with chance `audits.review_bp` x e it finds one padder (a rule-bender on the staff whose padding
has not come to light; the lowest id first, never a person flagged real) before a client does.
The padding stops (billing skips a found padder) and the find is a disciplinary trigger, as a
client's discovery would be. A vacant or weak GC (e <= 0) reviews nothing. The review's draw
is the first on the month's `discipline` generator (the firm's), before the cases' draws.
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from ptk.sim.data_models import Balance, GameData
from ptk.sim.risk import formulas as fx
from ptk.sim.risk.common import Books, gc_effect, lawyers, name
from ptk.sim.state import GameState


def billing_review(
    state: GameState, gen: np.random.Generator, books: Books, balance: Balance, data: GameData
) -> GameState:
    u = float(gen.random())
    e = gc_effect(state, books.firm_id, balance, data)
    if e <= 0 or u >= balance.risk.audits.review_bp / fx.BP * e:
        return state
    found = set(state.billing.padding_found)
    padders = [
        p
        for p in lawyers(state, books.firm_id, data)
        if "rule_bender" in p.tags and not p.real and p.id not in found
    ]
    if not padders:
        return state
    p = padders[0]
    billing = replace(state.billing, padding_found=tuple(sorted({*found, p.id})))
    books.inbox("padding_reviewed", p.id, link_kind="person", name=name(p))
    return replace(state, billing=billing)
