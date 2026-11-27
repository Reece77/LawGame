"""PT-M7c: decompose strategies' firms at December 2015 into the PEP identity's terms and the
growth terms (ptk/balance/economics.py), medians over seeds, against the benchmarks of
docs/research/firm-economics.md.

    uv run --project backend python tools/firm_economics.py --strategies steady boutique pyramid
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"


def _one(args: tuple[str, int, int, str]) -> dict:
    from ptk.balance.economics import decompose, row

    strategy, seed, year, data_dir = args
    d = decompose(strategy, seed, year, data_dir)
    return {"strategy": strategy, "seed": seed, "dissolved": d.dissolved, **row(d)}


def _fmt(v: object) -> str:
    if v is None:
        return "-"
    if isinstance(v, float):
        return f"{v:.2f}" if abs(v) < 10 else f"{v:.0f}"
    return str(v)


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--strategies", nargs="+", default=["steady", "boutique", "pyramid"])
    parser.add_argument("--seeds", type=int, nargs="+", default=list(range(1, 41)))  # PT-M18: ptk.balance.seeds.SEEDS
    parser.add_argument("--year", type=int, default=2015)
    parser.add_argument("--jobs", type=int, default=os.cpu_count() or 1)
    parser.add_argument("--data", default="data")
    parser.add_argument("--json", help="also write every run's row to this file")
    parser.add_argument("--runs", action="store_true", help="print one line per run too")
    args = parser.parse_args()
    os.environ.setdefault("PTK_LLM_ADAPTER", "mock")
    os.chdir(BACKEND)
    sys.path.insert(0, str(BACKEND))
    from ptk.balance.economics import medians

    plan = [(s, seed, args.year, args.data) for s in args.strategies for seed in args.seeds]
    with ProcessPoolExecutor(args.jobs) as pool:
        rows = list(pool.map(_one, plan))
    if args.json:
        Path(args.json).write_text(json.dumps(rows, indent=1))
    keys = [k for k in rows[0] if k not in ("strategy", "seed", "dissolved")]
    print("| strategy | " + " | ".join(keys) + " |")
    print("| --- " * (len(keys) + 1) + "|")
    for s in args.strategies:
        mine = [r for r in rows if r["strategy"] == s]
        if args.runs:
            for r in mine:
                flag = " (dissolved)" if r["dissolved"] else ""
                print(f"| {s} {r['seed']}{flag} | " + " | ".join(_fmt(r[k]) for k in keys) + " |")
        live = [r for r in mine if not r["dissolved"]] or mine
        med = medians([{k: r[k] for k in keys} for r in live])
        print(f"| **{s} median** | " + " | ".join(_fmt(med[k]) for k in keys) + " |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
