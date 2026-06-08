"""add pr_qty_contribution to po_items

Revision ID: 0049
Revises: 0048
Create Date: 2026-06-04
"""

import sqlalchemy as sa
from alembic import op

revision = "0049"
down_revision = "0048"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "po_items",
        sa.Column("pr_qty_contribution", sa.Numeric(18, 4), nullable=True),
    )
    op.execute(sa.text(
        "UPDATE po_items SET pr_qty_contribution = qty WHERE pr_item_id IS NOT NULL"
    ))


def downgrade() -> None:
    op.drop_column("po_items", "pr_qty_contribution")
