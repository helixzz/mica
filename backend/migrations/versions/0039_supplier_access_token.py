"""add supplier access_token for read-only portal

Revision ID: 0039
Revises: 0037
Create Date: 2026-05-10
"""

import sqlalchemy as sa
from alembic import op

revision = "0039"
down_revision = "0038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "suppliers",
        sa.Column("access_token", sa.String(64), nullable=True),
    )
    op.create_unique_constraint("uq_suppliers_access_token", "suppliers", ["access_token"])


def downgrade() -> None:
    op.drop_constraint("uq_suppliers_access_token", "suppliers", type_="unique")
    op.drop_column("suppliers", "access_token")
