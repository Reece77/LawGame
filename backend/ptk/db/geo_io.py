"""Load and write geography (schema v16, PT-M11): one row holding the `GeoState` as JSON
(offices, admissions in progress and their history, pro hac vice grants, training contracts,
trainees and each city's last demand; rewritten when it changes), as `ptk.db.automation_io`
does for automation. A save from before PT-M11 has no row: it has no offices.
"""

from __future__ import annotations

import json
from dataclasses import asdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from ptk.db.automation_io import decode_with
from ptk.db.models import GeoRow
from ptk.sim.geo import models as gm
from ptk.sim.geo.models import EMPTY_GEO, GeoState

ROW_ID = 1  # the one row


def load_geo(session: Session) -> GeoState:
    row = session.scalar(select(GeoRow).where(GeoRow.id == ROW_ID))
    if row is None:
        return EMPTY_GEO
    return decode_with(GeoState, json.loads(row.data_json), vars(gm))


def write_geo(session: Session, geo: GeoState) -> None:
    text = json.dumps(asdict(geo), sort_keys=True)
    row = session.get(GeoRow, ROW_ID)
    if row is None:
        if geo != EMPTY_GEO:
            session.add(GeoRow(id=ROW_ID, data_json=text))
    elif row.data_json != text:
        row.data_json = text
