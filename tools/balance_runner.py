"""The balance runner (docs/balance-targets.md, spec 17): plays the v1 strategies on fixed seeds
over the pure sim and prints every target with its measured value. Exits 1 when a pass/fail
target (T1, T2, T11, T12) fails, or any target with --strict. A recorded known miss
(ptk/balance/known_misses.py) within its bound prints KNOWN MISS (<owner>) and does not fail.

Ported from tools/balance_runner.py @ 121d318a (Tech Startup Tycoon); changed: Partner Track's
package, strategies, 132 turns and the T5/T8/T9 extra runs.

    uv run --project backend python tools/balance_runner.py              # 5 x 10 x 132, + extras
    uv run --project backend python tools/balance_runner.py --turns 24 --seeds 1 2
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--seeds", type=int, nargs="+", default=list(range(1, 11)))
    parser.add_argument("--turns", type=int, default=132)
    parser.add_argument("--strategies", nargs="+", default=None)
    parser.add_argument("--no-extra", action="store_true", help="skip T5's, T8's and T9's runs")
    parser.add_argument("--jobs", type=int, default=os.cpu_count() or 1)
    parser.add_argument("--runs", action="store_true", help="also print one line per run")
    parser.add_argument("--strict", action="store_true", help="exit 1 if any band fails too")
    args = parser.parse_args()

    os.environ.setdefault("PTK_LLM_ADAPTER", "mock")
    os.chdir(BACKEND)
    sys.path.insert(0, str(BACKEND))
    from ptk.balance.known_misses import verdict
    from ptk.balance.report import evaluate, run_all, runs_table, table
    from ptk.balance.strategies import STRATEGIES

    strategies = args.strategies or list(STRATEGIES)
    unknown = set(strategies) - set(STRATEGIES)
    if unknown:
        parser.error(f"unknown strategies {sorted(unknown)}; choose from {list(STRATEGIES)}")
    started = time.perf_counter()
    results = run_all(
        seeds=args.seeds,
        turns=args.turns,
        strategies=strategies,
        extra_runs=not args.no_extra,
        jobs=args.jobs,
    )
    rows = evaluate(results)
    if args.runs:
        print(runs_table(results), end="\n\n")
    print(table(rows))
    print(
        f"\n{len(results)} runs x {args.turns} turns in {time.perf_counter() - started:.0f} s "
        f"wall clock with {args.jobs} jobs"
    )
    failed = [r for r in rows if verdict(r) == "fail" and (r.gate or args.strict)]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
