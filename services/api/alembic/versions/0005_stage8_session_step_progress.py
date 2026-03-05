"""stage8 session step progress

Revision ID: 0005_stage8_session_step_progress
Revises: 0004_stage7_homework
Create Date: 2026-03-06
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0005_stage8_session_step_progress"
down_revision = "0004_stage7_homework"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "session_step_progress",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_date", sa.Date(), nullable=False),
        sa.Column("step_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "session_date", "step_id", name="uq_session_step_progress"),
    )
    op.create_index("ix_session_step_progress_user_id", "session_step_progress", ["user_id"])
    op.create_index("ix_session_step_progress_session_date", "session_step_progress", ["session_date"])


def downgrade() -> None:
    op.drop_index("ix_session_step_progress_session_date", table_name="session_step_progress")
    op.drop_index("ix_session_step_progress_user_id", table_name="session_step_progress")
    op.drop_table("session_step_progress")
