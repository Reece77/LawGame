"""Schema v2 (PT-M1a): people, employment and per-firm reveal records.

Revision ID: 0002_people
Revises: 0001_initial
Create Date: 2026-11-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_people"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "person",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("first_name", sa.String(40), nullable=False),
        sa.Column("last_name", sa.String(40), nullable=False),
        sa.Column("birth_turn", sa.Integer, nullable=False),
        sa.Column("role", sa.String(40), nullable=False),
        sa.Column("level", sa.String(40), nullable=False),
        sa.Column("skills_json", sa.Text, nullable=False),
        sa.Column("personality_json", sa.Text, nullable=False),
        sa.Column("hidden_json", sa.Text, nullable=False),
        sa.Column("potential_ability", sa.Float, nullable=False),
        sa.Column("familiarity_json", sa.Text, nullable=False),
        sa.Column("familiarity_peak_json", sa.Text, nullable=False),
        sa.Column("interests_json", sa.Text, nullable=False),
        sa.Column("work_style", sa.String(40), nullable=False),
        sa.Column("tags_json", sa.Text, nullable=False),
        sa.Column("school_tier", sa.String(40), nullable=True),
        sa.Column("bar_admissions_json", sa.Text, nullable=False),
        sa.Column("city", sa.String(40), nullable=False),
        sa.Column("strain", sa.Float, nullable=False),
        sa.Column("burnout_since", sa.Integer, nullable=True),
        sa.Column("last_burnout_turn", sa.Integer, nullable=True),
        sa.Column("book_cents", sa.BigInteger, nullable=False),
        sa.Column("portability_bp", sa.Integer, nullable=True),
        sa.Column("is_founder", sa.Boolean, nullable=False),
        sa.Column("founding_partner", sa.Boolean, nullable=False),
        sa.Column("background", sa.String(40), nullable=True),
        sa.Column("real", sa.Boolean, nullable=False),
    )
    op.create_table(
        "employment",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("person_id", sa.Integer, sa.ForeignKey("person.id"), nullable=False, index=True),
        sa.Column("firm_id", sa.Integer, sa.ForeignKey("firm.id"), nullable=False, index=True),
        sa.Column("start_turn", sa.Integer, nullable=False),
        sa.Column("end_turn", sa.Integer, nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("end_reason", sa.String(20), nullable=True),
    )
    op.create_table(
        "reveal_state",
        sa.Column(
            "observer_firm_id", sa.Integer, sa.ForeignKey("firm.id"), primary_key=True
        ),
        sa.Column("person_id", sa.Integer, sa.ForeignKey("person.id"), primary_key=True),
        sa.Column("attributes_json", sa.Text, nullable=False),
        sa.Column("profile_revealed_turn", sa.Integer, nullable=True),
        sa.Column("revealed_tags_json", sa.Text, nullable=False),
    )


def downgrade() -> None:
    for table in ("reveal_state", "employment", "person"):
        op.drop_table(table)
