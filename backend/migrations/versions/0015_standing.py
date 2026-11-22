"""Schema v15 (PT-M16; re-chained after PT-M9's 0014_automation): reputation, the press and the rankings.

One `standing` row holding reputation, the press and the rankings' latest editions as JSON, and
`ranking_entry`, the rankings' history (each published list's places and bands, appended).
A save from before PT-M16 has no row: its first month seeds reputation (spec 12.1).

Revision ID: 0015_standing
Revises: 0014_automation
Create Date: 2026-11-22
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0015_standing"
down_revision = "0014_automation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "standing",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("data_json", sa.Text, nullable=False),
    )
    op.create_table(
        "ranking_entry",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("turn", sa.Integer, nullable=False, index=True),
        sa.Column("kind", sa.String(20), nullable=False, index=True),
        sa.Column("practice", sa.String(40), nullable=True),
        sa.Column("place", sa.Integer, nullable=False),
        sa.Column("firm_id", sa.Integer, nullable=False, index=True),
        sa.Column("person_id", sa.Integer, nullable=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("value_cents", sa.BigInteger, nullable=True),
        sa.Column("count", sa.Integer, nullable=True),
        sa.Column("year", sa.Integer, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("ranking_entry")
    op.drop_table("standing")
