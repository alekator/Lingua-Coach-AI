"""stage7 homework tables

Revision ID: 0004_stage7_homework
Revises: 0003_stage6_srs_state
Create Date: 2026-03-05
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0004_stage7_homework"
down_revision = "0003_stage6_srs_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "homeworks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("tasks", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="assigned"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "homework_submissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "homework_id",
            sa.Integer(),
            sa.ForeignKey("homeworks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("answers", sa.JSON(), nullable=False),
        sa.Column("grade", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("homework_submissions")
    op.drop_table("homeworks")
