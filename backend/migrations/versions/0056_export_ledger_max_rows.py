"""seed export.max_rows system parameter

Revision ID: 0056
Revises: 0055
Create Date: 2026-06-03

v1.52.0 采购台账导出：
- 给 system_parameters.category 增加 'export' 取值
- seed export.max_rows（单次导出行数上限，默认 5000）
"""

import sqlalchemy as sa
from alembic import op

revision = "0056"
down_revision = "0055"
branch_labels = None
depends_on = None

_CATEGORIES_WITH_EXPORT = (
    "'approval','auth','sku','contract','upload','pagination',"
    "'audit','payment','feishu','email','currency','notification','system','fulfillment','export'"
)
_CATEGORIES_WITHOUT_EXPORT = (
    "'approval','auth','sku','contract','upload','pagination',"
    "'audit','payment','feishu','email','currency','notification','system','fulfillment'"
)


def upgrade() -> None:
    op.execute(
        sa.text(
            "ALTER TABLE system_parameters DROP CONSTRAINT IF EXISTS "
            "system_parameters_category_check"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE system_parameters ADD CONSTRAINT system_parameters_category_check"
            f" CHECK (category IN ({_CATEGORIES_WITH_EXPORT}))"
        )
    )

    op.execute(
        sa.text(
            "INSERT INTO system_parameters"
            " (id, key, category, value, data_type, default_value,"
            "  min_value, max_value, unit, description_zh, description_en,"
            "  is_sensitive, created_at, updated_at)"
            " VALUES (gen_random_uuid(), 'export.max_rows', 'export',"
            "  '5000'::jsonb, 'int', '5000'::jsonb, '1', '200000', 'rows',"
            "  '单次导出的最大行数上限；超过时提示用户先收窄筛选条件。',"
            "  'Maximum rows allowed in a single export; exceeding it asks the user"
            " to narrow the filters first.',"
            "  false, now(), now())"
            " ON CONFLICT (key) DO NOTHING"
        )
    )


def downgrade() -> None:
    op.execute("DELETE FROM system_parameters WHERE key = 'export.max_rows'")
    op.execute(
        sa.text(
            "ALTER TABLE system_parameters DROP CONSTRAINT IF EXISTS "
            "system_parameters_category_check"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE system_parameters ADD CONSTRAINT system_parameters_category_check"
            f" CHECK (category IN ({_CATEGORIES_WITHOUT_EXPORT}))"
        )
    )
