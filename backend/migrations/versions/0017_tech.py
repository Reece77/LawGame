"""Schema v17 (PT-M14): legal technology and AI.

One `tech` row holding the firm's adoption by era, its training programme and its fixed-fee
products as JSON (`ptk.db.tech_io`).

Revision ID: 0017_tech
Revises: 0016_geo
Create Date: 2026-11-23
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0017_tech"
down_revision = "0016_geo"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tech",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("data_json", sa.Text, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("tech")
