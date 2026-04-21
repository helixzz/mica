"""Add Department.parent_id and Supplier.notes columns.

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-21 21:30:00.000000

Supports Department tree hierarchy (parent_id FK to self) and
Supplier free-form notes field introduced by master data CRUD.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "departments",
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_departments_parent_id_departments",
        "departments",
        "departments",
        ["parent_id"],
        ["id"],
    )

    op.add_column(
        "suppliers",
        sa.Column("notes", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("suppliers", "notes")
    op.drop_constraint(
        "fk_departments_parent_id_departments",
        "departments",
        type_="foreignkey",
    )
    op.drop_column("departments", "parent_id")
