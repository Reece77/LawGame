"""T18, the AI era (PT-M18; the product manager's approval, 2026-11-27): PT-M14's criteria 2
and 4 on one seed, as `tools/tech_readings.py run_seed` reads them, without its `never` and
`ai-fixed` branches (criterion 3's).

Steady to December 2015 gives the saving at full adoption (criterion 2: a fully adopted firm's
AI-exposed tasks take 40-70% fewer hours by December 2030); `ai-hourly` to December 2029,
then 2030 three ways (AI off, untrained, trained) gives the junior cohort's growth (criterion
4: growth falls without training when AI removes the juniors' review hours, and training
restores at least half of the loss). The nightly's balance shards play it beside the runs
(`report.run_all`), and the summary judges row T18 (`report._t18`).
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, replace
from pathlib import Path

from ptk.balance.game import Game, start_game
from ptk.balance.seats import fill_seats
from ptk.balance.strategies import PLAYABLE, Script

AI_ERA = "ai-era"  # the pseudo-strategy of a T18 reading in the shards' results
JUNIORS = ("associate_1", "associate_2", "associate_3")  # tools/tech_readings.py's cohort


@dataclass(frozen=True, slots=True)
class AiEraReading:
    seed: int
    saving: float  # 1 - full adoption's mean efficiency over the exposed tasks, December 2030
    growth_off: float  # the 2030 cohort's mean ability gained in 2030, AI switched off
    growth_untrained: float  # ... AI on, no training
    growth_trained: float  # ... AI on, trained (ai-hourly)
    cohort: int  # juniors present in all three branches

    @property
    def lost(self) -> float:
        return self.growth_off - self.growth_untrained

    @property
    def restored(self) -> float | None:
        """The share of the loss that training restores (seeds whose cohort lost)."""
        if not self.cohort or self.lost <= 0:
            return None
        return (self.growth_trained - self.growth_untrained) / self.lost


def _play(game: Game, script: Script, until: tuple[int, int]) -> None:
    while not game.state.ended and game.ym <= until:
        fill_seats(game)
        script(game)
        game.turn()


def _juniors(game: Game) -> dict[int, float]:
    from ptk.sim.people.models import current_ability

    return {p.id: current_ability(p, game.data) for p in game.lawyers() if p.level in JUNIORS}


def read_seed(seed: int, data_dir: str = "data") -> AiEraReading:
    from ptk.balance.report import SCENARIO, _loaded
    from ptk.sim.tech import efficiency as ef

    data, balance = _loaded(str(Path(data_dir)))
    base = start_game(data, balance, seed, SCENARIO, "standard")
    _play(base, PLAYABLE["steady"], (2015, 12))
    full = ef.full_efficiency(base.state, data, (2030, 12))
    exposed = [x.key for x in data.market.tasks if x.ai_exposure >= balance.tech.exposed_min]
    saving = 1 - sum(full[x] for x in exposed) / len(exposed)
    stash = copy.deepcopy(base)
    _play(stash, PLAYABLE["ai-hourly"], (2029, 12))
    start = _juniors(stash)
    learn = []
    for name in ("off", "ai-untrained", "ai-hourly"):
        g = copy.deepcopy(stash)
        if name == "off":
            g.state = replace(g.state, tech=type(g.state.tech)())
            script = PLAYABLE["never"]
        else:
            script = PLAYABLE[name]
        _play(g, script, (2030, 12))
        end = _juniors(g)
        both = [pid for pid in start if pid in end]
        learn.append((both, {pid: end[pid] - start[pid] for pid in both}))
    common = set(learn[0][0]) & set(learn[1][0]) & set(learn[2][0])
    off, untrained, trained = (
        sum(d[pid] for pid in common) / len(common) if common else 0.0 for _, d in learn
    )
    return AiEraReading(seed, saving, off, untrained, trained, len(common))
