"""Schema v11 (PT-M17): the founder's life, family and personal books.

`founder_life`: two JSON documents (the founder-life state: lives, books' balances,
foundations, annuities, successions; the family state: the family and its members).
`personal_entry` and `personal_line`: the players' personal books, their own double entry
(9-accounts only), never in the firm ledger.

Revision ID: 0011_founder_life
Revises: 0010_v1_gaps
Create Date: 2026-11-21
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0011_founder_life"
down_revision = "0010_v1_gaps"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "founder_life",
        sa.Column("key", sa.String(20), primary_key=True),
        sa.Column("data_json", sa.Text, nullable=False),
    )
    op.create_table(
        "personal_entry",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("turn", sa.Integer, nullable=False, index=True),
        sa.Column("person_id", sa.Integer, nullable=False, index=True),
        sa.Column("memo", sa.Text, nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
    )
    op.create_table(
        "personal_line",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "entry_id", sa.Integer, sa.ForeignKey("personal_entry.id"), nullable=False, index=True
        ),
        sa.Column("account", sa.String(40), nullable=False),
        sa.Column("amount_cents", sa.BigInteger, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("personal_line")
    op.drop_table("personal_entry")
    op.drop_table("founder_life")
