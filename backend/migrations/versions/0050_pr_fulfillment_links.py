"""add pr_fulfillment_links table

Revision ID: 0050
Revises: 0049
Create Date: 2026-06-08

Maps POItems to PRItems with an explicit fulfillment type so we can track
deviations between original PR demand and actual PO fulfillment in later
versions (downgrades, substitutes, supplementary items).

v1.26 only writes EQUIVALENT links (preserves current 1:1 behavior).
Backfill: each existing po_items.pr_item_id becomes one EQUIVALENT link.
"""

import sqlalchemy as sa
from alembic import op

revision = "0050"
down_revision = "0049"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pr_fulfillment_links",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "pr_item_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("pr_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "po_item_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("po_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "qty_contribution",
            sa.Numeric(18, 4),
            nullable=False,
        ),
        sa.Column(
            "fulfillment_type",
            sa.String(32),
            nullable=False,
            server_default="equivalent",
        ),
        sa.Column("deviation_note", sa.Text, nullable=True),
        sa.Column(
            "created_by_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint("qty_contribution > 0", name="ck_pr_fulfillment_qty_positive"),
        sa.UniqueConstraint("po_item_id", name="uq_pr_fulfillment_po_item"),
    )
    op.create_index(
        "ix_pr_fulfillment_pr_item",
        "pr_fulfillment_links",
        ["pr_item_id", "fulfillment_type"],
    )

    # Backfill: every existing po_items row with pr_item_id gets one EQUIVALENT link.
    op.execute(
        sa.text(
            """
            INSERT INTO pr_fulfillment_links (
                id, pr_item_id, po_item_id, qty_contribution,
                fulfillment_type, created_by_id, created_at, updated_at
            )
            SELECT
                gen_random_uuid(),
                poi.pr_item_id,
                poi.id,
                COALESCE(poi.pr_qty_contribution, poi.qty),
                'equivalent',
                po.created_by_id,
                poi.created_at,
                poi.updated_at
            FROM po_items poi
            JOIN purchase_orders po ON po.id = poi.po_id
            WHERE poi.pr_item_id IS NOT NULL
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_pr_fulfillment_pr_item", table_name="pr_fulfillment_links")
    op.drop_table("pr_fulfillment_links")
