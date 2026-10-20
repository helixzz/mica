"""over-receipt tolerance for purchase order lines

Revision ID: 0061
Revises: 0060
Create Date: 2026-10-20

v1.58.3: registers ``fulfillment.over_receipt_tolerance``.

Receipts used to accumulate with no ceiling at all, so a mistyped batch plus a
corrected one could leave a PO line above its ordered quantity (the reported
"200% received"). The value is a multiplier of the ordered quantity: the default
``1`` means "never accept more than ordered", and a business that knowingly
tolerates a supplier over-shipping can raise it in the admin console without a
code change.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0061"
down_revision = "0060"
branch_labels = None
depends_on = None

PARAM_KEY = "fulfillment.over_receipt_tolerance"


def upgrade() -> None:
    op.execute(
        sa.text(
            "INSERT INTO system_parameters (id, key, category, value, data_type,"
            " default_value, min_value, max_value, unit, description_zh,"
            " description_en, is_sensitive, created_at, updated_at)"
            " VALUES (gen_random_uuid(), :key, 'fulfillment', '1'::jsonb, 'decimal',"
            "  '1'::jsonb, NULL, NULL, NULL,"
            "  '单个采购订单行允许的收货上限系数（订购量 × 该系数）。1 表示不允许超收；"
            " 供应商习惯性多送时可调高',"
            "  'Receipt ceiling for one PO line, as a multiplier of the ordered"
            " quantity. 1 refuses any over-receipt; raise it when a supplier"
            " routinely over-ships',"
            "  false, now(), now())"
        ).bindparams(key=PARAM_KEY)
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM system_parameters WHERE key = :key").bindparams(key=PARAM_KEY))
