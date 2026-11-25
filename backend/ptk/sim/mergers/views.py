"""Read-only views of deals for the API and governance (no hidden values: ADR PT-0016 4)."""

from __future__ import annotations

from ptk.sim.state import GameState


def deal_title(state: GameState, deal_id: int) -> str:
    deal = state.mergers.deal(deal_id)
    if deal is None:
        return "a merger"
    firm = state.rivals.firm(deal.rival_id)
    name = firm.name if firm is not None else deal.rival_key
    if deal.form == "verein":
        return f"a verein with {name}"
    return f"absorption by {name}" if deal.absorbed else f"a merger with {name}"
