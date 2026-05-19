"""Add budgets, user_dashboard_configs, insight_cache tables for Reporting & Insights."""

revision = "0045"
down_revision = "0044"

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


def upgrade() -> None:
    op.create_table(
        "budgets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("scope_type", sa.String(20), nullable=False),
        sa.Column("scope_id", sa.Uuid(), nullable=False),
        sa.Column("period_type", sa.String(20), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(3), server_default="CNY"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_by_id", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_budgets_scope", "budgets", ["scope_type", "scope_id"])
    op.create_index("ix_budgets_period", "budgets", ["period_start", "period_end"])

    op.create_table(
        "user_dashboard_configs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), unique=True, nullable=False),
        sa.Column("panels", JSONB, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "insight_cache",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("cache_key", sa.String(255), unique=True, nullable=False),
        sa.Column("content", JSONB, nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_insight_cache_expires", "insight_cache", ["expires_at"])


def downgrade() -> None:
    op.drop_table("insight_cache")
    op.drop_table("user_dashboard_configs")
    op.drop_table("budgets")
