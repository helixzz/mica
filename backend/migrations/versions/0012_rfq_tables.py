"""rfq tables

Revision ID: 0012
Revises: 0011
Create Date: 2026-04-22
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rfqs",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("rfq_number", sa.String(32), unique=True, nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column(
            "pr_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("purchase_requisitions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_id", PGUUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "company_id", PGUUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False
        ),
        sa.Column("awarded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "rfq_items",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column(
            "rfq_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("rfqs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("item_id", PGUUID(as_uuid=True), sa.ForeignKey("items.id"), nullable=True),
        sa.Column("item_name", sa.String(255), nullable=False),
        sa.Column("specification", sa.Text(), nullable=True),
        sa.Column("qty", sa.Numeric(18, 4), nullable=False),
        sa.Column("uom", sa.String(16), nullable=False, server_default="EA"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "rfq_suppliers",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column(
            "rfq_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("rfqs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "supplier_id", PGUUID(as_uuid=True), sa.ForeignKey("suppliers.id"), nullable=False
        ),
        sa.Column("status", sa.String(32), nullable=False, server_default="invited"),
        sa.Column(
            "invited_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("rfq_id", "supplier_id", name="uq_rfq_supplier"),
    )

    op.create_table(
        "rfq_quotes",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column(
            "rfq_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("rfqs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "rfq_item_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("rfq_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "supplier_id", PGUUID(as_uuid=True), sa.ForeignKey("suppliers.id"), nullable=False
        ),
        sa.Column("unit_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="CNY"),
        sa.Column("delivery_days", sa.Integer(), nullable=True),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_selected", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("rfq_item_id", "supplier_id", name="uq_quote_item_supplier"),
    )


def downgrade() -> None:
    op.drop_table("rfq_quotes")
    op.drop_table("rfq_suppliers")
    op.drop_table("rfq_items")
    op.drop_table("rfqs")
