"""relax pr_fulfillment_links uniqueness for multi-link POItems

Revision ID: 0051
Revises: 0050
Create Date: 2026-06-09

v1.26 introduced `pr_fulfillment_links` with UNIQUE(po_item_id) — assuming
each POItem maps to at most one PRItem. v1.27 needs to support:
  - splitting one PRItem across multiple POItems (1-to-N)
  - supplementary POItems that fulfill an additional context for an
    already-fulfilled PRItem (a POItem could in theory anchor to >1 link
    in future iterations)

We replace the constraint with UNIQUE(pr_item_id, po_item_id) so the same
(PRItem, POItem) pair cannot be linked twice, but the same POItem can
contribute to multiple PRItems if a future use case demands it.
"""

from alembic import op

revision = "0051"
down_revision = "0050"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_pr_fulfillment_po_item",
        "pr_fulfillment_links",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_pr_fulfillment_pr_item_po_item",
        "pr_fulfillment_links",
        ["pr_item_id", "po_item_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_pr_fulfillment_pr_item_po_item",
        "pr_fulfillment_links",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_pr_fulfillment_po_item",
        "pr_fulfillment_links",
        ["po_item_id"],
    )
