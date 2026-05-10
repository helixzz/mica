"""update bill.number_prefix description to match contract numbering rules

Revision ID: 0040
Revises: 0039
Create Date: 2026-05-10
"""

import sqlalchemy as sa
from alembic import op

revision = "0040"
down_revision = "0039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE system_parameters "
            "SET description_zh = '账单编号自动生成前缀（格式：{前缀}{YYYYMMDD}{001}）。留空默认 INV，如 INV20260510001。设为 ''B-'' 则生成 B-20260510001。', "
            "    description_en = 'Auto-generated bill number prefix (format: {prefix}{YYYYMMDD}{001}). Defaults to INV, e.g. INV20260510001. Custom prefix B- yields B-20260510001.' "
            "WHERE key = 'bill.number_prefix'"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE system_parameters "
            "SET description_zh = '账单编号自动生成的前缀；留空则自动按 INV-YYYY-NNNN 生成。例如设为 ''B-'' 可得 B-2026-0001。', "
            "    description_en = 'Prefix used when auto-generating internal bill numbers. Leave blank to fall back to INV-YYYY-NNNN format.' "
            "WHERE key = 'bill.number_prefix'"
        )
    )
