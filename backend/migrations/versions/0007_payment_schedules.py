"""payment schedules

Revision ID: 0007
Revises: 0006
Create Date: 2026-04-22
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payment_schedules",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column(
            "contract_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("contracts.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("installment_no", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(128), nullable=False),
        sa.Column("planned_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("planned_date", sa.Date(), nullable=True),
        sa.Column("trigger_type", sa.String(32), nullable=False, server_default="fixed_date"),
        sa.Column("trigger_description", sa.String(255), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="planned"),
        sa.Column("actual_amount", sa.Numeric(18, 4), nullable=True),
        sa.Column("actual_date", sa.Date(), nullable=True),
        sa.Column(
            "payment_record_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("payment_records.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "invoice_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("invoices.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint(
            "contract_id", "installment_no", name="uq_schedule_contract_installment"
        ),
    )

    op.add_column(
        "payment_records",
        sa.Column(
            "schedule_item_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("payment_schedules.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    op.execute(
        sa.text(
            "INSERT INTO system_parameters"
            " (id, key, category, value, data_type, default_value,"
            "  min_value, max_value, unit, description_zh, description_en,"
            "  is_sensitive, created_at, updated_at)"
            " VALUES (gen_random_uuid(), 'payment.invoice_due_days', 'payment',"
            "  '30'::jsonb, 'int', '30'::jsonb, '0'::jsonb, '365'::jsonb, 'days',"
            "  '收到发票后的默认付款期限天数',"
            "  'Default payment due days after invoice receipt',"
            "  false, now(), now())"
            " ON CONFLICT (key) DO NOTHING"
        )
    )


def downgrade() -> None:
    op.drop_column("payment_records", "schedule_item_id")
    op.drop_table("payment_schedules")
    op.execute("DELETE FROM system_parameters WHERE key = 'payment.invoice_due_days'")
