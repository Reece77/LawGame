"""Schema v14 (PT-M9): automation.

One `automation` row holding the areas' owners, their decisions and proposals as JSON, and
`inbox_item.in_digest`: an item from an automated area, which the inbox's default view leaves
out and the month's digest links to (TST formulas.md 40.4). Existing items are not from an
automated area (false).

Revision ID: 0014_automation
Revises: 0013_leadership
Create Date: 2026-11-22
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0014_automation"
down_revision = "0013_leadership"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "automation",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("data_json", sa.Text, nullable=False),
    )
    with op.batch_alter_table("inbox_item") as batch:
        batch.add_column(
            sa.Column("in_digest", sa.Boolean, nullable=False, server_default=sa.false())
        )


def downgrade() -> None:
    with op.batch_alter_table("inbox_item") as batch:
        batch.drop_column("in_digest")
    op.drop_table("automation")
