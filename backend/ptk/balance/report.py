"""Playing the strategies and checking docs/balance-targets.md (PT-M7).

Ported from backend/tst/balance/report.py @ 121d318a (Tech Startup Tycoon) as a framework:
`play` runs one strategy on one seed and keeps only plain numbers (`RunResult`), so runs can go
to worker processes; `evaluate` turns a set of results into one row per target; `table` prints
them with TST's verdicts and known misses. Changed: Partner Track's targets T1-T12 and their
measures (each defined in docs/balance-targets.md's "Measures"), its strategies and variants.
"""

from __future__ import annotations

import time
from collections import Counter
from collections.abc import Iterable, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from statistics import median
from typing import Final

from ptk.balance.game import PLAYER, Game, Month, start_game
from ptk.balance.known_misses import known_miss, verdict
from ptk.balance.strategies import PLAYABLE, STRATEGIES
from ptk.loader import load_balance, load_game_data
from ptk.sim.calendar import ym_to_turn
from ptk.sim.data_models import Balance, GameData
from ptk.sim.state import GameState

SEEDS: Final = tuple(range(1, 11))
TURNS: Final = 132  # January 2005 to December 2015
SCENARIO: Final = "biglaw_spinout"
FINAL_YEAR: Final = 2015  # "year 11"
YEAR_5: Final = 2009
DIFFICULTY_RUNS: Final = (("steady", "easy"), ("steady", "hard"))  # T5
VARIANT_RUNS: Final = ("lateral-rocket-heeded", "restructuring")  # T9, T8
CLASS_YEAR: Final = 2006  # T6: the first September class a 2005 start can hire
TRANSACTIONAL: Final = ("corporate_ma", "private_equity", "capital_markets", "banking_finance")
CENTS: Final = 100
MILLION: Final = 1_000_000 * CENTS


@dataclass(frozen=True, slots=True)
class RivalCheck:
    """T11 on one run's rivals: the worst gap to the pinned path, misses, the top 10 kept."""

    worst_gap: float
    misses: int
    kept: int


@dataclass(frozen=True, slots=True)
class RunResult:
    strategy: str
    seed: int
    difficulty: str
    turns: int
    seconds: float
    game_state: str
    ended_turn: int | None
    months: tuple[Month, ...]
    class_size: int  # T6: the CLASS_YEAR September class
    class_equity: int  # ... of them equity partners at the end
    rivals: RivalCheck | None
    refused: dict[str, int] = field(default_factory=dict)

    @property
    def dissolved(self) -> bool:
        return self.game_state == "dissolved"

    def december(self, year: int) -> Month | None:
        return next((m for m in self.months if m.ym == (year, 12)), None)

    def year_revenue(self, year: int) -> int:
        return sum(m.revenue_cents for m in self.months if m.ym[0] == year)

    def year_practice_revenue(self, year: int) -> Counter[str]:
        out: Counter[str] = Counter()
        for m in self.months:
            if m.ym[0] == year:
                for practice, cents in m.practice_revenue:
                    out[practice] += cents
        return out

    @property
    def score(self) -> float:
        """T2's score at year 11: what the founding partner (the player's partner) was
        allocated over 2005-2015 (TST's founder value, for a partnership); 0 for a firm that
        dissolved."""
        if self.dissolved or self.december(FINAL_YEAR) is None:
            return 0.0
        return float(sum(m.founder_comp_cents for m in self.months))


@cache
def _loaded(data_dir: str) -> tuple[GameData, Balance]:
    path = Path(data_dir)
    return load_game_data(path), load_balance(path)


def play(
    strategy: str,
    seed: int,
    turns: int = TURNS,
    difficulty: str = "standard",
    data_dir: str = "data",
) -> RunResult:
    """One strategy on one seed. Picklable arguments and result (worker processes)."""
    started = time.perf_counter()
    data, balance = _loaded(data_dir)
    game = start_game(data, balance, seed, SCENARIO, difficulty)
    script = PLAYABLE[strategy]
    for _ in range(turns):
        if game.state.ended:
            break
        script(game)
        game.turn()
    return _result(game, strategy, seed, difficulty, turns, time.perf_counter() - started)


