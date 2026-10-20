"""pdf compression: default to 200 dpi

Revision ID: 0066
Revises: 0065
Create Date: 2026-10-20

The team accepts 150-200 dpi for contract scans and asked for 200, which keeps
text noticeably crisper at ~7.7x instead of 10.4x. Measured on a synthetic
3-page 300 dpi scan: 200 dpi / q65 gives ~1 MB from 7.8 MB.

Only rewrites the row while it still holds the previous default, so a deliberate
manual choice is left alone.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0066"
down_revision = "0065"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE system_parameters "
            "SET value = to_jsonb(200), default_value = to_jsonb(200) "
            "WHERE key = 'pdf_compress.image_dpi' AND value = to_jsonb(150)"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE system_parameters "
            "SET value = to_jsonb(150), default_value = to_jsonb(150) "
            "WHERE key = 'pdf_compress.image_dpi' AND value = to_jsonb(200)"
        )
    )
