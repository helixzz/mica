"""add supplier payee bank fields

Revision ID: 0019
Revises: 0018
Create Date: 2026-04-24
"""

import sqlalchemy as sa
from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("suppliers", sa.Column("payee_name", sa.String(length=255), nullable=True))
    op.add_column("suppliers", sa.Column("payee_bank", sa.String(length=255), nullable=True))
    op.add_column(
        "suppliers",
        sa.Column("payee_bank_account", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("suppliers", "payee_bank_account")
    op.drop_column("suppliers", "payee_bank")
    op.drop_column("suppliers", "payee_name")
