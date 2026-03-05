"""stage2 initial schema

Revision ID: 0001_stage2_initial
Revises:
Create Date: 2026-03-05
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001_stage2_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=True, unique=True),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "learner_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("native_lang", sa.String(length=32), nullable=False),
        sa.Column("target_lang", sa.String(length=32), nullable=False),
        sa.Column("level", sa.String(length=4), nullable=False, server_default="A1"),
        sa.Column("goal", sa.String(length=255), nullable=True),
        sa.Column("preferences", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", name="uq_learner_profiles_user_id"),
    )

    op.create_table(
        "placement_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="in_progress"),
        sa.Column("native_lang", sa.String(length=32), nullable=False),
        sa.Column("target_lang", sa.String(length=32), nullable=False),
        sa.Column("current_question_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("questions", sa.JSON(), nullable=False),
        sa.Column("recommended_level", sa.String(length=4), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "placement_answers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "session_id",
            sa.Integer(),
            sa.ForeignKey("placement_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("question_index", sa.Integer(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "skill_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("speaking", sa.Float(), nullable=False, server_default="0"),
        sa.Column("listening", sa.Float(), nullable=False, server_default="0"),
        sa.Column("grammar", sa.Float(), nullable=False, server_default="0"),
        sa.Column("vocab", sa.Float(), nullable=False, server_default="0"),
        sa.Column("reading", sa.Float(), nullable=False, server_default="0"),
        sa.Column("writing", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("skill_snapshots")
    op.drop_table("placement_answers")
    op.drop_table("placement_sessions")
    op.drop_table("learner_profiles")
    op.drop_table("users")
