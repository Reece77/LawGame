"""Schema v3 (PT-M1b): searches, candidates, offers, person state, the inbox; salaries on
employments and the firm's pay policy.

Revision ID: 0003_hiring
Revises: 0002_people
Create Date: 2026-11-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_hiring"
down_revision = "0002_people"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("firm") as batch:
        batch.add_column(
            sa.Column("pay_policy_mode", sa.String(10), nullable=False, server_default="match")
        )
        batch.add_column(
            sa.Column("pay_policy_bp", sa.Integer, nullable=False, server_default="10000")
        )
    with op.batch_alter_table("employment") as batch:
        batch.add_column(
            sa.Column("salary_cents", sa.BigInteger, nullable=False, server_default="0")
        )
    op.create_table(
        "search",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("firm_id", sa.Integer, sa.ForeignKey("firm.id"), nullable=False, index=True),
        sa.Column("role", sa.String(40), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("actor_id", sa.Integer, nullable=False),
        sa.Column("opened_turn", sa.Integer, nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("closed_turn", sa.Integer, nullable=True),
        sa.Column("level", sa.String(40), nullable=True),
        sa.Column("school_tiers_json", sa.Text, nullable=False),
        sa.Column("plan_id", sa.Integer, nullable=True),
    )
    op.create_table(
        "candidate",
        sa.Column("person_id", sa.Integer, sa.ForeignKey("person.id"), primary_key=True),
        sa.Column("firm_id", sa.Integer, sa.ForeignKey("firm.id"), nullable=False, index=True),
        sa.Column(
            "search_id", sa.Integer, sa.ForeignKey("search.id"), nullable=False, index=True
        ),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("ask_cents", sa.BigInteger, nullable=False),
        sa.Column("created_turn", sa.Integer, nullable=False),
        sa.Column("expires_turn", sa.Integer, nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("resolved_turn", sa.Integer, nullable=True),
        sa.Column("interviewed_turn", sa.Integer, nullable=True),
    )
    op.create_table(
        "offer",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("firm_id", sa.Integer, sa.ForeignKey("firm.id"), nullable=False, index=True),
        sa.Column(
            "candidate_id", sa.Integer, sa.ForeignKey("person.id"), nullable=False, index=True
        ),
        sa.Column("actor_id", sa.Integer, nullable=False),
        sa.Column("salary_cents", sa.BigInteger, nullable=False),
        sa.Column("made_turn", sa.Integer, nullable=False),
        sa.Column("start_turn", sa.Integer, nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("resolved_turn", sa.Integer, nullable=True),
        sa.Column("plan_id", sa.Integer, nullable=True),
        sa.Column("unit_id", sa.Integer, nullable=True),
    )
    op.create_table(
        "person_state",
        sa.Column("person_id", sa.Integer, sa.ForeignKey("person.id"), primary_key=True),
        sa.Column("energy", sa.Integer, nullable=True),
        sa.Column("morale", sa.Float, nullable=True),
    )
    op.create_table(
        "inbox_item",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("turn", sa.Integer, nullable=False, index=True),
        sa.Column("firm_id", sa.Integer, nullable=False, index=True),
        sa.Column("template", sa.String(60), nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("link_kind", sa.String(20), nullable=True),
        sa.Column("link_id", sa.Integer, nullable=True),
        sa.Column("read", sa.Boolean, nullable=False),
    )


def downgrade() -> None:
    for table in ("inbox_item", "person_state", "offer", "candidate", "search"):
        op.drop_table(table)
    with op.batch_alter_table("employment") as batch:
        batch.drop_column("salary_cents")
    with op.batch_alter_table("firm") as batch:
        batch.drop_column("pay_policy_bp")
        batch.drop_column("pay_policy_mode")
