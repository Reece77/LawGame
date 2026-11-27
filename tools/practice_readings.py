"""PT-M12's readings of the practice strategies (lane A): steady, specialist and full-service on
fixed seeds over the pure sim, one line per run and PT-M12's rows (ptk/balance/report.py).

    uv run --project backend python tools/practice_readings.py --seeds 1 2 3 --jobs 4
"""

from __future__ import annotations

import argparse
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--seeds", type=int, nargs="+", default=list(range(1, 41))  # PT-M18: ptk.balance.seeds.SEEDS)
    parser.add_argument("--turns", type=int, default=132)
    parser.add_argument("--jobs", type=int, default=os.cpu_count() or 1)
    parser.add_argument(
        "--strategies", nargs="+", default=["steady", "specialist", "full-service"]
    )
    parser.add_argument("--data", default="data", help="data folder (relative to backend/)")
    args = parser.parse_args()
    os.environ.setdefault("PTK_LLM_ADAPTER", "mock")
    os.chdir(BACKEND)
    sys.path.insert(0, str(BACKEND))
    from ptk.balance.report import FINAL_YEAR, YEAR_5, _pep_change, _pt_m12, play

    plan = [(s, seed) for s in args.strategies for seed in args.seeds]
    with ProcessPoolExecutor(args.jobs) as pool:
        results = list(pool.map(lambda_play, [(s, seed, args.turns, args.data) for s, seed in plan]))
    print(f"{'strategy':14} {'seed':>4} {'state':10} {'lawyers':>7} {'rev 2015':>10} "
          f"{'PEP 2015':>9} {'PEP 09/08':>9}")
    for r in results:
        last = r.december(FINAL_YEAR) or r.months[-1]
        pep = 0 if r.dissolved or last.pep_cents is None else last.pep_cents
        ch = _pep_change(r, YEAR_5)
        print(
            f"{r.strategy:14} {r.seed:>4} {r.game_state:10} {last.lawyers:>7} "
            f"{r.year_revenue(FINAL_YEAR) / 1e8:>9.2f}M {pep / 1e8:>8.2f}M "
            f"{'-' if ch is None else f'{ch * 100:+.1f}%':>9}"
        )
    for row in _pt_m12(results):
        print(f"{row.target:24} {row.value:40} {row.band:30} {row.ok}")
    _ = play
    return 0


def lambda_play(args: tuple[str, int, int, str]):  # type: ignore[no-untyped-def]
    from ptk.balance.report import play

    strategy, seed, turns, data = args
    return play(strategy, seed, turns, "standard", data)


if __name__ == "__main__":
    raise SystemExit(main())
