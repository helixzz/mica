"""add feishu_open_id to users

Revision ID: 0032
Revises: 0031
Create Date: 2026-04-29
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0032"
down_revision: str | None = "0031"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("feishu_open_id", sa.String(128), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "feishu_open_id")
