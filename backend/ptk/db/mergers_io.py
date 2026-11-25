"""Load and write mergers (schema v18, PT-M13): one row holding the `MergersState` as JSON (deals
with their books, terms and clearance, integrations, the verein, the exit; rewritten when it
changes), as `ptk.db.geo_io` does for geography. A save from before PT-M13 has no row: it has
never merged.
"""

from __future__ import annotations

import json
from dataclasses import asdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from ptk.db.automation_io import decode_with
from ptk.db.models import MergersRow
from ptk.sim.mergers import models as mm
from ptk.sim.mergers.models import EMPTY_MERGERS, MergersState

ROW_ID = 1  # the one row


def load_mergers(session: Session) -> MergersState:
    row = session.scalar(select(MergersRow).where(MergersRow.id == ROW_ID))
    if row is None:
        return EMPTY_MERGERS
    return decode_with(MergersState, json.loads(row.data_json), vars(mm))


def write_mergers(session: Session, mergers: MergersState) -> None:
    text = json.dumps(asdict(mergers), sort_keys=True)
    row = session.get(MergersRow, ROW_ID)
    if row is None:
        if mergers != EMPTY_MERGERS:
            session.add(MergersRow(id=ROW_ID, data_json=text))
    elif row.data_json != text:
        row.data_json = text
