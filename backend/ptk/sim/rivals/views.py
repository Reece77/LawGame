"""What the API may show of rivals (CLAUDE.md section 10): names, public figures (the legal
press's revenue, lawyers and PEP, as Am Law publishes them, in December), labels and the
firm's own dealings. Never a rival's demand, shocks, the player's effects, a key person's
book, portability or hidden traits."""

from __future__ import annotations

from ptk.sim.data_models import GameData
from ptk.sim.state import GameState

POOL_COUNSEL = "a smaller firm"  # tunable-exempt: words for a case's pooled opposing counsel


def name_for_key(state: GameState, data: GameData, key: str) -> str:
    """A panel key's firm name: a rival's current name, else clients.yaml's."""
    firm = state.rivals.by_key(key)
    if firm is not None:
        return firm.name
    for f in data.clients.panel_firms:
        if f.key == key:
            return f.name
    return key


def opposing_counsel(state: GameState, matter_id: int) -> tuple[str | None, int | None]:
    """(name, rival firm id) of a case's opposing counsel once known (the month after
    intake); a pool's name with no id; (None, None) before then or for non-cases."""
    key = dict(state.rivals.opposing).get(matter_id)
    if key is None:
        return None, None
    if key == "":
        return POOL_COUNSEL, None
    firm = state.rivals.by_key(key)
    return (firm.name, firm.id) if firm is not None else (key, None)
