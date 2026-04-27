"""add user_cost_centers + user_departments M:N tables

Revision ID: 0028
Revises: 0027
Create Date: 2026-04-27

Backfills each user's existing department_id into the new user_departments
M:N table so v0.9.28 and earlier behaviour is preserved: a user who was
in department X is now in the user_departments link for department X.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_cost_centers",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cost_center_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE", name="fk_user_cost_centers_user_id"
        ),
        sa.ForeignKeyConstraint(
            ["cost_center_id"],
            ["cost_centers.id"],
            ondelete="CASCADE",
            name="fk_user_cost_centers_cost_center_id",
        ),
        sa.PrimaryKeyConstraint("user_id", "cost_center_id", name="pk_user_cost_centers"),
    )
    op.create_index(
        "ix_user_cost_centers_cost_center_id",
        "user_cost_centers",
        ["cost_center_id"],
    )

    op.create_table(
        "user_departments",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE", name="fk_user_departments_user_id"
        ),
        sa.ForeignKeyConstraint(
            ["department_id"],
            ["departments.id"],
            ondelete="CASCADE",
            name="fk_user_departments_department_id",
        ),
        sa.PrimaryKeyConstraint("user_id", "department_id", name="pk_user_departments"),
    )
    op.create_index(
        "ix_user_departments_department_id",
        "user_departments",
        ["department_id"],
    )

    op.execute(
        sa.text(
            """
            INSERT INTO user_departments (user_id, department_id, created_at)
            SELECT id, department_id, now()
            FROM users
            WHERE department_id IS NOT NULL
            ON CONFLICT DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_user_departments_department_id", table_name="user_departments")
    op.drop_table("user_departments")
    op.drop_index("ix_user_cost_centers_cost_center_id", table_name="user_cost_centers")
    op.drop_table("user_cost_centers")
