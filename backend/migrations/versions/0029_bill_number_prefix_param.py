"""seed bill.number_prefix system parameter

Revision ID: 0029
Revises: 0028
Create Date: 2026-04-28
"""

from datetime import UTC, datetime
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0029"
down_revision = "0028"
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
    existing = bind.execute(
        sa.text("SELECT 1 FROM system_parameters WHERE key = 'bill.number_prefix' LIMIT 1")
    ).first()
    if existing is None:
        op.bulk_insert(
            system_parameters,
            [
                {
                    "id": uuid4(),
                    "key": "bill.number_prefix",
                    "category": "contract",
                    "value": "",
                    "data_type": "string",
                    "default_value": "",
                    "min_value": None,
                    "max_value": None,
                    "unit": None,
                    "description_zh": "账单编号自动生成的前缀；留空则自动按 INV-YYYY-NNNN 生成。例如设为 'B-' 可得 B-2026-0001。",
                    "description_en": "Prefix used when auto-generating internal bill numbers. Leave blank to fall back to INV-YYYY-NNNN format.",
                    "is_sensitive": False,
                    "updated_by_id": None,
                    "created_at": now,
                    "updated_at": now,
                },
            ],
        )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM system_parameters WHERE key = 'bill.number_prefix';"))
