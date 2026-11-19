"""Schema v3 (PT-M2): org units, membership, hiring plans, delegates and one-off morale.

Revision ID: 0003_org
Revises: 0002_people
Create Date: 2026-11-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_org"
down_revision = "0002_people"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "org_unit",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("firm_id", sa.Integer, sa.ForeignKey("firm.id"), nullable=False, index=True),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("parent_id", sa.Integer, nullable=True),
        sa.Column("leader_id", sa.Integer, nullable=True),
        sa.Column("practice", sa.String(40), nullable=True),
        sa.Column("created_turn", sa.Integer, nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("dissolved_turn", sa.Integer, nullable=True),
    )
    op.create_table(
        "org_member",
        sa.Column("person_id", sa.Integer, sa.ForeignKey("person.id"), primary_key=True),
        sa.Column(
            "unit_id", sa.Integer, sa.ForeignKey("org_unit.id"), nullable=False, index=True
        ),
    )
    op.create_table(
        "hiring_plan",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("firm_id", sa.Integer, sa.ForeignKey("firm.id"), nullable=False, index=True),
        sa.Column("owner_id", sa.Integer, sa.ForeignKey("person.id"), nullable=False),
        sa.Column("unit_id", sa.Integer, nullable=True),
        sa.Column("role", sa.String(40), nullable=False),
        sa.Column("target", sa.Integer, nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("ratio_bp", sa.Integer, nullable=False),
        sa.Column("created_turn", sa.Integer, nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("hired", sa.Integer, nullable=False),
        sa.Column("closed_turn", sa.Integer, nullable=True),
        sa.Column("focus", sa.String(20), nullable=False),
        sa.Column("level", sa.String(40), nullable=True),
        sa.Column("hires_json", sa.Text, nullable=False),
        sa.Column("activity_json", sa.Text, nullable=True),
    )
    op.create_table(
        "org_person",
        sa.Column("person_id", sa.Integer, sa.ForeignKey("person.id"), primary_key=True),
        sa.Column("last_raise_turn", sa.Integer, nullable=True),
        sa.Column("accelerated_years", sa.Integer, nullable=False),
        sa.Column("last_promoted_turn", sa.Integer, nullable=True),
    )
    op.create_table(
        "org_morale_nudge",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("person_id", sa.Integer, sa.ForeignKey("person.id"), nullable=False),
        sa.Column("turn", sa.Integer, nullable=False),
        sa.Column("points", sa.Float, nullable=False),
        sa.Column("reason", sa.String(40), nullable=False),
    )


def downgrade() -> None:
    for table in ("org_morale_nudge", "org_person", "hiring_plan", "org_member", "org_unit"):
        op.drop_table(table)
