"""Schema v12 (PT-M7b): a new firm's card by practice and the firm's hours policy.

`firm.rate_card` holds the firm's share of each practice's top card ({practice: bp}, JSON); a
save from before PT-M7b keeps its rates (an empty card bills every practice at the full card).
`firm.billable_target_hours` is the firm-wide billable target (hours a year; NULL: the levels').

Revision ID: 0012_pressure
Revises: 0011_founder_life
Create Date: 2026-11-21
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0012_pressure"
down_revision = "0011_founder_life"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("firm") as batch:
        batch.add_column(sa.Column("rate_card", sa.Text, nullable=False, server_default="{}"))
        batch.add_column(sa.Column("billable_target_hours", sa.Integer, nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("firm") as batch:
        batch.drop_column("billable_target_hours")
        batch.drop_column("rate_card")
