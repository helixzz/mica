"""add supplier token_expires_at for portal token expiry

Revision ID: 0041
Revises: 0040
Create Date: 2026-05-11
"""

import sqlalchemy as sa
from alembic import op

revision = "0041"
down_revision = "0040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "suppliers",
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("suppliers", "token_expires_at")
