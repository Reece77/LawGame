"""Era strength and the market's adoption by month (ADR PT-0011 2; ADR PT-0002 2, PT-0015).

Each era's strength (0-1) and the market's average adoption of it (0-1) are dated paths to
`history_end` (December 2025) in `legal_eras.yaml`; after it each runs linearly from its
December 2025 value to a target drawn U(lo, hi) at the era's `by` month, then holds. The targets
come from stream `tech_seed` (110), turn 0, key `(era_index, 0)` for strength and
`(era_index, 1)` for the market: drawn once per save, so every save is its own world and the
same seed always gives the same one. Before an era's `start` both are 0.

An era's strength on a task = its strength x its `tasks` weight for the task. Eras compound:
the combined strength-times-adoption on a task is 1 - prod(1 - s_e,t x a_e) (with one era,
ADR PT-0011 3's `strength x adoption`).
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ptk.sim.rng import RngFactory
from ptk.sim.tech.config import TASKS, EraDef, LegalEras, PathPoint, SeededTarget

MONTHS = 12  # tunable-exempt
STREAM_TURN = 0  # tunable-exempt: the seeded paths are drawn once, at turn 0
STRENGTH_KEY, MARKET_KEY = 0, 1  # tech_seed key tags
CACHE = 32  # tunable-exempt: saves' era worlds kept in memory


def _m(ym: tuple[int, int]) -> int:
    return ym[0] * MONTHS + ym[1] - 1


def _path_value(points: Sequence[PathPoint], m: int) -> float:
    if m < _m(points[0].ym):
        return 0.0
    prev = points[0]
    for p in points[1:]:
        pm = _m(p.ym)
        if m < pm:
            lo = _m(prev.ym)
            return prev.value + (p.value - prev.value) * (m - lo) / (pm - lo)
        prev = p
    return prev.value


@dataclass(frozen=True, slots=True)
class EraWorld:
    """A save's era paths: the history plus its drawn targets after `history_end`."""

    eras: LegalEras
    strength_targets: tuple[float | None, ...]  # by era index
    market_targets: tuple[float | None, ...]

    def _value(
        self,
        era: EraDef,
        points: Sequence[PathPoint],
        seeded: SeededTarget | None,
        target: float | None,
        ym: tuple[int, int],
    ) -> float:
        m = _m(ym)
        if m < _m(era.start):
            return 0.0
        end = _m(self.eras.history_end)
        if m <= end or seeded is None or target is None:
            return _path_value(points, min(m, end) if seeded is not None else m)
        base = _path_value(points, end)
        by = _m(seeded.by)
        if by <= end:
            return target
        return base + (target - base) * min(1.0, (m - end) / (by - end))

    def strength(self, index: int, ym: tuple[int, int]) -> float:
        era = self.eras.eras[index]
        return self._value(era, era.strength, era.strength_seeded, self.strength_targets[index], ym)

    def market(self, index: int, ym: tuple[int, int]) -> float:
        era = self.eras.eras[index]
        return self._value(era, era.market, era.market_seeded, self.market_targets[index], ym)

    def task_strengths(self, ym: tuple[int, int]) -> tuple[dict[str, float], ...]:
        """Each era's strength on each task this month (task -> s_e,t), in era order."""
        out = []
        for i, era in enumerate(self.eras.eras):
            s = self.strength(i, ym)
            out.append({t: s * w for t, w in era.tasks.items()} if s > 0 else {})
        return tuple(out)

    def market_adoption(self, ym: tuple[int, int]) -> tuple[float, ...]:
        return tuple(self.market(i, ym) for i in range(len(self.eras.eras)))


def _draw(rng: RngFactory, index: int, tag: int, seeded: SeededTarget | None) -> float | None:
    if seeded is None:
        return None
    u = float(rng.stream(STREAM_TURN, "tech_seed", index, tag).random())
    return seeded.lo + (seeded.hi - seeded.lo) * u


_WORLDS: OrderedDict[tuple[int, int], tuple[LegalEras, EraWorld]] = OrderedDict()


def era_world(eras: LegalEras, seed: int) -> EraWorld:
    """The save's era paths (memoised; the same seed always gives the same world)."""
    key = (id(eras), seed)
    hit = _WORLDS.get(key)
    if hit is not None and hit[0] is eras:
        _WORLDS.move_to_end(key)
        return hit[1]
    rng = RngFactory(seed)
    world = EraWorld(
        eras=eras,
        strength_targets=tuple(
            _draw(rng, i, STRENGTH_KEY, e.strength_seeded) for i, e in enumerate(eras.eras)
        ),
        market_targets=tuple(
            _draw(rng, i, MARKET_KEY, e.market_seeded) for i, e in enumerate(eras.eras)
        ),
    )
    _WORLDS[key] = (eras, world)
    while len(_WORLDS) > CACHE:
        _WORLDS.popitem(last=False)
    return world


def combined(
    strengths: Sequence[Mapping[str, float]], adoption: Sequence[float]
) -> dict[str, float]:
    """Task -> 1 - prod_e (1 - s_e,t x a_e): the combined strength x adoption on each task."""
    out: dict[str, float] = {}
    for task in TASKS:
        keep = 1.0
        for s, a in zip(strengths, adoption, strict=True):
            v = s.get(task, 0.0) * a
            if v > 0:
                keep *= 1.0 - v
        out[task] = 1.0 - keep
    return out


def efficiencies(
    exposure: Mapping[str, float],
    strengths: Sequence[Mapping[str, float]],
    adoption: Sequence[float],
) -> dict[str, float]:
    """ADR PT-0011 3: efficiency on each task = 1 - exposure x (strength x adoption)."""
    sa = combined(strengths, adoption)
    return {t: 1.0 - exposure[t] * sa[t] for t in exposure}
