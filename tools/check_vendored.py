"""Check that files copied AS IS from Tech Startup Tycoon have not drifted (ADR PT-0001).

VENDORED.md lists every copied or ported file. For AS IS files it records the SHA-256 of
the upstream file after the package rename (tst -> ptk and the like), so this check needs
no network: an AS IS file must hash to its recorded value. Ported files carry a header
naming their upstream path and commit instead and are not hashed.

    python tools/check_vendored.py                    # CI: verify
    python tools/check_vendored.py --record ../tst    # after re-copying from a TST clone
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TABLE = REPO / "VENDORED.md"
ROW = re.compile(
    r"^\| `(?P<local>[^`]+)` \| `(?P<upstream>[^`]+)` \| (?P<mark>AS IS|ported) \|"
    r" (?P<sha>[0-9a-f]{64}|—) \|$"
)
RENAMES = (
    (re.compile(r"\btst\."), "ptk."),
    (re.compile(r"from tst "), "from ptk "),
    (re.compile(r"import tst\b"), "import ptk"),
    (re.compile(r"TST_"), "PTK_"),
    (re.compile(r'"tst-'), '"ptk-'),
    (re.compile(r"\.tst\.sqlite"), ".ptk.sqlite"),
    (re.compile(r"Tech Startup Tycoon"), "Partner Track"),
)


def renamed(text: str) -> str:
    for pattern, repl in RENAMES:
        text = pattern.sub(repl, text)
    return text


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def rows() -> list[re.Match[str]]:
    return [m for line in TABLE.read_text().splitlines() if (m := ROW.match(line))]


def verify() -> list[str]:
    problems = []
    for row in rows():
        local = REPO / row["local"]
        if not local.is_file():
            problems.append(f"{row['local']}: listed in VENDORED.md but missing")
        elif row["mark"] == "AS IS" and digest(local.read_text()) != row["sha"]:
            problems.append(
                f"{row['local']}: differs from {row['upstream']} as vendored; re-copy it from "
                "TST, or mark it ported with a note"
            )
        elif row["mark"] == "ported" and "Ported from" not in local.read_text()[:2000]:
            problems.append(f"{row['local']}: ported file lacks its 'Ported from' header")
    return problems


def record(tst_root: Path) -> None:
    lines = TABLE.read_text().splitlines()
    for i, line in enumerate(lines):
        m = ROW.match(line)
        if m and m["mark"] == "AS IS":
            sha = digest(renamed((tst_root / m["upstream"]).read_text()))
            lines[i] = line.replace(m["sha"], sha)
    TABLE.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--record":
        record(Path(sys.argv[2]))
    found = verify()
    for problem in found:
        print(problem)
    print("vendored files OK" if not found else f"{len(found)} problem(s)")
    sys.exit(1 if found else 0)
