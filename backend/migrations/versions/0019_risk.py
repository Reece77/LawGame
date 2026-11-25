"""Schema v19 (PT-M15): risk and ethics.

One `risk` row holding claims, insurance policies, disciplinary cases, regulators'
inquiries, client-account reconciliations, audits and fee arbitrations as JSON (`ptk.db.risk_io`).

Revision ID: 0019_risk
Revises: 0018_mergers
Create Date: 2026-11-25
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0019_risk"
down_revision = "0018_mergers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "risk",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("data_json", sa.Text, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("risk")
