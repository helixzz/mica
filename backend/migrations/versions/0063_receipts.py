"""receipts: receiving becomes its own act

Revision ID: 0063
Revises: 0062
Create Date: 2026-10-20

v1.58.4: separates "the supplier shipped it" from "we accepted it".

Until now a shipment line carried both quantities and the buyer filled them in
one gesture, so the order never had a state for "on its way" and a line could
only be received once. ``receipts`` gives receiving its own rows: several
partial receipts per line, each attributed to a person and a moment, optionally
pinned to the batch it arrived in.

* New table ``receipts`` (PO line, quantity, optional batch, receiver, time).
* Backfill: every existing shipment line with a non-zero received quantity
  becomes one receipt, so aggregates do not move during the upgrade. The
  receiver comes from the batch (``received_by_id``) or, failing that, from the
  order's creator; the timestamp from the batch's arrival date or its creation.
* ``po_items.qty_received`` is re-derived from receipts (idempotent: only rows
  that differ are written) and the order status is recomputed against the new
  four-state model, including the new ``shipped``.
* ``shipment_items.qty_received`` is kept, now as a derived cache of what each
  batch contributed. It stops being the source of truth.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0063"
down_revision = "0062"
branch_labels = None
depends_on = None

_BACKFILL = """
INSERT INTO receipts (
    id, po_id, po_item_id, shipment_id, qty, received_by_id, received_at,
    created_at, updated_at
)
SELECT gen_random_uuid(),
       s.po_id,
       si.po_item_id,
       si.shipment_id,
       si.qty_received,
       COALESCE(s.received_by_id, po.created_by_id),
       COALESCE(s.actual_date::timestamptz, s.created_at),
       now(),
       now()
FROM shipment_items si
JOIN shipments s ON s.id = si.shipment_id
JOIN purchase_orders po ON po.id = s.po_id
WHERE si.qty_received > 0
"""

# Mirrors services/flow.py::recompute_po_receipt for the item level.
_RECOMPUTE_ITEMS = """
UPDATE po_items pi
SET qty_received = COALESCE((
        SELECT SUM(r.qty) FROM receipts r WHERE r.po_item_id = pi.id
    ), 0)
WHERE pi.qty_received IS DISTINCT FROM COALESCE((
        SELECT SUM(r.qty) FROM receipts r WHERE r.po_item_id = pi.id
    ), 0)
"""

# Four-state model: receipts win, then "a batch exists" means shipped. Draft,
# cancelled and closed are terminal and never rewritten.
_RECOMPUTE_STATUS = """
WITH po_totals AS (
    SELECT po.id AS po_id,
           COALESCE(SUM(pi.qty_received), 0) AS received,
           COALESCE(SUM(pi.qty), 0) AS ordered
    FROM purchase_orders po
    LEFT JOIN po_items pi ON pi.po_id = po.id
    GROUP BY po.id
),
batch AS (
    SELECT DISTINCT po_id FROM shipments
)
UPDATE purchase_orders po
SET qty_received = t.received,
    status = CASE
        WHEN po.status IN ('draft', 'cancelled', 'closed') THEN po.status
        WHEN t.ordered > 0 AND t.received >= t.ordered THEN 'fully_received'
        WHEN t.received > 0 THEN 'partially_received'
        WHEN b.po_id IS NOT NULL THEN 'shipped'
        WHEN po.status IN ('fully_received', 'partially_received', 'shipped') THEN 'confirmed'
        ELSE po.status
    END
FROM po_totals t
LEFT JOIN batch b ON b.po_id = t.po_id
WHERE t.po_id = po.id
  AND (
        po.qty_received IS DISTINCT FROM t.received
     OR po.status IS DISTINCT FROM CASE
            WHEN po.status IN ('draft', 'cancelled', 'closed') THEN po.status
            WHEN t.ordered > 0 AND t.received >= t.ordered THEN 'fully_received'
            WHEN t.received > 0 THEN 'partially_received'
            WHEN b.po_id IS NOT NULL THEN 'shipped'
            WHEN po.status IN ('fully_received', 'partially_received', 'shipped') THEN 'confirmed'
            ELSE po.status
        END
  )
"""


def upgrade() -> None:
    op.create_table(
        "receipts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "po_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("purchase_orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "po_item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("po_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "shipment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("shipments.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("qty", sa.Numeric(18, 4), nullable=False),
        sa.Column(
            "received_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_receipts_po_id", "receipts", ["po_id"])
    op.create_index("ix_receipts_po_item_id", "receipts", ["po_item_id"])
    op.create_index("ix_receipts_shipment_id", "receipts", ["shipment_id"])

    op.execute(sa.text(_BACKFILL))
    op.execute(sa.text(_RECOMPUTE_ITEMS))
    op.execute(sa.text(_RECOMPUTE_STATUS))


def downgrade() -> None:
    op.drop_index("ix_receipts_shipment_id", table_name="receipts")
    op.drop_index("ix_receipts_po_item_id", table_name="receipts")
    op.drop_index("ix_receipts_po_id", table_name="receipts")
    op.drop_table("receipts")
