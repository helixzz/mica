"""seed approval SLA system parameters

Revision ID: 0036
Revises: 0035
Create Date: 2026-05-04
"""

from datetime import UTC, datetime
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0036"
down_revision = "0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
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
            "key": "approval.sla_hours",
            "category": "approval",
            "value": 24,
            "data_type": "int",
            "default_value": 24,
            "min_value": 1,
            "max_value": 720,
            "unit": "hours",
            "description_zh": "标准审批 SLA 时限（小时）",
            "description_en": "Standard approval SLA timeout in hours",
            "is_sensitive": False,
            "updated_by_id": None,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": uuid4(),
            "key": "approval.sla_urgent_hours",
            "category": "approval",
            "value": 4,
            "data_type": "int",
            "default_value": 4,
            "min_value": 1,
            "max_value": 168,
            "unit": "hours",
            "description_zh": "紧急审批 SLA 时限（小时）",
            "description_en": "Urgent approval SLA timeout in hours",
            "is_sensitive": False,
            "updated_by_id": None,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": uuid4(),
            "key": "approval.sla_alert_enabled",
            "category": "approval",
            "value": True,
            "data_type": "bool",
            "default_value": True,
            "min_value": None,
            "max_value": None,
            "unit": None,
            "description_zh": "是否启用审批 SLA 预警",
            "description_en": "Enable approval SLA alerts",
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
    op.execute(sa.text("DELETE FROM system_parameters WHERE key LIKE 'approval.sla_%';"))
