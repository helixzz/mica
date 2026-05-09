"""seed approval reminder and currency exchange system parameters

Revision ID: 0038
Revises: 0037
Create Date: 2026-05-10
"""

from datetime import UTC, datetime
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0038"
down_revision = "0037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop old CHECK constraint and re-add with 'currency' category
    op.execute("ALTER TABLE system_parameters DROP CONSTRAINT system_parameters_category_check")
    op.execute(
        """ALTER TABLE system_parameters ADD CONSTRAINT system_parameters_category_check
        CHECK (category = ANY (ARRAY[
            'approval','auth','sku','contract','upload','pagination',
            'audit','payment','feishu','email','currency'
        ]))"""
    )

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
                "email",
                "currency",
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
            "key": "approval.reminder_hours",
            "category": "approval",
            "value": 4,
            "data_type": "int",
            "default_value": 4,
            "min_value": 1,
            "max_value": 720,
            "unit": "hours",
            "description_zh": "待审批提醒间隔（小时），逾期未处理的审批将向审批人发送提醒",
            "description_en": "Approval reminder interval in hours; pending approvals beyond this interval will trigger reminder notifications to approvers",
            "is_sensitive": False,
            "updated_by_id": None,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": uuid4(),
            "key": "approval.reminder_enabled",
            "category": "approval",
            "value": True,
            "data_type": "bool",
            "default_value": True,
            "min_value": None,
            "max_value": None,
            "unit": None,
            "description_zh": "是否启用审批提醒通知",
            "description_en": "Enable approval reminder notifications",
            "is_sensitive": False,
            "updated_by_id": None,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": uuid4(),
            "key": "currency.exchange_rates",
            "category": "currency",
            "value": {"USD_CNY": 7.25, "EUR_CNY": 7.85, "JPY_CNY": 0.048, "GBP_CNY": 9.20, "HKD_CNY": 0.93},
            "data_type": "string",
            "default_value": {"USD_CNY": 7.25, "EUR_CNY": 7.85, "JPY_CNY": 0.048, "GBP_CNY": 9.20, "HKD_CNY": 0.93},
            "min_value": None,
            "max_value": None,
            "unit": None,
            "description_zh": "汇率对照表（JSON），键格式 SRC_DST（如 USD_CNY 表示美元兑人民币），值即汇率",
            "description_en": "Exchange rate table (JSON), key format SRC_DST (e.g. USD_CNY for USD to CNY), value is the rate",
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
            "DELETE FROM system_parameters WHERE key IN "
            "('approval.reminder_hours', 'approval.reminder_enabled', 'currency.exchange_rates');"
        )
    )
    op.execute("ALTER TABLE system_parameters DROP CONSTRAINT system_parameters_category_check")
    op.execute(
        """ALTER TABLE system_parameters ADD CONSTRAINT system_parameters_category_check
        CHECK (category = ANY (ARRAY[
            'approval','auth','sku','contract','upload','pagination',
            'audit','payment','feishu','email'
        ]))"""
    )
