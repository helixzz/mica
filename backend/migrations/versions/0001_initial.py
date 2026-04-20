"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-21 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name_zh", sa.String(255), nullable=False),
        sa.Column("name_en", sa.String(255), nullable=True),
        sa.Column("default_locale", sa.String(10), nullable=False, server_default="zh-CN"),
        sa.Column("default_currency", sa.String(3), nullable=False, server_default="CNY"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("code", name=op.f("uq_companies_code")),
    )

    op.create_table(
        "departments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name_zh", sa.String(128), nullable=False),
        sa.Column("name_en", sa.String(128), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], name=op.f("fk_departments_company_id_companies")),
        sa.UniqueConstraint("company_id", "code", name=op.f("uq_departments_company_id")),
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(128), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("preferred_locale", sa.String(10), nullable=False, server_default="zh-CN"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_local_admin", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("auth_provider", sa.String(32), nullable=False, server_default="local"),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], name=op.f("fk_users_company_id_companies")),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], name=op.f("fk_users_department_id_departments")),
        sa.UniqueConstraint("username", name=op.f("uq_users_username")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
        sa.CheckConstraint(
            "role IN ('admin','it_buyer','dept_manager','finance_auditor','procurement_mgr')",
            name=op.f("ck_users_valid_role"),
        ),
    )

    op.create_table(
        "suppliers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("contact_name", sa.String(128), nullable=True),
        sa.Column("contact_phone", sa.String(32), nullable=True),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column("tax_number", sa.String(64), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("code", name=op.f("uq_suppliers_code")),
    )

    op.create_table(
        "items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("category", sa.String(64), nullable=True),
        sa.Column("uom", sa.String(16), nullable=False, server_default="EA"),
        sa.Column("specification", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("code", name=op.f("uq_items_code")),
    )

    op.create_table(
        "purchase_requisitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("pr_number", sa.String(32), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("business_reason", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("requester_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="CNY"),
        sa.Column("total_amount", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("required_date", sa.Date(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decided_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("decision_comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["requester_id"], ["users.id"], name=op.f("fk_purchase_requisitions_requester_id_users")),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], name=op.f("fk_purchase_requisitions_company_id_companies")),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], name=op.f("fk_purchase_requisitions_department_id_departments")),
        sa.ForeignKeyConstraint(["decided_by_id"], ["users.id"], name=op.f("fk_purchase_requisitions_decided_by_id_users")),
        sa.UniqueConstraint("pr_number", name=op.f("uq_purchase_requisitions_pr_number")),
    )

    op.create_table(
        "pr_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("pr_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("item_name", sa.String(255), nullable=False),
        sa.Column("specification", sa.Text(), nullable=True),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("qty", sa.Numeric(18, 4), nullable=False),
        sa.Column("uom", sa.String(16), nullable=False, server_default="EA"),
        sa.Column("unit_price", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["pr_id"], ["purchase_requisitions.id"], ondelete="CASCADE", name=op.f("fk_pr_items_pr_id_purchase_requisitions")),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"], name=op.f("fk_pr_items_item_id_items")),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], name=op.f("fk_pr_items_supplier_id_suppliers")),
        sa.UniqueConstraint("pr_id", "line_no", name=op.f("uq_pr_items_pr_id")),
    )

    op.create_table(
        "purchase_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("po_number", sa.String(32), nullable=False),
        sa.Column("pr_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="confirmed"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="CNY"),
        sa.Column("total_amount", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("source_type", sa.String(32), nullable=False, server_default="manual"),
        sa.Column("source_ref", sa.String(128), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["pr_id"], ["purchase_requisitions.id"], name=op.f("fk_purchase_orders_pr_id_purchase_requisitions")),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], name=op.f("fk_purchase_orders_supplier_id_suppliers")),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], name=op.f("fk_purchase_orders_company_id_companies")),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], name=op.f("fk_purchase_orders_created_by_id_users")),
        sa.UniqueConstraint("po_number", name=op.f("uq_purchase_orders_po_number")),
    )

    op.create_table(
        "po_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("po_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pr_item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("item_name", sa.String(255), nullable=False),
        sa.Column("specification", sa.Text(), nullable=True),
        sa.Column("qty", sa.Numeric(18, 4), nullable=False),
        sa.Column("uom", sa.String(16), nullable=False, server_default="EA"),
        sa.Column("unit_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["po_id"], ["purchase_orders.id"], ondelete="CASCADE", name=op.f("fk_po_items_po_id_purchase_orders")),
        sa.ForeignKeyConstraint(["pr_item_id"], ["pr_items.id"], name=op.f("fk_po_items_pr_item_id_pr_items")),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"], name=op.f("fk_po_items_item_id_items")),
        sa.UniqueConstraint("po_id", "line_no", name=op.f("uq_po_items_po_id")),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_name", sa.String(128), nullable=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=True),
        sa.Column("resource_id", sa.String(64), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], name=op.f("fk_audit_logs_actor_id_users")),
    )
    op.create_index("ix_audit_logs_occurred_at", "audit_logs", ["occurred_at"])
    op.create_index("ix_audit_logs_event_type", "audit_logs", ["event_type"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_event_type", table_name="audit_logs")
    op.drop_index("ix_audit_logs_occurred_at", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_table("po_items")
    op.drop_table("purchase_orders")
    op.drop_table("pr_items")
    op.drop_table("purchase_requisitions")
    op.drop_table("items")
    op.drop_table("suppliers")
    op.drop_table("users")
    op.drop_table("departments")
    op.drop_table("companies")
