"""Schema v5 (PT-M3a): clients, judges, relationships, matters, appearances, origination,
the hours log, the month's demand, and the firm's conflicts-check policy.

Revision ID: 0005_matters
Revises: 0004_org
Create Date: 2026-11-20
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005_matters"
down_revision = "0004_org"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("firm") as batch:
        batch.add_column(
            sa.Column("conflict_checks", sa.Boolean, nullable=False, server_default=sa.true())
        )
    op.create_table(
        "client",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("sector", sa.String(40), nullable=False),
        sa.Column("real", sa.Boolean, nullable=False),
        sa.Column("data_json", sa.Text, nullable=False),
    )
    op.create_table(
        "judge",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("court", sa.String(40), nullable=False),
        sa.Column("first_name", sa.String(40), nullable=False),
        sa.Column("last_name", sa.String(40), nullable=False),
        sa.Column("traits_json", sa.Text, nullable=False),
        sa.Column("real", sa.Boolean, nullable=False),
    )
    op.create_table(
        "relationship",
        sa.Column("client_id", sa.Integer, sa.ForeignKey("client.id"), primary_key=True),
        sa.Column("firm_id", sa.Integer, sa.ForeignKey("firm.id"), primary_key=True),
        sa.Column("score", sa.Float, nullable=False),
        sa.Column("partner_id", sa.Integer, nullable=True),
        sa.Column("data_json", sa.Text, nullable=False),
    )
    op.create_table(
        "matter",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("firm_id", sa.Integer, sa.ForeignKey("firm.id"), nullable=False, index=True),
        sa.Column("client_id", sa.Integer, sa.ForeignKey("client.id"), nullable=False, index=True),
        sa.Column("practice", sa.String(40), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, index=True),
        sa.Column("opened_turn", sa.Integer, nullable=False),
        sa.Column("closed_turn", sa.Integer, nullable=True),
        sa.Column("data_json", sa.Text, nullable=False),
    )
    op.create_table(
        "appearance",
        sa.Column("person_id", sa.Integer, sa.ForeignKey("person.id"), primary_key=True),
        sa.Column("judge_id", sa.Integer, sa.ForeignKey("judge.id"), primary_key=True),
        sa.Column("tenths", sa.Integer, nullable=False),
    )
    op.create_table(
        "origination",
        sa.Column("person_id", sa.Integer, sa.ForeignKey("person.id"), primary_key=True),
        sa.Column("year", sa.Integer, primary_key=True),
        sa.Column("cents", sa.BigInteger, nullable=False),
    )
    op.create_table(
        "hours_log",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("turn", sa.Integer, nullable=False, index=True),
        sa.Column("person_id", sa.Integer, nullable=False, index=True),
        sa.Column("client_id", sa.Integer, nullable=False),
        sa.Column("practice", sa.String(40), nullable=False),
        sa.Column("matter_id", sa.Integer, nullable=True, index=True),
        sa.Column("tenths", sa.Integer, nullable=False),
        sa.Column("substantive_tenths", sa.Integer, nullable=False),
        sa.Column("value_cents", sa.BigInteger, nullable=False),
    )
    op.create_table(
        "market_demand",
        sa.Column("practice", sa.String(40), primary_key=True),
        sa.Column("demand_cents", sa.BigInteger, nullable=False),
    )


def downgrade() -> None:
    for table in (
        "market_demand",
        "hours_log",
        "origination",
        "appearance",
        "matter",
        "relationship",
        "judge",
        "client",
    ):
        op.drop_table(table)
    with op.batch_alter_table("firm") as batch:
        batch.drop_column("conflict_checks")
