"""add shipment_documents table for shipment attachments

Revision ID: 0016
Revises: 0015
Create Date: 2026-04-23
"""

import sqlalchemy as sa
from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shipment_documents",
        sa.Column("shipment_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("shipments.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("document_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("role", sa.String(32), nullable=False, server_default="attachment"),
        sa.Column("display_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("shipment_documents")
