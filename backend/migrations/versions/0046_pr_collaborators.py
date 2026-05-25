"""add pr_collaborators M:N table

Revision ID: 0046
Revises: 0045
Create Date: 2026-05-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0046"
down_revision = "0045"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pr_collaborators",
        sa.Column(
            "pr_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("purchase_requisitions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "added_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("pr_id", "user_id", name="pk_pr_collaborators"),
    )
    op.create_index(
        "ix_pr_collaborators_user_id",
        "pr_collaborators",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_pr_collaborators_user_id", table_name="pr_collaborators")
    op.drop_table("pr_collaborators")
