"""The state cache (PT-M7; TST M30's long state-cache check, ported): three scripted strategies
on seeds 1-3 for v1's 132 months (January 2005 to December 2015), the engine in memory
(`ptk.balance.game`), the full state and the ledger balances hashed after every month.
`tests/fixtures/state_hashes.json` holds the recorded hashes (`--update-state-cache`); the
nightly test compares a run with them month by month and names the first month that differs.
A speed-up never changes a result; an intentional change of results re-records it, with the
reason in CHANGELOG.md (CLAUDE.md section 8, as golden snapshots).

Ported from backend/tst/balance/m30.py @ 121d318a (Tech Startup Tycoon); changed: Partner
Track's strategies (steady, pyramid, boutique), 132 turns, its data loader and fixture path; the
Digester, `month_digest`, `first_difference` and the fixture format as TST's.

The digest is canonical: dataclasses by their compared fields in order, tuples and lists in
order (their order is the engine's iteration order, so it is part of the result), sets and
mappings sorted (their order is not). Floats are hashed exactly (`repr`), so the fixture is
recorded and checked on Linux (CI); libm's last bits can differ on another platform.

Immutable sub-objects are shared between one month's state and the next, so their digests are
memoised by identity for the month after (`Digester`): hashing a late state then costs what
changed, not the whole state.
"""

from __future__ import annotations

import dataclasses
import enum
import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from functools import cache
from pathlib import Path
from typing import Final

from ptk.balance.game import Game, start_game
from ptk.balance.report import SCENARIO
from ptk.loader import load_balance, load_game_data
from ptk.sim.data_models import Balance, GameData

SEEDS: Final = (1, 2, 3)
# Growth with delegates and practice groups, high leverage with income partners, and a small
# premium firm: between them every system v1's turn runs.
STRATEGIES: Final = ("steady", "pyramid", "boutique")
TURNS: Final = 132  # January 2005 to December 2015
DATA: Final = Path(__file__).resolve().parents[2] / "data"
HASH_FILE: Final = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "state_hashes.json"
HEX: Final = 16  # characters of each month's sha256 kept in the fixture

type Hashes = dict[str, list[str]]  # "strategy/seed" -> one hex digest per month played


@cache
def loaded() -> tuple[GameData, Balance]:
    return load_game_data(DATA), load_balance(DATA)


_FIELDS: dict[type, tuple[str, ...]] = {}


def _fields(cls: type) -> tuple[str, ...]:
    names = _FIELDS.get(cls)
    if names is None:
        names = tuple(f.name for f in dataclasses.fields(cls) if f.compare)
        _FIELDS[cls] = names
    return names


class Digester:
    """Canonical digests of engine values. Dataclass instances and tuples are memoised by
    identity, holding the object so its id cannot be reused; `next_month` keeps only what
    the last digest saw, so the memo never outgrows one state."""

    def __init__(self, skip: Mapping[type, frozenset[str]] | None = None) -> None:
        self._memo: dict[int, tuple[object, bytes]] = {}
        self._seen: dict[int, tuple[object, bytes]] = {}
        # M37: fields left out of the digest, by class (fields a later milestone added, to
        # compare a run with a fixture recorded before them: tst.balance.m37)
        self._skip = skip or {}

    def next_month(self) -> None:
        self._memo, self._seen = self._seen, {}

    def digest(self, value: object) -> bytes:
        key = id(value)
        hit = self._seen.get(key)
        if hit is not None and hit[0] is value:
            return hit[1]
        hit = self._memo.get(key)
        if hit is not None and hit[0] is value:
            self._seen[key] = hit
            return hit[1]
        out = hashlib.sha256(self._encode(value)).digest()
        if isinstance(value, tuple) or dataclasses.is_dataclass(value):
            self._seen[key] = (value, out)
        return out

    def _encode(self, value: object) -> bytes:
        if value is None or isinstance(value, bool | int | str):
            return f"{type(value).__name__}:{value!r}".encode()
        if isinstance(value, float):
            return f"float:{value!r}".encode()
        if isinstance(value, enum.Enum):
            return f"enum:{type(value).__name__}.{value.name}".encode()
        if dataclasses.is_dataclass(value) and not isinstance(value, type):
            cls = type(value)
            parts = [f"dc:{cls.__module__}.{cls.__qualname__}".encode()]
            left_out = self._skip.get(cls, frozenset())
            parts += [
                self.digest(getattr(value, name)) for name in _fields(cls) if name not in left_out
            ]
            return b"|".join(parts)
        if isinstance(value, tuple | list):
            return b"seq:" + b"".join(self.digest(v) for v in value)
        if isinstance(value, frozenset | set):
            return b"set:" + b"".join(sorted(self.digest(v) for v in value))
        if isinstance(value, Mapping):
            items = sorted(self.digest(k) + self.digest(v) for k, v in value.items())
            return b"map:" + b"".join(items)
        raise TypeError(f"no canonical digest for {type(value).__qualname__}")


def month_digest(digester: Digester, game: Game) -> str:
    """The digest of the game's full state and ledger balances after a month."""
    state = digester.digest(game.state)
    balances = digester.digest(game.balances)
    digester.next_month()
    return hashlib.sha256(state + balances).hexdigest()[:HEX]


def strategy(name: str) -> Callable[[Game], None]:
    from ptk.balance.strategies import PLAYABLE

    return PLAYABLE[name]


def run_hashes(job: tuple[str, int], turns: int = TURNS) -> list[str]:
    """One strategy's game on one seed: a digest after every month played."""
    name, seed = job
    data, balance = loaded()
    game = start_game(data, balance, seed, SCENARIO)
    script = strategy(name)
    digester = Digester()
    out: list[str] = []
    while game.state.turn < turns and not game.state.ended:
        script(game)
        game.turn()
        out.append(month_digest(digester, game))
    return out


def key(name: str, seed: int) -> str:
    return f"{name}/{seed}"


def jobs() -> list[tuple[str, int]]:
    return [(name, seed) for name in STRATEGIES for seed in SEEDS]


def all_hashes(workers: int = 1, turns: int = TURNS) -> Hashes:
    todo = jobs()
    if workers <= 1:
        return {key(*j): run_hashes(j, turns) for j in todo}
    with ProcessPoolExecutor(max_workers=workers) as pool:
        runs = pool.map(run_hashes, todo, [turns] * len(todo))
        return {key(*j): r for j, r in zip(todo, runs, strict=True)}


def recorded() -> Hashes:
    out: Hashes = json.loads(HASH_FILE.read_text(encoding="utf-8"))
    return out


def write(hashes: Hashes) -> None:
    HASH_FILE.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(hashes, indent=0, sort_keys=True) + "\n"
    HASH_FILE.write_text(text, encoding="utf-8", newline="\n")


def first_difference(got: Sequence[str], want: Sequence[str]) -> str | None:
    """None when the runs are identical, else the first month that differs (turn 0 is
    January 2005: the n-th digest is the state after turn n-1)."""
    for turn, (g, w) in enumerate(zip(got, want, strict=False)):
        if g != w:
            return f"first differs after turn {turn}: {g} != {w}"
    if len(got) != len(want):
        return f"{len(got)} months played, {len(want)} recorded"
    return None
