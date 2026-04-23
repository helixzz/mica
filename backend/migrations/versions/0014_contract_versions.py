"""contract versions

Revision ID: 0014
Revises: 0013
Create Date: 2026-04-23
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contract_versions",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("contract_id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("change_type", sa.String(length=32), nullable=False, server_default="created"),
        sa.Column("change_reason", sa.Text(), nullable=True),
        sa.Column("snapshot_json", JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("changed_by_id", PGUUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["contract_id"], ["contracts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["changed_by_id"], ["users.id"]),
        sa.UniqueConstraint("contract_id", "version_number"),
    )
    op.create_index("ix_contract_versions_contract_id", "contract_versions", ["contract_id"])


def downgrade() -> None:
    op.drop_index("ix_contract_versions_contract_id", table_name="contract_versions")
    op.drop_table("contract_versions")
