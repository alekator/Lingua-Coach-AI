"""stage6 srs state

Revision ID: 0003_stage6_srs_state
Revises: 0002_stage3_chat_memory
Create Date: 2026-03-05
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0003_stage6_srs_state"
down_revision = "0002_stage3_chat_memory"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "srs_state",
        sa.Column(
            "vocab_item_id",
            sa.Integer(),
            sa.ForeignKey("vocab_items.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("interval_days", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("ease", sa.Float(), nullable=False, server_default="2.5"),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("srs_state")
