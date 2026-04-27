"""add contract_id FK to shipments (nullable)

Revision ID: 0027
Revises: 0026
Create Date: 2026-04-27
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "shipments",
        sa.Column(
            "contract_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("contracts.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_shipments_contract_id",
        "shipments",
        ["contract_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_shipments_contract_id", table_name="shipments")
    op.drop_column("shipments", "contract_id")
