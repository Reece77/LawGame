"""Schema v6 (PT-M3b): billing engagements, flow accounts, bills, monthly billing totals,
padders found, and the client-money book.

Revision ID: 0006_billing
Revises: 0005_matters
Create Date: 2026-11-20
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0006_billing"
down_revision = "0005_matters"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "engagement",
        sa.Column("matter_id", sa.Integer, primary_key=True),
        sa.Column("firm_id", sa.Integer, sa.ForeignKey("firm.id"), nullable=False, index=True),
        sa.Column("client_id", sa.Integer, nullable=False, index=True),
        sa.Column("model", sa.String(20), nullable=False),
        sa.Column("closed", sa.Boolean, nullable=False),
        sa.Column("closed_turn", sa.Integer, nullable=True, index=True),
        sa.Column("data_json", sa.Text, nullable=False),
    )
    op.create_table(
        "flow_account",
        sa.Column("firm_id", sa.Integer, sa.ForeignKey("firm.id"), primary_key=True),
        sa.Column("client_id", sa.Integer, primary_key=True),
        sa.Column("practice", sa.String(40), primary_key=True),
        sa.Column("data_json", sa.Text, nullable=False),
    )
    op.create_table(
        "bill",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("firm_id", sa.Integer, sa.ForeignKey("firm.id"), nullable=False, index=True),
        sa.Column("client_id", sa.Integer, nullable=False, index=True),
        sa.Column("matter_id", sa.Integer, nullable=True, index=True),
        sa.Column("practice", sa.String(40), nullable=False),
        sa.Column("model", sa.String(20), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("issued_turn", sa.Integer, nullable=False, index=True),
        sa.Column("status", sa.String(20), nullable=False, index=True),
        sa.Column("closed_turn", sa.Integer, nullable=True),
        sa.Column("billed_cents", sa.BigInteger, nullable=False),
        sa.Column("data_json", sa.Text, nullable=False),
    )
    op.create_table(
        "billing_month",
        sa.Column("firm_id", sa.Integer, sa.ForeignKey("firm.id"), primary_key=True),
        sa.Column("turn", sa.Integer, primary_key=True),
        sa.Column("data_json", sa.Text, nullable=False),
    )
    op.create_table(
        "billing_padder",
        sa.Column("person_id", sa.Integer, primary_key=True),
    )
    op.create_table(
        "client_book_entry",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("turn", sa.Integer, nullable=False, index=True),
        sa.Column("firm_id", sa.Integer, sa.ForeignKey("firm.id"), nullable=False, index=True),
        sa.Column("memo", sa.Text, nullable=False),
    )
    op.create_table(
        "client_book_line",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "entry_id",
            sa.Integer,
            sa.ForeignKey("client_book_entry.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("account", sa.String(40), nullable=False),
        sa.Column("client_id", sa.Integer, nullable=False, index=True),
        sa.Column("amount_cents", sa.BigInteger, nullable=False),
    )


def downgrade() -> None:
    for table in (
        "client_book_line",
        "client_book_entry",
        "billing_padder",
        "billing_month",
        "bill",
        "flow_account",
        "engagement",
    ):
        op.drop_table(table)
