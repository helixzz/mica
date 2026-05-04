"""seed email system parameters

Revision ID: 0035
Revises: 0034
Create Date: 2026-05-04
"""

from datetime import UTC, datetime
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0035"
down_revision = "0034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add 'email' to the CHECK constraint on system_parameters.category
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
            'pagination', 'audit', 'payment', 'feishu', 'email'
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
            "key": "email.enabled",
            "category": "email",
            "value": False,
            "data_type": "bool",
            "default_value": False,
            "min_value": None,
            "max_value": None,
            "unit": None,
            "description_zh": "是否启用邮件通知",
            "description_en": "Enable email notifications",
            "is_sensitive": False,
            "updated_by_id": None,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": uuid4(),
            "key": "email.smtp_host",
            "category": "email",
            "value": "",
            "data_type": "string",
            "default_value": "",
            "min_value": None,
            "max_value": None,
            "unit": None,
            "description_zh": "SMTP 服务器地址",
            "description_en": "SMTP server host",
            "is_sensitive": False,
            "updated_by_id": None,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": uuid4(),
            "key": "email.smtp_port",
            "category": "email",
            "value": 587,
            "data_type": "int",
            "default_value": 587,
            "min_value": None,
            "max_value": None,
            "unit": None,
            "description_zh": "SMTP 服务器端口",
            "description_en": "SMTP server port",
            "is_sensitive": False,
            "updated_by_id": None,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": uuid4(),
            "key": "email.smtp_user",
            "category": "email",
            "value": "",
            "data_type": "string",
            "default_value": "",
            "min_value": None,
            "max_value": None,
            "unit": None,
            "description_zh": "SMTP 用户名",
            "description_en": "SMTP username",
            "is_sensitive": False,
            "updated_by_id": None,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": uuid4(),
            "key": "email.smtp_password",
            "category": "email",
            "value": "",
            "data_type": "string",
            "default_value": "",
            "min_value": None,
            "max_value": None,
            "unit": None,
            "description_zh": "SMTP 密码",
            "description_en": "SMTP password",
            "is_sensitive": True,
            "updated_by_id": None,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": uuid4(),
            "key": "email.daily_digest",
            "category": "email",
            "value": False,
            "data_type": "bool",
            "default_value": False,
            "min_value": None,
            "max_value": None,
            "unit": None,
            "description_zh": "是否启用每日邮件摘要",
            "description_en": "Enable daily email digest",
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
            "DELETE FROM system_parameters WHERE key LIKE 'email.%';"
        )
    )
    # Remove 'email' from CHECK constraint
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