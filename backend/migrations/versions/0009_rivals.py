"""Schema v9 (PT-M5): rival firms' state, and judges' time on the bench.

Revision ID: 0009_rivals
Revises: 0008_partnership
Create Date: 2026-11-20
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0009_rivals"
down_revision = "0008_partnership"
branch_labels = None
depends_on = None

def upgrade() -> None:
    with op.batch_alter_table("judge") as batch:
        batch.add_column(sa.Column("from_turn", sa.Integer, nullable=False, server_default="0"))
        batch.add_column(sa.Column("until_turn", sa.Integer, nullable=True))
    op.create_table(
        "rival_state",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("real_people", sa.Boolean, nullable=False),
        sa.Column("data_json", sa.Text, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("rival_state")
    with op.batch_alter_table("judge") as batch:
        batch.drop_column("until_turn")
        batch.drop_column("from_turn")
