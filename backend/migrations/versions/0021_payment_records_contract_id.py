"""add payment_records.contract_id with backfill

Revision ID: 0021
Revises: 0020
Create Date: 2026-04-24
"""

import sqlalchemy as sa
from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "payment_records",
        sa.Column("contract_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_payment_records_contract_id_contracts",
        "payment_records",
        "contracts",
        ["contract_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_payment_records_contract_id",
        "payment_records",
        ["contract_id"],
    )

    op.execute(
        sa.text(
            """
            UPDATE payment_records pr
            SET contract_id = ps.contract_id
            FROM payment_schedules ps
            WHERE pr.schedule_item_id = ps.id
              AND ps.contract_id IS NOT NULL
              AND pr.contract_id IS NULL;
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_payment_records_contract_id", table_name="payment_records")
    op.drop_constraint(
        "fk_payment_records_contract_id_contracts",
        "payment_records",
        type_="foreignkey",
    )
    op.drop_column("payment_records", "contract_id")
