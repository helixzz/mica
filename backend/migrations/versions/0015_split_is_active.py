"""split is_active into is_enabled + is_deleted for master data entities

Revision ID: 0015
Revises: 0014
Create Date: 2026-04-23
"""

import sqlalchemy as sa
from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None

TABLES = [
    "companies",
    "departments",
    "cost_centers",
    "procurement_categories",
    "lookup_values",
    "suppliers",
    "items",
]


def upgrade() -> None:
    for table in TABLES:
        op.add_column(table, sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")))
        op.add_column(table, sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")))

    for table in TABLES:
        op.execute(sa.text(f"UPDATE {table} SET is_enabled = is_active, is_deleted = NOT is_active"))

    for table in TABLES:
        op.drop_column(table, "is_active")


def downgrade() -> None:
    for table in TABLES:
        op.add_column(table, sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")))

    for table in TABLES:
        op.execute(sa.text(f"UPDATE {table} SET is_active = is_enabled AND NOT is_deleted"))

    for table in TABLES:
        op.drop_column(table, "is_enabled")
        op.drop_column(table, "is_deleted")
