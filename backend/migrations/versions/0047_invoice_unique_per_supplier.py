"""add unique constraint on (supplier_id, invoice_number)

Revision ID: 0047
Revises: 0046
Create Date: 2026-05-26
"""

from alembic import op

revision = "0047"
down_revision = "0046"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM invoices a
        USING invoices b
        WHERE a.id < b.id
          AND a.supplier_id = b.supplier_id
          AND a.invoice_number = b.invoice_number
        """
    )
    op.create_unique_constraint(
        "uq_invoices_supplier_number",
        "invoices",
        ["supplier_id", "invoice_number"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_invoices_supplier_number", "invoices", type_="unique")
