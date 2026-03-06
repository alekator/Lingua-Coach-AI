"""stage11 grammar history

Revision ID: 0008_stage11_grammar_history
Revises: 0007_stage10_app_secrets
Create Date: 2026-03-07
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0008_stage11_grammar_history"
down_revision = "0007_stage10_app_secrets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "grammar_analysis_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_lang", sa.String(length=32), nullable=False),
        sa.Column("input_text", sa.Text(), nullable=False),
        sa.Column("corrected_text", sa.Text(), nullable=False),
        sa.Column("errors", sa.JSON(), nullable=False),
        sa.Column("exercises", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_grammar_analysis_records_user_id", "grammar_analysis_records", ["user_id"])
    op.create_index("ix_grammar_analysis_records_created_at", "grammar_analysis_records", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_grammar_analysis_records_created_at", table_name="grammar_analysis_records")
    op.drop_index("ix_grammar_analysis_records_user_id", table_name="grammar_analysis_records")
    op.drop_table("grammar_analysis_records")
