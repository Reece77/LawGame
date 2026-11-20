"""Schema v10 (PT-M7a): pro bono and the yearly rate rise.

The firm's pro bono credit policy and moving average, its rate rise policy and rate index;
each person's pro bono hours this year; the pro bono client's row (id 0), which pro bono
matters reference. Early case assessment lives in the matter's JSON payload.

Revision ID: 0010_v1_gaps
Revises: 0009_rivals
Create Date: 2026-11-20
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0010_v1_gaps"
down_revision = "0009_rivals"
branch_labels = None
depends_on = None

# The pro bono client as ptk.db.market_io writes it (a migration is frozen: no app imports).
_PRO_BONO_CLIENT = {
    "country": "us",
    "revenue_bn": 0.0,
    "size_class": "mid",
    "price_sensitivity": 10.0,
    "loyalty": 10.0,
    "gc": {
        "first_name": "Clinic",
        "last_name": "Director",
        "birth_turn": 0,
        "personality": [
            [k, 10.0]
            for k in (
                "ambition",
                "loyalty",
                "professionalism",
                "temperament",
                "adaptability",
                "risk_appetite",
                "ego",
                "integrity",
                "sociability",
            )
        ],
    },
    "panel": [],
}


def upgrade() -> None:
    with op.batch_alter_table("firm") as batch:
        batch.add_column(sa.Column("pro_bono_credit_hours", sa.Integer, nullable=True))
        batch.add_column(
            sa.Column("pro_bono_avg_tenths", sa.Float, nullable=False, server_default="0")
        )
        batch.add_column(sa.Column("rate_rise_bp", sa.Integer, nullable=True))
        batch.add_column(sa.Column("rate_index", sa.Float, nullable=False, server_default="1"))
    with op.batch_alter_table("person_state") as batch:
        batch.add_column(
            sa.Column("pro_bono_ytd_tenths", sa.Integer, nullable=False, server_default="0")
        )
    bind = op.get_bind()
    if bind.execute(sa.text("SELECT COUNT(*) FROM client")).scalar():
        bind.execute(
            sa.text(
                "INSERT INTO client (id, name, sector, real, data_json) "
                "VALUES (0, 'Pro bono client', 'pro_bono', 0, :data)"
            ),
            {"data": json.dumps(_PRO_BONO_CLIENT)},
        )


def downgrade() -> None:
    op.execute("DELETE FROM client WHERE id = 0")
    with op.batch_alter_table("person_state") as batch:
        batch.drop_column("pro_bono_ytd_tenths")
    with op.batch_alter_table("firm") as batch:
        batch.drop_column("rate_index")
        batch.drop_column("rate_rise_bp")
        batch.drop_column("pro_bono_avg_tenths")
        batch.drop_column("pro_bono_credit_hours")
