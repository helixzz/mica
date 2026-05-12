"""add pr_title column to purchase_orders

Revision ID: 0043
Revises: 0042
Create Date: 2026-05-12
"""

import sqlalchemy as sa
from alembic import op

revision = "0043"
down_revision = "0042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "purchase_orders",
        sa.Column("pr_title", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("purchase_orders", "pr_title")