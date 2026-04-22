"""classification tables

Revision ID: 0008
Revises: 0007
Create Date: 2026-04-22
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cost_centers",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(32), unique=True, nullable=False),
        sa.Column("label_zh", sa.String(128), nullable=False),
        sa.Column("label_en", sa.String(128), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("budget_amount", sa.Numeric(18, 4), nullable=True),
        sa.Column("manager_id", PGUUID(as_uuid=True), nullable=True),
        sa.Column("meta", JSONB, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "procurement_categories",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(64), unique=True, nullable=False),
        sa.Column("label_zh", sa.String(128), nullable=False),
        sa.Column("label_en", sa.String(128), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "parent_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("procurement_categories.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "lookup_values",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("type", sa.String(64), nullable=False, index=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("label_zh", sa.String(128), nullable=False),
        sa.Column("label_en", sa.String(128), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("meta", JSONB, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("type", "code", name="uq_lookup_type_code"),
    )

    op.add_column(
        "purchase_requisitions",
        sa.Column(
            "cost_center_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("cost_centers.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "purchase_requisitions",
        sa.Column(
            "expense_type_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("lookup_values.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "purchase_requisitions",
        sa.Column(
            "procurement_category_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("procurement_categories.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    op.add_column(
        "items",
        sa.Column(
            "category_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("procurement_categories.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    op.execute(
        sa.text("""
        INSERT INTO cost_centers (id, code, label_zh, label_en, sort_order, created_at, updated_at)
        VALUES
            (gen_random_uuid(), 'CC-IT',    '信息技术部', 'IT Department',   1, now(), now()),
            (gen_random_uuid(), 'CC-ADMIN', '行政部',     'Administration',  2, now(), now()),
            (gen_random_uuid(), 'CC-PROD',  '产品部',     'Product',         3, now(), now()),
            (gen_random_uuid(), 'CC-FIN',   '财务部',     'Finance',         4, now(), now())
        ON CONFLICT (code) DO NOTHING
    """)
    )

    op.execute(
        sa.text("""
        INSERT INTO lookup_values (id, type, code, label_zh, label_en, sort_order, created_at, updated_at)
        VALUES
            (gen_random_uuid(), 'expense_type', 'capex', '资本性支出 CapEx', 'Capital Expenditure',  1, now(), now()),
            (gen_random_uuid(), 'expense_type', 'opex',  '运营性支出 OpEx',  'Operating Expenditure', 2, now(), now())
        ON CONFLICT (type, code) DO NOTHING
    """)
    )

    op.execute(
        sa.text("""
        INSERT INTO procurement_categories (id, code, label_zh, label_en, sort_order, level, created_at, updated_at)
        VALUES
            (gen_random_uuid(), 'server',       '服务器',     'Servers',           1, 1, now(), now()),
            (gen_random_uuid(), 'server_parts', '服务器配件', 'Server Parts',      2, 1, now(), now()),
            (gen_random_uuid(), 'laptop',       '笔记本电脑', 'Laptops',           3, 1, now(), now()),
            (gen_random_uuid(), 'network',      '网络设备',   'Network Equipment', 4, 1, now(), now()),
            (gen_random_uuid(), 'software',     '软件许可',   'Software Licenses', 5, 1, now(), now()),
            (gen_random_uuid(), 'service',      '服务',       'Services',          6, 1, now(), now())
        ON CONFLICT (code) DO NOTHING
    """)
    )

    op.execute(
        sa.text("""
        INSERT INTO procurement_categories (id, code, label_zh, label_en, sort_order, level, parent_id, created_at, updated_at)
        VALUES
            (gen_random_uuid(), 'memory', '内存', 'Memory', 1, 2, (SELECT id FROM procurement_categories WHERE code='server_parts'), now(), now()),
            (gen_random_uuid(), 'ssd',    'SSD',  'SSD',    2, 2, (SELECT id FROM procurement_categories WHERE code='server_parts'), now(), now()),
            (gen_random_uuid(), 'cpu',    'CPU',  'CPU',    3, 2, (SELECT id FROM procurement_categories WHERE code='server_parts'), now(), now()),
            (gen_random_uuid(), 'nic',    '网卡', 'NIC',    4, 2, (SELECT id FROM procurement_categories WHERE code='server_parts'), now(), now())
        ON CONFLICT (code) DO NOTHING
    """)
    )


def downgrade() -> None:
    op.drop_column("items", "category_id")
    op.drop_column("purchase_requisitions", "procurement_category_id")
    op.drop_column("purchase_requisitions", "expense_type_id")
    op.drop_column("purchase_requisitions", "cost_center_id")
    op.drop_table("lookup_values")
    op.drop_table("procurement_categories")
    op.drop_table("cost_centers")
