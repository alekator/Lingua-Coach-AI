"""stage10 app secrets

Revision ID: 0007_stage10_app_secrets
Revises: 0006_stage9_usage_events
Create Date: 2026-03-06
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0007_stage10_app_secrets"
down_revision = "0006_stage9_usage_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_secrets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("secret_key", sa.String(length=128), nullable=False, unique=True),
        sa.Column("encrypted_value", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_app_secrets_secret_key", "app_secrets", ["secret_key"])


def downgrade() -> None:
    op.drop_index("ix_app_secrets_secret_key", table_name="app_secrets")
    op.drop_table("app_secrets")

