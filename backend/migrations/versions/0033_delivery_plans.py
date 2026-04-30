"""create delivery_plans table

Revision ID: 0033
Revises: 0032
Create Date: 2026-04-30
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0033"
down_revision: str | None = "0032"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "delivery_plans",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("po_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("purchase_orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("contract_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("contracts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("item_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("items.id"), nullable=False),
        sa.Column("plan_name", sa.String(200), nullable=False),
        sa.Column("planned_qty", sa.Integer(), nullable=False),
        sa.Column("planned_date", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="planned"),
        sa.Column("created_by_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "po_id IS NOT NULL OR contract_id IS NOT NULL",
            name="ck_delivery_plans_po_or_contract",
        ),
    )
    op.create_index("ix_delivery_plans_po_date", "delivery_plans", ["po_id", "planned_date"])
    op.create_index("ix_delivery_plans_contract_date", "delivery_plans", ["contract_id", "planned_date"])
    op.create_index("ix_delivery_plans_status", "delivery_plans", ["status"])


def downgrade() -> None:
    op.drop_index("ix_delivery_plans_status", table_name="delivery_plans")
    op.drop_index("ix_delivery_plans_contract_date", table_name="delivery_plans")
    op.drop_index("ix_delivery_plans_po_date", table_name="delivery_plans")
    op.drop_table("delivery_plans")
