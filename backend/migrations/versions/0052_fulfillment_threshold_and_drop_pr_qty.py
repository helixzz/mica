"""drop pr_qty_contribution and seed fulfillment threshold

Revision ID: 0052
Revises: 0051
Create Date: 2026-06-09

v1.28 cleanup combining three changes:
- drop unused po_items.pr_qty_contribution (replaced by pr_fulfillment_links)
- seed fulfillment.deviation_approval_threshold (default 100000)
- add 'fulfillment' to system_parameters.category check constraint
"""

import sqlalchemy as sa
from alembic import op

revision = "0052"
down_revision = "0051"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("po_items", "pr_qty_contribution")

    op.execute(sa.text(
        "ALTER TABLE system_parameters DROP CONSTRAINT IF EXISTS system_parameters_category_check"
    ))
    op.execute(sa.text(
        "ALTER TABLE system_parameters ADD CONSTRAINT system_parameters_category_check"
        " CHECK (category IN ('approval','auth','sku','contract','upload','pagination',"
        "'audit','payment','feishu','email','currency','notification','system','fulfillment'))"
    ))

    op.execute(
        sa.text(
            "INSERT INTO system_parameters"
            " (id, key, category, value, data_type, default_value,"
            "  min_value, max_value, unit, description_zh, description_en,"
            "  is_sensitive, created_at, updated_at)"
            " VALUES (gen_random_uuid(), 'fulfillment.deviation_approval_threshold',"
            "  'fulfillment', '100000'::jsonb, 'number', '100000'::jsonb,"
            "  '0', '100000000', 'CNY',"
            "  '降配/替换履约审批阈值。单条 link 的金额（贡献数量 * PO 单价）超过该值将自动触发审批流程',"
            "  'Deviation approval threshold. Downgrade or substitute fulfillment links with amount above this value trigger an approval flow',"
            "  false, now(), now())"
            " ON CONFLICT (key) DO NOTHING"
        )
    )


def downgrade() -> None:
    op.execute("DELETE FROM system_parameters WHERE key = 'fulfillment.deviation_approval_threshold'")
    op.execute(sa.text(
        "ALTER TABLE system_parameters DROP CONSTRAINT IF EXISTS system_parameters_category_check"
    ))
    op.execute(sa.text(
        "ALTER TABLE system_parameters ADD CONSTRAINT system_parameters_category_check"
        " CHECK (category IN ('approval','auth','sku','contract','upload','pagination',"
        "'audit','payment','feishu','email','currency','notification','system'))"
    ))

    op.add_column(
        "po_items",
        sa.Column("pr_qty_contribution", sa.Numeric(18, 4), nullable=True),
    )
