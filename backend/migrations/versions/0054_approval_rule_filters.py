"""approval_rules add department_ids and cost_center_ids filter columns

Revision ID: 0054
Revises: 0053
Create Date: 2026-06-22

v1.37.0 path-B — approval rule matching now supports two extra dimensions:
- department_ids: JSONB array of UUIDs; rule only matches when PR's department
  is in this list (or list is NULL = no filter)
- cost_center_ids: JSONB array of UUIDs; same semantics for PR cost center

Both columns default to NULL (no filter) so existing rules keep current behavior.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0054"
down_revision = "0053"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "approval_rules",
        sa.Column("department_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "approval_rules",
        sa.Column("cost_center_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("approval_rules", "cost_center_ids")
    op.drop_column("approval_rules", "department_ids")
