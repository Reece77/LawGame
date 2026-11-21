"""Schema v11 (PT-M8): seats, authority, pitches and seat decisions.

One `leadership` row holding the seats' state as JSON. A practice group leader's seat reads
the unit's leader (`org_unit.leader_id`), so PT-M2's existing leaders become the seat holders
with no copy: there is nothing else to migrate.

Revision ID: 0011_leadership
Revises: 0010_v1_gaps
Create Date: 2026-11-21
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0011_leadership"
down_revision = "0010_v1_gaps"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "leadership",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("data_json", sa.Text, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("leadership")
