"""seed system parameter app.base_url

Revision ID: 0048
Revises: 0047
Create Date: 2026-05-26
"""

import sqlalchemy as sa
from alembic import op

revision = "0048"
down_revision = "0047"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text(
        "ALTER TABLE system_parameters DROP CONSTRAINT IF EXISTS system_parameters_category_check"
    ))
    op.execute(sa.text(
        "ALTER TABLE system_parameters ADD CONSTRAINT system_parameters_category_check"
        " CHECK (category IN ('approval','auth','sku','contract','upload','pagination',"
        "'audit','payment','feishu','email','currency','notification','system'))"
    ))
    op.execute(
        sa.text(
            "INSERT INTO system_parameters"
            " (id, key, category, value, data_type, default_value,"
            "  min_value, max_value, unit, description_zh, description_en,"
            "  is_sensitive, created_at, updated_at)"
            " VALUES (gen_random_uuid(), 'app.base_url', 'system',"
            "  '\"https://mica.jqdomain.com\"'::jsonb, 'string',"
            "  '\"http://localhost:8900\"'::jsonb,"
            "  null, null, null,"
            "  '系统访问地址（用于通知消息中的链接拼接）',"
            "  'Application base URL (used for notification link generation)',"
            "  false, now(), now())"
            " ON CONFLICT (key) DO NOTHING"
        )
    )


def downgrade() -> None:
    op.execute("DELETE FROM system_parameters WHERE key = 'app.base_url'")
    op.execute(sa.text(
        "ALTER TABLE system_parameters DROP CONSTRAINT IF EXISTS system_parameters_category_check"
    ))
    op.execute(sa.text(
        "ALTER TABLE system_parameters ADD CONSTRAINT system_parameters_category_check"
        " CHECK (category IN ('approval','auth','sku','contract','upload','pagination',"
        "'audit','payment','feishu','email','currency','notification'))"
    ))
