"""Schema v7 (PT-M4): the partnership, one JSON row per firm (capital and current accounts,
draws, comp, votes, confidence, laterals, flight, the revolver's state, the MP's term) and a
row of id counters.

Revision ID: 0007_partnership
Revises: 0006_billing
Create Date: 2026-11-20
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0007_partnership"
down_revision = "0006_billing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "partnership",
        sa.Column("firm_id", sa.Integer, primary_key=True),
        sa.Column("data_json", sa.Text, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("partnership")
