"""seed feishu system parameters and add feishu category

Revision ID: 0031
Revises: 0030
Create Date: 2026-04-29
"""

from datetime import UTC, datetime
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0031"
down_revision = "0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add 'feishu' to the CHECK constraint on system_parameters.category
    op.execute("""
        DO $$
        DECLARE
            constraint_name text;
        BEGIN
            SELECT con.conname INTO constraint_name
            FROM pg_constraint con
            JOIN pg_class rel ON rel.oid = con.conrelid
            WHERE rel.relname = 'system_parameters'
              AND con.contype = 'c'
              AND pg_get_constraintdef(con.oid) LIKE '%category%';
            IF constraint_name IS NOT NULL THEN
                EXECUTE 'ALTER TABLE system_parameters DROP CONSTRAINT ' || constraint_name;
            END IF;
        END $$;
    """)
    op.execute("""
        ALTER TABLE system_parameters ADD CONSTRAINT system_parameters_category_check
        CHECK (category IN (
            'approval', 'auth', 'sku', 'contract', 'upload',
            'pagination', 'audit', 'payment', 'feishu'
        ));
    """)

    system_parameters = sa.table(
        "system_parameters",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("key", sa.String),
        sa.column(
            "category",
            sa.Enum(
                "approval",
                "auth",
                "sku",
                "contract",
                "upload",
                "pagination",
                "audit",
                "payment",
                "feishu",
                name="systemparametercategory",
                native_enum=False,
                length=32,
            ),
        ),
        sa.column("value", postgresql.JSONB(astext_type=sa.Text())),
        sa.column("data_type", sa.String),
        sa.column("default_value", postgresql.JSONB(astext_type=sa.Text())),
        sa.column("min_value", postgresql.JSONB(astext_type=sa.Text())),
        sa.column("max_value", postgresql.JSONB(astext_type=sa.Text())),
        sa.column("unit", sa.String),
        sa.column("description_zh", sa.Text),
        sa.column("description_en", sa.Text),
        sa.column("is_sensitive", sa.Boolean),
        sa.column("updated_by_id", postgresql.UUID(as_uuid=True)),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )

    now = datetime.now(UTC)
    bind = op.get_bind()

    params = [
        {
            "id": uuid4(),
            "key": "auth.feishu.app_id",
            "category": "feishu",
            "value": "",
            "data_type": "string",
            "default_value": "",
            "min_value": None,
            "max_value": None,
            "unit": None,
            "description_zh": "飞书应用 App ID",
            "description_en": "Feishu App ID",
            "is_sensitive": False,
            "updated_by_id": None,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": uuid4(),
            "key": "auth.feishu.app_secret",
            "category": "feishu",
            "value": "",
            "data_type": "string",
            "default_value": "",
            "min_value": None,
            "max_value": None,
            "unit": None,
            "description_zh": "飞书应用 App Secret",
            "description_en": "Feishu App Secret",
            "is_sensitive": True,
            "updated_by_id": None,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": uuid4(),
            "key": "auth.feishu.enabled",
            "category": "feishu",
            "value": False,
            "data_type": "bool",
            "default_value": False,
            "min_value": None,
            "max_value": None,
            "unit": None,
            "description_zh": "是否启用飞书集成",
            "description_en": "Enable Feishu integration",
            "is_sensitive": False,
            "updated_by_id": None,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": uuid4(),
            "key": "auth.feishu.notify_on_pr",
            "category": "feishu",
            "value": True,
            "data_type": "bool",
            "default_value": True,
            "min_value": None,
            "max_value": None,
            "unit": None,
            "description_zh": "采购申请提交时发送飞书卡片通知",
            "description_en": "Send Feishu card notification on PR submission",
            "is_sensitive": False,
            "updated_by_id": None,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": uuid4(),
            "key": "auth.feishu.notify_on_approval",
            "category": "feishu",
            "value": True,
            "data_type": "bool",
            "default_value": True,
            "min_value": None,
            "max_value": None,
            "unit": None,
            "description_zh": "审批决定时发送飞书卡片通知",
            "description_en": "Send Feishu card notification on approval decision",
            "is_sensitive": False,
            "updated_by_id": None,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": uuid4(),
            "key": "auth.feishu.notify_on_po",
            "category": "feishu",
            "value": True,
            "data_type": "bool",
            "default_value": True,
            "min_value": None,
            "max_value": None,
            "unit": None,
            "description_zh": "采购订单创建时发送飞书卡片通知",
            "description_en": "Send Feishu card notification on PO creation",
            "is_sensitive": False,
            "updated_by_id": None,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": uuid4(),
            "key": "auth.feishu.notify_on_payment",
            "category": "feishu",
            "value": True,
            "data_type": "bool",
            "default_value": True,
            "min_value": None,
            "max_value": None,
            "unit": None,
            "description_zh": "付款待审核时发送飞书卡片通知",
            "description_en": "Send Feishu card notification on payment pending review",
            "is_sensitive": False,
            "updated_by_id": None,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": uuid4(),
            "key": "auth.feishu.notify_on_contract_expiry",
            "category": "feishu",
            "value": True,
            "data_type": "bool",
            "default_value": True,
            "min_value": None,
            "max_value": None,
            "unit": None,
            "description_zh": "合同即将到期时发送飞书卡片通知",
            "description_en": "Send Feishu card notification on contract expiry",
            "is_sensitive": False,
            "updated_by_id": None,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": uuid4(),
            "key": "auth.feishu.payment_workflow",
            "category": "feishu",
            "value": False,
            "data_type": "bool",
            "default_value": False,
            "min_value": None,
            "max_value": None,
            "unit": None,
            "description_zh": "是否启用飞书付款审批工作流（创建飞书审批实例）",
            "description_en": "Enable Feishu payment approval workflow (create Feishu approval instances)",
            "is_sensitive": False,
            "updated_by_id": None,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": uuid4(),
            "key": "auth.feishu.approval_code",
            "category": "feishu",
            "value": "",
            "data_type": "string",
            "default_value": "",
            "min_value": None,
            "max_value": None,
            "unit": None,
            "description_zh": "飞书审批定义 Code（用于付款审批工作流）",
            "description_en": "Feishu approval definition code (for payment approval workflow)",
            "is_sensitive": False,
            "updated_by_id": None,
            "created_at": now,
            "updated_at": now,
        },
    ]

    for param in params:
        existing = bind.execute(
            sa.text("SELECT 1 FROM system_parameters WHERE key = :key LIMIT 1"),
            {"key": param["key"]},
        ).first()
        if existing is None:
            op.bulk_insert(system_parameters, [param])


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM system_parameters WHERE key LIKE 'auth.feishu.%';"
        )
    )
    # Remove 'feishu' from CHECK constraint
    op.execute("""
        DO $$
        DECLARE
            constraint_name text;
        BEGIN
            SELECT con.conname INTO constraint_name
            FROM pg_constraint con
            JOIN pg_class rel ON rel.oid = con.conrelid
            WHERE rel.relname = 'system_parameters'
              AND con.contype = 'c'
              AND pg_get_constraintdef(con.oid) LIKE '%category%';
            IF constraint_name IS NOT NULL THEN
                EXECUTE 'ALTER TABLE system_parameters DROP CONSTRAINT ' || constraint_name;
            END IF;
        END $$;
    """)
    op.execute("""
        ALTER TABLE system_parameters ADD CONSTRAINT system_parameters_category_check
        CHECK (category IN (
            'approval', 'auth', 'sku', 'contract', 'upload',
            'pagination', 'audit', 'payment'
        ));
    """)