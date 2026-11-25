"""PT-M12 test support: the v2 practices, and data with them dormant or removed.

`v1_data_dir` writes a copy of backend/data without the ten v2 practices (their practices.yaml
rows, roles and every mention in mixes, strengths and notables); `dormant_data_dir` keeps the
practices and their roles but nothing in the market touches them (demand one cent a year, no
mix, strength or notable names them). A practice the firm and the market never touch must
change nothing (the brief's sub-task 2 test).
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Final

import yaml

DATA: Final = Path(__file__).resolve().parents[1] / "data"
V2: Final = (
    "international_arbitration",
    "tax",
    "antitrust",
    "financial_regulation",
    "healthcare",
    "energy",
    "technology_privacy",
    "private_client",
    "insurance",
    "mass_torts",
)
# files whose mappings and lists may name a practice (beyond practices.yaml and roles.yaml)
MENTIONS: Final = ("clients.yaml", "cities.yaml", "firms.yaml", "balance.yaml", "notables.yaml")


PRACTICE_MAPS: Final = ("mix", "strong", "demand", "hours")  # keys whose values name practices


def _strip(node: Any, inside: bool = False) -> Any:
    """Drop the v2 practices from every practice-keyed mapping or list (under PRACTICE_MAPS)
    and every row about one (`practice: <v2>`); "energy" is also a sector and a balance key,
    so nothing else is touched."""
    if isinstance(node, dict):
        if node.get("practice") in V2:
            return None
        out = {}
        for k, v in node.items():
            if inside and k in V2:
                continue
            s = _strip(v, k in PRACTICE_MAPS)
            if s is None and v is not None:
                continue
            out[k] = s
        return out
    if isinstance(node, list):
        items = [_strip(x) for x in node if not (inside and isinstance(x, str) and x in V2)]
        return [x for x in items if x is not None]
    return node


def _copy(dest: Path) -> Path:
    shutil.copytree(DATA, dest)
    for name in MENTIONS:
        path = dest / name
        path.write_text(yaml.safe_dump(_strip(yaml.safe_load(path.read_text())), sort_keys=False))
    return dest


def dormant_data_dir(dest: Path) -> Path:
    """The v2 practices present, untouched: demand a cent a year and named by no mix."""
    _copy(dest)
    path = dest / "practices.yaml"
    doc = yaml.safe_load(path.read_text())
    for p in doc["practices"]:
        if p["key"] in V2:
            p["demand_cents"] = 1
    path.write_text(yaml.safe_dump(doc, sort_keys=False))
    return dest


def v1_data_dir(dest: Path) -> Path:
    """v1's ten practices only (the v2 rows, roles and mentions removed)."""
    _copy(dest)
    path = dest / "practices.yaml"
    doc = yaml.safe_load(path.read_text())
    doc["practices"] = [
        {**p, "cross_sell": {k: v for k, v in p["cross_sell"].items() if k not in V2}}
        for p in doc["practices"]
        if p["key"] not in V2
    ]
    path.write_text(yaml.safe_dump(doc, sort_keys=False))
    path = dest / "roles.yaml"
    doc = yaml.safe_load(path.read_text())
    doc["roles"] = [r for r in doc["roles"] if r.get("practice") not in V2]
    path.write_text(yaml.safe_dump(doc, sort_keys=False))
    return dest
