"""Check that files copied AS IS from Tech Startup Tycoon have not drifted (ADR PT-0001).

VENDORED.md lists every copied or ported file. For AS IS files it records the SHA-256 of
the upstream file after the package rename (tst -> ptk and the like), so this check needs
no network: an AS IS file must hash to its recorded value. Ported files carry a header
naming their upstream path and commit instead and are not hashed.

    python tools/check_vendored.py                    # CI: verify
    python tools/check_vendored.py --record ../tst    # after re-copying from a TST clone

PT-M19a (ADR PT-0019): it also checks frontend/src/core/, a copy of sim-core's `ui/` at the
pinned tag, against that tag's MANIFEST.json (as Plaza's tools/check_ui.py does): the manifest's
own SHA-256 is pinned here (taken from the tag), so no sim-core checkout is needed, and every
file's SHA-256 must match the manifest. Upgrading sim-core re-copies `ui/` and updates both.
"""

from __future__ import annotations

import hashlib
import json
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


CORE_UI = REPO / "frontend" / "src" / "core"
SIMCORE_TAG = "v0.1.0"
MANIFEST_SHA256 = "1ecdf03bf74d22308fb825d45106c4fe11d08ee057b5a15f0b910606a207a835"
CORE_UI_SKIP = ("MANIFEST.json", "README.md")


def core_ui_problems(root: Path = CORE_UI) -> list[str]:
    manifest = root / "MANIFEST.json"
    if not manifest.is_file():
        return ["frontend/src/core/MANIFEST.json is missing"]
    out = []
    if hashlib.sha256(manifest.read_bytes()).hexdigest() != MANIFEST_SHA256:
        out.append(f"frontend/src/core/MANIFEST.json is not sim-core {SIMCORE_TAG}'s")
    recorded = json.loads(manifest.read_text(encoding="utf-8"))
    found = {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file() and p.name not in CORE_UI_SKIP
    }
    return out + [
        f"frontend/src/core: {name} differs from sim-core {SIMCORE_TAG}'s ui/"
        for name in sorted(set(recorded) | set(found))
        if recorded.get(name) != found.get(name)
    ]


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
    found = verify() + core_ui_problems()
    for problem in found:
        print(problem)
    print(f"vendored files OK; UI shell matches sim-core {SIMCORE_TAG}" if not found else f"{len(found)} problem(s)")
    sys.exit(1 if found else 0)
