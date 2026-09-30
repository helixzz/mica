"""clarify export.max_rows is a per-worksheet limit

Revision ID: 0057
Revises: 0056
Create Date: 2026-09-30

v1.53.0: the generic export framework (and, before it, the ledger endpoint)
enforces ``export.max_rows`` per worksheet, so a three-sheet workbook may hold
up to three times the configured value. Migration 0056 described it as a limit
on the whole export, which did not match the behaviour. Reword the parameter
instead of changing the limit, because tightening it would silently start
rejecting exports that used to succeed.
"""

import sqlalchemy as sa
from alembic import op

revision = "0057"
down_revision = "0056"
branch_labels = None
depends_on = None

_OLD_ZH = "单次导出的最大行数上限；超过时提示用户先收窄筛选条件。"
_NEW_ZH = "单次导出中每个工作表的最大行数上限；超过时提示用户先收窄筛选条件。"
_OLD_EN = (
    "Maximum rows allowed in a single export; exceeding it asks the user to narrow the "
    "filters first."
)
_NEW_EN = (
    "Maximum rows allowed per worksheet in a single export; exceeding it asks the user to "
    "narrow the filters first."
)


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE system_parameters SET description_zh = :zh, description_en = :en"
            " WHERE key = 'export.max_rows'"
        ).bindparams(zh=_NEW_ZH, en=_NEW_EN)
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE system_parameters SET description_zh = :zh, description_en = :en"
            " WHERE key = 'export.max_rows'"
        ).bindparams(zh=_OLD_ZH, en=_OLD_EN)
    )