def _result(
    game: Game, strategy: str, seed: int, difficulty: str, turns: int, seconds: float
) -> RunResult:
    state = game.state
    klass = game.hired_classes.get(CLASS_YEAR, ())
    equity = sum(
        1
        for pid in klass
        if pid in state.staff_ids(PLAYER) and state.person(pid).level == "equity_partner"
    )
    return RunResult(
        strategy=strategy,
        seed=seed,
        difficulty=difficulty,
        turns=turns,
        seconds=seconds,
        game_state=state.save_meta.game_state,
        ended_turn=state.save_meta.ended_turn,
        months=tuple(game.months),
        class_size=len(klass),
        class_equity=equity,
        rivals=rival_check(state, game.data, game.balance) if state.turn >= turns else None,
        refused=dict(game.refused),
    )


def rival_check(state: GameState, data: GameData, balance: Balance) -> RivalCheck:
    """T11 (PT-M5's measure): pinned rivals' FY revenue against history in 2009 and 2015,
    and how many of history's top 10 by 2015 revenue are in the game's top 10."""
    band = balance.rivals.pin.band
    ended = {
        e.firm: e.ym[0]
        for e in data.rivals.firms.events
        if e.kind in ("collapse", "absorbed", "merger")
    }
    ended |= {e.other: e.ym[0] for e in data.rivals.firms.events if e.kind == "merger" and e.other}

    def pinned(year: int) -> dict[str, int]:
        out = {}
        for f in data.rivals.firms.firms:
            if ended.get(f.key, 9999) <= year:
                continue
            point = next((p for p in f.path if p.year == year), None)
            if point and point.revenue_cents and point.src.startswith("rev S"):
                out[f.key] = point.revenue_cents
        return out

    worst, misses = 0.0, 0
    for year in (2009, FINAL_YEAR):
        for key, revenue in pinned(year).items():
            firm = state.rivals.by_key(key)
            record = (
                next((h for h in firm.history if h.year == year), None)
                if firm is not None
                else None
            )
            if record is None:
                misses += 1
                continue
            gap = record.revenue_cents / revenue - 1
            worst = max(worst, abs(gap))
            misses += abs(gap) > band
    history = sorted(pinned(FINAL_YEAR).items(), key=lambda kv: -kv[1])[:10]
    game = sorted(
        (f for f in state.rivals.firms if f.active),
        key=lambda f: -next((h.revenue_cents for h in f.history if h.year == FINAL_YEAR), 0),
    )[:10]
    kept = len({k for k, _ in history} & {f.key for f in game})
    return RivalCheck(worst, misses, kept)


def run_all(
    seeds: Sequence[int] = SEEDS,
    turns: int = TURNS,
    strategies: Iterable[str] = tuple(STRATEGIES),
    extra_runs: bool = True,
    jobs: int = 1,
    data_dir: str = "data",
) -> list[RunResult]:
    """Every strategy on every seed at standard difficulty, plus T5's difficulty runs and the
    T8/T9 variants."""
    plan = [(s, seed, "standard") for s in strategies for seed in seeds]
    if extra_runs:
        plan += [(s, seed, d) for s, d in DIFFICULTY_RUNS for seed in seeds]
        plan += [(v, seed, "standard") for v in VARIANT_RUNS for seed in seeds]
    if jobs <= 1:
        return [play(s, seed, turns, d, data_dir) for s, seed, d in plan]
    with ProcessPoolExecutor(jobs) as pool:
        futures = [pool.submit(play, s, seed, turns, d, data_dir) for s, seed, d in plan]
        return [f.result() for f in futures]


# --- Targets ---------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Row:
    target: str
    measure: str
    value: str
    band: str
    ok: bool | None  # None: printed only
    gate: bool = False  # a pass/fail target (T1, T2, T11, T12): the runner exits 1 if it fails
    score: float | None = None  # the numeric measure a known miss's bound reads


def _runs(
    results: Sequence[RunResult], strategy: str, difficulty: str = "standard"
) -> list[RunResult]:
    return [r for r in results if r.strategy == strategy and r.difficulty == difficulty]


def _in(value: float | None, low: float, high: float) -> bool:
    return value is not None and low <= value <= high


def _med(values: Iterable[float]) -> float | None:
    vals = list(values)
    return median(vals) if vals else None


def _m(cents: float | None) -> str:
    return "-" if cents is None else f"${cents / MILLION:.2f}M"


def _pct(x: float | None) -> str:
    return "-" if x is None else f"{x * 100:.1f}%"


def winners(results: Sequence[RunResult]) -> Counter[str]:
    """T2: the strategy with the best firm score on each seed (a tie wins nobody)."""
    wins: Counter[str] = Counter()
    standard = [r for r in results if r.difficulty == "standard" and r.strategy in STRATEGIES]
    for seed in sorted({r.seed for r in standard}):
        runs = sorted((r for r in standard if r.seed == seed), key=lambda r: -r.score)
        if len(runs) > 1 and runs[0].score > runs[1].score:
            wins[runs[0].strategy] += 1
    return wins


