"""payment schedules can attach to either contract or PO

Revision ID: 0018
Revises: 0017
Create Date: 2026-04-23
"""

import sqlalchemy as sa
from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "payment_schedules",
        "contract_id",
        existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.add_column(
        "payment_schedules",
        sa.Column("po_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_payment_schedules_po_id_purchase_orders",
        "payment_schedules",
        "purchase_orders",
        ["po_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_payment_schedules_po_id",
        "payment_schedules",
        ["po_id"],
    )
    op.create_check_constraint(
        "ck_payment_schedules_parent_exactly_one",
        "payment_schedules",
        "(contract_id IS NOT NULL AND po_id IS NULL) "
        "OR (contract_id IS NULL AND po_id IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_payment_schedules_parent_exactly_one",
        "payment_schedules",
        type_="check",
    )
    op.drop_index("ix_payment_schedules_po_id", table_name="payment_schedules")
    op.drop_constraint(
        "fk_payment_schedules_po_id_purchase_orders",
        "payment_schedules",
        type_="foreignkey",
    )
    op.drop_column("payment_schedules", "po_id")
    op.execute("DELETE FROM payment_schedules WHERE contract_id IS NULL")
    op.alter_column(
        "payment_schedules",
        "contract_id",
        existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
        nullable=False,
    )
