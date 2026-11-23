"""PT-M16's printed checks (`ptk.standing_pace`): on each seed, the steady firm's years to the
market's top decile in a practice, its highest card share in its first five years, and T3's
lawyers and revenue and T4's PEP in 2015.

    uv run --project backend python tools/reputation_pace.py              # seeds 1-10
    uv run --project backend python tools/reputation_pace.py --seeds 1 2 --jobs 2
"""

from __future__ import annotations

import argparse
import os
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))


def main() -> int:
    from ptk.standing_pace import run_all

    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--seeds", type=int, nargs="+", default=list(range(1, 11)))
    parser.add_argument("--jobs", type=int, default=os.cpu_count() or 1)
    args = parser.parse_args()
    rows = run_all(tuple(args.seeds), args.jobs)
    print("| Seed | Outcome | Years to top decile | Practice (2015) | Rep / top (2015) | Card max, first 5 years | Lawyers 2015 | Revenue 2015 | PEP 2015 |")
    print("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for r in rows:
        last = r.years[-1] if r.years else None
        print(
            f"| {r.seed} | {r.game_state} | {r.years_to_top or '-'} | "
            f"{last.practice if last else '-'} | "
            f"{f'{last.reputation} / {last.top}' if last else '-'} | "
            f"{r.card_max_first_years / 100:.1f}% | {r.lawyers_2015} | "
            f"${r.revenue_2015 / 1e8:.1f}M | "
            f"{'-' if r.pep_2015 is None else f'${r.pep_2015 / 1e8:.2f}M'} |"
        )
    lawyers = statistics.median(r.lawyers_2015 for r in rows)
    peps = [r.pep_2015 or 0 for r in rows]
    tops = [r.years_to_top for r in rows if r.years_to_top is not None]
    print()
    print(f"median lawyers 2015 {lawyers}; median PEP 2015 ${statistics.median(peps) / 1e8:.2f}M")
    print(f"reached the top decile on {len(tops)} of {len(rows)} seeds; years {sorted(tops)}")
    full = sum(1 for r in rows if r.card_max_first_years >= 10_000)
    print(f"seeds billing at the full card within five years: {full}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
