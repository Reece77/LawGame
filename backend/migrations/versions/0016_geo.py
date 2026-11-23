"""Schema v16 (PT-M11): offices, cities and the UK path.

One `geo` row holding the geography state as JSON (offices and their leases, bar exams and
motions in progress, admissions' history, pro hac vice grants, training contracts, trainees and
each city's last demand). A client's city is a key of its existing `data_json` (absent = the
home market), so the `client` table is unchanged. A save from before PT-M11 has no row and no
offices.

Revision ID: 0016_geo
Revises: 0015_standing
Create Date: 2026-11-23
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0016_geo"
down_revision = "0015_standing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "geo",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("data_json", sa.Text, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("geo")
