"""Print one shard's backend test files for CI's `check` (PT-M11: three parallel shards).

    python3 tools/test_shard.py 3 0      # shard 0 of 3: paths relative to backend/
    python3 tools/test_shard.py --check 3
    python3 tools/test_shard.py 3 0 --run  # run that shard's tests (make check-shard)

A stable split: the test files (backend/tests/**/test_*.py, sorted by path) dealt round-robin
over the shards, so a file's shard changes only when files are added or renamed before it.
`--check` verifies every file is in exactly one shard.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"


def files() -> list[str]:
    return sorted(str(p.relative_to(BACKEND)) for p in (BACKEND / "tests").rglob("test_*.py"))


def shard(n: int, k: int) -> list[str]:
    return [f for i, f in enumerate(files()) if i % n == k]


def main(argv: list[str]) -> int:
    if argv[:1] == ["--check"]:
        n = int(argv[1])
        dealt = sorted(f for k in range(n) for f in shard(n, k))
        return 0 if dealt == files() else 1
    n, k = int(argv[0]), int(argv[1])
    if not 0 <= k < n:
        print(f"shard {k} is not in 0..{n - 1}", file=sys.stderr)
        return 2
    if argv[2:3] == ["--run"]:
        cmd = ["uv", "run", "pytest", "-q", "-n", "auto", "-m", "not timing and not nightly"]
        return subprocess.call([*cmd, *shard(n, k)], cwd=BACKEND)
    print(" ".join(shard(n, k)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