def evaluate(results: Sequence[RunResult]) -> list[Row]:
    return [
        *_t1(results),
        *_t2(results),
        *_t3(results),
        *_t4(results),
        *_t5(results),
        *_t6(results),
        *_t7(results),
        *_t8(results),
        *_t9(results),
        *_t10(results),
        *_t11(results),
        *_t12(results),
    ]


def real_2005(cents: float, year: int, data: GameData, balance: Balance) -> float:
    """A year's revenue in 2005 dollars: deflated by the market's rate index that year (the
    macro history's January rises, ptk.sim.matters.rates)."""
    from ptk.sim.matters.rates import market_index

    return cents / market_index(ym_to_turn(year, 6, (2005, 1)), (2005, 1), data, balance)


def _t1(results: Sequence[RunResult]) -> list[Row]:
    runs = _runs(results, "do-nothing")
    if not runs:
        return []
    data, balance = _loaded("data")

    def failing(r: RunResult, real: bool) -> bool:
        now, before = r.year_revenue(YEAR_5), r.year_revenue(YEAR_5 - 1)
        level = real_2005(now, YEAR_5, data, balance) if real else now
        return r.dissolved or (level < 3 * MILLION and now < before)

    failed = sum(failing(r, True) for r in runs)
    nominal = sum(failing(r, False) for r in runs)
    need = len(runs) - len(runs) // 10
    return [
        Row(
            "T1",
            "do-nothing fails (2009 revenue < $3M in 2005 dollars and falling, or dissolved)",
            f"{failed}/{len(runs)} ({nominal} nominal)",
            f">= {need}/{len(runs)}",
            failed >= need,
            gate=True,
            score=-failed,
        )
    ]


def _t2(results: Sequence[RunResult]) -> list[Row]:
    wins = winners(results)
    seeds = len({r.seed for r in results if r.difficulty == "standard"})
    if not wins and not seeds:
        return []
    top = max(wins.values(), default=0)
    best = ", ".join(f"{s} {n}" for s, n in wins.most_common())
    limit = seeds * 6 // 10
    return [
        Row(
            "T2",
            "no dominant strategy (best founder's earnings 2005-2015, wins)",
            best or "-",
            f"<= {limit}/{seeds} each",
            top <= limit,
            gate=True,
            score=top,
        )
    ]


def _t3(results: Sequence[RunResult]) -> list[Row]:
    runs = _runs(results, "steady")
    if not runs:
        return []
    lawyers = _med((r.december(FINAL_YEAR) or r.months[-1]).lawyers for r in runs)
    revenue = _med(r.year_revenue(FINAL_YEAR) for r in runs)
    return [
        Row(
            "T3.lawyers",
            "steady lawyers, Dec 2015 (median)",
            f"{lawyers}",
            "100-250",
            _in(lawyers, 100, 250),
            score=None if lawyers is None else -lawyers,  # fewer is worse
        ),
        Row(
            "T3.revenue",
            "steady revenue 2015 (median)",
            _m(revenue),
            "$60M-$150M",
            _in(revenue, 60 * MILLION, 150 * MILLION),
        ),
    ]


def _pep(results: Sequence[RunResult], strategy: str) -> float | None:
    vals = []
    for r in _runs(results, strategy):
        last = r.december(FINAL_YEAR)
        vals.append(0 if r.dissolved or last is None or last.pep_cents is None else last.pep_cents)
    return _med(vals)


def _t4(results: Sequence[RunResult]) -> list[Row]:
    out = []
    for strategy, lo, hi in (("steady", 0.5, 1.2), ("boutique", 1.0, 2.5), ("pyramid", 0.7, 1.6)):
        if not _runs(results, strategy):
            continue
        pep = _pep(results, strategy)
        out.append(
            Row(
                f"T4.{strategy}",
                f"{strategy} PEP 2015 (median)",
                _m(pep),
                f"${lo}M-${hi}M",
                _in(pep, lo * MILLION, hi * MILLION),
                score=None if pep is None else pep / MILLION,  # $M: higher is worse (above band)
            )
        )
    return out


