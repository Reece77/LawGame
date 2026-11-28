"""ADR-0002 purity guard: scan ptk/sim for forbidden imports and calls.

Ported from tests/unit/test_sim_purity.py @ 02fba2aa; changed: the package rename. PT-M19a
(ADR PT-0019): the scanner is sim-core's (`simcore_testing.purity`), called with PT's own
packages banned; its standard library and framework bans include every module this file
banned before. The cases below are unchanged.

The scanner is also run against throwaway fixture modules that each break one rule, to
prove that it actually catches violations.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from simcore_testing import purity

SIM_DIR = Path(__file__).resolve().parents[2] / "ptk" / "sim"

# PT's own packages the engine may not import (sim-core's scanner bans the standard library's
# clock, filesystem, network and process modules, sqlalchemy, alembic, fastapi and anthropic).
BANNED_PACKAGES = ("ptk.db", "ptk.api", "ptk.llm", "ptk.loader", "ptk.config")


def find_violations(path: Path, sim_root: Path = SIM_DIR) -> list[str]:
    # the package root is ptk/, so a module's dotted name starts with ptk (`from .. import llm`
    # inside ptk/sim resolves to ptk.llm)
    return purity.find_violations(path, sim_root.parent, BANNED_PACKAGES)


def _sim_files() -> Iterator[Path]:
    yield from sorted(SIM_DIR.rglob("*.py"))


def test_sim_package_is_pure() -> None:
    files = list(_sim_files())
    assert files, "no sim modules found"
    problems = [p for f in files for p in find_violations(f)]
    assert problems == []


@pytest.fixture
def fake_sim(tmp_path: Path) -> Path:
    """A throwaway ptk/sim package where test cases write forbidden modules."""
    root = tmp_path / "ptk" / "sim"
    root.mkdir(parents=True)
    (root / "__init__.py").write_text("")
    return root


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("import random\n", "imports random"),
        ("from time import monotonic\n", "imports time"),
        ("import os\n", "imports os"),
        ("from pathlib import Path\n", "imports pathlib"),
        ("import yaml\n", "imports yaml"),
        ("import io\n", "imports io"),
        ("from ptk.db import repository\n", "imports ptk.db"),
        ("from ptk import api\n", "imports ptk.api"),
        ("from .. import llm\n", "imports ptk.llm"),
        ("from ptk.loader import load_all\n", "imports ptk.loader"),
        ("import sqlalchemy\n", "imports sqlalchemy"),
        ("from fastapi import FastAPI\n", "imports fastapi"),
        ("import anthropic\n", "imports anthropic"),
        ("data = open('x').read()\n", "calls open()"),
        ("import datetime\nx = datetime.datetime.now()\n", "reads the clock"),
        ("from datetime import date\nx = date.today()\n", "reads the clock"),
        ("import numpy as np\nx = np.random.default_rng(1)\n", "uses np.random.default_rng"),
        ("import numpy as np\nx = np.random.rand()\n", "uses np.random.rand"),
        ("from numpy.random import default_rng\n", "imports numpy.random.default_rng"),
    ],
)
def test_scanner_flags_forbidden_module(fake_sim: Path, source: str, expected: str) -> None:
    module = fake_sim / "bad_module.py"
    module.write_text(source)
    problems = find_violations(module, fake_sim)
    assert any(expected in p for p in problems), problems


def test_scanner_allows_generator_annotation(fake_sim: Path) -> None:
    module = fake_sim / "ok_module.py"
    module.write_text(
        "import numpy as np\n"
        "from datetime import timedelta\n"
        "def draw(gen: np.random.Generator) -> float:\n"
        "    return float(gen.random())\n"
    )
    assert find_violations(module, fake_sim) == []
