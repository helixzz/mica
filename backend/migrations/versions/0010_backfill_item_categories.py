"""backfill item category_id for seed items

Revision ID: 0010
Revises: 0009
Create Date: 2026-04-22
"""

from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text("""
        UPDATE items SET category_id = pc.id
        FROM procurement_categories pc
        WHERE items.category_id IS NULL AND items.category = pc.code
    """)
    )

    op.execute(
        sa.text("""
        UPDATE items SET category_id = (SELECT id FROM procurement_categories WHERE code='switch')
        WHERE code = 'SKU-NET-S5248' AND category_id = (SELECT id FROM procurement_categories WHERE code='network')
    """)
    )

    op.execute(
        sa.text("""
        UPDATE items SET category_id = (SELECT id FROM procurement_categories WHERE code='saas')
        WHERE code = 'SKU-SW-M365' AND category_id = (SELECT id FROM procurement_categories WHERE code='software')
    """)
    )


def downgrade() -> None:
    op.execute(
        sa.text("""
        UPDATE items SET category_id = NULL
        WHERE code LIKE 'SKU-%'
    """)
    )
