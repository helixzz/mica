"""add annual budget fields to cost_centers

Revision ID: 0036
Revises: 0035
Create Date: 2026-05-04
"""

import sqlalchemy as sa
from alembic import op

revision = "0036"
down_revision = "0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cost_centers", sa.Column("annual_budget", sa.Numeric(18, 2), nullable=True))
    op.add_column("cost_centers", sa.Column("budget_start_date", sa.Date(), nullable=True))
    op.add_column("cost_centers", sa.Column("budget_end_date", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("cost_centers", "budget_end_date")
    op.drop_column("cost_centers", "budget_start_date")
    op.drop_column("cost_centers", "annual_budget")
