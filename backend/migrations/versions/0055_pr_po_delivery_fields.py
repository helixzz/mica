"""Add delivery_address and expected_delivery_date to PRs and POs.

Revision ID: 0055
Revises: 0054
"""

import sqlalchemy as sa
from alembic import op

revision = "0055"
down_revision = "0054"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "purchase_requisitions",
        sa.Column("delivery_address", sa.Text(), nullable=True),
    )
    op.add_column(
        "purchase_requisitions",
        sa.Column("expected_delivery_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "purchase_orders",
        sa.Column("delivery_address", sa.Text(), nullable=True),
    )
    op.add_column(
        "purchase_orders",
        sa.Column("expected_delivery_date", sa.Date(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("purchase_orders", "expected_delivery_date")
    op.drop_column("purchase_orders", "delivery_address")
    op.drop_column("purchase_requisitions", "expected_delivery_date")
    op.drop_column("purchase_requisitions", "delivery_address")
