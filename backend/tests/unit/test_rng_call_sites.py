"""ADR-0013: one stream name per call site in ptk/sim.

Ported from tests/unit/test_rng_call_sites.py @ 02fba2aa; changed: the known-names set is a
parameter, so the fixtures do not depend on which streams exist yet. PT-M19a (ADR PT-0019):
the scanner is sim-core's (`simcore_testing.call_sites`). A name that is not a literal is
refused unless it is a parameter of the enclosing function (SC-0002 rule 4): the one such site
in ptk/sim is `ptk.sim.streams.RngFactory.stream`, which forwards its caller's name to
sim-core's factory.

Two call sites drawing from the same (turn, name, key) would reuse identical numbers, so
every `.stream(turn, "<name>", ...)` call must use a literal name no other call site uses.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from simcore_testing import call_sites

from ptk.sim.streams import STREAM_IDS

SIM_DIR = Path(__file__).resolve().parents[2] / "ptk" / "sim"


def stream_calls(path: Path, root: Path = SIM_DIR) -> list[tuple[str | None, str]]:
    """(stream name, PASSED_IN for a forwarded parameter, or None, "file:line") per call."""
    return call_sites.stream_calls(path, root)


def check_call_sites(
    files: list[Path], root: Path = SIM_DIR, known: frozenset[str] | None = None
) -> list[str]:
    names = frozenset(STREAM_IDS) if known is None else known
    problems = call_sites.check_call_sites(files, root, names)
    # sim-core's wording for a non-literal name; PT's cases below keep PT's message
    return [
        p.replace("must be a literal or a parameter", "must be a string literal") for p in problems
    ]


def test_only_the_factory_forwards_a_stream_name() -> None:
    forwarded = [
        where
        for path in sorted(SIM_DIR.rglob("*.py"))
        for name, where in stream_calls(path)
        if name == call_sites.PASSED_IN
    ]
    assert [w.split(":")[0] for w in forwarded] == ["streams.py"]


def test_each_stream_name_has_one_call_site() -> None:
    files = sorted(SIM_DIR.rglob("*.py"))
    assert check_call_sites(files) == []


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("a = rng.stream(t, 'misc', 1)\nb = rng.stream(t, 'misc', 2)\n", "already used"),
        ("name = 'misc'\na = rng.stream(t, name)\n", "must be a string literal"),
        ("a = rng.stream(t, 'nonsense')\n", "unknown stream"),
    ],
)
def test_scanner_catches_violations(tmp_path: Path, source: str, expected: str) -> None:
    module = tmp_path / "bad.py"
    module.write_text(source)
    problems = check_call_sites([module], tmp_path)
    assert any(expected in p for p in problems), problems


def test_scanner_accepts_distinct_names(tmp_path: Path) -> None:
    module = tmp_path / "ok.py"
    module.write_text("a = rng.stream(t, 'one', 1)\nb = rng.stream(t, 'two', 1, 2)\n")
    assert check_call_sites([module], tmp_path, frozenset({"one", "two"})) == []
