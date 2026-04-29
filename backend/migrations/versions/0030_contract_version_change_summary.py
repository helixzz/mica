"""add change_summary column to contract_versions

Revision ID: 0030
Revises: 0029
Create Date: 2026-04-29
"""

import sqlalchemy as sa
from alembic import op

revision = "0030"
down_revision = "0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "contract_versions",
        sa.Column("change_summary", sa.String(500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("contract_versions", "change_summary")
