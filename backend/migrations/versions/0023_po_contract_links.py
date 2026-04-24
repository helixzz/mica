"""create po_contract_links M:N table and backfill from contract.po_id

Revision ID: 0023
Revises: 0022
Create Date: 2026-04-25
"""

import sqlalchemy as sa
from alembic import op

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "po_contract_links",
        sa.Column(
            "po_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("purchase_orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "contract_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("contracts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("po_id", "contract_id"),
    )
    op.create_index(
        "ix_po_contract_links_contract_id",
        "po_contract_links",
        ["contract_id"],
    )

    op.execute(
        sa.text(
            """
            INSERT INTO po_contract_links (po_id, contract_id, created_at, updated_at)
            SELECT po_id, id, now(), now() FROM contracts
            WHERE po_id IS NOT NULL
            ON CONFLICT (po_id, contract_id) DO NOTHING;
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_po_contract_links_contract_id", table_name="po_contract_links")
    op.drop_table("po_contract_links")
