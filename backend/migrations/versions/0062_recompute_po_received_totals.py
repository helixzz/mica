"""recompute purchase order received totals from shipment lines

Revision ID: 0062
Revises: 0061
Create Date: 2026-10-20

v1.58.3: heals the totals that the increment-only receipt path left behind.

Before this release a shipment delete never gave back the quantities it had
added, so deleting a wrong batch and re-creating a corrected one counted the
same goods twice (the reported "200% received"). Fixing the write path stops new
drift, but rows already written keep their inflated totals — this migration
re-derives them from the shipment lines, which are the source of truth.

It also rolls a PO back to ``confirmed`` when every batch is gone, so a PO does
not keep claiming it was (partially) received after its shipments were deleted.

Rows are only rewritten when the recomputed value differs, so a healthy
database sees an empty update and the migration stays cheap.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0062"
down_revision = "0061"
branch_labels = None
depends_on = None

# Sum of received quantities per shipment line, ignoring shipments that were
# removed. This mirrors services/flow.py::recompute_po_receipt exactly.
_RECOMPUTE_ITEMS = """
UPDATE po_items pi
SET qty_received = COALESCE((
        SELECT SUM(si.qty_received)
        FROM shipment_items si
        JOIN shipments s ON s.id = si.shipment_id
        WHERE si.po_item_id = pi.id
    ), 0)
WHERE pi.qty_received IS DISTINCT FROM COALESCE((
        SELECT SUM(si.qty_received)
        FROM shipment_items si
        JOIN shipments s ON s.id = si.shipment_id
        WHERE si.po_item_id = pi.id
    ), 0)
"""

_RECOMPUTE_POS = """
WITH po_totals AS (
    SELECT po.id AS po_id,
           COALESCE(SUM(pi.qty_received), 0) AS received,
           COALESCE(SUM(pi.qty), 0) AS ordered
    FROM purchase_orders po
    LEFT JOIN po_items pi ON pi.po_id = po.id
    GROUP BY po.id
)
UPDATE purchase_orders po
SET qty_received = t.received,
    status = CASE
        WHEN t.ordered > 0 AND t.received >= t.ordered THEN 'fully_received'
        WHEN t.received > 0 THEN 'partially_received'
        WHEN po.status IN ('fully_received', 'partially_received') THEN 'confirmed'
        ELSE po.status
    END
FROM po_totals t
WHERE t.po_id = po.id
  AND (
        po.qty_received IS DISTINCT FROM t.received
     OR po.status IS DISTINCT FROM CASE
            WHEN t.ordered > 0 AND t.received >= t.ordered THEN 'fully_received'
            WHEN t.received > 0 THEN 'partially_received'
            WHEN po.status IN ('fully_received', 'partially_received') THEN 'confirmed'
            ELSE po.status
        END
  )
"""


def upgrade() -> None:
    op.execute(sa.text(_RECOMPUTE_ITEMS))
    op.execute(sa.text(_RECOMPUTE_POS))


def downgrade() -> None:
    # The pre-migration values were the corruption this migration removes, so
    # there is nothing meaningful to restore.
    pass
