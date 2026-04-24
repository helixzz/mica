"""auto-link orphan PaymentRecords to unambiguous contract

Revision ID: 0022
Revises: 0021
Create Date: 2026-04-25
"""

import sqlalchemy as sa
from alembic import op

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            WITH unambiguous AS (
                SELECT c.po_id, c.id AS contract_id
                FROM contracts c
                WHERE (SELECT COUNT(*) FROM contracts c2 WHERE c2.po_id = c.po_id) = 1
            )
            UPDATE payment_records pr
            SET contract_id = u.contract_id
            FROM unambiguous u
            WHERE pr.po_id = u.po_id
              AND pr.contract_id IS NULL;
            """
        )
    )


def downgrade() -> None:
    pass
