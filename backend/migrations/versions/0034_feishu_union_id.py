"""add feishu_union_id and feishu_user_id columns to users

Revision ID: 0034
Revises: 0033
Create Date: 2026-04-30
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0034"
down_revision: str | None = "0033"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("feishu_union_id", sa.String(128), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("feishu_user_id", sa.String(64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "feishu_user_id")
    op.drop_column("users", "feishu_union_id")
