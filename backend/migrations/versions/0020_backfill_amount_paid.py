"""backfill purchase_orders.amount_paid from historical schedule-linked payments

Revision ID: 0020
Revises: 0019
Create Date: 2026-04-24
"""

import sqlalchemy as sa
from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            WITH schedule_paid AS (
                SELECT pr.po_id, COALESCE(SUM(pr.amount), 0) AS total_paid
                FROM payment_records pr
                WHERE pr.schedule_item_id IS NOT NULL
                  AND pr.status = 'confirmed'
                GROUP BY pr.po_id
            ),
            direct_paid AS (
                SELECT pr.po_id, COALESCE(SUM(pr.amount), 0) AS total_paid
                FROM payment_records pr
                WHERE pr.schedule_item_id IS NULL
                  AND pr.status = 'confirmed'
                GROUP BY pr.po_id
            )
            UPDATE purchase_orders po
            SET amount_paid = COALESCE(s.total_paid, 0) + COALESCE(d.total_paid, 0)
            FROM purchase_orders po2
            LEFT JOIN schedule_paid s ON s.po_id = po2.id
            LEFT JOIN direct_paid   d ON d.po_id = po2.id
            WHERE po.id = po2.id;
            """
        )
    )


def downgrade() -> None:
    pass
