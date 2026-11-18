"""Schema v1 (PT-M0): save meta, firms, ledger, snapshots, turn and decision logs.

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-17
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "save_meta",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("master_seed", sa.BigInteger, nullable=False),
        sa.Column("scenario_id", sa.String(40), nullable=False),
        sa.Column("difficulty", sa.String(20), nullable=False),
        sa.Column("start_year", sa.Integer, nullable=False),
        sa.Column("start_month", sa.Integer, nullable=False),
        sa.Column("current_turn", sa.Integer, nullable=False),
        sa.Column("game_state", sa.String(20), nullable=False),
        sa.Column("ended_turn", sa.Integer, nullable=True),
    )
    op.create_table(
        "firm",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("is_player", sa.Boolean, nullable=False),
        sa.Column("stage", sa.Integer, nullable=False),
        sa.Column("founded_turn", sa.Integer, nullable=False),
        sa.Column("home_city", sa.String(40), nullable=False),
    )
    op.create_table(
        "ledger_entry",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("turn", sa.Integer, nullable=False, index=True),
        sa.Column("firm_id", sa.Integer, sa.ForeignKey("firm.id"), nullable=False, index=True),
        sa.Column("memo", sa.Text, nullable=False),
    )
    op.create_table(
        "ledger_line",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "entry_id", sa.Integer, sa.ForeignKey("ledger_entry.id"), nullable=False, index=True
        ),
        sa.Column("account", sa.String(40), nullable=False, index=True),
        sa.Column("amount_cents", sa.BigInteger, nullable=False),
        sa.Column("practice", sa.String(40), nullable=True),
        sa.Column("office_id", sa.Integer, nullable=True),
    )
    op.create_table(
        "turn_snapshot",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("turn", sa.Integer, nullable=False, index=True),
        sa.Column("firm_id", sa.Integer, sa.ForeignKey("firm.id"), nullable=False, index=True),
        sa.Column("kpis_json", sa.Text, nullable=False),
    )
    op.create_table(
        "turn_log",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("turn", sa.Integer, nullable=False, index=True),
        sa.Column("firm_id", sa.Integer, nullable=True),
        sa.Column("kind", sa.String(60), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
    )
    op.create_table(
        "decision_log",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("turn", sa.Integer, nullable=False, index=True),
        sa.Column("seq", sa.Integer, nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("payload_json", sa.Text, nullable=False),
    )


def downgrade() -> None:
    for table in (
        "decision_log",
        "turn_log",
        "turn_snapshot",
        "ledger_line",
        "ledger_entry",
        "firm",
        "save_meta",
    ):
        op.drop_table(table)