def _t5(results: Sequence[RunResult]) -> list[Row]:
    out = []
    for difficulty, lo, hi in (("easy", 0.0, 0.10), ("standard", 0.05, 0.20), ("hard", 0.20, 0.45)):
        runs = _runs(results, "steady", difficulty)
        if not runs:
            continue
        rate = sum(r.dissolved for r in runs) / len(runs)
        out.append(
            Row(
                f"T5.{difficulty}",
                f"steady dissolves ({difficulty})",
                _pct(rate),
                f"{lo:.0%}-{hi:.0%}",
                _in(rate, lo, hi),
                score=-rate,  # too few dissolve is the miss: fewer is worse
            )
        )
    return out


def _attrition(r: RunResult) -> list[float]:
    """Associates who left in each full year / the year's average associates."""
    out = []
    for year in range(2006, FINAL_YEAR + 1):
        ms = [m for m in r.months if m.ym[0] == year]
        avg = sum(m.associates for m in ms) / len(ms) if len(ms) == 12 else 0
        if avg >= 2:
            out.append(sum(m.associates_left for m in ms) / avg)
    return out


def _t6(results: Sequence[RunResult]) -> list[Row]:
    rates = [
        x
        for r in results
        if r.difficulty == "standard" and r.strategy in STRATEGIES and r.strategy != "do-nothing"
        for x in _attrition(r)
    ]
    attrition = _med(rates)
    steady = _runs(results, "steady")
    size = sum(r.class_size for r in steady)
    share = sum(r.class_equity for r in steady) / size if size else None
    return [
        Row(
            "T6.attrition",
            "associate attrition a year (median of years and strategies)",
            _pct(attrition),
            "15%-25%",
            _in(attrition, 0.15, 0.25),
        ),
        Row(
            "T6.partners",
            f"steady: Sept {CLASS_YEAR} class made equity partner by Dec 2015",
            _pct(share),
            "8%-15%",
            _in(share, 0.08, 0.15),
        ),
    ]


def _t7(results: Sequence[RunResult]) -> list[Row]:
    runs = [r for r in results if r.difficulty == "standard" and r.strategy in STRATEGIES]
    months = [m for r in runs for m in r.months if m.ym[0] >= 2006]
    decembers = [m for m in months if m.ym[1] == 12]

    def med(attr: str, rows: Sequence[Month]) -> float | None:
        return _med(getattr(m, attr) for m in rows if getattr(m, attr) is not None)

    util, real = med("utilisation_bp", months), med("realisation_bp", decembers)
    coll, lock = med("collection_bp", decembers), med("lockup_days", decembers)
    bp = lambda x: None if x is None else x / 10_000  # noqa: E731
    return [
        Row(
            "T7.realisation", "median realisation", _pct(bp(real)), "84%-92%", _in(real, 8400, 9200)
        ),
        Row("T7.collection", "median collection", _pct(bp(coll)), "93%-98%", _in(coll, 9300, 9800)),
        Row(
            "T7.utilisation", "median utilisation", _pct(bp(util)), "75%-90%", _in(util, 7500, 9000)
        ),
        Row(
            "T7.lockup",
            "median lockup (days)",
            "-" if lock is None else f"{lock:.0f}",
            "90-150",
            _in(lock, 90, 150),
        ),
    ]


def _change(r: RunResult) -> float | None:
    before = r.year_revenue(2008)
    return (
        None
        if before <= 0 or (r.dissolved and (r.ended_turn or 0) < ym_to_turn(2009, 12, (2005, 1)))
        else r.year_revenue(2009) / before - 1
    )


def _t8(results: Sequence[RunResult]) -> list[Row]:
    corporate, restructuring = [], []
    for r in results:
        if r.difficulty != "standard":
            continue
        mix = r.year_practice_revenue(2008)
        total = sum(mix.values())
        if total <= 0:
            continue
        change = _change(r)
        if change is None:
            continue
        if sum(mix[p] for p in TRANSACTIONAL) / total >= 0.5:
            corporate.append(change)
        mix09 = r.year_practice_revenue(2009)
        if sum(mix09.values()) > 0 and mix09["restructuring"] / sum(mix09.values()) > 0.2:
            restructuring.append(change)
    c, s = _med(corporate), _med(restructuring)
    return [
        Row(
            "T8.corporate",
            f"2009 vs 2008, corporate-heavy firms (n={len(corporate)})",
            _pct(c),
            "-30% to -10%",
            _in(c, -0.30, -0.10),
            score=c,  # a smaller fall is worse
        ),
        Row(
            "T8.restructuring",
            f"2009 vs 2008, restructuring > 20% (n={len(restructuring)})",
            _pct(s),
            "-5% to +20%",
            _in(s, -0.05, 0.20),
            score=s,  # more growth is worse
        ),
    ]


