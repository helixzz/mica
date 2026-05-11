"""seed notification toggle system parameters

Revision ID: 0042
Revises: 0041
Create Date: 2026-05-11
"""

from datetime import UTC, datetime
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0042"
down_revision = "0041"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop old CHECK constraint and re-add with 'notification' category
    op.execute("ALTER TABLE system_parameters DROP CONSTRAINT system_parameters_category_check")
    op.execute(
        """ALTER TABLE system_parameters ADD CONSTRAINT system_parameters_category_check
        CHECK (category = ANY (ARRAY[
            'approval','auth','sku','contract','upload','pagination',
            'audit','payment','feishu','email','currency','notification'
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
                "notification",
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
            "key": "notification.po_created_enabled",
            "category": "notification",
            "value": True,
            "data_type": "bool",
            "default_value": True,
            "min_value": None,
            "max_value": None,
            "unit": None,
            "description_zh": "是否启用采购订单创建通知",
            "description_en": "Enable PO created notification",
            "is_sensitive": False,
            "updated_by_id": None,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": uuid4(),
            "key": "notification.contract_created_enabled",
            "category": "notification",
            "value": True,
            "data_type": "bool",
            "default_value": True,
            "min_value": None,
            "max_value": None,
            "unit": None,
            "description_zh": "是否启用合同创建通知",
            "description_en": "Enable contract created notification",
            "is_sensitive": False,
            "updated_by_id": None,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": uuid4(),
            "key": "notification.payment_created_enabled",
            "category": "notification",
            "value": True,
            "data_type": "bool",
            "default_value": True,
            "min_value": None,
            "max_value": None,
            "unit": None,
            "description_zh": "是否启用付款创建通知",
            "description_en": "Enable payment created notification",
            "is_sensitive": False,
            "updated_by_id": None,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": uuid4(),
            "key": "notification.invoice_created_enabled",
            "category": "notification",
            "value": True,
            "data_type": "bool",
            "default_value": True,
            "min_value": None,
            "max_value": None,
            "unit": None,
            "description_zh": "是否启用发票创建通知",
            "description_en": "Enable invoice created notification",
            "is_sensitive": False,
            "updated_by_id": None,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": uuid4(),
            "key": "notification.shipment_received_enabled",
            "category": "notification",
            "value": True,
            "data_type": "bool",
            "default_value": True,
            "min_value": None,
            "max_value": None,
            "unit": None,
            "description_zh": "是否启用收货通知",
            "description_en": "Enable shipment received notification",
            "is_sensitive": False,
            "updated_by_id": None,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": uuid4(),
            "key": "notification.rfq_created_enabled",
            "category": "notification",
            "value": True,
            "data_type": "bool",
            "default_value": True,
            "min_value": None,
            "max_value": None,
            "unit": None,
            "description_zh": "是否启用 RFQ 创建通知",
            "description_en": "Enable RFQ created notification",
            "is_sensitive": False,
            "updated_by_id": None,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": uuid4(),
            "key": "notification.rfq_awarded_enabled",
            "category": "notification",
            "value": True,
            "data_type": "bool",
            "default_value": True,
            "min_value": None,
            "max_value": None,
            "unit": None,
            "description_zh": "是否启用 RFQ 定标通知",
            "description_en": "Enable RFQ awarded notification",
            "is_sensitive": False,
            "updated_by_id": None,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": uuid4(),
            "key": "notification.contract_status_changed_enabled",
            "category": "notification",
            "value": True,
            "data_type": "bool",
            "default_value": True,
            "min_value": None,
            "max_value": None,
            "unit": None,
            "description_zh": "是否启用合同状态变更通知",
            "description_en": "Enable contract status changed notification",
            "is_sensitive": False,
            "updated_by_id": None,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": uuid4(),
            "key": "notification.invoice_matched_enabled",
            "category": "notification",
            "value": True,
            "data_type": "bool",
            "default_value": True,
            "min_value": None,
            "max_value": None,
            "unit": None,
            "description_zh": "是否启用发票匹配通知",
            "description_en": "Enable invoice matched notification",
            "is_sensitive": False,
            "updated_by_id": None,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": uuid4(),
            "key": "notification.delivery_plan_created_enabled",
            "category": "notification",
            "value": True,
            "data_type": "bool",
            "default_value": True,
            "min_value": None,
            "max_value": None,
            "unit": None,
            "description_zh": "是否启用交货计划创建通知",
            "description_en": "Enable delivery plan created notification",
            "is_sensitive": False,
            "updated_by_id": None,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": uuid4(),
            "key": "notification.pr_created_enabled",
            "category": "notification",
            "value": True,
            "data_type": "bool",
            "default_value": True,
            "min_value": None,
            "max_value": None,
            "unit": None,
            "description_zh": "是否启用采购申请创建通知",
            "description_en": "Enable PR created notification",
            "is_sensitive": False,
            "updated_by_id": None,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": uuid4(),
            "key": "notification.approval_enabled",
            "category": "notification",
            "value": True,
            "data_type": "bool",
            "default_value": True,
            "min_value": None,
            "max_value": None,
            "unit": None,
            "description_zh": "是否启用审批通知",
            "description_en": "Enable approval notification",
            "is_sensitive": False,
            "updated_by_id": None,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": uuid4(),
            "key": "notification.approval_reminder_enabled",
            "category": "notification",
            "value": True,
            "data_type": "bool",
            "default_value": True,
            "min_value": None,
            "max_value": None,
            "unit": None,
            "description_zh": "是否启用审批提醒通知",
            "description_en": "Enable approval reminder notification",
            "is_sensitive": False,
            "updated_by_id": None,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": uuid4(),
            "key": "notification.sla_escalation_enabled",
            "category": "notification",
            "value": True,
            "data_type": "bool",
            "default_value": True,
            "min_value": None,
            "max_value": None,
            "unit": None,
            "description_zh": "是否启用 SLA 升级通知",
            "description_en": "Enable SLA escalation notification",
            "is_sensitive": False,
            "updated_by_id": None,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": uuid4(),
            "key": "notification.contract_expiring_enabled",
            "category": "notification",
            "value": True,
            "data_type": "bool",
            "default_value": True,
            "min_value": None,
            "max_value": None,
            "unit": None,
            "description_zh": "是否启用合同到期通知",
            "description_en": "Enable contract expiring notification",
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
            "DELETE FROM system_parameters WHERE key LIKE 'notification.%';"
        )
    )
    op.execute("ALTER TABLE system_parameters DROP CONSTRAINT system_parameters_category_check")
    op.execute(
        """ALTER TABLE system_parameters ADD CONSTRAINT system_parameters_category_check
        CHECK (category = ANY (ARRAY[
            'approval','auth','sku','contract','upload','pagination',
            'audit','payment','feishu','email','currency'
        ]))"""
    )
