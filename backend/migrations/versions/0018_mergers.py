"""Schema v18 (PT-M13): mergers and the verein.

One `mergers` row holding the deals (books, terms, clearance), integrations, the verein and
the exit as JSON (`ptk.db.mergers_io`).

Revision ID: 0018_mergers
Revises: 0017_tech
Create Date: 2026-11-25
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0018_mergers"
down_revision = "0017_tech"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mergers",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("data_json", sa.Text, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("mergers")
