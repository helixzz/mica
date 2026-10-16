"""delivery address book for purchase requisitions and orders

Revision ID: 0060
Revises: 0059
Create Date: 2026-10-16

v1.57.0: delivery details stop being one free-text blob. Requisitions and
orders gain a reusable address book plus three structured fields.

* ``delivery_addresses`` holds either a company-wide shared entry
  (``owner_id IS NULL``, maintained by admins / procurement managers) or a
  private one. Both are scoped to the reader's company.
* ``purchase_requisitions`` and ``purchase_orders`` gain
  ``delivery_contact_name``, ``delivery_contact_phone`` and
  ``delivery_address_id``.
* The existing ``delivery_address`` column keeps its name and its data; its
  meaning narrows to "detailed address". Renaming it would force a data
  migration and touch every export and PO-propagation site for no functional
  gain.
* ``delivery_address_id`` is provenance only, with ``ON DELETE SET NULL``. The
  three text columns are copied at save time, so editing or deleting an address
  book entry never rewrites a historical requisition.

No index is added for ``delivery_address_id``: the project's other foreign keys
(``requester_id``, ``company_id``, ``supplier_id``) carry none either, and both
the tables and the delete path are small.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0060"
down_revision = "0059"
branch_labels = None
depends_on = None

_ADDRESS_TABLES = ("purchase_requisitions", "purchase_orders")


def upgrade() -> None:
    op.create_table(
        "delivery_addresses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("label", sa.String(length=64), nullable=True),
        sa.Column("contact_name", sa.String(length=64), nullable=False),
        sa.Column("contact_phone", sa.String(length=32), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
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
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name="fk_delivery_addresses_owner_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name="fk_delivery_addresses_company_id_companies",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_delivery_addresses"),
    )
    op.create_index("ix_delivery_addresses_owner_id", "delivery_addresses", ["owner_id"])
    op.create_index("ix_delivery_addresses_company_id", "delivery_addresses", ["company_id"])
    op.create_index(
        "ix_delivery_addresses_last_used_at", "delivery_addresses", ["last_used_at"]
    )

    for table in _ADDRESS_TABLES:
        op.add_column(
            table, sa.Column("delivery_contact_name", sa.String(length=64), nullable=True)
        )
        op.add_column(
            table, sa.Column("delivery_contact_phone", sa.String(length=32), nullable=True)
        )
        op.add_column(
            table, sa.Column("delivery_address_id", postgresql.UUID(as_uuid=True), nullable=True)
        )
        op.create_foreign_key(
            f"fk_{table}_delivery_address_id_delivery_addresses",
            table,
            "delivery_addresses",
            ["delivery_address_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    for table in reversed(_ADDRESS_TABLES):
        op.drop_constraint(
            f"fk_{table}_delivery_address_id_delivery_addresses", table, type_="foreignkey"
        )
        op.drop_column(table, "delivery_address_id")
        op.drop_column(table, "delivery_contact_phone")
        op.drop_column(table, "delivery_contact_name")

    op.drop_index("ix_delivery_addresses_last_used_at", table_name="delivery_addresses")
    op.drop_index("ix_delivery_addresses_company_id", table_name="delivery_addresses")
    op.drop_index("ix_delivery_addresses_owner_id", table_name="delivery_addresses")
    op.drop_table("delivery_addresses")
