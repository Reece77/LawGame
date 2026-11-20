"""Schema v6 (PT-M6): events, storylines, queued events, modifiers, colleague pairs, the events
id counters, the LLM's read-only texts and its call log.

Revision ID: 0006_events
Revises: 0005_matters
Create Date: 2026-11-20
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0006_events"
down_revision = "0005_matters"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "game_event",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("firm_id", sa.Integer, sa.ForeignKey("firm.id"), nullable=False, index=True),
        sa.Column("turn", sa.Integer, nullable=False, index=True),
        sa.Column("template_id", sa.String(60), nullable=False),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("severity", sa.String(10), nullable=False),
        sa.Column("status", sa.String(10), nullable=False, index=True),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("data_json", sa.Text, nullable=False),
    )
    op.create_table(
        "storyline",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("firm_id", sa.Integer, sa.ForeignKey("firm.id"), nullable=False, index=True),
        sa.Column("key", sa.String(60), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("data_json", sa.Text, nullable=False),
    )
    op.create_table(
        "queued_event",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("firm_id", sa.Integer, sa.ForeignKey("firm.id"), nullable=False, index=True),
        sa.Column("template_id", sa.String(60), nullable=False),
        sa.Column("due_turn", sa.Integer, nullable=False),
        sa.Column("done", sa.Boolean, nullable=False),
        sa.Column("data_json", sa.Text, nullable=False),
    )
    op.create_table(
        "event_modifier",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("firm_id", sa.Integer, sa.ForeignKey("firm.id"), nullable=False, index=True),
        sa.Column("event_id", sa.Integer, nullable=True),
        sa.Column("target", sa.String(40), nullable=False),
        sa.Column("stat", sa.String(40), nullable=False),
        sa.Column("value_pct", sa.Float, nullable=False),
        sa.Column("start_turn", sa.Integer, nullable=False),
        sa.Column("end_turn", sa.Integer, nullable=False),
    )
    op.create_table(
        "colleague_pair",
        sa.Column("a", sa.Integer, sa.ForeignKey("person.id"), primary_key=True),
        sa.Column("b", sa.Integer, sa.ForeignKey("person.id"), primary_key=True),
        sa.Column("value", sa.Float, nullable=False),
        sa.Column("start", sa.Float, nullable=False),
        sa.Column("since_turn", sa.Integer, nullable=False),
    )
    op.create_table(
        "event_counters",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("next_event_id", sa.Integer, nullable=False),
        sa.Column("next_storyline_id", sa.Integer, nullable=False),
        sa.Column("next_queued_id", sa.Integer, nullable=False),
        sa.Column("next_modifier_id", sa.Integer, nullable=False),
    )
    op.create_table(
        "llm_text",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("turn", sa.Integer, nullable=False, index=True),
        sa.Column("firm_id", sa.Integer, nullable=False),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("ref_id", sa.Integer, nullable=True),
        sa.Column("status", sa.String(10), nullable=False, index=True),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
    )
    op.create_table(
        "llm_call_log",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("turn", sa.Integer, nullable=False, index=True),
        sa.Column("purpose", sa.String(30), nullable=False),
        sa.Column("model", sa.String(60), nullable=False),
        sa.Column("prompt_hash", sa.String(16), nullable=False),
        sa.Column("input_tokens", sa.Integer, nullable=False),
        sa.Column("output_tokens", sa.Integer, nullable=False),
        sa.Column("cost_cents", sa.Float, nullable=False),
        sa.Column("latency_ms", sa.Integer, nullable=False),
        sa.Column("outcome", sa.String(20), nullable=False),
        sa.Column("created_at", sa.String(32), nullable=False),
        sa.Column("prompt", sa.Text, nullable=True),
        sa.Column("response", sa.Text, nullable=True),
    )


def downgrade() -> None:
    for table in (
        "llm_call_log",
        "llm_text",
        "event_counters",
        "colleague_pair",
        "event_modifier",
        "queued_event",
        "storyline",
        "game_event",
    ):
        op.drop_table(table)