def _t9(results: Sequence[RunResult]) -> list[Row]:
    out = []
    rocket = _runs(results, "lateral-rocket")
    if rocket:
        n = sum(r.dissolved for r in rocket)
        out.append(
            Row(
                "T9.rocket",
                "lateral rocket dissolves by 2015",
                f"{n}/{len(rocket)}",
                "3-6/10",
                3 <= n <= 6,
                score=float(n),  # too many dissolve: more is worse
            )
        )
    heeded = _runs(results, "lateral-rocket-heeded")
    if heeded:
        n = sum(r.dissolved for r in heeded)
        out.append(
            Row(
                "T9.heeded",
                "the rocket with the CFO's warnings heeded dissolves",
                f"{n}/{len(heeded)}",
                "<= 1/10",
                n <= 1,
                score=float(n),
            )
        )
    return out


def _burnout(results: Sequence[RunResult], strategy: str) -> float | None:
    runs = _runs(results, strategy)
    burnouts = sum(m.burnouts for r in runs for m in r.months)
    years = sum(m.associates for r in runs for m in r.months) / 12
    return burnouts / years if years > 0 else None


def _t10(results: Sequence[RunResult]) -> list[Row]:
    pyramid, steady = _burnout(results, "pyramid"), _burnout(results, "steady")
    ratio = None if not pyramid or not steady else pyramid / steady
    return [
        Row(
            "T10.ratio",
            "pyramid burnout / steady's (per associate-year)",
            "-" if ratio is None else f"{ratio:.2f}x",
            ">= 2x",
            ratio is not None and ratio >= 2.0,
            score=None if ratio is None else -ratio,  # a smaller ratio is worse
        ),
        Row(
            "T10.steady",
            "steady burnout a year",
            _pct(steady),
            "<= 5%",
            steady is not None and steady <= 0.05,
        ),
    ]


def _t11(results: Sequence[RunResult]) -> list[Row]:
    checks = [
        r.rivals
        for r in results
        if r.rivals is not None and r.difficulty == "standard" and r.strategy == "steady"
    ]
    if not checks:
        return []
    worst = max(c.worst_gap for c in checks)
    misses = sum(c.misses for c in checks)
    kept = min(c.kept for c in checks)
    return [
        Row(
            "T11",
            "rivals hold history (worst gap, misses, top-10 kept)",
            f"{worst:.1%}, {misses}, {kept}",
            "±15%, 0, >= 8",
            misses == 0 and kept >= 8,
            gate=True,
        )
    ]


def _t12(results: Sequence[RunResult]) -> list[Row]:
    runs = _runs(results, "steady")
    ms = [m.seconds * 1000 for r in runs for m in r.months if m.ym[0] == FINAL_YEAR]
    t = _med(ms)
    return [
        Row(
            "T12",
            "steady's median turn in 2015 (pure sim, runner's machine)",
            "-" if t is None else f"{t:.0f} ms",
            "<= 250 ms",
            t is not None and t <= 250,
            gate=False,  # the gate is `make check-timing` (alone; the runner's workers share cores)
            score=t,
        )
    ]


def table(rows: Sequence[Row]) -> str:
    width = max(len(r.measure) for r in rows)
    lines = []
    marks = {"printed": "    ", "ok": " ok ", "known": "MISS", "fail": "FAIL"}
    for r in rows:
        v = verdict(r)
        known = known_miss(r.target) if v == "known" else None
        tail = f"  KNOWN MISS ({known.owner})" if known else ""
        lines.append(
            f"{marks[v]} {r.target:16s} {r.measure:{width}s}  {r.value:>24s}  ({r.band}){tail}"
        )
    return "\n".join(lines)


def runs_table(results: Sequence[RunResult]) -> str:
    """One line per run: the end state and 2015's numbers."""
    head = ("strategy", "seed", "diff", "state", "lawyers", "revenue 2015", "PEP", "09/08", "secs")
    lines = [" ".join(f"{h:>10s}" for h in head)]
    for r in sorted(results, key=lambda r: (r.strategy, r.difficulty, r.seed)):
        last = r.december(FINAL_YEAR) or (r.months[-1] if r.months else None)
        change = _change(r)
        lines.append(
            f"{r.strategy:24s} {r.seed:4d} {r.difficulty:8s} {r.game_state:10s} "
            f"{last.lawyers if last else 0:7d} {_m(r.year_revenue(FINAL_YEAR)):>12s} "
            f"{_m(last.pep_cents if last else None):>10s} {_pct(change):>9s} {r.seconds:6.0f}"
        )
    return "\n".join(lines)
