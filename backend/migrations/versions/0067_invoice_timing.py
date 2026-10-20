"""payments: 先票 / 后票 (invoice before or after payment)

Revision ID: 0067
Revises: 0066
Create Date: 2026-10-20

Whether an invoice arrives before or after the money moves depends on the
supplier and the deal, so both need to be representable:

* ``suppliers.default_invoice_timing`` — the usual arrangement for that supplier,
  prefilled when a payment is executed and overridable per payment.
* ``payment_records.invoice_timing`` / ``invoice_id`` — what actually happened,
  and which invoice backs a 先票 payment (a 后票 one starts empty).
* ``payment_records.invoice_due_date`` — the catch-up deadline for 后票, so the
  payment list and reports can show what is still owed an invoice.

Existing payments get no timing (NULL): we cannot know after the fact, and
inventing one would make the "waiting for invoice" list lie.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0067"
down_revision = "0066"
branch_labels = None
depends_on = None

_GRACE_PARAMETER = """
INSERT INTO system_parameters (
    id, key, category, value, data_type, default_value, min_value, max_value,
    unit, description_zh, description_en, is_sensitive, updated_by_id,
    created_at, updated_at
) VALUES (
    gen_random_uuid(), 'payment.invoice_grace_days', 'payment',
    to_jsonb(30), 'int', to_jsonb(30), NULL, NULL, 'days',
    '后票付款允许的补票天数',
    'Days allowed to supply the invoice after a post-payment',
    false, NULL, now(), now()
)
"""


def upgrade() -> None:
    op.add_column(
        "suppliers",
        sa.Column(
            "default_invoice_timing",
            sa.String(length=16),
            nullable=False,
            server_default="postpaid",
        ),
    )
    op.add_column("payment_records", sa.Column("invoice_timing", sa.String(length=16)))
    op.add_column("payment_records", sa.Column("invoice_due_date", sa.Date()))
    op.add_column(
        "payment_records",
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_payment_records_invoice_id_invoices",
        "payment_records",
        "invoices",
        ["invoice_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_payment_records_invoice_id", "payment_records", ["invoice_id"])

    op.execute(sa.text(_GRACE_PARAMETER))


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM system_parameters WHERE key = 'payment.invoice_grace_days'"))
    op.drop_index("ix_payment_records_invoice_id", table_name="payment_records")
    op.drop_constraint(
        "fk_payment_records_invoice_id_invoices", "payment_records", type_="foreignkey"
    )
    op.drop_column("payment_records", "invoice_id")
    op.drop_column("payment_records", "invoice_due_date")
    op.drop_column("payment_records", "invoice_timing")
    op.drop_column("suppliers", "default_invoice_timing")
